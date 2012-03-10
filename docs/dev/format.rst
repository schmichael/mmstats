mmap Format
===========

Structure of version 1 mmstat's mmaps:

+-------------------+-----------+
| version number    | fields... |
+===================+===========+
| ``byte`` = ``01`` | ...       |
+-------------------+-----------+


Fields
------

There are two types of field structures so far in mmstats:

#. buffered
#. unbuffered

Buffered fields use multiple buffers for handling values which cannot be
written atomically.

Unbuffered structures have ``ff`` in the write buffer field.

Buffered
^^^^^^^^

+------------+------------+------------+------------+--------------+----------+----------+
| label size | label      | type size  | type       | write buffer | buffer 1 | buffer 2 |
+============+============+============+============+==============+==========+==========+
| ``ushort`` | ``char[]`` | ``ushort`` | ``char[]`` | ``byte``     | varies   | varies   |
+------------+------------+------------+------------+--------------+----------+----------+

The buffers field length = sizeof(type) * buffers.

The current write buffer is referenced by: write_buffer * sizeof(type)

TODO: field for total number of buffers?


Unbuffered
^^^^^^^^^^

+------------+------------+------------+------------+-------------------+---------+
| label size | label      | type size  | type       | write buffer      | value   |
+============+============+============+============+===================+=========+
| ``ushort`` | ``char[]`` | ``ushort`` | ``char[]`` | ``byte`` = ``ff`` | varies  |
+------------+------------+------------+------------+-------------------+---------+

The value field length = sizeof(type).
