#!/usr/bin/env python
import ctypes
import mmap
import os
import struct
import sys
import tempfile
import traceback


NULL_BYTE = '\x00'
VERSION_1 = '\x01'
WRITE_BUFFER_UNUSED = 255
DEBUG = os.environ.get('SLURPSTATS_DEBUG')


class MmStatsException(Exception):
    """mmstats file could not be parsed"""


def dbg(*args):
    if DEBUG:
        sys.stderr.write('%s\n' % ' '.join(map(str, args)))


def err(*args):
    """Laziness"""
    sys.stderr.write('%s\n' % ' '.join(map(str, args)))


def slurp_v1(m):
    """Reads a single mmstat v1 record"""
    dbg(repr(m[0:20]))
    dbg(repr(m[20:40]))
    label_sz = struct.unpack('H', m.read(2))[0]
    label = m.read(label_sz)
    dbg(label_sz, label)
    type_ = m.read(4)
    dbg(type_)
    sz = struct.calcsize(type_)
    idx = struct.unpack('B', m.read_byte())[0]
    if idx == WRITE_BUFFER_UNUSED:
        value = struct.unpack(type_, m.read(sz))[0]
    else:
        idx ^= 1 # Flip bit as the stored buffer is the *write* buffer
        buffers = m.read(sz * 2)
        offset = sz * idx
        value = struct.unpack(type_, buffers[offset:sz+offset])[0]
    return label, value


def slurp_stats(full_fn, m):
    """mmap parsing mainloop"""
    if m.read_byte() == VERSION_1:
        print '==>', full_fn
        out = []
        label_max = 0
        while m[m.tell()] != NULL_BYTE:
            label, value = slurp_v1(m)
            if len(label) > label_max:
                label_max = len(label)
            out.append((label, value))
        for label, value in out:
            print ('  %-'+str(label_max)+'s %s') % (label, value)
        print
    else:
        raise MmStatsException('Unknown version: %x' % ord(m[0]))


def main():
    """MmStats CLI Entry point"""
    searchdir = tempfile.gettempdir()
    for fn in os.listdir(searchdir):
        if fn.startswith('mmstats-'):
            full_fn = os.path.join(searchdir, fn)
            with open(full_fn) as f:
                mmst = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
                try:
                    slurp_stats(full_fn, mmst)
                except Exception:
                    err('Error reading: %s' % full_fn)
                    err(traceback.format_exc())
                finally:
                    mmst.close()


if __name__ == '__main__':
    main()
