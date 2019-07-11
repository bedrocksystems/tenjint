from . import plugins
from .. import api
from .. import event

class SLPPermUpdateViolation(Exception):
    pass

class SLPPlugin(plugins.EventPlugin):
    """SLP Service

    This plugin implements the SLP service and is responsible for handling
    requests to update page permissions as well as requests for SLP permission
    violations.

    NOTE: This service does not concern itself with merging requests for
    callbacks as this is done in the kernel.
    """
    _abstract = False
    produces = [api.SystemEventSLP]

    def __init__(self):
        super().__init__()
        self._request_id_cntr = 0
        self._requests = dict()
        self._slp_cb = event.EventCallback(self._slp_cb_func, "SystemEventSLP",
                                           {"global_req": True, "trap_r": True,
                                            "trap_w": True, "trap_x": True})
        self._event_manager.request_event(self._slp_cb, send_request=False)
        self._event_manager.add_continue_hook(self._cont_hook)
        self._perm_requests = dict()
        self._slp_events = list()
        self._rwx_perm_request = [None] * self._vm.cpu_count
        self._ss_cb = list()
        for i in range(self._vm.cpu_count):
            self._ss_cb.append(event.EventCallback(self._ss_cb_func,
                                                   "SystemEventSingleStep",
                                                   {"cpu_num":i}))

    def uninit(self):
        super().uninit()
        for _, value in self._requests.items():
            (cpu_num, global_req, gfn, num_pages, trap_r, trap_w, trap_x) = value
            api.tenjint_api_update_feature_slp(cpu_num, False, global_req, gfn,
                                              num_pages, trap_r, trap_w, trap_x)
        self._requests = dict()

        self._event_manager.cancel_event(self._slp_cb)
        self._slp_cb = None

        self._event_manager.remove_continue_hook(self._cont_hook)

    def request_event(self, event_cls, **kwargs):
        """Request SLP violation event

        This function is called by the event manager when a
        (:py:class:`api.SystemEventSLP`) is requested.
        """
        [cpu_num, global_req, gfn, num_pages,
         trap_r, trap_w, trap_x] = event_cls.parse_request(**kwargs)

        request_id = self._request_id_cntr
        self._request_id_cntr += 1
        api.tenjint_api_update_feature_slp(cpu_num, True, global_req, gfn,
                                          num_pages, trap_r, trap_w, trap_x)
        self._requests[request_id] = (cpu_num, global_req, gfn, num_pages,
                                      trap_r, trap_w, trap_x)
        return request_id

    def cancel_event(self, request_id):
        """Cancel SLP violation event

        This function is called by the event manager when a
        (:py:class:`api.SystemEventSLP`) is canceled.
        """
        (cpu_num, global_req, gfn, num_pages, trap_r,
            trap_w, trap_x) = self._requests.pop(request_id)
        api.tenjint_api_update_feature_slp(cpu_num, False, global_req, gfn,
                                          num_pages, trap_r, trap_w, trap_x)

    def _slp_mutex_violation(self, prev_perms, req_perms):
        merge = (req_perms[0] or prev_perms[0],
                 req_perms[1] or prev_perms[1],
                 req_perms[2] or prev_perms[2])
        if merge[1] and merge[2]:
            return True
        return False

    def update_permissions(self, gpa, r=False, w=False, x=False):
        """Update page permissions for a given GPA

        This function allows the caller to request page permissions to be
        updated.

        Parameters
        ----------
        gpa : int
            The GPA for which permissions are requested
        r : bool
            Whether the page should be readable
        w : bool
            Whether the page should be writeable
        x : bool
            Whether the page should be executable

        Raises
        ------
        SLPPermUpdateViolation
            If the call violates the W/X mutual exclusion rule
        """
        gfn = gpa >> api.PAGE_SHIFT
        req_perms = (r, w, x, True)
        if gfn in self._perm_requests:
            prev_perms = self._perm_requests[gfn]
            if self._slp_mutex_violation(prev_perms, req_perms):
                raise SLPPermUpdateViolation("W/X mutual exclusion violated")
            self._perm_requests[gfn] = (req_perms[0] or prev_perms[0],
                                        req_perms[1] or prev_perms[1],
                                        req_perms[2] or prev_perms[2],
                                        False)
        else:
            api.tenjint_api_slp_update(gpa, r=req_perms[0], w=req_perms[1], x=req_perms[2])
            self._perm_requests[gfn] = req_perms

    def _slp_cb_func(self, event):
        self._slp_events.append(event)

    def _ss_cb_func(self, event):
        (gfn, (r, w, x)) = self._rwx_perm_request[event.cpu_num]
        self.update_permissions(gfn << api.PAGE_SHIFT, r=r, w=w, x=x)
        self._rwx_perm_request[event.cpu_num] = None
        self._disable_single_step(event.cpu_num)

    def _enable_single_step(self, cpu_num):
        self._event_manager.request_event(self._ss_cb[cpu_num])

    def _disable_single_step(self, cpu_num):
        self._event_manager.cancel_event(self._ss_cb[cpu_num])

    def _merge_event_perms(self):
        for event in self._slp_events:
            gfn = event.gpa >> api.PAGE_SHIFT
            if event.rwx:
                if self._rwx_perm_request[event.cpu_num] is not None:
                    raise RuntimeError("Unexpected second RWX on same CPU")
                if gfn in self._perm_requests:
                    self._rwx_perm_request[event.cpu_num] = (gfn, self._perm_requests[gfn])
                else:
                    self._rwx_perm_request[event.cpu_num] = (gfn, (True, True, False))
                self._perm_requests[gfn] = (True, True, True, False)
                self._enable_single_step(event.cpu_num)
            else:
                if gfn not in self._perm_requests:
                    if event.r or event.w:
                        self._perm_requests[gfn] = (True, True, False, False)
                    else:
                        self._perm_requests[gfn] = (True, False, True, False)

    def _cont_hook(self):
        self._merge_event_perms()
        for gfn, perms in self._perm_requests.items():
            if not perms[3]:
                gpa = gfn << api.PAGE_SHIFT
                api.tenjint_api_slp_update(gpa, r=perms[0], w=perms[1], x=perms[2])
        self._slp_events.clear()
        self._perm_requests.clear()
