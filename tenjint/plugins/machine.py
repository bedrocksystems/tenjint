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

from . import plugins
from .. import api

class VirtualMachineBase(plugins.Plugin):
    @property
    def phys_mem_size(self):
        return api.tenjint_api_get_ram_size()

    def phys_mem_read(self, addr, size):
        return api.tenjint_api_read_phys_mem(addr, size)

    def phys_mem_write(self, addr, buf):
        return api.tenjint_api_write_phys_mem(addr, buf)

    def vtop(self, addr, dtb=None, cpu_num=None):
        if dtb is None:
            if cpu_num is None:
                cpu_num = 0
            dtb = self.cpu(cpu_num).page_table_base(addr)
        return api.tenjint_api_vtop(addr, dtb)

    @property
    def cpu_count(self):
        return api.tenjint_api_get_num_cpus()

    def cpu(self, cpu_num):
        if cpu_num >= self.cpu_count:
            raise ValueError("This machine only has {} cpu(s)".format(
                                                                self.cpu_count))

        try:
            rv = self._cpus[cpu_num]
        except KeyError:
            rv = api.tenjint_api_get_cpu_state(cpu_num)
            self._cpus[cpu_num] = rv
        return rv

class VirtualMachineX86_64(VirtualMachineBase):
    _abstract = False
    name = "VirtualMachine"
    arch = api.Arch.X86_64

    def __init__(self):
        super().__init__()
        self._lbr_enabled = [0 for _ in range(self.cpu_count)]
        self._cpus = dict()
        self._lbrs = dict()

        self._event_manager.add_continue_hook(self._cont_hook)

    def _cont_hook(self):
        self._cpus.clear()
        self._lbrs.clear()

    def lbr_enable(self, cpu_num=None):
        enable = False

        if cpu_num is None:
            for i in range(len(self._lbr_enabled)):
                self._lbr_enabled[i] += 1

                if self._lbr_enabled[i] == 1:
                    enable = True
        else:
            self._lbr_enabled[cpu_num] += 1

            if self._lbr_enabled[cpu_num] == 1:
                enable = True

        if enable:
            api.tenjint_api_update_feature_lbr(cpu_num, True, 0)

    def lbr_disable(self, cpu_num=None):
        disable = False

        if cpu_num is None:
            for i in range(len(self._lbr_enabled)):
                self._lbr_enabled[i] -= 1

                if self._lbr_enabled[i] == 0:
                    disable = True
        else:
            self._lbr_enabled[cpu_num] -= 1

            if self._lbr_enabled[cpu_num] == 0:
                disable = True

        if disable:
            api.tenjint_api_update_feature_lbr(cpu_num, False, 0)

    def lbr(self, cpu_num):
        if not self._lbr_enabled[cpu_num]:
            raise RuntimeError("LBR was never enabled for this CPU")
        try:
            rv = self._lbrs[cpu_num]
        except KeyError:
            rv = api.tenjint_api_lbr_get(cpu_num)
            self._lbrs[cpu_num] = rv
        return rv


class VirtualMachineAARCH64(VirtualMachineBase):
    _abstract = False
    name = "VirtualMachine"
    arch = api.Arch.AARCH64

    def __init__(self):
        super().__init__()
        self._cpus = dict()

        self._event_manager.add_continue_hook(self._cont_hook)

    def _cont_hook(self):
        self._cpus.clear()
