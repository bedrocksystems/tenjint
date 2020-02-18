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

    def get_stack_pointer(self, cpu_num):
        """Get the stack pointer on the given vCPU.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.

        Returns
        -------
        int
            The stack pointer

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

    def set_stack_pointer(self, cpu_num, x):
        """Set the stack pointer on the given vCPU.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        x : int
            The new value of the stack pointer.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

    def sub_stack_pointer(self, cpu_num, x):
        """Substract a value from the stack pointer.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        x : int
            The value to substract.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        self.set_stack_pointer(cpu_num, self.get_stack_pointer(cpu_num) - x)

    def _make_room_stack(self, cpu_num, size, alignment=16):
        """Make some room on the stack for an arbitrary value.

        This function will update the stack pointer to point to a location
        that provides enough space for the given number of bytes. In addition,
        it will align the stack to the given boundary.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        size : int
            The number of bytes to make room for.
        alignment : int
            The alignment of the stack.

        Returns
        -------
        int
            The new location of the stack pointer.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        sp = self.get_stack_pointer(cpu_num=cpu_num)
        sp -= size
        sp -= (sp % alignment)

        return sp

    def write_to_stack(self, cpu_num, x, alignment=16):
        """Write data to the stack.

        This function allows you to write some data to the stack. For instance,
        this is helpful to place string or byte arrays on the stack. Once on the
        stack, a pointer to the written data can be passed as an argument to a
        function.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        x : str or bytes
            The data to write.
        alignment : int
            The alignment of the stack.

        Returns
        -------
        int
            A pointer to the beginning of the written data.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        TypeError
            If x is neither a str or bytes.
        """
        if (not type(x) == bytes and not type(x) == str):
            raise TypeError("Argument must be str or bytes")

        # Add zero byte to strings
        if (type(x) == str):
            if (x[-1] != "\x00"):
                x += "\x00"
            x = bytes(x, encoding="ascii")

        sp = self._make_room_stack(cpu_num, len(x), alignment=alignment)
        self._vm.mem_write(sp, x, cpu_num=cpu_num)
        self._logger.debug("Wrote {} to 0x{:x}".format(x, sp))
        self.set_stack_pointer(cpu_num, sp)
        return sp

    def set_arg(self, cpu_num, nr, x):
        """Set an argument on the given CPU.

        This function will set the given argument on the given vCPU.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        nr : int
            The number of the argument to write.
        x : int
            The argument to write.

        Raises
        ------
        ValueError
            If their is not vCPU with this number.
        """
        raise NotImplementedError()

    def get_return_value(self, cpu_num):
        """Get the return value of a function call.

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

    def set_return_value(self, cpu_num, x, update_stack=False):
        """Set the return value of a function call.

        Parameters
        ----------
        cpu_num : int
            The number of the vCPU to use.
        x : int
            The value to set.
        update_stack : bool
            Whether to update the stack pointer. This is useful if we do not
            alter an existing return address, but write a new one.

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

    def set_return_address(self, cpu_num, x):
        """Set the return address of a function call.

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
            return cpu.rdx
        elif (nr == 3):
            return cpu.rcx
        elif (nr == 4):
            return cpu.r8
        elif (nr == 5):
            return cpu.r9
        else:
            data = self._vm.mem_read(cpu.rsp - ((nr - 5) * pointer_width),
                                     cpu.pointer_width, cpu_num=cpu_num)
            return struct.unpack("<Q", data)[0]

    def _get_arg_x86(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        data = self._vm.mem_read(cpu.rsp - ((nr + 1) * pointer_width),
                                 cpu.pointer_width, cpu_num=cpu_num)
        return struct.unpack("<I", data)[0]

    def get_arg(self, cpu_num, nr):
        cpu = self._vm.cpu(cpu_num)

        if cpu.is_ia32e and cpu.is_code_64:
            return self._get_arg_x64(cpu_num, nr)
        elif cpu.is_paging_set and cpu.is_code_32:
            return self._get_arg_x86(cpu_num, nr)

        raise RuntimeError("Unsupported vCPU mode")

    def get_stack_pointer(self, cpu_num):
        return self._vm.cpu(cpu_num).rsp

    def set_stack_pointer(self, cpu_num, x):
        self._vm.cpu(cpu_num).rsp = x

    def _set_arg_x64(self, cpu_num, nr, x):
        cpu = self._vm.cpu(cpu_num)

        if (nr == 0):
            cpu.rdi = x
        elif (nr == 1):
            cpu.rsi = x
        elif (nr == 2):
            cpu.rdx = x
        elif (nr == 3):
            cpu.rcx = x
        elif (nr == 4):
            cpu.r8 = x
        elif (nr == 5):
            cpu.r9 = x
        else:
            data = struct.pack("<Q", x)
            self._vm.mem_write(cpu.rsp - ((nr - 5) * cpu.pointer_width), data,
                               cpu_num=cpu_num)
            self.sub_stack_pointer(cpu_num, 8)

    def _set_arg_x86(self, cpu_num, nr, x):
        cpu = self._vm.cpu(cpu_num)

        data = struct.pack("<I", x)
        data = self._vm.mem_write(cpu.rsp - ((nr + 1) * cpu.pointer_width),
                                  data, cpu_num=cpu_num)
        self.sub_stack_pointer(cpu_num, 4)

    def set_arg(self, cpu_num, nr, x):
        cpu = self._vm.cpu(cpu_num)

        if cpu.is_ia32e and cpu.is_code_64:
            return self._set_arg_x64(cpu_num, nr, x)
        elif cpu.is_paging_set and cpu.is_code_32:
            return self._set_arg_x86(cpu_num, nr, x)

        raise RuntimeError("Unsupported vCPU mode")

    def get_return_value(self, cpu_num):
        return self._vm.cpu(cpu_num).rax

    def set_return_value(self, cpu_num, x):
        cpu = self._vm.cpu(cpu_num)
        cpu.rax = x

    def get_return_address(self, cpu_num):
        cpu = self._vm.cpu(cpu_num)
        data = self._vm.mem_read(cpu.rsp, cpu.pointer_width, cpu_num=cpu_num)

        if cpu.is_ia32e and cpu.is_code_64:
            return struct.unpack("<Q", data)[0]
        elif cpu.is_paging_set and cpu.is_code_32:
            return struct.unpack("<I", data)[0]

        raise RuntimeError("Unsupported vCPU mode")

    def set_return_address(self, cpu_num, x, update_stack=False):
        cpu = self._vm.cpu(cpu_num)

        if cpu.is_ia32e and cpu.is_code_64:
            data = struct.pack("<Q", x)
            if update_stack:
                self.sub_stack_pointer(cpu_num, 8)
        elif cpu.is_paging_set and cpu.is_code_32:
            data = struct.pack("<I", x)
            if update_stack:
                self.sub_stack_pointer(cpu_num, 4)

        self._vm.mem_write(cpu.rsp, data, cpu_num=cpu_num)

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

    def get_stack_pointer(self, cpu_num):
        cpu = self._vm.cpu(cpu_num)

        if cpu.el == 0:
            return cpu.sp_el0
        elif cpu.el == 1:
            return cpu.sp_el1

        raise RuntimeError("Unsupported EL ({})".format(cpu.el))

    def set_stack_pointer(self, cpu_num, x):
        cpu = self._vm.cpu(cpu_num)

        if cpu.el == 0:
            cpu.sp_el0 = x
            cpu.r31 = x
        elif cpu.el == 1:
            cpu.sp_el1 = x
            cpu.r31 = x
        else:
            raise RuntimeError("Unsupported EL ({})".format(cpu.el))

    def set_arg(self, cpu_num, nr, x):
        cpu = self._vm.cpu(cpu_num)

        if (nr == 0):
            cpu.r0 = x
        elif (nr == 1):
            cpu.r1 = x
        elif (nr == 2):
            cpu.r2 = x
        elif (nr == 3):
             cpu.r3 = x
        elif (nr == 4):
            cpu.r4 = x
        elif (nr == 5):
            cpu.r5 = x
        elif (nr == 6):
            cpu.r6 = x
        elif (nr == 7):
            cpu.r7 = x
        else:
            raise RuntimeError("Unsupported arg number")

    def get_return_value(self, cpu_num):
        return self._vm.cpu(cpu_num).r0

    def set_return_value(self, cpu_num, x):
        cpu = self._vm.cpu(cpu_num)
        cpu.r0 = x

    def get_return_address(self, cpu_num):
        cpu = self._vm.cpu(cpu_num)
        return cpu.r30

    def set_return_address(self, cpu_num, x, update_stack=False):
        cpu = self._vm.cpu(cpu_num)
        cpu.r30 = x

