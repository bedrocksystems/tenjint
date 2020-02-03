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

"""tenjint's event layer.

This module provides all functionality related to tenjints event layer. The
event layer is one of the key components within tenjint. It allows to register
callbacks for events or to publish custom events to the system.
"""

from . import service
from . import api
from . import logger

class Event(object):
    """The base class for all events."""

    producer = None
    """The event producer.

    The event producer is the class that is responsible for emitting an event.
    The producer is set automatically by event manager, do not touch!
    """

    params = {}
    """Event request params

    This must contain a dict with the default parameters for requesting this
    event.
    """

    @classmethod
    def parse_request(cls, **kwargs):
        """Parse an event request using the event request params.

        This function will parse a call to
        :py:class:`tenjint.event.EventPlugin.request_event` using the event
        params (:py:attr:`tenjint.event.Event.params`). For this purpose all
        keyword arguments to request_event are passed to this function. For
        each param that is missing in the request (was not passed as an
        argument to request_event) the function will use the default value
        as specified in the event params. Otherwise the specified value will
        be used.

        Parameters
        ----------
        kwargs
            The keyword arguments that were passed to
            :py:class:`tenjint.event.EventPlugin.request_event`.

        Returns
        -------
        list
            A list that contains all event params in the order that they were
            specified in the event class. If a param was not passed in kwargs,
            the list will contain its default value as specified in the event
            params.
        """
        rv = list()
        for name, def_value in cls.params.items():
            value = def_value if name not in kwargs else kwargs[name]
            rv.append(value)
        return rv

    @classmethod
    def parse_request_to_dict(cls, **kwargs):
        """Parse an event request using the event request params.

        This function will parse a call to
        :py:class:`tenjint.event.EventPlugin.request_event` using the event
        params (:py:attr:`tenjint.event.Event.params`). For this purpose all
        keyword arguments to request_event are passed to this function. For
        each param that is missing in the request (was not passed as an
        argument to request_event) the function will use the default value
        as specified in the event params. Otherwise the specified value will
        be used.

        Parameters
        ----------
        kwargs
            The keyword arguments that were passed to
            :py:class:`tenjint.event.EventPlugin.request_event`.

        Returns
        -------
        dict
            A dictionary that contains all event params. If a param was not
            passed in kwargs, the dictionary will contain its default value
            as specified in the event params.
        """
        rv = {}
        for name, def_value in cls.params.items():
            value = def_value if name not in kwargs else kwargs[name]
            rv[name] = value
        return rv

    @classmethod
    def filter(cls, event_params, event):
        """Event filter function

        This function should be implemented for each event.  The default
        implementation ignores the event_params and simply passes if the
        type matches.
        """
        if type(event) == cls:
            return True
        return False

class CpuEvent(Event):
    """Base class for all CPU events.

    A CPU event is an event that occurs on a specific CPU. For instance, a
    breakpoint is hit. Most events are CPU events, but not all of them.
    """
    def __init__(self, cpu_num):
        super().__init__()
        self.cpu_num = cpu_num

class EventPluginExists(Exception):
    pass

class EventCallback(object):
    """Base class for event related callbacks.

    This is the base class for event related callbacks. Event callbacks are used
    to request notifications from the event system whenever a certain event
    occurs. They allow to specify which event we are interested in and what
    function we want to invoke whenever this event occurs. In addition, we can
    filter events based on event parameters (event_params). If we specify
    event parameters our callback function will only be invoked when an event is
    of the given event type (event_name) and has the specified parameters. For
    more information see :py:func:`__init__`.

    See Also
    --------
    __init__
    """
    def __init__(self, callback_func, event_name=None, event_params=None):
        """Create a new event callback.

        The constructor allows us to create a new event callback for a specific
        event or all events.

        Parameters
        ----------
        callback_func : function
            The callback function to invoke whenever our event criteria (event
            name and event params) match.
        event_name : str, optional
            The name of the event we want to filter on. Our callback_func will
            only be invoked for events of this type. If no event_name is given
            all events will invoke our callback.
        event_params : dict, optional
            Event parameters allow us to further filter events on a more fine
            granular basis. For instance, we might not be interested in all
            second level paging events, but only in execute violations. Event
            parameters allow us to filter events based on such criteria. What
            paramaters are supported depend on the event type (event_name) that
            we are interested in. The event paramters that are supported can be
            found in the documentation of the event class.

        Returns
        -------
        object
            A new event callback object. To use this callback we have to
            register it with the event system
            (see :py:func:`tenjint.event.EventManager.request_event`).

        See Also
        --------
        EventManager.request_event
        EventManager.cancel_event
        """
        self._event_manager = service.manager().get("EventManager")

        self._callback_func = callback_func
        self.event_name = event_name
        if event_params is None:
            self.event_params = dict()
        else:
            self.event_params = event_params

        self.active = False
        self.request_id = None

    @property
    def event_key(self):
        if self.event_name is None:
            return "*"
        return self.event_name

    @property
    def event_cls(self):
        if self.event_name is None:
            return None
        try:
            event_cls = self._event_manager.get_event_cls(self.event_name)
        except KeyError:
            event_cls = None
        return event_cls

    def deliver(self, event):
        if ((self.event_cls is None) or
                (self.event_cls.filter(self.event_params, event))):
            self._callback_func(event)

