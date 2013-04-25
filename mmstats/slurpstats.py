#!/usr/bin/env python
import errno
import glob
import mmap
import sys
import traceback

from mmstats import defaults, reader as mmstats_reader


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
        stats_files = glob.glob(defaults.DEFAULT_GLOB)

    for fn in stats_files:
        with open(fn) as f:
            mmst = None
            try:
                mmst = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
                slurp_stats(fn, mmst)
            except IOError as ex:
                if ex.errno == errno.EPIPE:
                    # A broken pipe (probably) means the process was killed
                    # while piped to another command (e.g.: grep) - so die
                    return
                else:
                    err('Error reading: %s' % fn)
                    err(traceback.format_exc())
            except Exception:
                err('Error reading: %s' % fn)
                err(traceback.format_exc())
            finally:
                if mmst is not None:
                    mmst.close()


if __name__ == '__main__':
    main()
