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

from enum import Enum

from .. import event

class OsType(Enum):
    """The guest operating system types."""
    OS_WIN = 0
    OS_LINUX = 1

PAGE_SHIFT = 12
PAGE_SIZE = 4096

# Global variable os. Holds the current os. This is set by the os plugin.
os = None
"""Global variable for the guest operating system.

This variable holds an object that represents the current guest operating
system. The variable is set by the
:py:class:`tenjint.plugins.operatingsystem.OperatingSystemBase` plugin.
"""

class QemuFeatureError(Exception):
    pass

class TranslationError(Exception):
    pass

class UpdateSLPError(Exception):
    pass

class SystemEventVmShutdown(event.Event):
    """Emitted before the VM is destroyed.

    This evemt is emitted when the VM finished execution and is about to be
    destroyed. This is the last chance to collect information.
    """
    pass

class SystemEventVmReady(event.Event):
    """Emitted when the VM is ready to run.

    This event is emitted when the VM is ready to run. It is the last chance
    to setup callbacks before the execution of the VM begins.
    """
    pass

class SystemEventVmStop(event.Event):
    """Emitted when the VM is paused."""
    pass

class SystemEventBreakpoint(event.CpuEvent):
    """Emitted when a breakpoint is hit within the guest."""
    params = {
                "gpa": None,
              }

    def __init__(self, cpu_num, gva, gpa):
        super().__init__(cpu_num)
        self.gva = gva
        self.gpa = gpa

    def __str__(self):
        return ("SystemEventBreakpoint: cpu={}, gva=0x{:x}, gpa=0x{:x}"
                "".format(self.cpu_num, self.gva, self.gpa))

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False

        gpa = cb_params.get("gpa", cls.params["gpa"])

        if gpa is None:
            return True

        if gpa == event.gpa:
            return True

        return False

class SingleStepMethod(Enum):
    """The various single stepping methods that the system supports."""
    DEBUG = 0
    MTF = 1

class SystemEventSingleStep(event.CpuEvent):
    """Emitted after a single step was executed."""
    params = {
                "cpu_num": None,
                "method": None
              }

    def __init__(self, cpu_num, method):
        super().__init__(cpu_num)
        self.method = method

    def __str__(self):
        return ("SystemEventSingleStep: {}: cpu={}".format(self.method,
                                                           self.cpu_num))

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False
        cpu_num = cb_params.get("cpu_num", cls.params["cpu_num"])
        method = cb_params.get("method", cls.params["method"])

        if (cpu_num is not None and
                cpu_num != event.cpu_num):
            return False
        if (method is not None and
                method != event.method):
            return False
        return True
