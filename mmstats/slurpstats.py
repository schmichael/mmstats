#!/usr/bin/env python
import mmap
import os
import sys
import tempfile
import traceback

from mmstats import reader as mmstats_reader


def err(*args):
    """Laziness"""
    sys.stderr.write('%s\n' % ' '.join(map(str, args)))


def slurp_stats(full_fn, m):
    """mmap parsing mainloop"""
    reader = mmstats_reader.MmStatsReader(m)

    print '==>', full_fn
    out = []
    label_max = 0
    for label, value in reader:
        if len(label) > label_max:
            label_max = len(label)
        out.append((label, value))

    for label, value in out:
        if isinstance(value, str):
            value = value.split('\x00', 1)[0]
        print ('  %-' + str(label_max) + 's %s') % (label, value)
    print


def main():
    """MmStats CLI Entry point"""
    # Accept paths and dirs to read as mmstats files from the command line
    stats_files = set()
    for arg in sys.argv[1:]:
        stats_files.add(arg)

    # Only read from tempdir if no files specified on the command line
    if not stats_files:
        tempdir = tempfile.gettempdir()
        stats_files = (os.path.join(tempdir, fn) for fn in os.listdir(tempdir)
                            if fn.startswith('mmstats-'))

    for fn in stats_files:
        with open(fn) as f:
            mmst = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
            try:
                slurp_stats(fn, mmst)
            except Exception:
                err('Error reading: %s' % fn)
                err(traceback.format_exc())
            finally:
                mmst.close()


if __name__ == '__main__':
    main()
