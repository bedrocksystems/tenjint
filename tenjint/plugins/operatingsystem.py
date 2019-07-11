
from . import plugins
from .. import api
from .. import config

from rekall.session import InteractiveSession
from rekall.plugins.addrspaces import tenjint
from rekall.plugin import PluginError

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
        self.session.cache.Clear()

    def process(self, pid=None, dtb=None):
        if pid is None and dtb is None:
            raise ValueError("you must specify a pid or dtb")

        for proc in self.session.plugins.pslist().filter_processes():
            if pid is not None and pid == proc.pid:
                return proc
            elif dtb is not None and dtb == proc.dtb:
                return proc

        return None

    def vtop(self, vaddr, pid=None, dtb=None):
        if pid is not None or dtb is not None:
            proc = self.process(pid=pid, dtb=dtb)

            if proc is None:
                raise ValueError("process not found")

            return proc.get_process_address_space().vtop(vaddr)

        return self.session.default_address_space.vtop(vaddr)

class OperatingSystemWinX86_64(OperatingSystemBase):
    _abstract = False
    name = "OperatingSystem"
    arch = api.Arch.X86_64
    os = api.OsType.OS_WIN

class OperatingSystemLinuxX86_64(OperatingSystemBase):
    _abstract = False
    name = "OperatingSystem"
    arch = api.Arch.X86_64
    os = api.OsType.OS_LINUX

    def current_process(self, cpu_num):
        for task in self.session.plugins.pslist().filter_processes():
            if task.dtb == self._vm.cpu(cpu_num).cr3:
                return task
        return None

class OperatingSystemLinuxAarch64(OperatingSystemBase):
    _abstract = False
    name = "OperatingSystem"
    arch = api.Arch.AARCH64
    os = api.OsType.OS_LINUX

    def current_process(self, cpu_num):
        return self.session.profile.task_struct(self._vm.cpu(cpu_num).sp_el0)
