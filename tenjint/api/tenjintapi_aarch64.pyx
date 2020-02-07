# cython: language_level=3

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

import numpy

from . cimport tenjintapi

from . import api
from . import api_aarch64

ctypedef signed char __s8
ctypedef signed short __s16
ctypedef signed int __s32
ctypedef signed long long __s64
ctypedef unsigned char __u8
ctypedef unsigned short __u16
ctypedef unsigned int __u32
ctypedef unsigned long long __u64

ctypedef signed char  int8_t
ctypedef signed short int16_t
ctypedef signed int int32_t
ctypedef signed long long int64_t
ctypedef unsigned char  uint8_t
ctypedef unsigned short uint16_t
ctypedef unsigned int uint32_t
ctypedef unsigned long long uint64_t

ctypedef unsigned long long target_ulong
ctypedef signed long long target_long

cdef extern from "asm-arm64/kvm_vmi.h":
    const int KVM_VMI_FEATURE_TRAP_TASK_SWITCH
    const int KVM_VMI_FEATURE_SLP
    const int KVM_VMI_FEATURE_DEBUG
    const int KVM_VMI_FEATURE_MAX

    const int KVM_VMI_EVENT_TASK_SWITCH
    const int KVM_VMI_EVENT_SLP
    const int KVM_VMI_EVENT_DEBUG

    const int KVM_VMI_TTBR0
    const int KVM_VMI_TTBR1
    const int KVM_VMI_TCR

    struct kvm_vmi_feature_task_switch:
        __u32 feature
        __u8 enable
        __u8 reg

    struct kvm_vmi_feature_slp:
        __u32 feature
        __u8 enable
        __u8 global_req
        __u64 gfn
        __u64 num_pages
        __u64 violation

    struct kvm_vmi_feature_debug:
        __u32 feature
        __u8 enable
        __u8 single_step
        __u8 watchpoint
        __u64 addr

    union kvm_vmi_feature:
        __u32 feature
        kvm_vmi_feature_task_switch ts
        kvm_vmi_feature_slp slp
        kvm_vmi_feature_debug debug

    struct kvm_vmi_event_task_switch:
        __u32 type
        __u32 cpu_num
        __u8 reg
        __u64 old_val
        __u64 new_val

    struct kvm_vmi_event_slp:
        __u32 type
        __u32 cpu_num
        __u64 violation
        __u64 gva
        __u64 gpa
        __u8 rwx

    struct kvm_vmi_event_debug:
        __u32 type
        __u32 cpu_num
        __u8 single_step
        __u8 watchpoint
        __u64 watchpoint_gva
        __s32 watchpoint_flags
        __u64 breakpoint_gva
        __u64 breakpoint_gpa

    union kvm_vmi_event:
        __u32 type
        kvm_vmi_event_task_switch ts
        kvm_vmi_event_slp slp
        kvm_vmi_event_debug debug

cdef extern from "qemu/osdep.h":
    pass

cdef extern from "arm/cpu.h":
    ctypedef struct TCR:
        uint64_t raw_tcr
        uint32_t mask
        uint32_t base_mask

    struct _cp15_t:
        uint64_t ttbr0_el[4]
        uint64_t ttbr1_el[4]
        uint64_t vttbr_el2
        TCR tcr_el[4]
        TCR vtcr_el2

    struct CPUARMState:
        uint32_t regs[16]
        uint64_t xregs[32]
        uint64_t pc
        uint64_t elr_el[4]
        uint64_t sp_el[4]
        _cp15_t cp15

    struct ARMCPU:
        CPUARMState env

cdef extern from "arm/vmi_api.h":
    CPUARMState* vmi_api_get_cpu_state(uint32_t)

