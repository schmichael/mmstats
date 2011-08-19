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

+============+==================+======+==============+=========+
| label size | label            | type | write buffer | buffers |
+============+==================+======+==============+=========+
| ushort     | label size bytes | char | byte         | varies  |
+------------+------------------+------+--------------+---------+

The buffers field length = sizeof(type) * buffers.

The current write buffer is referenced by: write_buffer * sizeof(type)

TODO: field for total number of buffers?

----------
Unbuffered
----------

+============+==================+======+==============+=========+
| label size | label            | type | write buffer | value   |
+============+==================+======+==============+=========+
| ushort     | label size bytes | char | ff           | varies  |
+------------+------------------+------+--------------+---------+

The value field length = sizeof(type).
