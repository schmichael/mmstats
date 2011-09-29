====
Wat?
====

Mmstats is a way to expose and read (slurpstats.py) diagnostic/statistical
values for applications.

You could think of mmstats as /proc for your application and slurpstats.py as one
of the procps tools.

-----
Goals
-----

* Separate publishing/writing from consuming/reading tools
* Platform/language independent (a Java writer can be read by a Python tool)
* Predictable performance impact for writers via:

  * No locks (1 writer per thread)
  * No syscalls
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

PyPy once `issue869 <https://bugs.pypy.org/issue869>`_ is resolved.

-----
Using
-----

1. ``python setup.py install`` # Or copy mmstats.py into your project
2. ``import mmstats``
3. Create a subclass of mmstats.MmStats like:

::

    class WebStats(mmstats.MmStats):
        status2xx = mmstats.UIntField(label='status.2XX')
        status3xx = mmstats.UIntField(label='status.3XX')
        status4xx = mmstats.UIntField(label='status.4XX')
        status5xx = mmstats.UIntField(label='status.5XX')

4. Instantiate it once per thread/process:

::

    webstats = WebStats(label_prefix='web.stats.')

5. Record some data:

::

    if response.status_code == 200:
        webstats.status2xx += 1

6. Run ``python slurpstats.py`` to read it
7. Run ``python mmash.py`` to create a web interface for stats

-------------------
Testing/Development
-------------------

#. Run your favorite Python test runner (py.test or nosetests)
#. Run slurpstats.py
#. Clean /tmp/mmstats-* files up

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
