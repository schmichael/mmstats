import atexit
import warnings

import flask

import mmstats


# Make sure the example only uses the latest and greatest
warnings.simplefilter('error')


application = app = flask.Flask(__name__)
app.config['DEBUG'] = True


class Stats(mmstats.MmStats):
    ok = mmstats.CounterField(label="flask.example.ok")
    bad = mmstats.CounterField(label="flask.example.bad")
    working = mmstats.BoolField(label="flask.example.working")

stats = Stats(filename='mmstats-flask-example-%PID%')
atexit.register(stats.remove)


def set_working(sender):
    stats.working = True
flask.request_started.connect(set_working, app)

def unset_working(sender, response):
    stats.working = False
flask.request_finished.connect(unset_working, app)

def inc_response(sender, response):
    if response.status_code == 200:
        stats.ok.incr()
    elif response.status_code == 500:
        stats.bad.incr()
flask.request_finished.connect(inc_response, app)


@app.route('/')
def ok():
    return "OK or see /status for a single process's status"


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
