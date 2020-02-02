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

"""Provides all functionality related to configuration.

This module provides classes and functions that parse and handle configuration
files and make the parsed data available to the rest of the system.
"""

import yaml
import os

from . import logger

_config_data = None

class ConfigMixin(object):
    """Adds configuration options.

    This class can be used to add configuration options for a specific object
    or plugin. It will automatically parse the config and will store the
    relevant parts of the config in the internal variable "_config_values".
    The relevant part of the config is identified by a section name. The config
    section name can be specified in the class variable
    :py:attr:`tenjint.config.ConfigMixin._config_section`. If no section name is
    specified the name of the class will be used as default.

    Example
    -------
    _config_options = [
        {"name": "option_name1", "default": 1, "help": "help description"},
        {"name": "option_name2", "default": "abc", "help": "help description"},
    ]

    if _config_section is None, the class name will be used as a default.
    """
    _config_options = list()
    _config_section = None

    def __init__(self):
        super().__init__()
        self._config_values = dict()
        if self._config_section is None:
            self._config_section = type(self).__name__

        for item in self._config_options:
            self._config_values[item["name"]] = item["default"]

        if (self._config_section in _config_data and
                _config_data[self._config_section] is not None):
            for k, v in _config_data[self._config_section].items():
                if k not in self._config_values:
                    continue
                if isinstance(v, dict):
                    self._merge_configs(self._config_values[k], v)
                else:
                    self._config_values[k] = v

    @staticmethod
    def _merge_configs(global_config, new_config):
        for k, v in new_config.items():
            if k in global_config:
                if isinstance(v, dict):
                    if not isinstance(global_config[k], dict):
                        raise RuntimeError("merging dict with non-dict")
                    ConfigMixin._merge_configs(global_config[k], v)
                else:
                    global_config[k] = v
            else:
                global_config[k] = v

def init(configs):
    """Initialize the config module.

    This function will initialize the config module and parse the provided
    configuration file(s).
    """
    global _config_data
    configs = configs.split(":") if configs is not None else []
    _config_data = dict()
    for config in configs:
        config_full_path = os.path.expanduser(config)
        config_full_path = os.path.abspath(config_full_path)
        with open(config_full_path, "r") as f:
            _config = yaml.safe_load(f)
        ConfigMixin._merge_configs(_config_data, _config)

    if "logging" in _config_data:
        logger.set_config(_config_data["logging"])

    logger.logger.debug("config files: {}".format(configs))
    logger.logger.debug("config data: {}".format(_config_data))

def uninit():
    """Uninitialize the config module."""
    global _config_data
    _config_data = None
