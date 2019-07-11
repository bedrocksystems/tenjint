# cython: language_level=3

import numpy

from . cimport tenjintapi

from . import api
from . import api_x86_64

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

cdef extern from "asm-x86/kvm_vmi.h":
    const int MAX_LBR_ENTRIES

    const int KVM_VMI_FEATURE_TRAP_TASK_SWITCH
    const int KVM_VMI_FEATURE_LBR
    const int KVM_VMI_FEATURE_MTF
    const int KVM_VMI_FEATURE_SLP
    const int KVM_VMI_FEATURE_DEBUG
    const int KVM_VMI_FEATURE_MAX

    const int KVM_VMI_EVENT_TASK_SWITCH
    const int KVM_VMI_EVENT_DEBUG
    const int KVM_VMI_EVENT_MTF
    const int KVM_VMI_EVENT_SLP

    struct kvm_vmi_feature_task_switch:
        __u32 feature
        __u8 enable
        __u64 dtb
        __u8 incoming
        __u8 outgoing

    struct kvm_vmi_feature_lbr:
        __u32 feature
        __u8 enable
        __u64 lbr_select

    struct kvm_vmi_feature_mtf:
        __u32 feature
        __u8  enable

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
        kvm_vmi_feature_lbr lbr
        kvm_vmi_feature_mtf mtf
        kvm_vmi_feature_slp slp
        kvm_vmi_feature_debug debug

    struct kvm_vmi_event_task_switch:
        __u32 type
        __u32 cpu_num
        __u64 old_cr3
        __u64 new_cr3

    struct kvm_vmi_event_debug:
        __u32 type
        __u32 cpu_num
        __u8 single_step
        __u8 watchpoint
        __u64 watchpoint_gva
        __s32 watchpoint_flags
        __u64 breakpoint_gva
        __u64 breakpoint_gpa

    struct kvm_vmi_event_mtf:
        __u32 type
        __u32 cpu_num

    struct kvm_vmi_event_slp:
        __u32 type
        __u32 cpu_num
        __u64 violation
        __u64 gva
        __u64 gpa
        __u8 rwx

    union kvm_vmi_event:
        __u32 type
        kvm_vmi_event_task_switch ts
        kvm_vmi_event_debug debug
        kvm_vmi_event_mtf mtf
        kvm_vmi_event_slp slp

    struct kvm_vmi_lbr_info:
        __u32 entries
        __u8 tos
        __u64 lbr_from[MAX_LBR_ENTRIES]
        __u64 lbr_to[MAX_LBR_ENTRIES]

cdef extern from "qemu/osdep.h":
    pass

cdef extern from "i386/cpu.h":
    const int CPU_NB_REGS

    const int R_EAX
    const int R_ECX
    const int R_EDX
    const int R_EBX
    const int R_ESP
    const int R_EBP
    const int R_ESI
    const int R_EDI
    const int R_R8
    const int R_R9
    const int R_R10
    const int R_R11
    const int R_R12
    const int R_R13
    const int R_R14
    const int R_R15

    const int R_ES
    const int R_CS
    const int R_SS
    const int R_DS
    const int R_FS
    const int R_GS
    const int R_LDTR
    const int R_TR

    struct SegmentCache:
        uint32_t selector
        target_ulong base
        uint32_t limit
        uint32_t flags

    struct CPUX86State:
        target_ulong regs[CPU_NB_REGS]
        target_ulong eip
        target_ulong eflags

        SegmentCache segs[6]
        SegmentCache ldt
        SegmentCache tr
        SegmentCache gdt
        SegmentCache idt

        target_ulong cr[5]

    struct X86CPU:
        CPUX86State env

cdef extern from "i386/vmi_api.h":
    CPUX86State* vmi_api_get_cpu_state(uint32_t)
    int vmi_api_get_lbr_state(uint32_t cpu_num,
                              kvm_vmi_lbr_info *lbr_state)

