"""mmash - Flask JSON Web API for publishing mmstats"""
from collections import defaultdict
import glob
import json
import operator
import os
import sys

import flask

from mmstats import reader as mmstats_reader


app = flask.Flask(__name__)
app.config.from_object('mmstats.mmash_settings')
if 'MMASH_SETTINGS' in os.environ:
    app.config.from_envvar('MMASH_SETTINGS')

GLOB = os.path.join(app.config['MMSTATS_DIR'], 'mmstats-*')


def iter_stats():
    """Yields a label at a time from every mmstats file in MMSTATS_DIR"""
    for fn in glob.glob(GLOB):
        try:
            for label, value in mmstats_reader.MmStatsReader.from_mmap(fn):
                yield fn, label, value
        except Exception:
            continue


def find_labels():
    """Returns a set of all available labels"""
    labels = set()
    for fn, label, value in iter_stats():
        labels.add(label)
    return labels


@app.route('/stats/')
def stats():
    return json.dumps(sorted(find_labels()), indent=4)


aggregators = {
    'avg': lambda v: float(sum(v)) / len(v),
    'one': operator.itemgetter(0),
    'max': max,
    'min': min,
    'sum': sum,
}


@app.route('/stats/<statname>')
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


@app.route('/')
def index():
    return flask.render_template('index.html',
            mmstats_dir=app.config['MMSTATS_DIR'],
            stats=sorted(find_labels()))


def main():
    if len(sys.argv) > 1:
        print __doc__
        print
        print 'Set MMASH_SETTINGS=path/to/settings.py to change settings.'
        return

    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG']
        )


if __name__ == '__main__':
    main()
