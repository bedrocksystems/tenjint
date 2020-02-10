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

"""This module contains the virtual machine abstractions."""

from . import plugins
from .. import api

import struct

class VirtualMachineBase(plugins.Plugin):
    """Base class for all virtual machines (VMs)."""

    @property
    def phys_mem_size(self):
        """Get the size of the physical memory of the VM.

        Returns
        -------
        int
            The size of the physical memory of the VM.
        """
        return api.tenjint_api_get_ram_size()

    def phys_mem_read(self, addr, size):
        """Read from the VM's physical memory.

        Parameters
        ----------
        addr : int
            The physical address to read from.
        size : int
            The number of bytes to read.

        Returns
        -------
        bytes
            The requested bytes.

        Raises
        ------
        RuntimeError
            If the requested physical memory cannot be read.

        See Also
        --------
        phys_mem_size
        """
        return api.tenjint_api_read_phys_mem(addr, size)

    def phys_mem_write(self, addr, buf):
        """Write to the VM's physical mamory.

        Paramaters
        ----------
        addr : int
            The physical address to write to.
        buf : bytes
            The data to write.

        Raises
        ------
        RuntimeError
            If the requested physical memory cannot be written.
        """
        return api.tenjint_api_write_phys_mem(addr, buf)

    def vtop(self, addr, dtb=None, cpu_num=None):
        """Translate a guest virtual address to a guest physical address.

        Parameters
        ----------
        addr : int
            The virtual address to translate.
        dtb : int, optional
            The directory table base that should be used for the translation. If
            no dtb is provided, the dtb on the given cpu (cpu_num) will be used.
        cpu_num : int, optional
            The number of the CPU that should be used for the translation. If no
            dtb and cpu_num have been specified, cpu_num 0 will be used.

        Raises
        ------
        tenjint.api.api.TranslationError
            If the virtual address connot be translated.
        """
        if dtb is None:
            if cpu_num is None:
                cpu_num = 0
            dtb = self.cpu(cpu_num).page_table_base(addr)
        return api.tenjint_api_vtop(addr, dtb)

    def mem_read(self, addr, size, dtb=None, cpu_num=None):
        """Read virtual memory.

        This function allows to read the guests virtual memory.

        Parameters
        ----------
        addr : int
            The virtual address to read from.
        size : int
            The number of bytes to read.
        dtb : int, optional
            The directory table base that should be used for the read. If
            no dtb is provided, the dtb on the given cpu (cpu_num) will be used.
        cpu_num : int, optional
            The number of the CPU that should be used for the read. If no
            dtb and cpu_num have been specified, cpu_num 0 will be used.

        Returns
        -------
        bytes
            The requested bytes.

        Raises
        ------
        tenjint.api.api.TranslationError
            If the virtual address connot be translated to a physical address.
        RuntimeError
            If the requested physical memory cannot be read.
        """
        paddr = self.vtop(addr, dtb=dtb, cpu_num=cpu_num)
        return self.phys_mem_read(paddr, size)

    def mem_write(self, addr, buf, dtb=None, cpu_num=None):
        """Write virtual memory.

        This function allows to write to the guests virtual memory.

        Parameters
        ----------
        addr : int
            The virtual address to write to.
        buf : bytes
            The data to write.
        dtb : int, optional
            The directory table base that should be used for the write. If
            no dtb is provided, the dtb on the given cpu (cpu_num) will be used.
        cpu_num : int, optional
            The number of the CPU that should be used for the write. If no
            dtb and cpu_num have been specified, cpu_num 0 will be used.

        Returns
        -------
        bytes
            The requested bytes.

        Raises
        ------
        tenjint.api.api.TranslationError
            If the virtual address connot be translated to a physical address.
        RuntimeError
            If the requested physical memory cannot be written.
        """
        paddr = self.vtop(addr, dtb=dtb, cpu_num=cpu_num)
        return self.phys_mem_write(paddr, buf)

    def read_pointer(self, addr, dtb=None, cpu_num=None, width=None):
        """Read pointer from guest memory.

        This function reads a pointer from the guest.  It allows the caller to
        specify either a 4 or an 8 byte width.  If this is omitted, the width
        is queried from the cpu.

        Parameters
        ----------
        addr : int
            The virtual address to read from.
        dtb : int, optional
            The directory table base that should be used for the read.  If
            no dtb is provided, the dtb on the given cpu (cpu_num) will be used.
        cpu_num : int, optional
            The number of the CPU that should be used for the read. If no
            dtb and cpu_num have been specified, cpu_num 0 will be used for the
            read.
        width : int, optional
            The width of the pointer to read.  This value must either be 4 or 8.
            If no width is provided, the cpu specified by cpu_num will be used
            to determine the width.

        Raises
        ------
        RuntimeError
            This is raised if neither a width or cpu_num is specified or if the
            width specified is neither 4 nor 8.
        """
        if width is None:
            if cpu_num is None:
                raise RuntimeError("Unable to determine width without cpu_num")
            width = self.cpu(cpu_num).pointer_width

        if width != 4 and width != 8:
            raise RuntimeError("invalid pointer length")

        buf = self.mem_read(addr, width, dtb=dtb, cpu_num=cpu_num)

        if width == 8:
            rv = struct.unpack("<Q", buf)[0]
        else:
            rv = struct.unpack("<I", buf)[0]

        return rv

    @property
    def cpu_count(self):
        """Obtain the number of vCPUs that the VM has."""
        return api.tenjint_api_get_num_cpus()

    def cpu(self, cpu_num):
        """Get a virtual CPU (vCPU).

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to get.

        Returns
        -------
        object
            An object representing the vCPU for the current architecture of
            the virtual machine.

        Raises
        ------
        ValueError
            If the requested vCPU number does not exists.

        See Also
        --------
        cpu_count
        """
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
    """Virtual machine class for x86-64."""

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
        """Enable the Last Branch Record Stack (LBR).

        Parameters
        ----------
        cpu_num : int, optional
            The vCPU number to enable the LBR on. If no cpu number is provided,
            the LBR will be enabled on all vCPUs.
        """
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
        """Disable the Last Branch Record Stack (LBR).

        Parameters
        ----------
        cpu_num : int, optional
            The vCPU number to disable the LBR on. If no cpu number is provided,
            the LBR will be disabled on all vCPUs.
        """
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
        """Retrieve the Last Branch Record Stack (LBR).

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU whose LBR we want to retrieve.

        Returns
        -------
        tenjint.api.api_x86_64.LBRState
            The LBRState of the vCPU.

        Raises
        ------
        RuntimeError
            If the LBR has not been enabled to the requested vCPU.
        """
        if not self._lbr_enabled[cpu_num]:
            raise RuntimeError("LBR was never enabled for this CPU")
        try:
            rv = self._lbrs[cpu_num]
        except KeyError:
            rv = api.tenjint_api_lbr_get(cpu_num)
            self._lbrs[cpu_num] = rv
        return rv


class VirtualMachineAARCH64(VirtualMachineBase):
    """Virtual machine class for aarch64."""

    _abstract = False
    name = "VirtualMachine"
    arch = api.Arch.AARCH64

    def __init__(self):
        super().__init__()
        self._cpus = dict()

        self._event_manager.add_continue_hook(self._cont_hook)

    def _cont_hook(self):
        self._cpus.clear()
