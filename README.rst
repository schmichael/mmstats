=====
About
=====

Mmstats is a way to expose and read diagnostic values and metrics for
applications.

Think of mmstats as /proc for your application and the readers as procps
utilities.

This project is a Python implementation, but compatible implementations can be
made in any language (see Goals).

-----
Goals
-----

* Separate publishing/writing from consuming/reading tools
* Platform/language independent (a Java writer can be read by a Python tool)
* Predictable performance impact for writers via:

  * No locks (1 writer per thread)
  * No syscalls (after instantiation)
  * All in userspace
  * Reading has no impact on writers

* Optional persistent (writer can sync anytime)
* 1-way (Publish/consume only; mmstats are not management extensions)

=====
Usage
=====

------------
Requirements
------------

CPython 2.6 or 2.7 (Windows is untested)

PyPy (only tested in 1.7, should be faster in 1.8)

-----
Using
-----

1. ``python setup.py install``
2. ``import mmstats``
3. Create a subclass of mmstats.MmStats like:

::

    class WebStats(mmstats.MmStats):
        status2xx = mmstats.CounterField(label='status.2XX')
        status3xx = mmstats.CounterField(label='status.3XX')
        status4xx = mmstats.CounterField(label='status.4XX')
        status5xx = mmstats.CounterField(label='status.5XX')
        last_hit = mmstats.DoubleField(label='timers.last_hit')

4. Instantiate it once per thread/process:

::

    webstats = WebStats(label_prefix='web.stats.')

5. Record some data:

::

    if response.status_code == 200:
        webstats.status2xx.inc()

    webstats.last_hit = time.time()

6. Run ``slurpstats`` to read it
7. Run ``mmash`` to create a web interface for stats
8. Run ``pollstats -p web.stats.status 2XX,3XX,4XX,5XX /tmp/mmstats-*`` for a
   vmstat/dstat like view.
9. Did a process die unexpectedly and leave around a stale mmstat file?
   ``cleanstats /path/to/mmstat/files`` will check to see which files are stale
   and remove them.

-----------
Development
-----------

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

TODO: Factor mmash out into it's own project (with a meaningful name?)

--------
Testing
--------

Feel free to use your favorite test runner like `nose
<http://readthedocs.org/docs/nose/>`_ or `pytest <http://pytest.org/>`_ or just
run:

::

    $ python setup.py test

===============
Data Structures
===============

There are two types of data structures so far in mmstats:

#. buffered
#. unbuffered

Buffered structures use multiple buffers for handling values which cannot be
written atomically.

Unbuffered structures have ff in the write buffer field.

--------
Buffered
--------

+----------------+------------+---------------+------------+------------------+-------------+
| ``label size`` | ``label``  | ``type size`` | ``type``   | ``write buffer`` | ``buffers`` |
+================+============+===============+============+==================+=============+
| ``ushort``     | ``char[]`` | ``ushort``    | ``char[]`` | ``byte``         | ``varies``  |
+----------------+------------+---------------+------------+------------------+-------------+

The buffers field length = sizeof(type) * buffers.

The current write buffer is referenced by: write_buffer * sizeof(type)

TODO: field for total number of buffers?

----------
Unbuffered
----------


+----------------+------------+---------------+------------+------------------+-------------+
| ``label size`` | ``label``  | ``type size`` | ``type``   | ``write buffer`` | ``value``   |
+================+============+===============+============+==================+=============+
| ``ushort``     | ``char[]`` | ``ushort``    | ``char[]`` | ``ff``           | ``varies``  |
+----------------+------------+---------------+------------+------------------+-------------+

The value field length = sizeof(type).
