
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

"""This module provides function call injection.

This module provides plugin classes that allow to inject function calls into
the guest. It depends on the :py:mod:`fargs` module.
"""

from . import plugins
from .. import api
from .. import event

import struct

class FunctionCallInjectionEvent(event.Event):
    params = {
        "symbol": None,
        "gva": None,
        "args": None,
        "pid": None,
        "kernel": None,
    }

    def __init__(self, symbol, gva, args, pid):
        super().__init__()

        self.symbol = symbol
        self.gva = gva
        self.args = args
        self.pid = pid

    @classmethod
    def filter(cls, cb_params, event):
        if type(event) != cls:
            return False

        sym = cb_params.get("symbol", cls.params["symbol"])
        gva = cb_params.get("gva", cls.params["gva"])
        args = cb_params.get("args", cls.params["args"])
        pid = cb_params.get("pid", cls.params["pid"])

        if sym is not None and sym != event.symbol:
            return False

        if gva is not None and gva != event.gva:
            return False

        if args is not None:
            e_args = event.args
            for i, a in enumerate(args):
                if i >= len(e_args):
                    return False
                if a != e_args[i]:
                    return False

        if pid is not None and pid != event.pid:
            return False

        return True

class FunctionCallInjectionBase(plugins.EventPlugin):
    """Base plugin for all function call injections."""

    _abstract = True
    name = "FunctionCallInjection"
    produces = [FunctionCallInjectionEvent]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # gpa, tid/pid, rsp, callback, symbol, gva, args, state
        self._running_injections = []

        # Symbol, gva, args, tid/pid, kernel
        self._waiting_injections = []

        # symbol, gva, args, tid/pid, gpa, cb, kernel
        self._armed_injections = []

        self._syscall_cb = None

    def _armed_cb(self, e):
        proc = self._os.current_process(cpu_num=e.cpu_num)
        ctid = proc.tid if hasattr(proc, "tid") else proc.pid
        for i, (symbol, gva, args, tid, gpa, cb, kernel) in enumerate(
                                                        self._armed_injections):
            if kernel:
                self._logger.debug("Injecting kernel function call...")
                self._event_manager.cancel_event(cb)
                self._armed_injections.pop(i)
                self._inject(e.cpu_num, symbol, gva, *args)
                break
            elif e.gpa == gpa and ctid == tid:
                self._logger.debug("Injecting user function call...")
                self._event_manager.cancel_event(cb)
                self._armed_injections.pop(i)
                self._inject(e.cpu_num, symbol, gva, *args)
                break

    def _inject_bp_cb(self, e):
        """Called when an function call injection returns."""
        self._logger.debug("Injection BP callback 0x{:x}".format(e.gpa))

        # Get data
        cpu = self._vm.cpu(e.cpu_num)
        proc = self._os.current_process(cpu_num=e.cpu_num)
        tid = proc.tid if hasattr(proc, "tid") else proc.pid
        sp = self._fargs.get_stack_pointer(e.cpu_num)
        ret = self._fargs.get_return_value(e.cpu_num)
        injection = None

        # Find injection
        for i, x in enumerate(self._running_injections):
            self._logger.debug("GPA {:x} <-> {:x}, TID {} <-> {}, "
                               "RSP {:x} <-> {:x}".format(x[0], e.gpa, x[1],
                                                          tid, x[2], sp))
            if (x[0] == e.gpa and x[1] == tid and
                (x[2] >= sp and x[2] < sp + 0x1000)):
                injection = self._running_injections.pop(i)
                break

        if injection is None:
            return

        self._logger.debug("Injection for function '{}' complete ({}).".format(
                                                                  injection[4],
                                                                  ret))
        # Cancel event
        self._event_manager.cancel_event(injection[3])

        # Restore state
        cpu.restore_state(injection[7])

        # Emit event
        evt = FunctionCallInjectionEvent(injection[4], injection[5],
                                         injection[6], proc.pid)
        self._event_manager.put_event(evt)

    def _inject(self, cpu_num, symbol, gva, *args):
        """Performs the actual injection."""
        self._logger.debug("Injecting function call to '{}'...".format(symbol))

        # Get CPU
        cpu = self._vm.cpu(cpu_num)

        # Save state
        state = cpu.save_state()

        # Get data
        proc = self._os.current_process(cpu_num=cpu_num)
        tid = proc.tid if hasattr(proc, "tid") else proc.pid
        sp = self._fargs.get_stack_pointer(cpu_num)
        ip = cpu.instruction_pointer
        ip_gpa = self._vm.vtop(ip, cpu_num=cpu_num)
        self._logger.debug("RET set to {:#x}".format(ip))

        # Write args
        _args = []
        for a in args:
            if type(a) == str or type(a) == bytes:
                _args.append(self._fargs.write_to_stack(cpu_num, a))
            elif type(a) == list:
                tmp = b""
                f = "<Q" if cpu.pointer_width == 8 else "<I"
                for e in a:
                    if type(e) == str:
                        tmp += struct.pack(f,
                                        self._fargs.write_to_stack(cpu_num, e))
                        self._logger.debug(tmp)
                    else:
                        raise RuntimeError("only list of strings are supported")
                tmp += struct.pack(f, 0)
                _args.append(self._fargs.write_to_stack(cpu_num, tmp))
            else:
                _args.append(a)

        # Set args
        for i, a in enumerate(_args):
            self._fargs.set_arg(cpu_num, i, a)

        # Set ret
        self._fargs.set_return_address(cpu_num, ip, update_stack=True)

        # Set rip
        cpu.rip = gva
        self._logger.debug("Set RIP to {:#x}".format(gva))

        # Set BP
        cb = event.EventCallback(self._inject_bp_cb,
                                 event_name="SystemEventBreakpoint",
                                 event_params={"gpa": ip_gpa})

        # Store
        self._running_injections.append((ip_gpa, tid, sp, cb, symbol, gva,
                                         args, state))

        # Set BP
        self._event_manager.request_event(cb)

    def request_event(self, event_cls, **kwargs):
        """Request a function call injection event."""
        if "gva" in kwargs:
            gva = kwargs["gva"]
        else:
            gva = self._os.get_symbol_address(kwargs["symbol"])

        symbol = kwargs.get("symbol", None)
        pid = kwargs.get("pid", None)
        args = kwargs.get("args", [])
        kernel = kwargs.get("kernel", False)

        self._waiting_injections.append((symbol, gva, args, pid, kernel))
        self._install_syscall_cb()

