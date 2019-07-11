# cython: language_level=3
import numpy
from enum import Enum
from cpython.exc cimport PyErr_CheckSignals

from . import api

from . cimport tenjintapi

api.PAGE_SHIFT = vmi_api_get_page_bits()
api.PAGE_SIZE = vmi_api_get_page_size()

cdef _decode_event(vmi_event *c_event):
    if c_event.type == VMI_EVENT_STOP:
        return api.SystemEventVmStop()
    elif c_event.type == VMI_EVENT_VM_READY:
        return api.SystemEventVmReady()
    elif c_event.type == VMI_EVENT_VM_SHUTDOWN:
        return api.SystemEventVmShutdown()
    else:
        raise RuntimeError()

def tenjint_api_init():
    vmi_api_init()

def tenjint_api_uninit():
    vmi_api_uninit()

def tenjint_api_request_stop():
    vmi_api_request_stop()

def tenjint_api_request_shutdown():
    vmi_api_request_shutdown()

# if secs == 0 there is no timeout
def tenjint_api_wait_event(secs=0):
    cdef time_t t = secs

    if not vmi_api_start_vm():
        return

    while True:
        with nogil:
            r = vmi_api_wait_event(t)
        PyErr_CheckSignals()
        if r == 0:
            break

    vmi_api_stop_vm()

def tenjint_api_get_ram_size():
    return vmi_api_get_ram_size()

def tenjint_api_get_num_cpus():
    return vmi_api_get_num_cpus()

def tenjint_api_slp_update(gpa, r=False, w=False, x=False):
    cdef kvm_vmi_slp_perm c_slp_perm
    cdef int rv
    c_slp_perm.gfn = gpa >> api.PAGE_SHIFT
    c_slp_perm.num_pages = 1
    c_slp_perm.perm = KVM_VMI_SLP_R if r else 0
    c_slp_perm.perm |= KVM_VMI_SLP_W if w else 0
    c_slp_perm.perm |= KVM_VMI_SLP_X if x else 0
    rv = vmi_api_slp_update_all(&c_slp_perm)
    if rv != 0:
        raise api.UpdateSLPError("SLP update returned {}".format(rv))

def tenjint_api_read_phys_mem(addr, size):
    np_buf = numpy.empty(size, numpy.uint8)
    cdef uint8_t[::1] c_buf = np_buf
    r = vmi_api_read_phys_mem(addr, &c_buf[0], size)
    if r < 0:
        raise RuntimeError("Memory read failed")
    return np_buf.tobytes()

def tenjint_api_write_phys_mem(addr, buf):
    cdef uint8_t* c_buf = buf
    r = vmi_api_write_phys_mem(addr, c_buf, len(buf))
    if r < 0:
        raise RuntimeError("Memory write failed")

def tenjint_api_vtop(addr, dtb):
    rv = vmi_api_vtop(addr, dtb)
    if rv == 0xffffffffffffffff:
        raise api.TranslationError("Error translating 0x{:x} with dtb 0x{:x}".format(addr, dtb))
    return rv
