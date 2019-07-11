import pickle

from .config import ConfigMixin
from .event import EventCallback
from .service import manager

_manager = None

class PickleOutputManager(ConfigMixin):
    _config_section = "OutputManager"
    _config_options = [
        {"name": "store", "default": False,
         "help": "Path where to store events. If set to False no events "
                 "will be recoreded."}
    ]

    def __init__(self):
        super().__init__()

        if self._config_values["store"]:
            self._cb = EventCallback(self._log_event)
            self._event_manager = manager().get("EventManager")
            self._event_manager.request_event(self._cb)
            self._events = []
        else:
            self._cb = None

    def uninit(self):
        if self._cb is not None:
            self._event_manager.cancel_event(self._cb)
            self._cb = None
            self._flush()

    def _flush(self):
        with open(self._config_values["store"], "ab+", buffering=0) as f:
            for event in self._events:
                pickle.dump(event, f)

        self._events.clear()

    def _log_event(self, event):
        self._events.append(event)

def init():
    global _manager

    _manager = PickleOutputManager()

def uninit():
    global _manager

    if _manager is not None:
        _manager.uninit()
        _manager = None