"""mmash - Flask JSON Web API for publishing mmstats"""
from collections import defaultdict
import glob
import operator
import os
import sys

import flask

from mmstats import reader as mmstats_reader


app = flask.Flask(__name__)
app.config.from_object('mmstats.mmash_settings')
if 'MMASH_SETTINGS' in os.environ:
    app.config.from_envvar('MMASH_SETTINGS')


def iter_stats(stats_glob=None):
    """Yields a label at a time from every mmstats file in MMSTATS_GLOB"""
    if not stats_glob:
        stats_glob = app.config['MMSTATS_GLOB']
    elif '..' in stats_glob:
        # Don't allow path traversal in custom globs
        flask.abort(400)
    for fn in glob.glob(stats_glob):
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
    return flask.jsonify(stats=sorted(find_labels()))


@app.route('/graph/')
def graph():
    string_stats = []
    numeric_stats = []
    for fn, label, value in iter_stats():
        stat_data = {
                'label': label,
                'value': value,
                'jsid': label.replace('.', '_'),
            }
        try:
            float(value)
        except ValueError:
            string_stats.append(stat_data)
        else:
            numeric_stats.append(stat_data)
    return flask.render_template('graph.html',
            mmstats_dir=app.config['MMSTATS_GLOB'],
            string_stats=sorted(string_stats, key=lambda x: x['label']),
            numeric_stats=sorted(numeric_stats, key=lambda x: x['label']))


def _nonzero_avg(values):
    """Return the average of ``values`` ignoring 0 values"""
    nonzero_values = [v for v in values if v]
    return float(sum(nonzero_values)) / len(nonzero_values)

aggregators = {
    'avg': lambda v: float(sum(v)) / len(v),
    'one': operator.itemgetter(0),
    'max': max,
    'min': min,
    'sum': sum,
    'nonzero-min': lambda vals: min([v for v in vals if v]),
    'nonzero-avg': _nonzero_avg,
}


@app.route('/files/', defaults={'glob': ''})
@app.route('/files/<glob>')
def getfiles(glob):
    files = set(fn for fn, _, _ in iter_stats(glob))
    return flask.jsonify(files=list(files))


@app.route('/stats/<statname>')
def getstat(statname):
    stats = defaultdict(list)
    exact = flask.request.args.get('exact')
    stats_glob = flask.request.args.get('glob')
    for fn, label, value in iter_stats(stats_glob):
        if exact and label == statname:
            stats[label].append(value)
        elif label.startswith(statname):
            stats[label].append(value)

    aggr = aggregators.get(flask.request.args.get('aggr'))
    if aggr:
        for label, values in stats.iteritems():
            try:
                stats[label] = aggr(values)
            except Exception:
                flask.abort(400)

    return flask.jsonify(stats)


@app.route('/')
def index():
    return flask.render_template(
        'index.html',
        mmstats_dir=app.config['MMSTATS_GLOB'],
        stats=sorted(find_labels())
    )


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
