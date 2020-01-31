"""Python API for x86-64

This file contains all python definitions (see tenjint_x86_64.pyx for the Cython
definitions of the API) that are specific for x86-64.
"""
from . import api
from .. import event

class LBRState(object):
    """Represents the state of the LBR."""
    def __init__(self, tos, lbr_from, lbr_to):
        super().__init__()
        self.tos = tos
        self.lbr_from = lbr_from
        self.lbr_to = lbr_to
        self.size = min(len(self.lbr_from), len(self.lbr_to))

    def __repr__(self):
        result = "LBR State - TOS: {}\n".format(self.tos)
        result += "{}\n".format("-" * 46)
        for i in range(0, self.size):
            cur = (self.tos + i) % self.size
            result += "[{:2d}]  0x{:16x} -> 0x{:16x}\n".format(cur,
                                                             self.lbr_from[cur],
                                                             self.lbr_to[cur])
        return result

class SystemEventTaskSwitch(event.CpuEvent):
    """Emitted when a task switch occurs."""
    params = {
                "dtb": None,
                "incoming": True,
                "outgoing": True
              }

    def __init__(self, cpu_num, incoming_dtb, outgoing_dtb):
        super().__init__(cpu_num)
        self.incoming_dtb = incoming_dtb
        self.outgoing_dtb = outgoing_dtb

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False

        dtb = cb_params.get("dtb", cls.params["dtb"])
        incoming = cb_params.get("incoming", cls.params["incoming"])
        outgoing = cb_params.get("outgoing", cls.params["outgoing"])

        if dtb is not None:
            if incoming:
                if dtb == event.incoming_dtb:
                    return True
            if outgoing:
                if dtb == event.outgoing_dtb:
                    return True
            return False
        return True

    def __str__(self):
        return ("SystemEventTaskSwitch: cpu={}, outgoing_dtb=0x{:x}, "
                "incoming_dtb=0x{:x}".format(self.cpu_num, self.outgoing_dtb,
                                        self.incoming_dtb))

class SystemEventSLP(event.CpuEvent):
    """Emitted when an second level pagaing violation occurs."""
    params = {
                "cpu_num": None,
                "global_req": False,
                "gfn": None,
                "num_pages": None,
                "trap_r": False,
                "trap_w": False,
                "trap_x": False
              }

    def __init__(self, cpu_num, gva, gpa, r, w, x, rwx):
        super().__init__(cpu_num)
        self.gva = gva
        self.gpa = gpa
        self.r = r
        self.w = w
        self.x = x
        self.rwx = rwx

    def __str__(self):
        gva = "-" if self.gva is None else "0x{:x}".format(self.gva)
        return ("SystemEventSLP: cpu={}, gva={}, gpa=0x{:x}, r={}, w={}, "
                "x={}{}".format(self.cpu_num, gva, self.gpa, self.r,
                                self.w, self.x," RWX" if self.rwx else ""))

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False

        global_req = cb_params.get("global_req", cls.params["global_req"])
        gfn = cb_params.get("gfn", cls.params["gfn"])
        num_pages = cb_params.get("num_pages", cls.params["num_pages"])
        trap_r = cb_params.get("trap_r", cls.params["trap_r"])
        trap_w = cb_params.get("trap_w", cls.params["trap_w"])
        trap_x = cb_params.get("trap_x", cls.params["trap_x"])

        if global_req:
            if event.r and trap_r:
                return True
            elif event.w and trap_w:
                return True
            elif event.x and trap_x:
                return True
        elif gfn is not None and num_pages is not None and num_pages > 0:
            min_range = gfn << api.PAGE_SHIFT
            max_range = ((gfn + (num_pages - 1)) << api.PAGE_SHIFT) | 0xfff
            if event.gpa >= min_range and event.gpa <= max_range:
                if event.r and trap_r:
                    return True
                elif event.w and trap_w:
                    return True
                elif event.x and trap_x:
                    return True
        return False
