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

from . import plugins
from .. import api
from .. import event

class SingleStepPluginBase(plugins.EventPlugin):
    _abstract = True
    produces = [api.SystemEventSingleStep]
    name = "SingleStepPlugin"

    def __init__(self):
        super().__init__()
        self._request_id_cntr = 0

        self._ss = [None] * self._vm.cpu_count
        self._ss_inst_ptr = [None] * self._vm.cpu_count

        self._cb_ss = event.EventCallback(self._cb_func_ss, "SystemEventSingleStep")
        self._event_manager.request_event(self._cb_ss, send_request=False)

    def uninit(self):
        super().uninit()
        self._event_manager.cancel_event(self._cb_ss)
        self._cb_ss = None

    def request_event(self, event_cls, **kwargs):
        [cpu_num, method] = event_cls.parse_request(**kwargs)

        if method is None:
            method = self._default_method

        if self._ss[cpu_num] is not None and self._ss[cpu_num] != method:
            raise ValueError("attempting to SS same cpu with multiple methods")

        request_id = self._request_id_cntr
        self._request_id_cntr += 1

        self._feature_update(True, method, cpu_num)

        self._ss[cpu_num] = method
        self._ss_inst_ptr[cpu_num] = self._vm.cpu(cpu_num).instruction_pointer
        return request_id

    def cancel_event(self, request_id):
        return

    def _cb_func_ss(self, event):
        if self._ss[event.cpu_num] is None:
            self._logger.warning("non-service SS recieved")
        self._feature_update(False, self._ss[event.cpu_num], event.cpu_num)
        self._logger.debug("SS CPU{} PC:{:x}".format(event.cpu_num,
                               self._vm.cpu(event.cpu_num).instruction_pointer))

    def last_ss_gva(self, cpu_num):
        return self._ss_inst_ptr[cpu_num]

class SingleStepPluginAarch64(SingleStepPluginBase):
    _abstract = False
    arch = api.Arch.AARCH64

    _default_method = api.SingleStepMethod.DEBUG

    def _feature_update(self, enable, method, cpu_num):
        if method is not api.SingleStepMethod.DEBUG:
            raise ValueError("Unexpected single step method recieved.")
        api.tenjint_api_update_feature_debug(cpu_num=cpu_num, enable=enable,
                                            single_step=True)

class SingleStepPluginX86(SingleStepPluginBase):
    _abstract = False
    arch = api.Arch.X86_64

    _default_method = api.SingleStepMethod.MTF

    def _feature_update(self, enable, method, cpu_num):
        if method == api.SingleStepMethod.MTF:
            api.tenjint_api_update_feature_mtf(cpu_num, enable)
        elif method == api.SingleStepMethod.DEBUG:
            api.tenjint_api_update_feature_debug(cpu_num=cpu_num, enable=enable,
                                                single_step=True)
        else:
            raise ValueError("Unexpected single step method recieved.")
