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


#class Stat(ctypes.Structure):
class Stat(object):
    """ABC"""

class UIntStat(Stat):
    """32bit Unsigned Integer field"""

    buffer_type = ctypes.c_uint
    type_signature = "L"

    def __init__(self):
        self._struct = None # initialized in _init

    def _init(self, label, mm, offset):
        """Initializes mmaped buffers and returns next offset"""
        if isinstance(label, unicode):
           label = label.encode('utf8')

        class _Struct(ctypes.Structure):
            _fields_ = [
                ('label_sz', ctypes.c_byte),
                ('label', ctypes.c_char * len(label)),
                ('type_signature', ctypes.c_char),
                ('write_buffer', ctypes.c_byte),
                ('buffers', (self.buffer_type * 2)),
            ]

        self._struct = _Struct.from_buffer(mm, offset)
        self._struct.label_sz = len(label)
        self._struct.label = label
        self._struct.type_signature = self.type_signature
        self._struct.write_buffer = 0
        self._struct.buffers = 0, 0
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


class MetaMmStats(type):
    def __new__(mcs, name, bases, dict_):
        mmap_ = _init_mmap()
        mmap_[0] = '\x01' # Stupid version number
        offset = 1

        for attrname, attrval in dict_.items():
            if isinstance(attrval, Stat):
                print 'initing %s at %d' % (attrname, offset)
                offset = attrval._init(attrname, mmap_, offset)

        dict_['mmap'] = mmap_
        dict_['offset'] = offset

        return type.__new__(mcs, name, bases, dict_)

class MmStats(object):
    __metaclass__ = MetaMmStats
