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


def _struct_factory(label_sz, buffer_type):
    """Helper function to generate the proper stat field structure"""

    #FIXME There's got to be a more elegant way. There are 3 dynamic
    #      fields: label & the 2 value buffers
    class _Struct(ctypes.Structure):
        _fields_ = [
            ('label_sz', ctypes.c_ushort),
            ('label', (ctypes.c_char * label_sz)),
            ('type_signature', ctypes.c_char),
            ('write_buffer', ctypes.c_byte),
            ('buffers', (buffer_type * 2)),
        ]

    return _Struct


class Stat(object):
    """Sentinel class"""


class UIntStat(Stat):
    """32bit Unsigned Integer field"""

    type_signature = "L"

    def _init(self, label, mm, offset):
        if isinstance(label, unicode):
           label = label.encode('utf8')

        _Struct = _struct_factory(len(label), ctypes.c_uint)

        self._struct = _Struct.from_buffer(mm, offset)
        self._struct.label_sz = len(label)
        self._struct.label = label
        self._struct.type_signature = self.type_signature
        self._struct.write_buffer = 0
        self._struct.buffers = 0, 0
        #self.buffers = (self._struct.a, self._struct.b)
        return offset + ctypes.sizeof(_Struct)

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
