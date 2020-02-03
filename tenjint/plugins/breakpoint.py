# tenjint - VMI Python Library
#
# Copyright (C) 2020 Bedrock Systems, Inc
# Authors: Jonas Pfoh <jonas@bedrocksystems.com>
#          Sebastian Vogl <sebastian@bedrocksystems.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""This module implements breakpoints."""

from . import plugins
from .. import api
from .. import event

class Breakpoint(object):
    """This class represents a breakpoint.

    An object of this class represents a single requested BP.  It handles the
    automatic removal and insertion of the underlying QEMU breakpoint if the
    page is written/read?
    """
    def __init__(self, gpa, event_manager, slp_service, logger):
        super().__init__()
        self.gpa = gpa
        self._event_manager = event_manager
        self._slp_service = slp_service
        self._logger = logger
        self.is_set = False

        gfn = gpa >> api.PAGE_SHIFT
        self._slp_rw_cb = event.EventCallback(self._slp_rw_cb_func,
                                              "SystemEventSLP",
                                              {"gfn": gfn, "num_pages": 1,
                                               "trap_r": True, "trap_w": True,
                                               "trap_x": False})
        self._slp_x_cb = event.EventCallback(self._slp_x_cb_func,
                                             "SystemEventSLP",
                                             {"gfn": gfn, "num_pages": 1,
                                              "trap_r": False, "trap_w": False,
                                              "trap_x": True})

    def _set_bp(self):
        api.tenjint_api_update_feature_debug(cpu_num=None,
                                            enable=True, gpa=self.gpa)
        self._logger.debug("Breakpoint: bp set on 0x{:x}".format(self.gpa))
        self.is_set = True

    def set_bp(self):
        """Set the breakpoint

        This function is called to set the breakpoint.  This should be called
        once.  Any subsequent insertions and removals of the underlying QEMU
        breakpoint are handled internally.
        """
        try:
            self._slp_service.update_permissions(self.gpa, r=False, w=False, x=True)
        except api.UpdateSLPError:
            self._logger.warning("Breakpoint: slp update perm failed")
            # this is safe as the kernel will default any new pages to
            # X-only since we are requesting rw violations
        self._event_manager.request_event(self._slp_rw_cb)
        self._set_bp()

    def _unset_bp(self):
        api.tenjint_api_update_feature_debug(cpu_num=None,
                                            enable=False, gpa=self.gpa)
        self._logger.debug("Breakpoint: bp removed on 0x{:x}".format(self.gpa))
        self.is_set = False

    def unset_bp(self):
        """Unset the breakpoint

        This function is called to unset the breakpoint.  This should be called
        once.
        """
        if self.is_set:
            self._unset_bp()
            self._event_manager.cancel_event(self._slp_rw_cb)
        else:
            self._event_manager.cancel_event(self._slp_x_cb)

    def _slp_rw_cb_func(self, event):
        self._logger.debug("Breakpoint: rw callback ob 0x{:x}".format(event.gva))
        self._unset_bp()
        self._slp_service.update_permissions(self.gpa, r=True, w=True, x=False)
        self._event_manager.cancel_event(self._slp_rw_cb)
        self._event_manager.request_event(self._slp_x_cb)

    def _slp_x_cb_func(self, event):
        self._logger.debug("Breakpoint: x callback ob 0x{:x}".format(event.gva))
        self._event_manager.cancel_event(self._slp_x_cb)
        self._event_manager.request_event(self._slp_rw_cb)
        self._slp_service.update_permissions(self.gpa, r=False, w=False, x=True)
        self._set_bp()

class BreakpointPlugin(plugins.EventPlugin):
    """Breakpoint Service

    This plugin implements the Breakpoint service and is responsible for setting
    and removing breakpoints.  The breakpoints are set on a specificfied GPA and
    are hidden by this service.
    """
    _abstract = False
    produces = [api.SystemEventBreakpoint]

    def __init__(self):
        super().__init__()
        self._request_id_cntr = 0
        self._requests = dict()

        self._ss_service = self._service_manager.get("SingleStepPlugin")
        self._slp_service = self._service_manager.get("SLPPlugin")

        self._cb_bp = event.EventCallback(self._cb_func_bp, "SystemEventBreakpoint")
        self._event_manager.request_event(self._cb_bp, send_request=False)

        self._ss = list()
        for i in range(self._vm.cpu_count):
            self._ss.append(event.EventCallback(self._cb_func_ss,
                                            event_name="SystemEventSingleStep",
                                            event_params={"cpu_num":i}))
        self._cb_ss = event.EventCallback(self._cb_func_ss, "SystemEventSingleStep")
        self._event_manager.request_event(self._cb_ss, send_request=False)

    def uninit(self):
        super().uninit()
        for _, bp in self._requests.items():
            bp.unset_bp()
        self._requests = dict()

        self._event_manager.cancel_event(self._cb_bp)
        self._cb_bp = None

        self._event_manager.cancel_event(self._cb_ss)
        self._cb_ss = None

    def request_event(self, event_cls, **kwargs):
        """Request Breakpoint event

        This function is called by the event manager when a
        (:py:class:`api.SystemEventBreakpoint`) is requested.  The event params
        are specified in the (:py:class:`api.SystemEventBreakpoint`) class.
        """
        [gpa] = event_cls.parse_request(**kwargs)

        request_id = self._request_id_cntr
        self._request_id_cntr += 1
        bp = Breakpoint(gpa, self._event_manager, self._slp_service, self._logger)
        self._requests[request_id] = bp
        bp.set_bp()
        return request_id

    def cancel_event(self, request_id):
        """Cancel Breakpoint event

        This function is called by the event manager when a
        (:py:class:`api.SystemEventBreakpoint`) is canceled.
        """
        bp = self._requests.pop(request_id)
        bp.unset_bp()

    def _cb_func_bp(self, event):
        # Activate single stepping to step over the BP
        # BPs will be automatically disabled by QEMU when we single step
        if self._ss[event.cpu_num].active:
            return
        self._event_manager.request_event(self._ss[event.cpu_num])

    def _cb_func_ss(self, event):
        if self._ss[event.cpu_num].active:
            self._event_manager.cancel_event(self._ss[event.cpu_num])
        else:
            last_gva = self._ss_service.last_ss_gva(event.cpu_num)
            last_gpa = self._vm.vtop(last_gva, cpu_num=event.cpu_num)
            for _, bp in self._requests.items():
                if bp.gpa == last_gpa:
                    evt = api.SystemEventBreakpoint(event.cpu_num,
                                                    last_gva,
                                                    last_gpa)
                    self._event_manager.put_event(evt)