class FunctionCallInjectionLinuxX86(FunctionCallInjectionBase):
    """Function call injection for Linux on x86"""

    _abstract = False
    arch = api.Arch.X86_64
    os = api.OsType.OS_LINUX

    def _install_syscall_cb(self):
        if self._syscall_cb is not None and self._syscall_cb.active:
            return

        if self._syscall_cb is None:
            vaddr = self._os.get_symbol_address("linux!entry_SYSCALL_64")
            paddr = self._os.vtop(vaddr, kernel_address_space=True)
            self._syscall_cb = event.EventCallback(self._syscall_bp,
                                 event_name="SystemEventBreakpoint",
                                 event_params={"gpa": paddr})

        if not self._syscall_cb.active:
            # Request
            self._event_manager.request_event(self._syscall_cb)

    def _syscall_bp(self, e):
        proc = self._os.current_process(cpu_num=e.cpu_num)
        ctid = proc.tid if hasattr(proc, "tid") else proc.pid

        new_waiting = []
        for (symbol, gva, args, tid, kernel) in self._waiting_injections:
            if kernel:
                self._logger.debug("Setting userspace BP for syscall {}"
                                   "".format(self._vm.cpu(e.cpu_num).rax))
                # Install cb
                vaddr = self._os.get_symbol_address("linux!do_syscall_64")
                gpa = self._os.vtop(vaddr, kernel_address_space=True)
                cb = event.EventCallback(self._armed_cb,
                                         event_name="SystemEventBreakpoint",
                                         event_params={"gpa": gpa})

                self._armed_injections.append((symbol, gva, args, tid, gpa, cb,
                                               kernel))
                self._event_manager.request_event(cb)
            elif (tid is None or ctid == tid):
                self._logger.debug("Setting userspace BP for syscall {}"
                                   "".format(self._vm.cpu(e.cpu_num).rax))
                # Install cb
                gpa = self._vm.vtop(self._vm.cpu(e.cpu_num).rcx,
                                    cpu_num=e.cpu_num)
                cb = event.EventCallback(self._armed_cb,
                                         event_name="SystemEventBreakpoint",
                                         event_params={"gpa": gpa})

                self._armed_injections.append((symbol, gva, args, tid, gpa, cb,
                                               kernel))
                self._event_manager.request_event(cb)
            else:
                new_waiting.append((symbol, gva, args, tid, kernel))

        self._waiting_injections = new_waiting

        if not self._waiting_injections:
            self._event_manager.cancel_event(self._syscall_cb)