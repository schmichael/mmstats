#!/usr/bin/env python
"""pollstats - vmstat/dstat like CLI for mmstats

pollstats [options] <fields> <files>...
"""
import argparse
import collections
import mmap
import os
import struct
import sys
import time

import pkg_resources

from mmstats import reader


VERSION = pkg_resources.require('mmstats')[0].version
WARN_LEVEL = 1
INFO_LEVEL = 2
DEBUG_LEVEL = 3

ansi = {
    'black': '\033[0;30m',
    'darkred': '\033[0;31m',
    'darkgreen': '\033[0;32m',
    'darkyellow': '\033[0;33m',
    'darkblue': '\033[0;34m',
    'darkmagenta': '\033[0;35m',
    'darkcyan': '\033[0;36m',
    'gray': '\033[0;37m',

    'darkgray': '\033[1;30m',
    'red': '\033[1;31m',
    'green': '\033[1;32m',
    'yellow': '\033[1;33m',
    'blue': '\033[1;34m',
    'magenta': '\033[1;35m',
    'cyan': '\033[1;36m',
    'white': '\033[1;37m',

    'blackbg': '\033[40m',
    'redbg': '\033[41m',
    'greenbg': '\033[42m',
    'yellowbg': '\033[43m',
    'bluebg': '\033[44m',
    'magentabg': '\033[45m',
    'cyanbg': '\033[46m',
    'whitebg': '\033[47m',

    'reset': '\033[0;0m',
    'bold': '\033[1m',
    'reverse': '\033[2m',
    'underline': '\033[4m',

    'clear': '\033[2J',
#   'clearline': '\033[K',
    'clearline': '\033[2K',
#   'save': '\033[s',
#   'restore': '\033[u',
    'save': '\0337',
    'restore': '\0338',
    'linewrap': '\033[7h',
    'nolinewrap': '\033[7l',

    'up': '\033[1A',
    'down': '\033[1B',
    'right': '\033[1C',
    'left': '\033[1D',

    'default': '\033[0;0m',
}



opts = argparse.ArgumentParser()
opts.add_argument('-c', '--count', type=int)
opts.add_argument('-d', '--delay', type=int, default=1)
opts.add_argument('-f', '--filter', nargs='*', default=[])
opts.add_argument('-n', '--headers', default=20, type=int,
        help='print headers every HEADERS lines')
opts.add_argument('-p', '--prefix', default='', help='field prefix')
opts.add_argument('fields', help='Comma seperated list of fields')
opts.add_argument('files', nargs='+')
opts.add_argument('-v', action='append_const', const=1, dest='verbosity',
        default=[], help='verbosity: warnings=1, info=2, debug=3')
opts.add_argument('--version', action='version',
        version='%%(prog)s %s' %  VERSION)


def get_console_size():
    """Returns rows, columns for current console"""
    #FIXME Only tested on linux
    return map(int, os.popen('stty size', 'r').read().split())


def iter_stats(m):
    """Yields label, value pairs for the given mmstats map"""
    # Hop to the beginning
    m.seek(1)
    while m[m.tell()] != '\x00':
        label_sz = struct.unpack('H', m.read(2))[0]
        label = m.read(label_sz)
        type_sz = struct.unpack('H', m.read(2))[0]
        type_ = m.read(type_sz)
        sz = struct.calcsize(type_)
        idx = struct.unpack('B', m.read_byte())[0]
        if idx == reader.UNBUFFERED_FIELD:
            value = struct.unpack(type_, m.read(sz))[0]
        else:
            idx ^= 1 # Flip bit as the stored buffer is the *write* buffer
            buffers = m.read(sz * 2)
            offset = sz * idx
            value = struct.unpack(type_, buffers[offset:sz+offset])[0]
        yield label, value


Mmap = collections.namedtuple('Mmap', ('file', 'mmap'))


class PollStats(object):
    def __init__(self, args):
        self.args = args
        self.verbosity = len(self.args.verbosity)
        self.fields = args.fields.split(',')
        self.prefix = args.prefix
        if args.prefix:
            self.fields = ["%s%s" % (args.prefix, field)
                    for field in self.fields]
        self.last_vals = dict((field, 0) for field in self.fields)
        self.files = {}
        self._mmap_files()

        # By default filter down to just files that have the given fields
        self.key_filters = set(self.fields)
        self.kv_filters = set()
        for filterstr in args.filter:
            if '=' in filterstr:
                # Filter on exact key-value pairs
                self.kv_filters.add(filterstr.split('='))
            else:
                # Filter on presence of keys
                self.key_filters.add(filterstr)

        self._filter_mmaps()
        self.print_headers()

    def _mmap_files(self):
        for fn in set(self.args.files):
            f = open(fn, 'rb')
            m = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
            if m.read_byte() == reader.VERSION_1:
                self.files[fn] = Mmap(f, m)
            else:
                m.close()
                f.close()
                self.warn('Skipping %s - unknown file format' % fn)

    def _filter_mmaps(self):
        for fn, (f, m) in self.files.items():
            # By default remove files that don't match filters
            remove = True
            fields = dict(pair for pair in iter_stats(m))
            for kf in self.key_filters:
                for k in fields.iterkeys():
                    # Key filters match the start of the key name
                    if k.startswith(kf):
                        remove = False
                        break
                if not remove:
                    break

            if not remove:
                # Matched key filter, don't remove and continue on
                continue

            # Didn't remove file, check kv_filters
            for kf, vf in self.kv_filters:
                if kf in fields and fields[kf] == vf:
                    remove = False
                    break

            if remove:
                # fn didn't match key filter or key/value filter, remove
                self.remove_file(fn)

    def remove_file(self, fn):
        """Remove file `fn` from open mmstat files"""
        m = self.files[fn]
        m.file.close()
        m.mmap.close()
        del self.files[fn]

    def dbg(self, msg):
        if self.verbosity >= DEBUG_LEVEL:
            print >> sys.stderr, msg

    def warn(self, msg):
        if self.verbosity >= WARN_LEVEL:
            print >> sys.stderr, msg

    def print_headers(self):
        #_, width = get_console_size()
        #field_width = (width / len(self.fields)) - 1
        width = 20
        print '|'.join(
            ansi['bold'] + 
                f.replace(self.prefix, '', 1)[:width].center(width)
                + ansi['default']
            for f in self.fields
        )

    def read_once(self):
        cur_vals = collections.defaultdict(int)
        for _, m in self.files.itervalues():
            mvals = dict(pair for pair in iter_stats(m))
            for field in self.fields:
                cur_vals[field] += mvals[field]

        print '|'.join("%s%19d%s " % (ansi['yellow'],
                cur_vals[field] - self.last_vals[field], ansi['default'])
            for field in self.fields)
        self.last_vals = cur_vals

    def run(self):
        if self.args.count:
            for _ in xrange(self.args.count):
                self.read_once()
                time.sleep(self.args.delay)
        else:
            lines_since_header = 0
            while 1:
                if lines_since_header == self.args.headers:
                    self.print_headers()
                    lines_since_header = 0
                self.read_once()
                lines_since_header += 1
                time.sleep(self.args.delay)



def main():
    """CLI Entry Point"""
    p = PollStats(opts.parse_args())
    try:
        p.run()
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    main()
