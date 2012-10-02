Getting Started
===============

It's easiest to develop mmstats within a virtualenv:

::

    $ git clone git://github.com/schmichael/mmstats.git
    $ cd mmstats
    $ virtualenv .
    $ source bin/activate
    $ python setup.py develop
    $ ./run_flask_example # This starts up a sample web app
    $ curl http://localhost:5001/
    $ curl http://localhost:5001/500
    $ curl http://localhost:5001/status
    $ # If you have ab installed:
    $ ab -n 50 -c 10 http://localhost:5001/

Now to view the stats run the following in a new terminal:

::

    $ # To get a raw view of the data:
    $ slurpstats mmstats-*
    $ # Or start up the web interface:
    $ mmash
    $ # Run pollstats while ab is running:
    $ pollstats -p flask.example. ok,bad,working mmstats-*

To cleanup stray mmstats files: ``rm mmstats-flask-*``

The web interface will automatically reload when you change source files.

Put static files into static/ and template files into templates/

--------
Testing
--------

Feel free to use your favorite test runner like `nose
<http://readthedocs.org/docs/nose/>`_ or `pytest <http://pytest.org/>`_ or just
run:

::

    $ python setup.py test

