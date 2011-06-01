import ctypes
import mmap
import os
import tempfile
import threading


BUFFER_IDX_TYPE = ctypes.c_byte
LABEL_SZ_TYPE = ctypes.c_ushort


def _init_mmap(path=None, filename=None, size=None):
    """Create mmap instance"""
    if path is None:
        path = tempfile.gettempdir()

    if filename is None:
        filename = 'mmstats-%d' % os.getpid()
        t = threading.current_thread()
        if t.ident:
            filename += '-%d' % t.ident

    full_path = os.path.join(path, filename)

    # Create new empty file to back memory map on disk
    fd = os.open(full_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

    # Zero out the file to insure it's the right size
    os.write(fd, '\x00' * mmap.PAGESIZE)

    return mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)


class Stat(ctypes.Structure):
    """ABC"""

class UIntStat(Stat):
    """32bit Unsigned Integer field"""

    buffer_type = ctypes.c_uint
    type_signature = "L"

    _fields_ = [
        ('type_signature', ctypes.c_char),
        ('write_buffer', ctypes.c_byte),
        ('buffers', (buffer_type * 2)),
    ]

    @classmethod
    def create(cls, label, mm, offset):
        if isinstance(label, unicode):
           label = label.encode('utf8')

        s = cls.from_buffer(mm, offset)
        s.label_sz = len(label)
        s.label = label
        s.type_signature = cls.type_signature
        s.write_buffer = 0
        s.buffers = 0, 0
        #s.buffers = (self._struct.a, self._struct.b)
        return offset + ctypes.sizeof(cls)

    # TODO Support descriptor protocol
    def get(self):
        # Get from the read buffer
        return self._struct.buffers[self._struct.write_buffer ^ 1]

    def set(self, val):
        # Set the write buffer
        self._struct.buffers[self._struct.write_buffer] = val
        # Swap the write buffer
        self._struct.write_buffer ^= 1


class MmStats(object):

    def __init__(self):
        mmap_ = _init_mmap()
        mmap_[0] = '\x01' # Stupid version number
        offset = 1

        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, Stat):
                offset = attr._init(attrname, mmap_, offset)

        self.mmap = mmap_
        self.offset = offset
