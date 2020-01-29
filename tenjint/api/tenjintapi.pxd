# cython: language_level=3

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

ctypedef long int time_t

cdef extern union kvm_vmi_event
cdef extern union kvm_vmi_feature

cdef extern from "linux/kvm_vmi.h":
    const __u64 KVM_VMI_SLP_R
    const __u64 KVM_VMI_SLP_W
    const __u64 KVM_VMI_SLP_X

    struct kvm_vmi_slp_perm:
        __u64 gfn
        __u64 num_pages
        __u64 perm

cdef extern from "sysemu/vmi_api.h":
    const int VMI_ARCH_UNSUPPORTED
    const int VMI_ARCH_X86_64
    const int VMI_ARCH_AARCH64

    const int VMI_EVENT_KVM
    const int VMI_EVENT_STOP
    const int VMI_EVENT_VM_READY
    const int VMI_EVENT_VM_SHUTDOWN

    struct vmi_event:
        uint32_t type
        int32_t arch
        kvm_vmi_event *kvm_vmi_event

    int vmi_api_init()
    void vmi_api_uninit()

    void vmi_api_request_stop()
    void vmi_api_request_shutdown()

    vmi_event* vmi_api_get_event()
    int vmi_api_start_vm()
    int vmi_api_wait_event(time_t) nogil
    void vmi_api_stop_vm()

    int vmi_api_feature_update_all(kvm_vmi_feature*)
    int vmi_api_feature_update_single(uint32_t, kvm_vmi_feature*)

    int vmi_api_slp_update_all(kvm_vmi_slp_perm*)
    int vmi_api_slp_update_single(uint32_t, kvm_vmi_slp_perm*)

    uint64_t vmi_api_get_num_cpus()

    uint64_t vmi_api_get_ram_size()
    int vmi_api_read_phys_mem(uint64_t, void*, uint64_t)
    int vmi_api_write_phys_mem(uint64_t, const void*, uint64_t)

    uint32_t vmi_api_get_page_bits()
    uint32_t vmi_api_get_page_size()

    uint64_t vmi_api_vtop(uint64_t, uint64_t)

    void vmi_api_mouse_out()

cdef _decode_event(vmi_event *c_event)
