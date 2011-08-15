#!/usr/bin/env python
import mmap
import os
import struct
import sys
import tempfile
import traceback


NULL_BYTE = '\x00'
VERSION_1 = '\x01'


class MmStatsException(Exception):
    """mmstats file could not be parsed"""


def err(msg=''):
    """Laziness"""
    sys.stderr.write('%s\n' % msg)


def slurp_v1(m):
    """Reads a single mmstat v1 record"""
    label_sz = struct.unpack('H', m.read(2))[0]
    label = m.read(label_sz)
    type_ = m.read_byte()
    sz = struct.calcsize(type_)
    idx = struct.unpack('B', m.read_byte())[0]
    idx ^= 1 # Flip bit as the stored buffer is the *write* buffer
    buffers = m.read(sz * 2)
    offset = sz * idx
    value = struct.unpack(type_, buffers[offset:sz+offset])[0]
    return label, value


def slurp_stats(full_fn, m):
    """mmap parsing mainloop"""
    if m.read_byte() == VERSION_1:
        print full_fn
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
