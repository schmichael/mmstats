import flask

import mmstats


application = app = flask.Flask(__name__)
app.config['DEBUG'] = True


class Stats(mmstats.MmStats):
    ok = mmstats.UIntStat(label="mmstats.example.ok")
    bad = mmstats.UIntStat(label="mmstats.example.bad")
    working = mmstats.BoolStat(label="mmstats.example.working")

stats = Stats()


def set_working(sender):
    stats.working = True
flask.request_started.connect(set_working, app)

def unset_working(sender, response):
    stats.working = False
flask.request_finished.connect(unset_working, app)

def inc_response(sender, response):
    if response.status_code == 200:
        stats.ok += 1
    elif response.status_code == 500:
        stats.bad += 1
flask.request_finished.connect(inc_response, app)


@app.route('/200')
def ok():
    return 'OK'


@app.route('/500')
def bad():
    return 'oh noes!', 500


@app.route('/status')
def status():
    return """\
<html>
    <body>
        <pre>
            ok:      %s
            bad:     %s
            working: %s
        </pre>
    </body>
</html>""" % (stats.ok, stats.bad, stats.working)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