cdef class X86SegmentState:
    cdef SegmentCache *_qemu_x86_segment_state
    cdef int32_t _dirty

    cdef reset(self, SegmentCache *state):
        self._dirty = 0
        self._qemu_x86_segment_state = state

    @property
    def selector(self):
        return self._qemu_x86_segment_state.selector

    @selector.setter
    def selector(self, value):
        self._dirty = 1
        self._qemu_x86_segment_state.selector = numpy.uint32(value)

    @property
    def base(self):
        return self._qemu_x86_segment_state.base

    @base.setter
    def base(self, value):
        self._dirty = 1
        self._qemu_x86_segment_state.base = numpy.uint64(value)

    @property
    def limit(self):
        return self._qemu_x86_segment_state.limit

    @limit.setter
    def limit(self, value):
        self._dirty = 1
        self._qemu_x86_segment_state.limit = numpy.uint32(value)

    @property
    def flags(self):
        return self._qemu_x86_segment_state.flags

    @flags.setter
    def flags(self, value):
        self._dirty = 1
        self._qemu_x86_segment_state.flags = numpy.uint32(value)

    def __repr__(self):
        return "{:04x} {:016x} {:08x} {:08x}".format(self.selector, self.base,
                                                     self.limit, self.flags)


cdef class X86CpuState:
    cdef CPUX86State *_qemu_x86_cpu_state
    cdef int32_t _dirty
    cdef uint32_t cpu_num

    cdef public X86SegmentState es
    cdef public X86SegmentState cs
    cdef public X86SegmentState ss
    cdef public X86SegmentState ds
    cdef public X86SegmentState fs
    cdef public X86SegmentState gs

    cdef public X86SegmentState ldt
    cdef public X86SegmentState tr
    cdef public X86SegmentState gdt
    cdef public X86SegmentState idt

    def __cinit__(self, cpu_num):
        self.es = X86SegmentState()
        self.cs = X86SegmentState()
        self.ss = X86SegmentState()
        self.ds = X86SegmentState()
        self.fs = X86SegmentState()
        self.gs = X86SegmentState()

        self.ldt = X86SegmentState()
        self.tr = X86SegmentState()
        self.gdt = X86SegmentState()
        self.idt = X86SegmentState()
        self.cpu_num = numpy.uint32(cpu_num)

    def __dealloc__(self):
        del self.es
        del self.cs
        del self.ss
        del self.ds
        del self.fs
        del self.gs

        del self.ldt
        del self.tr
        del self.gdt
        del self.idt

    cdef reset(self, CPUX86State *state):
        self._dirty = 0
        self._qemu_x86_cpu_state = state

        self.es.reset(&(state.segs[R_ES]))
        self.cs.reset(&(state.segs[R_CS]))
        self.ss.reset(&(state.segs[R_SS]))
        self.ds.reset(&(state.segs[R_DS]))
        self.fs.reset(&(state.segs[R_FS]))
        self.gs.reset(&(state.segs[R_GS]))

        self.ldt.reset(&(state.ldt))
        self.tr.reset(&(state.tr))
        self.gdt.reset(&(state.gdt))
        self.idt.reset(&(state.idt))

    # virtual registers
    @property
    def instruction_pointer(self):
        return self._qemu_x86_cpu_state.eip

    @instruction_pointer.setter
    def instruction_pointer(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.eip = numpy.uint64(value)

    def page_table_base(self, addr):
        return self._qemu_x86_cpu_state.cr[3]

    # physical registers
    @property
    def rax(self):
        return self._qemu_x86_cpu_state.regs[R_EAX]

    @rax.setter
    def rax(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_EAX] = numpy.uint64(value)

    @property
    def rbx(self):
        return self._qemu_x86_cpu_state.regs[R_EBX]

    @rbx.setter
    def rbx(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_EBX] = numpy.uint64(value)

    @property
    def rcx(self):
        return self._qemu_x86_cpu_state.regs[R_ECX]

    @rcx.setter
    def rcx(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_ECX] = numpy.uint64(value)

    @property
    def rdx(self):
        return self._qemu_x86_cpu_state.regs[R_EDX]

    @rdx.setter
    def rdx(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_EDX] = numpy.uint64(value)

    @property
    def rsp(self):
        return self._qemu_x86_cpu_state.regs[R_ESP]

    @rsp.setter
    def rsp(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_ESP] = numpy.uint64(value)

    @property
    def rbp(self):
        return self._qemu_x86_cpu_state.regs[R_EBP]

    @rbp.setter
    def rbp(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_EBP] = numpy.uint64(value)

    @property
    def rsi(self):
        return self._qemu_x86_cpu_state.regs[R_ESI]

    @rsi.setter
    def rsi(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_ESI] = numpy.uint64(value)

    @property
    def rdi(self):
        return self._qemu_x86_cpu_state.regs[R_EDI]

    @rdi.setter
    def rdi(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_EDI] = numpy.uint64(value)

    @property
    def r8(self):
        return self._qemu_x86_cpu_state.regs[R_R8]

    @r8.setter
    def r8(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R8] = numpy.uint64(value)

    @property
    def r9(self):
        return self._qemu_x86_cpu_state.regs[R_R9]

    @r9.setter
    def r9(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R9] = numpy.uint64(value)

    @property
    def r10(self):
        return self._qemu_x86_cpu_state.regs[R_R10]

    @r10.setter
    def r10(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R10] = numpy.uint64(value)

    @property
    def r11(self):
        return self._qemu_x86_cpu_state.regs[R_R11]

    @r11.setter
    def r11(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R11] = numpy.uint64(value)

    @property
    def r12(self):
        return self._qemu_x86_cpu_state.regs[R_R12]

    @r12.setter
    def r12(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R12] = numpy.uint64(value)

    @property
    def r13(self):
        return self._qemu_x86_cpu_state.regs[R_R13]

    @r13.setter
    def r13(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R13] = numpy.uint64(value)

    @property
    def r14(self):
        return self._qemu_x86_cpu_state.regs[R_R14]

    @r14.setter
    def r14(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R14] = numpy.uint64(value)

    @property
    def r15(self):
        return self._qemu_x86_cpu_state.regs[R_R15]

    @r15.setter
    def r15(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.regs[R_R15] = numpy.uint64(value)

    @property
    def rip(self):
        return self._qemu_x86_cpu_state.eip

    @rip.setter
    def rip(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.eip = numpy.uint64(value)

    @property
    def rflags(self):
        return self._qemu_x86_cpu_state.eflags

    @rflags.setter
    def rflags(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.eflags = numpy.uint64(value)

    @property
    def cr0(self):
        return self._qemu_x86_cpu_state.cr[0]

    @cr0.setter
    def cr0(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.cr[0] = numpy.uint64(value)

    @property
    def cr2(self):
        return self._qemu_x86_cpu_state.cr[2]

    @cr2.setter
    def cr2(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.cr[2] = numpy.uint64(value)

    @property
    def cr3(self):
        return self._qemu_x86_cpu_state.cr[3]

    @cr3.setter
    def cr3(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.cr[3] = numpy.uint64(value)

    @property
    def cr4(self):
        return self._qemu_x86_cpu_state.cr[4]

    @cr4.setter
    def cr4(self, value):
        self._dirty = 1
        self._qemu_x86_cpu_state.cr[4] = numpy.uint64(value)

    def __repr__(self):
        result = "CPU {} State\n".format(self.cpu_num)
        result += "-----------------------------------------------\n"
        result += "RAX: 0x{:016x}\tRBX: 0x{:016x}\n".format(self.rax, self.rbx)
        result += "RCX: 0x{:016x}\tRDX: 0x{:016x}\n".format(self.rcx, self.rdx)
        result += "RSI: 0x{:016x}\tRDI: 0x{:016x}\n".format(self.rsi, self.rdi)
        result += "R8:  0x{:016x}\tR9:  0x{:016x}\n".format(self.r8, self.r9)
        result += "R10: 0x{:016x}\tR11: 0x{:016x}\n".format(self.r10, self.r11)
        result += "R12: 0x{:016x}\tR13: 0x{:016x}\n".format(self.r12, self.r13)
        result += "R14: 0x{:016x}\tR15: 0x{:016x}\n".format(self.r14, self.r15)
        result += "\n"
        result += "RIP: 0x{:016x}\tRSP: 0x{:016x}\n".format(self.rip, self.rsp)
        result += "RBP: 0x{:016x}\n".format(self.rbp)
        result += "\n"
        result += "CR0: 0x{:016x}\tCR2: 0x{:016x}\n".format(self.cr0, self.cr2)
        result += "CR3: 0x{:016x}\tCR4: 0x{:016x}\n".format(self.cr3, self.cr4)
        result += "\n"
        result += "ES:  {}\n".format(self.es)
        result += "CS:  {}\n".format(self.cs)
        result += "SS:  {}\n".format(self.ss)
        result += "DS:  {}\n".format(self.ds)
        result += "FS:  {}\n".format(self.fs)
        result += "GS:  {}\n".format(self.gs)
        result += "\n"
        result += "LDT: {}\n".format(self.ldt)
        result += "TR:  {}\n".format(self.tr)
        result += "GDT: {}\n".format(self.gdt)
        result += "IDT: {}\n".format(self.idt)
        result += "\n"
        result += "FLAGS: 0x{:016x}\n".format(self.rflags)
        result += "\n"

        return result

cdef dict CPU_STATE = {}
def tenjint_api_get_cpu_state(cpu_num):
    if cpu_num not in CPU_STATE:
        CPU_STATE[cpu_num] = X86CpuState(cpu_num)
    c_cpu_state = vmi_api_get_cpu_state(cpu_num)
    (<X86CpuState>CPU_STATE[cpu_num]).reset(c_cpu_state)
    return CPU_STATE[cpu_num]

cdef _x86_decode_event(kvm_vmi_event *c_event):
    if c_event.type == KVM_VMI_EVENT_TASK_SWITCH:
        return api_x86_64.SystemEventTaskSwitch(c_event.ts.cpu_num,
                                                c_event.ts.new_cr3,
                                                c_event.ts.old_cr3)
    elif c_event.type == KVM_VMI_EVENT_SLP:
        if c_event.slp.gva == 0xffffffffffffffff:
            gva = None
        else:
            gva = c_event.slp.gva
        return api_x86_64.SystemEventSLP(c_event.slp.cpu_num,
                        gva,
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
    elif c_event.type == KVM_VMI_EVENT_MTF:
        return api.SystemEventSingleStep(c_event.debug.cpu_num,
                                         api.SingleStepMethod.MTF)
    else:
        raise RuntimeError()

def tenjint_api_get_event():
    c_event = tenjintapi.vmi_api_get_event()
    if c_event == NULL:
        return None
    if c_event.type == tenjintapi.VMI_EVENT_KVM:
        return _x86_decode_event(c_event.kvm_vmi_event)
    return tenjintapi._decode_event(c_event)

def tenjint_api_update_feature_taskswitch(enable, dtb, incoming, outgoing):
    cdef kvm_vmi_feature c_feature

    if dtb is None:
        dtb = 0

    c_feature.feature = KVM_VMI_FEATURE_TRAP_TASK_SWITCH
    c_feature.ts.enable = enable
    c_feature.ts.dtb = dtb
    c_feature.ts.incoming = incoming
    c_feature.ts.outgoing = outgoing

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

def tenjint_api_update_feature_lbr(cpu_num, enable, lbr_select):
    cdef kvm_vmi_feature c_feature

    c_feature.feature = KVM_VMI_FEATURE_LBR
    c_feature.lbr.enable = enable
    c_feature.lbr.lbr_select = lbr_select

    if cpu_num is None:
        rv = tenjintapi.vmi_api_feature_update_all(&c_feature)
    else:
        rv = tenjintapi.vmi_api_feature_update_single(cpu_num, &c_feature)

    if rv < 0:
        raise api.QemuFeatureError("LBR feature update returned {}".format(rv))

def tenjint_api_lbr_get(cpu_num):
    cdef kvm_vmi_lbr_info lbr_state

    rv = vmi_api_get_lbr_state(cpu_num, &lbr_state)

    if rv < 0:
        raise api.QemuFeatureError("LBR get request returned {}".format(rv))

    lbr_from = list()
    lbr_to = list()
    for i in range(lbr_state.entries):
        lbr_from.append(lbr_state.lbr_from[i])
        lbr_to.append(lbr_state.lbr_to[i])

    return api_x86_64.LBRState(lbr_state.tos, lbr_from, lbr_to)

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

def tenjint_api_update_feature_mtf(cpu_num, enable):
    cdef kvm_vmi_feature c_feature

    if cpu_num is None:
        raise ValueError("cpu_num must be set when single stepping")

    c_feature.feature = KVM_VMI_FEATURE_MTF
    c_feature.mtf.enable = enable

    rv = tenjintapi.vmi_api_feature_update_single(cpu_num, &c_feature)

    if rv < 0:
        raise api.QemuFeatureError("MTF feature update returned {}".format(rv))

    return rv
