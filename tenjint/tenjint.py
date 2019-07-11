from . import api
from . import service
from . import event
from . import config
from . import debug
from . import output
from .logger import logger
from .plugins import plugins

from .plugins import machine
from .plugins import taskswitch
from .plugins import slp
from .plugins import singlestep
from .plugins import breakpoint
from .plugins import interactive
from .plugins import operatingsystem

def run(configs=None):
    init(configs)
    event.run()
    uninit()

def init(configs):
    # Load modules
    logger.debug("Loading modules...")
    config.init(configs)
    debug.init()
    service.init()
    event.init()
    output.init()
    plugins.init()
    api.tenjint_api_init()

    # Load plugins
    logger.debug("Loading system plugins...")
    pm = service.manager().get("PluginManager")
    pm.load_module(machine)
    pm.load_module(operatingsystem)
    pm.load_module(taskswitch)
    pm.load_module(slp)
    pm.load_module(singlestep)
    pm.load_module(breakpoint)
    pm.load_module(interactive)

    logger.debug("Loading user plugins...")
    pm.load_user_plugins()

    logger.debug("tenjint initialized")

def uninit():
    # Unload plugins
    logger.debug("Unoading plugins...")
    pm = service.manager().get("PluginManager")
    pm.unload_all()

    # Unload modules
    logger.debug("Unloading modules...")
    api.tenjint_api_uninit()
    plugins.uninit()
    output.uninit()
    event.uninit()
    service.uninit()
    config.uninit()
    debug.uninit()
    logger.debug("tenjint uninitialized")
