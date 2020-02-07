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

"""tenjint's main module.

This is tenjint's main module that can be used to initialize, uninitialize,
and to run tenjint.
"""

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
from .plugins import fargs

def run(configs=None):
    """Initialize tenjint, start the event loop, and uninitialize tenjint after
    it returns."""
    init(configs)
    event.run()
    uninit()

def init(configs):
    """Initialize tenjint."""
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
    pm.load_module(fargs)
    pm.load_module(interactive)

    logger.debug("Loading user plugins...")
    pm.load_user_plugins()

    logger.debug("tenjint initialized")

def uninit():
    """Uninitialize tenjint."""
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
