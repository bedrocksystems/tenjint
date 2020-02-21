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

"""tenjint's service layer.

This module contains all classes and functions that provide tenjint's service
layer. The service layer is responsible for maintaining all services available
within the system. Effectively, the service layer allows modules to register
services (objects) that can then be retrieved by other modules.
"""

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
    ServiceRegisteredError
            If a service with this name already exists.
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
    """Error that is emitted when a service cannot be registered."""
    pass

class ServiceManager(logger.LoggerMixin):
    """The service manager.

    The service manager is the main component of the tenjint service layer. It
    allows to register (:py:func:`register`) and lookup (:py:func:`get`)
    services in the system.
    """
    def __init__(self):
        super().__init__()
        self._service_registry = dict()

    def register(self, obj, name=None):
        """Register an object with the service manager.

        Parameters
        ----------
        obj : object
            The object to register.
        name : str, optional
            The name to register the object with. If no name is provided,
            the class name will be used.

        Raises
        ------
        ServiceRegisteredError
            If a service with this name already exists.
        """
        if name is None:
            name = type(obj).__name__
        if name in self._service_registry:
            raise ServiceRegisteredError(
                                "Service {} already registered".format(name))
        self._logger.debug("Registering {} with service manager".format(name))
        self._service_registry[name] = obj

    def unregister_by_object(self, obj):
        """Unregister an object using the object itself.

        This function allows to unregister a previously registered object.

        Parameters
        ----------
        obj : object
            The object to unregister.

        Raises
        ------
        KeyError
            If the object has not been registered with the service layer.
        """
        self._logger.debug("Unregistering {} with service manager".format(obj.name))
        return self._service_registry.pop(obj.name)

    def unregister_by_name(self, name):
        """Unregister an object using its name.

        This function allows to unregister a previously registered object.

        Parameters
        ----------
        name : str
            The name of the object to unregister.

        Raises
        ------
        KeyError
            If the object has not been registered with the service layer.
        """
        self._logger.debug("Unregistering {} with service manager".format(name))
        return self._service_registry.pop(name)

    def get(self, name):
        return self._service_registry[name]

    def services(self):
        return self._service_registry.keys()

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
    """Initialize the service layer."""
    global _service_manager
    _service_manager = ServiceManager()

def uninit():
    """Uninitialize the service layer."""
    global _service_manager
    _service_manager = None
