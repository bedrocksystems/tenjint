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

"""Contains classes and functions for debugging.

This module contains various classes and functions that make it easier to
debug or test tenjint.
"""

import cProfile
import io
import pickle
import pstats
import sys
import tblib.pickling_support
import traceback

from . import config
from . import logger

_init = False
_exception_handler = None
_profiling = None

class Profiling(config.ConfigMixin, logger.LoggerMixin):
    """Provides profiling of tenjint based on cProfile."""
    _config_options = [
        {"name": "enable", "default": False, "help": "Enable profiling."},
        {"name": "profile_builtins", "default": False, "help": "Profile builtins."},
        {"name": "print_percentage", "default": 0.1,
         "help": "Percentage of profiled functions to print."},
        {"name": "print_sortby", "default": "tottime",
         "help": "Sort order of the profiled functions."},
    ]

    def __init__(self):
        super().__init__()

        if self._config_values["enable"]:
            # enable profiling
            self._profile = cProfile.Profile(builtins=self._config_values["profile_builtins"])
            self._profile.enable()
        else:
            self._profile = None

    def uninit(self):
        if self._profile is not None:
            self._profile.disable()
            s = io.StringIO()
            s.write("\n\n=====================================================================\n")
            s.write("Profiling data:\n\n")
            ps = pstats.Stats(self._profile, stream=s).sort_stats(self._config_values["print_sortby"])
            ps.print_stats(self._config_values["print_percentage"])
            s.write("=====================================================================\n")
            self._logger.debug(s.getvalue())

class ExceptionHandling(config.ConfigMixin, logger.LoggerMixin):
    """This class allows to pickle exceptions that occure during runtime.

    This class enables us to pickle and store unhandled exceptions that
    occur during runtime. This is helpful for testing and other use cases.
    Exception pickling is based on tblib.
    """
    _config_options = [
        {"name": "log", "default": False, "help": "Log exceptions."},
        {"name": "store", "default": False,
         "help": "Store exceptions to a file. Specify a path to store exceptions to"
                 " or False to not store exceptions"},
    ]

    def __init__(self):
        super().__init__()

        if self._config_values["log"] or self._config_values["store"]:
            self._install_exception_handler()
        else:
            self._orig_except_hook = None

    def uninit(self):
        self._uninstall_exception_handler()

    def _install_exception_handler(self):
        tblib.pickling_support.install()

        self._orig_except_hook = sys.excepthook

        def except_hook(etype, value, tb):
            if self._config_values["log"]:
                exc_str = traceback.format_exception(etype, value, tb)

                self._logger.debug("[ EXCEPTION OCCURED ]\n"
                                   "---------------------\n"
                                   "{}\n".format("\n".join(exc_str)))
            if self._config_values["store"]:
                with open(self._config_values["store"], "wb+") as f:
                    pickle.dump((etype, value, tb), f)

            self._orig_except_hook(etype, value, tb)

        sys.excepthook = except_hook

    def _uninstall_exception_handler(self):
        if self._orig_except_hook is not None:
            sys.excepthook = self._orig_except_hook

def init():
    """Initialize the debugging module.

    This function must be called during the initialization of tenjint, if
    debugging functionality should be used.
    """
    global _init
    global _exception_handler
    global _profiling

    _exception_handler = ExceptionHandling()
    _profiling = Profiling()

    _init = True

def uninit():
    """Uninitialize the debugging module.

    This function must be called when tenjint is uninitialized. It will in-turn
    uninitialize objects used throughout the module. For instance, it will
    uninitialize the profiling class, which will print the cProfile if
    profiling was enabled.
    """
    global _init
    global _exception_handler
    global _profiling

    if not _init:
        return

    _profiling.uninit()
    _exception_handler.uninit()

    _init = False
    _profiling = None
