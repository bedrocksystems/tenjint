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

"""tenjint's plugin subsystem.

This module provides tenjint's plugin subsystem. The plugin subsystem is
responsible for loading, unloading, and managing plugins.
"""

import glob
import os
import types
import inspect
import importlib.machinery

from collections import OrderedDict

from .. import api
from .. import config
from .. import logger
from .. import service

class Plugin(logger.LoggerMixin):
    """Base class for all plugins.

    This is the base class for all plugins.
    """

    _abstract = True
    """Whether this is an abstract class.

    An abstract class will not be loaded by the plugin manager and is an
    abstract class meant to be sub-classed.
    """

    name = None
    """The name of the plugin.

    If this is not provided, the class name will be used.
    """

    arch = None
    """The prerequisite architecture

    The plugin will only be loaded if arch is None or matches the host arch.
    This must be None or of type tenjint.api.Arch.
    """

    os = None
    """The prerequisite operating system

    The plugin will only be loaded if is is None or matches the guest OS. This
    must be None or of type OsType.
    """

    path = None
    """The path of the module containing the plugin.

    This variable will be populated when the plugin is loaded. If the path to
    the module containing the plugin is known, the variable will be set.
    """

    @classmethod
    def get_name(cls):
        """Get the name of the plugin.

        Returns
        -------
        str
            The name of the plugin.
        """
        return cls.__name__ if cls.name is None else cls.name

    @classmethod
    def loadable(cls):
        """Check whether the plugin can be loaded.

        This function will check whether the plugin can be loaded given the
        current environment. For example, some plugins may only work with a
        certain operating system (e.g. Linux) or a certain architecture
        (e.g. x86).

        Returns
        -------
        bool
            True if the plugin can be loaded, False otherwise.
        """
        if cls._abstract:
            return False
        if cls.arch is not None and cls.arch != api.arch:
            return False
        if cls.os is not None and cls.os != api.os:
            return False

        return True

    @classmethod
    def load(cls, **kwargs):
        """Load function

        This function is called by the plugin manager to load the plugin.
        """
        if not cls.loadable():
            return None

        name = cls.get_name()
        logger.logger.debug("Loading plugin: {}".format(name))
        return cls(**kwargs)

    def __init__(self):
        super().__init__()
        if self.name is None:
            self.name = type(self).__name__
        self._logger.debug("Initializing {} ({})".format(type(self).__name__,
                                                         self.name))
        self._service_manager.register(self, self.name)

    @property
    def _service_manager(self):
        """Get the service manager (self replacing)

        This property will obtain the service manager. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._service_manager = service.manager()
        return self._service_manager

    @property
    def _event_manager(self):
        """Get the event manager (self replacing)

        This property will obtain the event manager. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._event_manager = self._service_manager.get("EventManager")
        return self._event_manager

    @property
    def _plugin_manager(self):
        """Get the plugin manager (self replacing)

        This property will obtain the plugin manager. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._plugin_manager = self._service_manager.get("PluginManager")
        return self._plugin_manager

    @property
    def _vm(self):
        """Get the vm (self replacing)

        This property will obtain the vm. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._vm = self._service_manager.get("VirtualMachine")
        return self._vm

    @property
    def _os(self):
        """Get the os (self replacing)

        This property will obtain the os. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._os = self._service_manager.get("OperatingSystem")
        return self._os

    @property
    def _fargs(self):
        """Get the function argument service (self replacing)

        This property will obtain the os. It will replace itself
        on the first access by adding a class attribute with the same name. This
        will improve the performance of further accesses to the property for
        all classes that use it.
        """
        Plugin._fargs = self._service_manager.get("FunctionArguments")
        return self._fargs

    def uninit(self):
        """Uninit function

        This function will be called by the plugin manager on unload.
        """
        self._logger.debug("Uninitializing {}".format(type(self).__name__))
        self._service_manager.unregister_by_object(self)

class EventPlugin(Plugin):
    """Plugin class for plugins that produce events."""

    produces = None
    """produces should hold a list of event classes this plugin produces."""

    def __init__(self):
        super().__init__()
        self._event_manager.register(self)

    def uninit(self):
        """Uninit function

        This function will be called by the plugin manager on unload.
        """
        super().uninit()
        self._event_manager.unregister(self)

    def request_event(self, **kwargs):
        raise NotImplementedError("request_event not implemented")

    def cancel_event(self, request_id):
        raise NotImplementedError("cancel_event not implemented")

class PluginManager(config.ConfigMixin, logger.LoggerMixin):
    """The plugin manager.

    The plugin manager is the main component of the plugin subsystem. It is
    responsible for loading and unloading plugins.
    """
    _config_options = [
        {
            "name": "plugin_dir", "default": None,
            "help": "The directory to look for third-party plugins."
        },
    ]
    """Configuration options."""

    def __init__(self):
        super().__init__()
        self._loaded_plugins = OrderedDict()

    def load_plugin(self, cls, path=None, reload=True, **kwargs):
        """Load the given plugin class.

        Parameters
        ----------
        cls : class
            The plugin class to load.
        path : str
            The path to the module containing the plugin.
        reload : bool
            Whether to reload an already existing module.
        """
        if reload and cls.get_name() in self._loaded_plugins and cls.loadable():
            self.unload_plugin(self._loaded_plugins[cls.get_name()])

        plugin = cls.load(**kwargs)
        if plugin is not None:
            plugin.path = path
            self._loaded_plugins[plugin.name] = plugin

    def unload_plugin(self, plugin):
        """Unload the given plugin.

        Parameters
        ----------
        plugin : Plugin
            The plugin to unload.
        """
        self._loaded_plugins.pop(plugin.name)
        plugin.uninit()

    def get_plugins_in_module(self, mod):
        """Get all plugins contained in a module.

        This function will find all plugins in module and return them.

        Parameters
        ----------
        mod :  types.ModuleType
            The module to search.

        Returns
        -------
        list
            A list of :py:class:´BasePlugin´ plugins
        """
        result = []
        for _, obj in inspect.getmembers(mod):
            if (inspect.isclass(obj) and issubclass(obj, Plugin)):
                result.append(obj)

        return result

    def load_module(self, mod, path=None, **kwargs):
        """Load all plugins contained in a module.

        This function will find and load all plugins in a module.  Any
        additional keyword arguments will be passed to the loaded plugins.

        Parameters
        ----------
        mod :  types.ModuleType
            The module to search.
        path : str
            The path to the module.
        """
        if path is None and hasattr(mod, "__file__"):
            path = mod.__file__

        for plugin in self.get_plugins_in_module(mod):
            self.load_plugin(plugin, path=path, **kwargs)

    def import_file(self, path, module_name=None):
        """Import a python source file.

        This function will load a python source file as a python module. The
        name of the module can be provided using the module_name parameter.

        Parameters
        ----------
        path : str
            The full path to the python source file to load.
        module_name : str
            The module name that the loaded source file should use.

        Returns
        -------
        types.ModuleType
            A python module representing the source file.
        """
        if module_name is None:
            module_name = os.path.splitext(path)[0]

        loader = importlib.machinery.SourceFileLoader(module_name, path)
        mod = types.ModuleType(loader.name)
        loader.exec_module(mod)
        return mod

    def import_and_load_file(self, path, module_name=None, **kwargs):
        """Import and load all plugins contained in python source file.

        This function will import and load all plugins contained in a python
        source file. Any additional keyword arguments will be passed to the
        loaded plugins.

        Parameters
        ----------
        path : str
            The full path to the python source file to consider.
        module_name : str
            The module name that the loaded source file should use.
        """
        mod = self.import_file(path, module_name=module_name)
        self.load_module(mod, path=path, **kwargs)

    def import_directory(self, path, module_prefix=None, recursive=False):
        """Import all python source files in a directory.

        This function will import all python source files in a directory. For
        each imported file a module will be returned. The imported modules will
        have the name "<module_prefix>.<filename>".

        Parameters
        ----------
        path : str
            The full path to the directory to import from.
        module_prefix : str
            A prefix for the name of the modules.
        recursive : bool
            Whether to import from subdirectories.

        Returns
        -------
        list
            A list of tuples (python module, path)
        """
        result = []
        glob_path = os.path.join(path, "*.py")

        if module_prefix is None:
            module_prefix = "runtime_import."

        for src_file in glob.glob(glob_path, recursive=recursive):
            mod_dir = ".".join(os.path.dirname(src_file[len(path):]).split("/"))
            mod_name = "{}{}.{}".format(module_prefix, mod_dir,
                                        os.path.splitext(src_file)[0])
            result.append((self.import_file(src_file, module_name=mod_name),
                           src_file))

        return result

    def import_and_load_directory(self, path, module_prefix=None,
                                  recursive=False, **kwargs):
        """Import and load all plugins contained in a directory.

        This function will import and load all plugins contained in a
        directory. Any additional keyword arguments will be passed to the
        loaded plugins.

        Parameters
        ----------
        path : str
            The full path to the directory to load from.
        module_prefix : str
            A prefix for the name of the modules that will be imported.
        recursive : bool
            Whether to consider subdirectories.
        """
        for mod, src in self.import_directory(path, module_prefix=module_prefix,
                                              recursive=recursive):
            self.load_module(mod, path=src, **kwargs)

    def load_user_plugins(self):
        """Load all user plugins specified in the configuration."""
        if self._config_values["plugin_dir"] is not None:
            self._logger.debug("Loading user plugins from \"{}\"...".format(
                                            self._config_values["plugin_dir"]))
            plugin_dir = os.path.expanduser(self._config_values["plugin_dir"])
            plugin_dir = os.path.abspath(plugin_dir)
            self.import_and_load_directory(plugin_dir)

    def unload_all(self):
        """Unload all plugins."""
        while self._loaded_plugins:
            _, plugin = self._loaded_plugins.popitem()
            plugin.uninit()

def init():
    """Initialize the plugin subsystem."""
    pm = PluginManager()
    service.manager().register(pm)

def uninit():
    """Uninitialize the plugin subsystem."""
    service.manager().unregister_by_name("PluginManager")

