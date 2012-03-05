import ctypes
import ctypes.util
import errno
libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))
import mmap as stdlib_mmap
import os


from . import libgettid
from .defaults import DEFAULT_PATH, DEFAULT_FILENAME


PAGESIZE = stdlib_mmap.PAGESIZE


def init_mmap(path=DEFAULT_PATH, filename=DEFAULT_FILENAME, size=PAGESIZE):
    """Given path, filename => filename, size, mmap

    In `filename` "%PID%" and "%TID%" will be replaced with pid and thread id
    """
    # Replace %PID% with actual pid
    filename = filename.replace('%PID%', str(os.getpid()))
    # Replace %TID% with thread id or 0 if thread id is None
    filename = filename.replace('%TID%', str(libgettid.gettid() or 0))

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
    if size > PAGESIZE:
        if size % PAGESIZE:
            size = size + (PAGESIZE - (size % PAGESIZE))
    else:
        size = PAGESIZE

    # Zero out the file
    os.ftruncate(fd, size)
    m_ptr = mmap(size, fd)
    return (fd, full_path, size, m_ptr)


# Linux consts from /usr/include/bits/mman.h
MS_ASYNC = 1
MS_SYNC = 4


libc.mmap.restype = ctypes.c_void_p
libc.mmap.argtypes = [
    ctypes.c_void_p, # address
    ctypes.c_size_t, # size of mapping
    ctypes.c_int,    # protection
    ctypes.c_int,    # flags
    ctypes.c_int,    # fd
    ctypes.c_int,    # offset (needs to be off_t type?)
]


def mmap(size, fd):
    m_ptr = libc.mmap(None,
                      size,
                      stdlib_mmap.PROT_READ | stdlib_mmap.PROT_WRITE,
                      stdlib_mmap.MAP_SHARED,
                      fd,
                      0
            )
    if m_ptr == -1:
        # Error
        e = ctypes.get_errno()
        raise OSError(e, errno.errorcode[e])
    return m_ptr


libc.msync.restype = ctypes.c_int
libc.msync.argtypes = [
    ctypes.c_void_p, # address
    ctypes.c_size_t, # size of mapping
    ctypes.c_int,    # flags
]


def msync(mm_ptr, size, async=False):
    if async:
        flags = MS_ASYNC
    else:
        flags = MS_SYNC
    status = libc.msync(mm_ptr, size, flags)
    if status == -1:
        e = ctypes.get_errno()
        raise OSError(e, errno.errorcode[e])


libc.munmap.restype = ctypes.c_int
libc.munmap.argtypes = [
    ctypes.c_void_p, # address
    ctypes.c_size_t, # size of mapping
]


def munmap(mm_ptr, size):
    status = libc.munmap(mm_ptr, size)
    if status == -1:
        e = ctypes.get_errno()
        raise OSError(e, errno.errorcode[e])