cdef class Aarch64CpuState:
    cdef CPUARMState *_qemu_arm_cpu_state
    cdef int32_t _dirty
    cdef uint32_t cpu_num

    def __cinit__(self, cpu_num):
        self.cpu_num = numpy.uint32(cpu_num)

    cdef reset(self, CPUARMState *state):
        self._dirty = 0
        self._qemu_arm_cpu_state = state

    # virtual registers
    @property
    def instruction_pointer(self):
        return self._qemu_arm_cpu_state.pc

    @instruction_pointer.setter
    def instruction_pointer(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.pc = numpy.uint64(value)

    def page_table_base(self, addr):
        t0sz = self.tcr_el1 & 0x3f
        mask = ~numpy.uint64(((2**(64-t0sz))-1))
        if (numpy.uint64(addr) & mask):
            return self.ttbr1_el1 & 0xfffffffffffe
        else:
            return self.ttbr0_el1 & 0xfffffffffffe

    # physical registers
    @property
    def r0(self):
        return self._qemu_arm_cpu_state.xregs[0]

    @r0.setter
    def r0(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[0] = numpy.uint64(value)

    @property
    def r1(self):
        return self._qemu_arm_cpu_state.xregs[1]

    @r1.setter
    def r1(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[1] = numpy.uint64(value)

    @property
    def r2(self):
        return self._qemu_arm_cpu_state.xregs[2]

    @r2.setter
    def r2(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[2] = numpy.uint64(value)

    @property
    def r3(self):
        return self._qemu_arm_cpu_state.xregs[3]

    @r3.setter
    def r3(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[3] = numpy.uint64(value)

    @property
    def r4(self):
        return self._qemu_arm_cpu_state.xregs[4]

    @r4.setter
    def r4(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[4] = numpy.uint64(value)

    @property
    def r5(self):
        return self._qemu_arm_cpu_state.xregs[5]

    @r5.setter
    def r5(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[5] = numpy.uint64(value)

    @property
    def r6(self):
        return self._qemu_arm_cpu_state.xregs[6]

    @r6.setter
    def r6(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[6] = numpy.uint64(value)

    @property
    def r7(self):
        return self._qemu_arm_cpu_state.xregs[7]

    @r7.setter
    def r7(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[7] = numpy.uint64(value)

    @property
    def r8(self):
        return self._qemu_arm_cpu_state.xregs[8]

    @r8.setter
    def r8(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[8] = numpy.uint64(value)

    @property
    def r9(self):
        return self._qemu_arm_cpu_state.xregs[9]

    @r9.setter
    def r9(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[9] = numpy.uint64(value)

    @property
    def r10(self):
        return self._qemu_arm_cpu_state.xregs[10]

    @r10.setter
    def r10(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[10] = numpy.uint64(value)

    @property
    def r11(self):
        return self._qemu_arm_cpu_state.xregs[11]

    @r11.setter
    def r11(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[11] = numpy.uint64(value)

    @property
    def r12(self):
        return self._qemu_arm_cpu_state.xregs[12]

    @r12.setter
    def r12(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[12] = numpy.uint64(value)

    @property
    def r13(self):
        return self._qemu_arm_cpu_state.xregs[13]

    @r13.setter
    def r13(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[13] = numpy.uint64(value)

    @property
    def r14(self):
        return self._qemu_arm_cpu_state.xregs[14]

    @r14.setter
    def r14(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[14] = numpy.uint64(value)

    @property
    def r15(self):
        return self._qemu_arm_cpu_state.xregs[15]

    @r15.setter
    def r15(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[15] = numpy.uint64(value)

    @property
    def r16(self):
        return self._qemu_arm_cpu_state.xregs[16]

    @r16.setter
    def r16(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[16] = numpy.uint64(value)

    @property
    def r17(self):
        return self._qemu_arm_cpu_state.xregs[17]

    @r17.setter
    def r17(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[17] = numpy.uint64(value)

    @property
    def r18(self):
        return self._qemu_arm_cpu_state.xregs[18]

    @r18.setter
    def r18(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[18] = numpy.uint64(value)

    @property
    def r19(self):
        return self._qemu_arm_cpu_state.xregs[19]

    @r19.setter
    def r19(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[19] = numpy.uint64(value)

    @property
    def r20(self):
        return self._qemu_arm_cpu_state.xregs[20]

    @r20.setter
    def r20(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[20] = numpy.uint64(value)

    @property
    def r21(self):
        return self._qemu_arm_cpu_state.xregs[21]

    @r21.setter
    def r21(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[21] = numpy.uint64(value)

    @property
    def r22(self):
        return self._qemu_arm_cpu_state.xregs[22]

    @r22.setter
    def r22(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[22] = numpy.uint64(value)

    @property
    def r23(self):
        return self._qemu_arm_cpu_state.xregs[23]

    @r23.setter
    def r23(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[23] = numpy.uint64(value)

    @property
    def r24(self):
        return self._qemu_arm_cpu_state.xregs[24]

    @r24.setter
    def r24(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[24] = numpy.uint64(value)

    @property
    def r25(self):
        return self._qemu_arm_cpu_state.xregs[25]

    @r25.setter
    def r25(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[25] = numpy.uint64(value)

    @property
    def r26(self):
        return self._qemu_arm_cpu_state.xregs[26]

    @r26.setter
    def r26(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[26] = numpy.uint64(value)

    @property
    def r27(self):
        return self._qemu_arm_cpu_state.xregs[27]

    @r27.setter
    def r27(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[27] = numpy.uint64(value)

    @property
    def r28(self):
        return self._qemu_arm_cpu_state.xregs[28]

    @r28.setter
    def r28(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[28] = numpy.uint64(value)

    @property
    def r29(self):
        return self._qemu_arm_cpu_state.xregs[29]

    @r29.setter
    def r29(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[29] = numpy.uint64(value)

    @property
    def r30(self):
        return self._qemu_arm_cpu_state.xregs[30]

    @r30.setter
    def r30(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[30] = numpy.uint64(value)

    @property
    def r31(self):
        return self._qemu_arm_cpu_state.xregs[31]

    @r31.setter
    def r31(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.xregs[31] = numpy.uint64(value)

    @property
    def pc(self):
        return self._qemu_arm_cpu_state.pc

    @pc.setter
    def pc(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.pc = numpy.uint64(value)

    @property
    def sp_el0(self):
        return self._qemu_arm_cpu_state.sp_el[0]

    @sp_el0.setter
    def sp_el0(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.sp_el[0] = numpy.uint64(value)

    @property
    def sp_el1(self):
        return self._qemu_arm_cpu_state.sp_el[1]

    @sp_el1.setter
    def sp_el1(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.sp_el[1] = numpy.uint64(value)

    @property
    def sp_el2(self):
        return self._qemu_arm_cpu_state.sp_el[2]

    @sp_el2.setter
    def sp_el2(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.sp_el[2] = numpy.uint64(value)

    @property
    def sp_el3(self):
        return self._qemu_arm_cpu_state.sp_el[3]

    @sp_el3.setter
    def sp_el3(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.sp_el[3] = numpy.uint64(value)

    @property
    def ttbr0_el0(self):
        return self._qemu_arm_cpu_state.cp15.ttbr0_el[0]

    @ttbr0_el0.setter
    def ttbr0_el0(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr0_el[0] = numpy.uint64(value)

    @property
    def ttbr0_el1(self):
        return self._qemu_arm_cpu_state.cp15.ttbr0_el[1]

    @ttbr0_el1.setter
    def ttbr0_el1(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr0_el[1] = numpy.uint64(value)

    @property
    def ttbr0_el2(self):
        return self._qemu_arm_cpu_state.cp15.ttbr0_el[2]

    @ttbr0_el2.setter
    def ttbr0_el2(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr0_el[2] = numpy.uint64(value)

    @property
    def ttbr0_el3(self):
        return self._qemu_arm_cpu_state.cp15.ttbr0_el[3]

    @ttbr0_el3.setter
    def ttbr0_el3(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr0_el[3] = numpy.uint64(value)

    @property
    def ttbr1_el0(self):
        return self._qemu_arm_cpu_state.cp15.ttbr1_el[0]

    @ttbr1_el0.setter
    def ttbr1_el0(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr1_el[0] = numpy.uint64(value)

    @property
    def ttbr1_el1(self):
        return self._qemu_arm_cpu_state.cp15.ttbr1_el[1]

    @ttbr1_el1.setter
    def ttbr1_el1(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr1_el[1] = numpy.uint64(value)

    @property
    def ttbr1_el2(self):
        return self._qemu_arm_cpu_state.cp15.ttbr1_el[2]

    @ttbr1_el2.setter
    def ttbr1_el2(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr1_el[2] = numpy.uint64(value)

    @property
    def ttbr1_el3(self):
        return self._qemu_arm_cpu_state.cp15.ttbr1_el[3]

    @ttbr1_el3.setter
    def ttbr1_el3(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.ttbr1_el[3] = numpy.uint64(value)

    @property
    def tcr_el1(self):
        return self._qemu_arm_cpu_state.cp15.tcr_el[1].raw_tcr

    @tcr_el1.setter
    def tcr_el1(self, value):
        self._dirty = 1
        self._qemu_arm_cpu_state.cp15.tcr_el[1].raw_tcr = value

    @property
    def pointer_width(self):
        return 8

    def __repr__(self):
        result = "CPU {} State\n".format(self.cpu_num)
        result += "-----------------------------------------------\n"
        result += "R0:  0x{:016x}\tR1:  0x{:016x}\n".format(self.r0, self.r1)
        result += "R2:  0x{:016x}\tR3:  0x{:016x}\n".format(self.r2, self.r3)
        result += "R4:  0x{:016x}\tR5:  0x{:016x}\n".format(self.r4, self.r5)
        result += "R6:  0x{:016x}\tR7:  0x{:016x}\n".format(self.r6, self.r7)
        result += "R8:  0x{:016x}\tR9:  0x{:016x}\n".format(self.r8, self.r9)
        result += "R10: 0x{:016x}\tR11: 0x{:016x}\n".format(self.r10, self.r11)
        result += "R12: 0x{:016x}\tR13: 0x{:016x}\n".format(self.r12, self.r13)
        result += "R14: 0x{:016x}\tR15: 0x{:016x}\n".format(self.r14, self.r15)
        result += "R16: 0x{:016x}\tR17: 0x{:016x}\n".format(self.r16, self.r17)
        result += "R18: 0x{:016x}\tR19: 0x{:016x}\n".format(self.r18, self.r19)
        result += "R20: 0x{:016x}\tR21: 0x{:016x}\n".format(self.r20, self.r21)
        result += "R22: 0x{:016x}\tR23: 0x{:016x}\n".format(self.r22, self.r23)
        result += "R24: 0x{:016x}\tR25: 0x{:016x}\n".format(self.r24, self.r25)
        result += "R26: 0x{:016x}\tR27: 0x{:016x}\n".format(self.r26, self.r27)
        result += "R28: 0x{:016x}\tR29: 0x{:016x}\n".format(self.r28, self.r29)
        result += "R30: 0x{:016x}\tR31: 0x{:016x}\n".format(self.r30, self.r31)
        result += "\n"
        result += "PC:  0x{:016x}\n".format(self.pc)
        result += "SP_EL0: 0x{:016x}\tSP_EL1: 0x{:016x}\n".format(self.sp_el0,
                                                                  self.sp_el1)
        result += "SP_EL2: 0x{:016x}\tSP_EL3: 0x{:016x}\n".format(self.sp_el2,
                                                                  self.sp_el3)
        result += "\n"
        result += "TTBR0_EL0: 0x{:016x}\tTTBR0_EL1: 0x{:016x}\n".format(
                                                                self.ttbr0_el0,
                                                                self.ttbr0_el1)
        result += "TTBR0_EL2: 0x{:016x}\tTTBR0_EL3: 0x{:016x}\n".format(
                                                                self.ttbr0_el2,
                                                                self.ttbr0_el3)
        result += "TTBR1_EL0: 0x{:016x}\tTTBR1_EL1: 0x{:016x}\n".format(
                                                                self.ttbr1_el0,
                                                                self.ttbr1_el1)
        result += "TTBR1_EL2: 0x{:016x}\tTTBR1_EL3: 0x{:016x}\n".format(
                                                                self.ttbr1_el2,
                                                                self.ttbr1_el3)
        result += "TCR_EL1: 0x{:016x}\n".format(self.tcr_el1)
        result += "\n"

        return result

cdef dict CPU_STATE = {}
def tenjint_api_get_cpu_state(cpu_num):
    if cpu_num not in CPU_STATE:
        CPU_STATE[cpu_num] = Aarch64CpuState(cpu_num)
    c_cpu_state = vmi_api_get_cpu_state(cpu_num)
    (<Aarch64CpuState>CPU_STATE[cpu_num]).reset(c_cpu_state)
    return CPU_STATE[cpu_num]

cdef _aarch64_decode_event(kvm_vmi_event *c_event):
    if c_event.type == KVM_VMI_EVENT_TASK_SWITCH:
        return api_aarch64.SystemEventTaskSwitch(c_event.ts.cpu_num,
                                     api_aarch64.Aarch64TsRegs(c_event.ts.reg),
                                     c_event.ts.old_val,
                                     c_event.ts.new_val)
    elif c_event.type == KVM_VMI_EVENT_SLP:
        return api_aarch64.SystemEventSLP(c_event.slp.cpu_num,
                        c_event.slp.gva,
                        c_event.slp.gpa,
                        bool(c_event.slp.violation & tenjintapi.KVM_VMI_SLP_R),
                        bool(c_event.slp.violation & tenjintapi.KVM_VMI_SLP_W),
                        bool(c_event.slp.violation & tenjintapi.KVM_VMI_SLP_X),
                        bool(c_event.slp.rwx))
    elif c_event.type == KVM_VMI_EVENT_DEBUG:
        if c_event.debug.single_step:
            return api.SystemEventSingleStep(c_event.debug.cpu_num,
                                             api.SingleStepMethod.DEBUG)
        elif c_event.debug.watchpoint:
            raise NotImplementedError()
        else:
            return api.SystemEventBreakpoint(c_event.debug.cpu_num,
                                             c_event.debug.breakpoint_gva,
                                             c_event.debug.breakpoint_gpa)
    else:
        raise RuntimeError()

def tenjint_api_get_event():
    c_event = tenjintapi.vmi_api_get_event()
    if c_event == NULL:
        return None
    if c_event.type == tenjintapi.VMI_EVENT_KVM:
        return _aarch64_decode_event(c_event.kvm_vmi_event)
    return tenjintapi._decode_event(c_event)

def tenjint_api_update_feature_taskswitch(enable, reg):
    cdef kvm_vmi_feature c_feature

    c_feature.feature = KVM_VMI_FEATURE_TRAP_TASK_SWITCH
    c_feature.ts.enable = enable
    c_feature.ts.reg = reg.value

    rv = tenjintapi.vmi_api_feature_update_all(&c_feature)

    if rv < 0:
        raise api.QemuFeatureError("TS feature update returned {}".format(rv))

def tenjint_api_update_feature_slp(cpu_num, enable, global_req, gfn, num_pages,
                                  req_r, req_w, req_x):
    cdef kvm_vmi_feature c_feature

    c_feature.feature = KVM_VMI_FEATURE_SLP
    c_feature.slp.enable = enable
    c_feature.slp.global_req = global_req
    c_feature.slp.gfn = 0 if gfn is None else gfn
    c_feature.slp.num_pages = 0 if num_pages is None else num_pages
    c_feature.slp.violation = tenjintapi.KVM_VMI_SLP_R if req_r else 0
    c_feature.slp.violation |= tenjintapi.KVM_VMI_SLP_W if req_w else 0
    c_feature.slp.violation |= tenjintapi.KVM_VMI_SLP_X if req_x else 0

    if cpu_num is None:
        rv = tenjintapi.vmi_api_feature_update_all(&c_feature)
    else:
        rv = tenjintapi.vmi_api_feature_update_single(cpu_num, &c_feature)

    if rv < 0:
        raise api.QemuFeatureError("SLP feature update returned {}".format(rv))

def tenjint_api_update_feature_debug(cpu_num, enable, single_step=False,
                                    watchpoint=False, gpa=None):
    cdef kvm_vmi_feature c_feature

    if (not single_step and not watchpoint and gpa is None):
        raise ValueError("debug feature must be single step, watchpoint, "
                         "or breakpoint")

    if (single_step and cpu_num is None):
        raise ValueError("cpu_num must be set when single stepping")

    c_feature.feature = KVM_VMI_FEATURE_DEBUG
    c_feature.debug.enable = enable
    c_feature.debug.single_step = single_step
    c_feature.debug.watchpoint = watchpoint
    c_feature.debug.addr = gpa if gpa is not None else 0

    if cpu_num is None:
        rv = tenjintapi.vmi_api_feature_update_all(&c_feature)
    else:
        rv = tenjintapi.vmi_api_feature_update_single(cpu_num, &c_feature)

    if rv < 0:
        raise api.QemuFeatureError("Debug feature update returned {}".format(rv))

    return rv
