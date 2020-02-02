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

from . import logger

_service_manager = None

def register(obj, name=None):
    """Register a new object with the service layer.

    This function registers an object with the service layer. Once registered,
    the object can be obtained by other objects using the
    :py:func:`tenjint.service.get` function. If no name for the object is
    provided, the object can be retrieved by its class name.

    Parameters
    ----------
    obj : object
        The object to register.
    name : str
        The name to register the object under. If no name is provided, the
        class name will be used.

    Raises
    ------
    ValueError
        If the service layer has not been initialized.
    """
    if _service_manager is None:
        raise ValueError("Service manager is not initialized")

    _service_manager.register(obj, name=name)

def get(name):
    """Get an object by name.

    This function allows to retrieve objects that have been registered with
    the service layer (:py:func:`tenjint.service.register`) using their
    name.

    Parameters
    ----------
    name : str
        The name of the object to retrieve

    Raises
    ------
    ValueError
        If the service layer has not been initialized.
    KeyError
        If the object cannot be found.
    """
    if _service_manager is None:
        raise ValueError("Service manager is not initialized")

    return _service_manager.get(name)

class ServiceRegisteredError(Exception):
    pass

class ServiceManager(logger.LoggerMixin):
    def __init__(self):
        super().__init__()
        self._service_registry = dict()

    def register(self, obj, name=None):
        if name is None:
            name = type(obj).__name__
        if name in self._service_registry:
            raise ServiceRegisteredError(
                                "Service {} already registered".format(name))
        self._logger.debug("Registering {} with service manager".format(name))
        self._service_registry[name] = obj

    def unregister_by_object(self, obj):
        self._logger.debug("Unregistering {} with service manager".format(obj.name))
        return self._service_registry.pop(obj.name)

    def unregister_by_name(self, name):
        self._logger.debug("Unregistering {} with service manager".format(name))
        return self._service_registry.pop(name)

    def get(self, name):
        return self._service_registry[name]

def manager():
    """Get the service manager.

    Returns
    -------
    :py:obj:`tenjint.service.ServiceManager`
        The service manager.

    Raises
    ------
    ValueError
        If the service layer was not initialized.
    """
    if _service_manager is None:
        raise ValueError("Service manager is not initialized")
    return _service_manager

def init():
    global _service_manager
    _service_manager = ServiceManager()

def uninit():
    global _service_manager
    _service_manager = None
