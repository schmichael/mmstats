"""mmstats reader implementation"""
from collections import namedtuple
import mmap
import struct


VERSION_1 = '\x01'
UNBUFFERED_FIELD = 255


def reader(fmt):
    struct_fmt = struct.Struct(fmt)
    size = struct.calcsize(fmt)
    unpacker = struct_fmt.unpack

    def wrapper(v):
        return unpacker(v.read(size))[0]
    wrapper.__name__ = 'unpack_' + fmt

    return wrapper


read_ushort = reader('H')
read_ubyte = reader('B')


Stat = namedtuple('Stat', ('label', 'value'))


class InvalidMmStatsVersion(Exception):
    """Unsupported mmstats version"""


class MmStatsReader(object):
    def __init__(self, data):
        """`data` should be a file-like object (mmap or file)"""
        self.data = data
        rawver = self.data.read(1)
        if rawver == VERSION_1:
            self.version = 1
        else:
            raise InvalidMmStatsVersion(repr(rawver))

    @classmethod
    def from_file(cls, fn):
        return cls(open(fn, 'rb'))

    @classmethod
    def from_mmap(cls, fn):
        f = open(fn, 'rb')
        try:
            mmapf = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
        except:
            f.close()
            raise
        return cls(mmapf)

    def __iter__(self):
        d = self.data
        while 1:
            raw_label_sz = d.read(2)
            if (not raw_label_sz or raw_label_sz == '\x00' or
                    raw_label_sz == '\x00\x00'):
                # EOF
                break
            label_sz = struct.unpack('H', raw_label_sz)[0]
            label = d.read(label_sz).decode('utf8', 'ignore')
            type_sz = read_ushort(d)
            type_ = d.read(type_sz)
            sz = struct.calcsize(type_)
            buf_idx = read_ubyte(d)
            if buf_idx == UNBUFFERED_FIELD:
                value = struct.unpack(type_, d.read(sz))[0]
            else:
                # Flip bit as the stored buffer is the *write* buffer
                buf_idx ^= 1
                buffers = d.read(sz * 2)
                offset = sz * buf_idx
                read_buffer = buffers[offset:(offset + sz)]
                value = struct.unpack(type_, read_buffer)[0]
            if isinstance(value, str):
                # Special case strings as they're \x00 padded
                value = value.split('\x00', 1)[0].decode('utf8', 'ignore')
            yield Stat(label, value)

        try:
            d.close()
        except Exception:
            # Don't worry about exceptions closing the file
            pass
