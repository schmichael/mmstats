mmap Format: Version 2 proposal
===============================

Structure of version 2 mmstat's mmaps:

+-------------------+-----------+
| version number    | fields... |
+===================+===========+
| ``byte`` = ``02`` | ...       |
+-------------------+-----------+


Fields
------

There are three classes of field structures so far in mmstats:

#. buffered
#. unbuffered
#. buffered array

Buffered fields use multiple buffers for handling values which cannot be
written atomically.

Unbuffered structures have ``ff`` in the write buffer field.

Each field has two distinct type definitions -- data type and metric type.

Example data types:
#. Buffered Unsigned Integer
#. Static Float
#. Buffered Double
#. Buffered Integer Array
#. Static String

TODO: document data type IDs

Example metric types:
#. Gauge
#. Counter
#. Informational (what should we call a string output?)

Each field is prefixed by the length of the entire field data.

Unbuffered
^^^^^^^^^^

+------------+------------+------------+------------+-------------+---------+
| field size | label size | label      | data type  | metric type | value   |
+============+============+============+============+=============+=========+
| ``int32``  | ``ushort`` | ``char[]`` | ``ushort`` | ``ushort``  | varies  |
+------------+------------+------------+------------+-------------+---------+

Data type is an integer enum for the list of defined types. The value field length = sizeof(type)

Buffered
^^^^^^^^

+------------+------------+------------+------------+-------------+--------------+----------+----------+
| field size | label size | label      | data type  | metric type | write buffer | buffer 1 | buffer 2 |
+============+============+============+============+=============+==============+==========+==========+
| ``int32``  | ``ushort`` | ``char[]`` | ``ushort`` | ``ushort``  | ``byte``     | varies   | varies   |
+------------+------------+------------+------------+-------------+--------------+----------+----------+

Data type is an integer enum for the list of defined types. The buffers field length = sizeof(type) * buffers.

The current write buffer is referenced by: write_buffer * sizeof(type)

TODO: field for total number of buffers?

Array
~~~~~

+------------+------------+------------+------------+-------------+---------------------+------------+--------+
| field size | label size | label      | data type  | metric type | write buffer offset | array size | buffer |
+============+============+============+============+=============+=====================+============+========+
| ``int32``  | ``ushort`` | ``char[]`` | ``ushort`` | ``ushort``  | ``ushort``          | ``ushort`` | varies |
+------------+------------+------------+------------+-------------+---------------------+------------+--------+

An array is made up of ``array size`` + 1 individual buffers, each of length = sizeof(type)

The buffers field length = sizeof(type) * (array size + 1).

The current write buffer is referenced by: write_buffer * data size. Readers should ignore that subfield when reading values. The reader should present "beginning" of the array as the first subfield after the write buffer subfield, wrapping around until the write buffer subfield is reached.
