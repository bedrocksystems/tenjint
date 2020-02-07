# tenjint - VMI Python Library
#
# Copyright (C) 2020 Bedrock Systems, Inc
# Authors: Sebastian Vogl <sebastian@bedrocksystems.com>
#          Jonas Pfoh <jonas@bedrocksystems.com>
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

"""This module provides plugins for accessing and modifying function arguments.

This module provides plugins that allow to access arguments of function calls,
the function return address, and the function return value. The goal is to
provide a common interface independent from the underlying hardware architecture
and operating system.
"""

from . import plugins
from .. import api

import struct

class FunctionArguments(plugins.Plugin):
    """Base class for all function argument classes.

    This is the base class for all plugins that provide access to the function
    arguments. It defines the interface that all function argument plugins
    implements. This will allow us to use the same code to retrive and modify
    function class independent of the underlying hardware architecture and
    operating system.
    """
    def get_arg(self, cpu_num, nr):
        """Get the nth argument from the given vCPU.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        nr : int
            The number of the argument to get.

        Returns
        -------
        int
            The requested argument.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

    def set_return_value(self, cpu_num, x):
        """Set the return value of a function call.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        x : int
            The value to set.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

    def get_return_address(self, cpu_num):
        """Get the return address of a function call.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

class FunctionArgumentsLinuxX86(FunctionArguments):
    """Implementation for x86 and x86-64 Linux."""
    _abstract = False
    name = "FunctionArguments"
    arch = api.Arch.X86_64
    os = api.OsType.OS_LINUX

    def _get_arg_x64(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        if (nr == 0):
            return cpu.rdi
        elif (nr == 1):
            return cpu.rsi
        elif (nr == 2):
            return cpu.rcx
        elif (nr == 3):
            return cpu.rdx
        elif (nr == 4):
            return cpu.r8
        elif (nr == 5):
            return cpu.r9
        else:
            data = self._vm.mem_read(cpu.rsp - ((nr - 5) * pointer_width),
                                     cpu.pointer_width)
            return struct.unpack("<Q", data)[0]

    def _get_arg_x86(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        data = self._vm.mem_read(cpu.rsp - ((nr + 1) * pointer_width),
                                 cpu.pointer_width)
        return struct.unpack("<I", data)[0]

    def get_arg(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        if cpu.is_ia32e and cpu.is_code_64:
            return self._get_arg_x64(cpu_num, nr)
        elif cpu.is_paging_set and cpu.is_code_32:
            return self._get_arg_x86(cpu_num, nr)

        raise RuntimeError("Unsupported vCPU mode")

    def set_return_value(self, cpu_num, x):
        cpu = self._vm.cpu(cpu_num)
        cpu.rax = x

    def get_return_address(self, cpu_num):
        cpu = self._vm.cpu(cpu_num)
        data = self._vm.mem_read(cpu.rsp, cpu.pointer_width)

        if cpu.is_ia32e and cpu.is_code_64:
            return struct.unpack("<Q", data)[0]
        elif cpu.is_paging_set and cpu.is_code_32:
            return struct.unpack("<I", data)[0]

        raise RuntimeError("Unsupported vCPU mode")

class FunctionArgumentsLinuxAarch64(FunctionArguments):
    """Implementation for Aarch64 and Linux."""
    _abstract = False
    name = "FunctionArguments"
    arch = api.Arch.AARCH64
    os = api.OsType.OS_LINUX

    def get_arg(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        if (nr == 0):
            return cpu.r0
        elif (nr == 1):
            return cpu.r1
        elif (nr == 2):
            return cpu.r2
        elif (nr == 3):
            return cpu.r3
        elif (nr == 4):
            return cpu.r4
        elif (nr == 5):
            return cpu.r5
        elif (nr == 6):
            return cpu.r6
        elif (nr == 7):
            return cpu.r7
        else:
            raise RuntimeError("Unsupported arg number")

    def set_return_value(self, cpu_num, x):
        cpu = self._vm.cpu(cpu_num)
        cpu.r0 = x

    def get_return_address(self, cpu_num):
        cpu = self._vm.cpu(cpu_num)
        return cpu.r30

