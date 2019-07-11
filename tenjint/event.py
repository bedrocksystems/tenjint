from . import service
from . import api
from . import logger

class Event(object):
    producer = None
    """Event base class

    producer is set automatically by event manager, do not touch!
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
    def __init__(self, cpu_num):
        super().__init__()
        self.cpu_num = cpu_num

class EventPluginExists(Exception):
    pass

class EventCallback(object):
    def __init__(self, callback_func, event_name=None, event_params=None):
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
        for event_cls in plugin.produces:
            event_name = event_cls.__name__
            self._logger.debug("Unregistering {} with event manager as {} "
                          "producer".format(type(plugin).__name__, event_name))
            self._event_plugins.pop(event_name)
            event_cls.producer = None

    def get_event_cls(self, event_key):
        return self._event_plugins[event_key]

    def get_registered_events(self):
        for event_name, event_cls in self._event_plugins.items():
            yield event_name, event_cls.params

    def request_event(self, callback, send_request=True):
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
        self._event_callbacks[callback.event_key].remove(callback)
        if callback.request_id is not None:
            plugin = self._event_plugins[callback.event_key].producer
            plugin.cancel_event(callback.request_id)
        callback.request_id = None
        callback.active = False

    def put_event(self, event):
        self._event_queue.append(event)

    def add_continue_hook(self, callback_func):
        self._logger.debug("Adding continue hook: {}".format(callback_func))
        self._continue_hooks.append(callback_func)

    def remove_continue_hook(self, callback_func):
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
        while True:
            self._get_system_events()
            while self._event_queue:
                event = self._event_queue.pop(0)
                self._dispatch_event(event)
                if type(event) == api.SystemEventVmShutdown:
                    return

def run():
    em = service.manager().get("EventManager")
    em.run_loop()

def init():
    em = EventManager()
    service.manager().register(em)

def uninit():
    service.manager().unregister_by_name("EventManager")