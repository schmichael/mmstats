`Documentation <http://mmstats.readthedocs.org/>`_ |
`Package <http://pypi.python.org/pypi/mmstats>`_ |
`Code <http://github.com/schmichael/mmstats/>`_

.. image:: https://secure.travis-ci.org/schmichael/mmstats.png?branch=master
   :target: http://travis-ci.org/schmichael/mmstats/


**Not under active development**


About
=====

Mmstats is a way to expose and read diagnostic values and metrics for
applications.

Think of mmstats as /proc for your application and the readers as procps
utilities.

This project is a Python implementation, but compatible implementations can be
made in any language (see Goals).

Discuss at https://groups.google.com/group/python-introspection

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

Usage
=====

Requirements
------------

CPython 2.6 or 2.7 (Windows is untested)

PyPy (only tested in 1.7, should be faster in 1.8)

Using
-----

1. ``easy_install mmstats`` or ``pip install mmstats`` or if you've downloaded
   the source: ``python setup.py install``
2. Then in your Python project create a sublcass of mmstats.MmStats like

.. code-block:: python

    import mmstats

    class WebStats(mmstats.MmStats):
        status2xx = mmstats.CounterField(label='status.2XX')
        status3xx = mmstats.CounterField(label='status.3XX')
        status4xx = mmstats.CounterField(label='status.4XX')
        status5xx = mmstats.CounterField(label='status.5XX')
        last_hit = mmstats.DoubleField(label='timers.last_hit')

3. Instantiate it once per process: (instances are automatically thread local)

.. code-block:: python

    webstats = WebStats(label_prefix='web.stats.')

4. Record some data:

.. code-block:: python

    if response.status_code == 200:
        webstats.status2xx.inc()

    webstats.last_hit = time.time()

5. Run ``slurpstats`` to read it
6. Run ``mmash`` to create a web interface for stats
7. Run ``pollstats -p web.stats.status 2XX,3XX,4XX,5XX /tmp/mmstats-*`` for a
   vmstat/dstat like view.
8. Did a process die unexpectedly and leave around a stale mmstat file?
   ``cleanstats /path/to/mmstat/files`` will check to see which files are stale
   and remove them.


.. include:: CHANGES.rst
   :end-before: 0.5.0
