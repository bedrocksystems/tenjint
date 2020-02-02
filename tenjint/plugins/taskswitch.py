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

"""Contains all functionality related to task switch trapping.

This module contains plugins that control the lower-level API to enable or
disable the trapping of task switches.
"""
from . import plugins
from .. import api

class TaskSwitchPluginBase(plugins.EventPlugin):
    """Base task switch plugin.

    This is the base plugin for all task switch plugins on the various
    architectures.
    """
    _abstract = True
    name = "TaskSwitchPlugin"
    produces = [api.SystemEventTaskSwitch]

    def __init__(self):
        super().__init__()

        self._request_id_cntr = 0
        self._requests = dict()

    def uninit(self):
        super().uninit()

        while self._requests:
            _, request = self.request.popitem()
            self._update_feature(request, enable=False)

    def _update_feature(self, request, enable=True):
        """Update the state of the task switch feature.

        This function decides whether a feature update request should be
        send to the kernel. It will consider the current state of the task
        switch feature and the new request to decide whether a feature
        request is necessary.

        Parameters
        ----------
        request : dict
            The parameters of the new request.
        enable : bool
            Whether this is a new event request or the cancelation of a
            previous request.
        """
        pass

    def request_event(self, event_cls, **kwargs):
        # Parse request
        request = event_cls.parse_request_to_dict(**kwargs)

        # Update feature
        self._update_feature(request, enable=True)

        # Store request
        request_id = self._request_id_cntr
        self._request_id_cntr += 1
        self._requests[request_id] = request

        return request_id

    def cancel_event(self, request_id):
        request = self._requests.pop(request_id)
        self._update_feature(request, enable=False)

class TaskSwitchPluginX86_64(TaskSwitchPluginBase):
    """Task switching plugin for x86-64.

    This plugin allows to trap task switches on x86-64. Task switch trapping
    will be enabled if a :py:class:`tenjint.api.api_x86_64.SystemEventTaskSwitch`
    event is requested and disabled if all requests for
    :py:class:`tenjint.api.api_x86_64.SystemEventTaskSwitch` have been
    canceled.
    """
    _abstract = False
    arch = api.Arch.X86_64

    def _update_feature(self, request, enable=True):
        # Check if this request is covered
        found = None
        incoming = False
        outgoing = False

        f = filter(lambda v: v["dtb"] == request["dtb"],
                   self._requests.values())
        for x in f:
            if not found:
                # At least
                found = True

            if (x["incoming"]):
                incoming = True

            if (x["outgoing"]):
                outgoing = True

            if (incoming and outgoing):
                # Request covered
                break

        if not found and not enable:
            api.tenjint_api_update_feature_taskswitch(False,
                                                     request["dtb"],
                                                     incoming,
                                                     outgoing)
        else:
            if (not found or
                (request["incoming"] and not incoming) or
                (request["outgoing"] and not outgoing)):
                if enable:
                    if not incoming and enable:
                        incoming = request["incoming"]
                    if not outgoing and enable:
                        outgoing = request["outgoing"]

                api.tenjint_api_update_feature_taskswitch(True,
                                                         request["dtb"],
                                                         incoming,
                                                         outgoing)


class TaskSwitchPluginAarch64(TaskSwitchPluginBase):
    """Task switching plugin for aarch64.

    This plugin allows to trap task switches on aarch64. Task switch trapping
    will be enabled if a
    :py:class:`tenjint.api.api_aarch64.SystemEventTaskSwitch`
    event is requested and disabled if all requests for
    :py:class:`tenjint.api.api_aarch64.SystemEventTaskSwitch` have been
    canceled.
    """
    _abstract = False
    arch = api.Arch.AARCH64

    def _update_feature(self, request, enable=True):
        # Check if this request is covered
        found = None

        f = filter(lambda v: v["reg"] == request["reg"],
                   self._requests.values())
        for x in f:
            if not found:
                # At least
                found = True
                break

        if not found and not enable:
            api.tenjint_api_update_feature_taskswitch(False, request["reg"])
        elif not found:
            api.tenjint_api_update_feature_taskswitch(True, request["reg"])
