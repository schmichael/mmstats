#!/usr/bin/env python
import os
import sys
import tempfile
import traceback


def err(msg):
    sys.stderr.write('%s\n' % msg)


def slurp_stats(contents):
    import json
    print json.dumps(contents)


def main():
    searchdir = tempfile.gettempdir()
    for fn in os.listdir(searchdir):
        if fn.startswith('mmstats-'):
            full_fn = os.path.join(searchdir, fn)
            with open(full_fn) as f:
                contents = f.read()
            try:
                slurp_stats(contents)
            except Exception:
                err('Error reading %s' % full_fn)
                err(traceback.format_exc())


if __name__ == '__main__':
    main()
