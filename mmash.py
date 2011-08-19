from collections import defaultdict
import glob
import json
import mmap
import os
import traceback

import flask

from slurpstats import (
        NULL_BYTE, VERSION_1,
        MmStatsException,
        err,
        slurp_v1,
    )


app = flask.Flask(__name__)
app.config.from_object('mmash_settings')
if 'MMASH_SETTINGS' in os.environ:
    app.config.from_envvar('MMASH_SETTINGS')

GLOB = os.path.join(app.config['MMSTATS_DIR'], 'mmstats-*')


def slurp_stats(m):
    """mmap parsing mainloop"""
    if m.read_byte() == VERSION_1:
        out = []
        label_max = 0
        while m[m.tell()] != NULL_BYTE:
            yield slurp_v1(m)
    else:
        raise MmStatsException('Unknown version: %x' % ord(m[0]))


def iter_stats():
    for fn in glob.glob(GLOB):
        with open(fn) as f:
            mmst = mmap.mmap(f.fileno(), 0, prot=mmap.ACCESS_READ)
            try:
                for label, value in slurp_stats(mmst):
                    yield fn, label, value
            except Exception:
                err('Error reading: %s' % fn)
                err(traceback.format_exc())
            finally:
                mmst.close()


def find_labels():
    labels = set()
    for fn, label, value in iter_stats():
        labels.add(label)
    return labels


@app.route('/')
def index():
    return json.dumps(sorted(find_labels()), indent=4)


aggregators = {
    'sum': sum,
    'avg': lambda v: float(sum(v)) / len(v),
    'min': min,
    'max': max,
}


@app.route('/<statname>')
def getstat(statname):
    stats = defaultdict(list)
    exact = flask.request.args.get('exact')
    for _, label, value in iter_stats():
        if exact and label == statname:
            stats[label].append(value)
        elif label.startswith(statname):
            stats[label].append(value)

    aggr = aggregators.get(flask.request.args.get('aggr'))
    if aggr:
        for label, values in stats.iteritems():
            stats[label] = aggr(values)
    return json.dumps(stats, indent=4)


if __name__ == '__main__':
    app.run()
