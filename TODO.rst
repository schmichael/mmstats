====
TODO
====

* Add string field
* Rename _InternalFieldInterface
* Create base class for CounterField & RunningAverageField
* Add timer field/contextmanager
* Add memory usage field/contextmanager
* Vary filename based on class name
* Add API to dynamically add fields to MmStat classes
* Add alternative procedural writer API (vs existing declarative models)
* Test severity of race conditions
* Test performance

==============
Scrapped Ideas
==============

---------------------------------------------------------------
Compounds Fields where 1 Writer Field = Many Mmap/Reader Fields
---------------------------------------------------------------

This seemed like a honking great idea at first. Compound fields would look just
like a mini-MmStat model:

::

    class SamplingCounterField(CompoundField):
        """Records increments per ms every N increments"""
        counter = CounterField()
        per_ms = UInt64Field()

        class _Counter(object):
            """Implement counter/rate-sampling logic here"""

        def __get__(self, inst, owner):
            if inst is None:
                return self
            return inst._fields[self.key]._counter_instance

The blocker is that there's no way to atomically update all of the compound
fields. The only way to accomplish this is for compound fields to appear as a
single double buffered field with each component field as a type in the type
signature:

::

    class SamplingCounterField(DoubleBufferedField):
        initial = (
            CounterField.initial,
            UInt64Field.initial,
        )
        buffer_type = (
            CounterField.buffer_type,
            UInt64Field.buffer_type,
        )
        type_signature = (
            CounterField.type_signature + UInt64Field.type_signature
        )

Obviously an actual implementation should remove the redundant references to
the component types.

------------------------
Metadata metaprogramming
------------------------

To get around having to dynamically creating the structs due to a variable
label size, put the labels in a header index with a pointer to the actual
struct field.

-------------
Page Flipping
-------------

Store metadata seperate from values. Then store values in multiple pages and
flip between pages for read/write buffering.
