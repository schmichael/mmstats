"""mmstats reader implementation"""
from collections import defaultdict, namedtuple
import ctypes
import math
import mmap
import struct
from . import defaults, fields


VERSION_1 = '\x01'
VERSION_2 = '\x02'
UNBUFFERED_FIELD = 255


def _mean(values):
    if values:
        return sum(values) / len(values)
    else:
        return 0.0


def _median(values):
    if values:
        return values[len(values) // 2]
    else:
        return 0.0


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

    @classmethod
    def from_file(cls, fn):
        return cls._create_by_version(open(fn, 'rb'))

    @classmethod
    def from_mmap(cls, fn):
        f = open(fn, 'rb')
        try:
            mmapf = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
        except:
            f.close()
            raise
        return cls._create_by_version(mmapf)

    @classmethod
    def _create_by_version(cls, data):
        rawver = data.read(1)
        if rawver == VERSION_1:
            return MmStatsReaderV1(data)
        if rawver == VERSION_2:
            return MmStatsReaderV2(data)
        else:
            raise InvalidMmStatsVersion(repr(rawver))

    def __iter__(self):
        raise NotImplementedError


class MmStatsReaderV1(MmStatsReader):
    version = 1

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


class MmStatsReaderV2(MmStatsReader):
    version = 2

    def __iter__(self):
        d = self.data
        frame_header_sz = ctypes.sizeof(defaults.FIELD_SIZE_TYPE)
        while 1:
            field_sz = d.read(frame_header_sz)
            if not field_sz:
                break
            field_sz, = struct.unpack('I', field_sz)
            body = d.read(field_sz)
            if not body:
                break
            stats = fields.load_field(body)
            for stat in stats:
                yield stat


class MmStatsAggregatingReader(object):
    """Aggregating Reader for v2 mmstats files"""

    def __init__(self, files):
        self.mmstats_files = files


    def get_percentile(self, values, percentile):
        if not values or percentile <= 0:
            return values[0]
        if percentile >= 1:
            return values[-1]
        pos = percentile * (len(values) + 1)
        if pos < 1:
            return values[0]
        if pos >= len(values):
            return values[-1]
        lower = values[int(pos - 1)]
        upper = values[int(pos)]
        return lower + (pos - math.floor(pos)) * (upper - lower)

    def __iter__(self):
        stats = defaultdict(list)

        # First pass: load all stats
        for fn in self.mmstats_files:
            reader = MmStatsReaderV2.from_mmap(fn)
            for stat in reader:
                #FIXME
                if hasattr(stat.value, '__iter__'):
                    stats[stat.label].extend(stat.value)
                else:
                    stats[stat.label].append(stat.value)

        # Second pass: aggregate by label
        for label, values in stats.iteritems():
            sorted_values = sorted(values)
            yield Stat(label + '.values', values)
            yield Stat(label + '.length', len(values))
            yield Stat(label + '.min', min(values))
            yield Stat(label + '.max', max(values))
            yield Stat(label + '.sum', sum(values))
            yield Stat(label + '.mean', _mean(values))
            yield Stat(label + '.median', _median(sorted_values))
            yield Stat(label + '.75thPercentile',
                self.get_percentile(sorted_values, 0.75))
            yield Stat(label + '.95thPercentile',
                self.get_percentile(sorted_values, 0.95))
            yield Stat(label + '.98thPercentile',
                self.get_percentile(sorted_values, 0.98))
            yield Stat(label + '.99thPercentile',
                self.get_percentile(sorted_values, 0.99))
            yield Stat(label + '.999thPercentile',
                self.get_percentile(sorted_values, 0.999))