class EventManager(logger.LoggerMixin):
    """tenjint's event manager.

    The event manager is the main component of the event system. It is
    responsible for getting events from QEMU and to distpatch them within the
    system. In addition, the event manager allows us to request callbacks for
    certain events or to publish our own events within the system. See
    :py:func:`request_event` and :py:func:`put_event` for details respectively.
    """
    def __init__(self):
        super().__init__()
        self._event_queue = list()
        self._event_callbacks = {"*": list()}
        self._continue_hooks = list()
        self._event_plugins = {
                        "SystemEventVmShutdown": api.SystemEventVmShutdown,
                        "SystemEventVmReady": api.SystemEventVmReady,
                        "SystemEventVmStop": api.SystemEventVmStop}

    def register(self, plugin):
        """Register a plugin with the event manager.

        Plugins must be registered with the event manager if they produce
        events. The plugin manager should take care of this automatically. Users
        should not call this function.

        Parameters
        ----------
        plugin : tenjint.plugins.plugins.Plugin
            The plugin to register.
        """
        for event_cls in plugin.produces:
            event_name = event_cls.__name__
            if event_name in self._event_plugins:
                raise EventPluginExists("{} already provided by {}".format(
                                event_name, self._event_plugins[event_name]))
            self._logger.debug("Registering {} with event manager as {} "
                          "producer".format(type(plugin).__name__, event_name))
            event_cls.producer = plugin
            self._event_plugins[event_name] = event_cls

    def unregister(self, plugin):
        """Unregister a plugin from the event manager.

        Plugins must be registered with the event manager if they produce
        events. The plugin manager should take care of this automatically. Users
        should not call this function.

        Parameters
        ----------
        plugin : tenjint.plugins.plugins.Plugin
            The plugin to unregister.
        """
        for event_cls in plugin.produces:
            event_name = event_cls.__name__
            self._logger.debug("Unregistering {} with event manager as {} "
                          "producer".format(type(plugin).__name__, event_name))
            self._event_plugins.pop(event_name)
            event_cls.producer = None

    def get_event_cls(self, event_key):
        return self._event_plugins[event_key]

    def get_registered_events(self):
        """Get all events that the event manager is aware of.

        This function can be used to retrieve all events that the event manager
        is aware of.

        Yields
        ------
        tuple (str, dict)
            Returns tuples of the form (event class name, event parameters)
        """
        for event_name, event_cls in self._event_plugins.items():
            yield event_name, event_cls.params

    def request_event(self, callback, send_request=True):
        """Register an event callback with the event manager.

        This function allows us to register an event callback with the event
        manager. Once registered, the callback function specified in the event
        callback will be invoked whenever a matching event is published in the
        system.

        Parameters
        ----------
        callback : EventCallback
            The event callback to register.
        send_request : bool, optional
            Whether the event request should be forwarded to the plugin that
            produces this event. Users should generally not provide this
            argument and use its default value. If the event producer is not
            informed about an event request it might not enable the appropriate
            features and the event might never be produced.

        See Also
        --------
        EventCallback
        """
        if (send_request and callback.event_cls is not None and
                callback.event_cls.producer is not None):
            plugin = self._event_plugins[callback.event_key].producer
            callback.request_id = plugin.request_event(callback.event_cls,
                                                       **callback.event_params)

        if callback.event_key not in self._event_callbacks:
            self._event_callbacks[callback.event_key] = list()

        self._event_callbacks[callback.event_key].append(callback)

        callback.active = True

    def cancel_event(self, callback):
        """Cancel an event request.

        This function allows us to unregister a event callback from the event
        manager.

        Parameters
        ----------
        callback : EventCallback
            The event callback to unregister.

        Raises
        ------
        KeyError
            If the callback has not been registered with the event manager.
        """
        self._event_callbacks[callback.event_key].remove(callback)
        if callback.request_id is not None:
            plugin = self._event_plugins[callback.event_key].producer
            plugin.cancel_event(callback.request_id)
        callback.request_id = None
        callback.active = False

    def put_event(self, event):
        """Publish an event in the system.

        This function allows a plugin to publish an event within the system.
        Any event callbacks that have been registered with the event manager
        and match the published event will be notified.

        Parameters
        ----------
        event : Event
            The event to publish.
        """
        self._event_queue.append(event)

    def add_continue_hook(self, callback_func):
        """Add a continue hook.

        This function allows to register a function that will be executed
        before the virtual machine is resumed. In general, users should not use
        continue hooks.
        """
        self._logger.debug("Adding continue hook: {}".format(callback_func))
        self._continue_hooks.append(callback_func)

    def remove_continue_hook(self, callback_func):
        """Remove a continue hook."""
        self._logger.debug("Removing continue hook: {}".format(callback_func))
        self._continue_hooks.remove(callback_func)

    def _call_continue_hooks(self):
        for hook in self._continue_hooks:
            hook()

    def _dispatch_event(self, event):
        self._logger.debug("Dispatching event: {}".format(event))
        for callback in self._event_callbacks["*"]:
            callback.deliver(event)
        event_key = type(event).__name__
        if event_key in self._event_callbacks:
            for callback in self._event_callbacks[event_key]:
                callback.deliver(event)

    def _get_system_events(self):
        self._call_continue_hooks()
        api.tenjint_api_wait_event(secs=1)
        event = api.tenjint_api_get_event()
        while event is not None:
            self.put_event(event)
            event = api.tenjint_api_get_event()

    def run_loop(self):
        """The event managers internal run loop."""
        while True:
            self._get_system_events()
            while self._event_queue:
                event = self._event_queue.pop(0)
                self._dispatch_event(event)
                if type(event) == api.SystemEventVmShutdown:
                    return

def run():
    """Start the run loop of the event manager.

    This function starts the run loop of the systemwide event manager. This
    function should only be called internally.
    """
    em = service.manager().get("EventManager")
    em.run_loop()

def init():
    """Initialize the event subsystem."""
    em = EventManager()
    service.manager().register(em)

def uninit():
    """Uninitialize the event subystem."""
    service.manager().unregister_by_name("EventManager")