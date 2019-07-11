"""Python API for aarch64

This file contains all python definitions (see tenjint_aarch64.pyx for the Cython
definitions of the API) that are specific for aarch64.
"""
from enum import Enum

from . import api

from .. import event

class Aarch64TsRegs(Enum):
    TTBR0 = 0
    TTBR1 = 1
    TCR = 2

class SystemEventTaskSwitch(event.CpuEvent):
    """Emitted when a task switch occurs."""
    params = {
                "cpu_num": None,
                "reg": Aarch64TsRegs.TTBR0,
              }

    def __init__(self, cpu_num, reg, old_val, new_val):
        super().__init__(cpu_num)
        self.reg = reg
        self.old_val = old_val
        self.new_val = new_val

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False

        reg = cb_params.get("reg", cls.params["reg"])

        if reg == event.reg:
            return True
        return False

    def __str__(self):
        return ("SystemEventTaskSwitch: cpu={}, reg={}, old_val=0x{:x}, "
                "new_val=0x{:x}".format(self.cpu_num, self.reg, self.old_val,
                                        self.new_val))

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
        return ("SystemEventSLP: cpu={}, gva=0x{:x}, gpa=0x{:x}, r={}, w={}, "
                "x={}{}".format(self.cpu_num, self.gva, self.gpa, self.r,
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
