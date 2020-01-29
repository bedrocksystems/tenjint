import sys
import os
import re
import signal
from pygments.token import Token

from pprint import pprint
from IPython.config.loader import Config
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.terminal.prompts import Prompts
from IPython.core.inputtransformer import StatelessInputTransformer
from rekall.session import DynamicNameSpace
from rekall import ipython_support

from . import plugins
from .. import api
from .. import config
from ..event import EventCallback

class TenjintPrompts(Prompts):
    def in_prompt_tokens(self, cli=None):
        if sys.stdout.encoding == "UTF-8":
            return [
                        (Token.Name.Class, "テ"),
                        (Token.Prompt, '> '),
                    ]
        else:
            return [
                        (Token.Name.Class, "tenjint"),
                        (Token.Prompt, '> '),
                    ]

class TenjintShell(InteractiveShellEmbed):
    utf8_banner = """
----------------------------------------------------------------------------
                        __               _ _       __
                       / /____  ____    (_|_)___  / /_
                      / __/ _ \/ __ \  / / / __ \/ __/
                     / /_/  __/ / / / / / / / / / /_
                     \__/\___/_/ /_/_/ /_/_/ /_/\__/
                                /___/

                              テンジント

For all your introspection needs.
----------------------------------------------------------------------------

"""
    banner = """
----------------------------------------------------------------------------
                        __               _ _       __
                       / /____  ____    (_|_)___  / /_
                      / __/ _ \/ __ \  / / / __ \/ __/
                     / /_/  __/ / / / / / / / / / /_
                     \__/\___/_/ /_/_/ /_/_/ /_/\__/
                                /___/

For all your introspection needs.
----------------------------------------------------------------------------

"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if sys.stdout.encoding == "UTF-8":
            self.banner = self.utf8_banner

    def init_inspector(self):
        self.inspector = ipython_support.RekallObjectInspector()

class InteractiveShell(plugins.Plugin, config.ConfigMixin):
    _abstract = False
    _config_options = [
        {
            "name": "enable", "default": False,
            "help": "Whether to invoke an interactive iPython shell."
        },
        {
            "name": "wait", "default": True,
            "help": "If this option is true, the VM will pause and give "
                    "control to the shell before starting."
        }
    ]

    def __init__(self):
        super().__init__()
        self._callbacks = dict()
        self._cb_id = 0
        self.event = None
        self._session = None
        self._stop_cb = None
        self._renderer = None
        self._original_sigint_handler = None
        if self._config_values["enable"]:
            self._enable()

    def uninit(self):
        super().uninit()
        for _, cb in self._callbacks.items():
            self._event_manager.cancel_event(cb)
        self._callbacks.clear()
        if self._session is not None:
            self._session = None
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            self._original_sigint_handler = None
        if self._stop_cb is not None:
            self._event_manager.cancel_event(self._stop_cb)
            self._stop_cb = None

    def _enable(self):
        self.service_manager = self._service_manager
        self.plugin_manager = self._plugin_manager
        self.vm = self._vm
        self.os = self._os

        self._session = self._service_manager.get("OperatingSystem").session
        # Allow all special plugins to run.
        self._session.privileged = True
        self._session.locals = DynamicNameSpace(
            # What rekall usually passes
            session=self._session, v=self._session.v, sys=sys, os=os,
            session_list=self._session.session_list,
            # Pass additional environment.
            tenjint=self, shutdown=self.request_shutdown, cont=self.cont
        )

        self._session.mode = "Interactive"

        cfg = Config()
        cfg.InteractiveShellEmbed.autocall = 2
        cfg.TerminalInteractiveShell.prompts_class = TenjintPrompts
        cfg.InteractiveShell.separate_in = ''
        cfg.InteractiveShell.separate_out = ''
        cfg.InteractiveShell.separate_out2 = ''

        shell = TenjintShell(config=cfg, user_ns=self._session.locals)

        shell.push({"exit":self.shutdown})
        shell.push({"quit":self.shutdown})

        shell.display_banner = True

        shell.Completer.merge_completions = False
        #shell.exit_msg = "VM Continue"
        shell.set_custom_completer(ipython_support.RekallCompleter, 0)

        #readline.set_completer_delims(' \t\n`!@#$^&*()=+[{]}\\|;:\'",<>?')

        # Input transfomer
        shell.input_splitter.logical_line_transforms.append(
                                                       tenjintInputTransformer())
        shell.input_transformer_manager.logical_line_transforms.append(
                                                       tenjintInputTransformer())

        self._shell = shell
        self._session.shell = shell

        self._stop_cb = EventCallback(self._cb_func,
                                      event_name="SystemEventVmStop")
        self._event_manager.request_event(self._stop_cb)
        if self._config_values["wait"]:
            self.request_callback(event_name="SystemEventVmReady")

        self._original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._sigint_handler)

    def _sigint_handler(self, sig, frame):
        api.tenjint_api_request_stop()

    def cont(self):
        self._session.shell.exiter()

    def request_callback(self, event_name=None, event_params=None):
        cb = EventCallback(self._cb_func,
                           event_name=event_name,
                           event_params=event_params)
        self._event_manager.request_event(cb)
        self._callbacks[self._cb_id] = cb
        self._cb_id += 1

    @property
    def callbacks(self):
        self._renderer.format("Set Callbacks\n")
        self._renderer.table_header([dict(name="ID", width=5),
                                     dict(name="Name", width=50)])
        for cb_id, cb in self._callbacks.items():
            self._renderer.table_row(cb_id, cb.event_name)

    def cancel_callback(self, cb_id):
        cb = self._callbacks.pop(cb_id)
        self._event_manager.cancel_event(cb)

    @property
    def show_events(self):
        self._renderer.format("Available Events\n")
        self._renderer.table_header([dict(name="Event", width=30),
                                     dict(name="Parameters", width=90)])
        for name, params in self._event_manager.get_registered_events():
            self._renderer.table_row(name, str(params))

    def request_shutdown(self):
        api.tenjint_api_request_shutdown()

    def shutdown(self):
        self.request_shutdown()
        self._shell.ask_exit()

    def get_context(self):
         # Print current state
        if api.arch == api.Arch.X86_64:
            arch = "X86_64"
        elif api.arch == api.Arch.AARCH64:
            arch = "AARCH64"
        else:
            arch = "Unknown"

        if api.os == api.OsType.OS_WIN:
            os = "Windows"
        elif api.os == api.OsType.OS_LINUX:
            os = "Linux"
        else:
            os = "Unknown"

        result = "Current Context (ARCH: {}, OS: {})\n".format(arch, os)
        result += ("-" * len(result) + "\n")

        for cpu_num in range(0, self._vm.cpu_count):
            cur = self._vm.cpu(cpu_num)
            ip = cur.instruction_pointer
            result += ("CPU {} - PC: 0x{:016x}, DTB: 0x{:016x}\n"
                       "".format(cpu_num, ip, cur.page_table_base(ip)))
        result += "\n"

        return result

    def _cb_func(self, e):
        self.event = e
        self._renderer = self._session.GetRenderer()
        self._renderer.start()
        old_banner = self._shell.banner
        if self._shell.display_banner:
            self._shell.banner +=  "\n" + self.get_context()
        else:
            self._renderer.format(self.get_context())
        api.tenjint_api_mouse_out()
        self._shell(module=self._session.locals)
        self._renderer.flush()
        self._shell.display_banner = False
        self._shell.banner = old_banner

@StatelessInputTransformer.wrap
def tenjintInputTransformer(text):
    text = re.sub(r"^\$([a-zA-Z0-9_-]+)(\[([a-zA-Z0-9_.-]+)\])?(\s)*=",
                  lambda m: (r"tenjint.vm.cpu(" + (m.group(3) or "0") +
                             ")." + m.group(1) + (m.group(4) or "") + "="), text)
    text = re.sub(r"\$([a-zA-Z0-9_-]+)(\[([a-zA-Z0-9_.-]+)\])?",
                  lambda m: (r"tenjint.vm.cpu(" + (m.group(3) or "0") +
                             ")." + m.group(1)), text)
    return text
