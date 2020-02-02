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

import struct

from . import plugins
from .. import api
from .. import config

from rekall.session import InteractiveSession
from rekall.plugins.addrspaces import tenjint
from rekall.plugin import PluginError

class SymbolResolutionError(Exception):
    pass

class OperatingSystemConfig(config.ConfigMixin):
    _config_options = [
        {
            "name": "rekall_profile", "default": None,
            "help": "The profile string to pass to the Rekall session."
        },
    ]

class OperatingSystemBase(plugins.Plugin):
    session = None
    _config_values = None

    @classmethod
    def load(cls, **kwargs):
        if cls.session is None:
            if cls._config_values is None:
                config = OperatingSystemConfig()
                cls._config_values = config._config_values

            profile = cls._config_values["rekall_profile"]
            session = InteractiveSession(session_name="interrupt",
                                         profile=profile)
            session.session_list.append(session)

            session.SetParameter("cache", "tenjint")
            addr_space = tenjint.TenjintAddressSpace(session=session)
            session.physical_address_space = addr_space

            if session.GetParameter("mode_windows"):
                api.os = api.OsType.OS_WIN
            elif session.GetParameter("mode_linux"):
                api.os = api.OsType.OS_LINUX
            else:
                raise RuntimeError("Unable to determine guest OS type.")

            rekall_arch_str = session.profile.metadata("arch")
            if rekall_arch_str == "AMD64":
                api.arch = api.Arch.X86_64
            elif rekall_arch_str == "I386":
                api.arch = api.Arch.X86
            elif rekall_arch_str == "ARM":
                api.arch = api.Arch.AARCH32
            elif rekall_arch_str == "ARM64":
                api.arch = api.Arch.AARCH64
            else:
                raise RuntimeError("Unexpected guest kernel architecture")

            try:
                session.plugins.load_as().GetVirtualAddressSpace()
            except PluginError as e:
                for item in session.plugins.find_kaslr(
                        scan_whole_physical_space=True):
                    if item["Valid"]:
                        find_dtb = session.plugins.find_dtb()
                        session.kernel_address_space = find_dtb.GetAddressSpaceImplementation()(
                                base=session.physical_address_space, dtb=item["DTB"], session=session,
                                profile=session.profile, kernel_slide=item["kernel_slide"])
                        session.SetCache("kernel_slide", item["kernel_slide"], volatile=False)
                        break
                if not session.kernel_address_space:
                    raise e
                session.SetCache("default_address_space",
                                 session.kernel_address_space,
                                 volatile=False)

            cls.session = session

        # Now load
        return super().load(**kwargs)

    def __init__(self):
        super().__init__()
        self._event_manager.add_continue_hook(self._cont_hook)

    def uninit(self):
        super().uninit()
        self._event_manager.remove_continue_hook(self._cont_hook)

    def _cont_hook(self):
        self.session.cache.ClearVolatile()

    def process(self, pid=None, dtb=None):
        if pid is None and dtb is None:
            raise ValueError("you must specify a pid or dtb")

        for proc in self.session.plugins.pslist().filter_processes():
            if pid is not None and pid == proc.pid:
                return proc
            elif dtb is not None and dtb == proc.dtb:
                return proc

        return None

    def vtop(self, vaddr, pid=None, dtb=None, kernel_address_space=False):
        if kernel_address_space:
            return self.session.kernel_address_space.vtop(vaddr)
        if pid is not None or dtb is not None:
            proc = self.process(pid=pid, dtb=dtb)

            if proc is None:
                raise ValueError("process not found")

            return proc.get_process_address_space().vtop(vaddr)

        return self.session.default_address_space.vtop(vaddr)

    def get_symbol_address(self, symbol):
        rv = self.session.address_resolver.get_address_by_name(symbol)
        if rv == None:
            raise SymbolResolutionError(rv.reason)
        return rv

    def get_nearest_symbol_by_address(self, address):
        """Get symbols by address.

        This function will attempt to look up the nearest symbol based on an
        address. If multiple symbols are located at an equal distance from the
        address, all of them will be returned.

        Parameters
        ----------
        address : int
            The address to use for the search.

        Returns
        -------
        list
            The nearest symbols for the given address. If no symbol can be
            found an empty list will be returned.
        """
        return self.session.address_resolver.get_nearest_constant_by_address(
                                                                     address)[1]

class OperatingSystemWinX86_64(OperatingSystemBase):
    _abstract = False
    name = "OperatingSystem"
    arch = api.Arch.X86_64
    os = api.OsType.OS_WIN

class OperatingSystemLinux(OperatingSystemBase):
    _abstract = False
    name = "OperatingSystem"
    os = api.OsType.OS_LINUX

    def __init__(self):
        self._per_cpu = None
        self._per_cpu_current_task_offset = None
        self._pointer_width = None
        self._struct_ptr_fmt = None
        super().__init__()

    @property
    def pointer_width(self):
        if self._pointer_width is None:
            if api.arch == api.Arch.X86_64 or api.arch == api.Arch.AARCH64:
                self._pointer_width = 8
            else:
                self._pointer_width = 4
        return self._pointer_width

    def read_kernel_pointer(self, addr):
        if self._struct_ptr_fmt is None:
            if self.pointer_width == 4:
                self._struct_ptr_fmt = "<L"
            else:
                self._struct_ptr_fmt = "<Q"
        return struct.unpack(self._struct_ptr_fmt,
                             self.session.kernel_address_space.read(addr,
                                                         self.pointer_width))[0]

    @property
    def per_cpu(self):
        if self._per_cpu is None:
            base = self.session.address_resolver.get_address_by_name(
                                                       "linux!__per_cpu_offset")
            self._per_cpu = list()
            for offset in range(0, (self._vm.cpu_count * self.pointer_width),
                                                            self.pointer_width):
                self._per_cpu.append(self.read_kernel_pointer(base+offset))
        return self._per_cpu

    def current_process(self, cpu_num):
        if self._per_cpu_current_task_offset is None:
            self._per_cpu_current_task_offset = self.session.profile.get_constant("current_task")
        task_struct_address = self.read_kernel_pointer(
                    (self.per_cpu[cpu_num] + self._per_cpu_current_task_offset))
        return self.session.profile.task_struct(task_struct_address)
