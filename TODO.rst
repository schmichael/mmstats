====
TODO
====

* Add API to dynamically add fields to MmStat classes
* Percentiles
* Time based windows for moving averages (eg last 60 seconds)
* Multiple exposed fields (average, mean, and percentiles from 1 model field)
* Add alternative procedural writer API (vs existing declarative models)
* Test severity of race conditions (especially: byte value indicating write
  buffer)
* Test performance
* Vary filename based on class name


=========================
Layout and Conventions v2
=========================

- Packages and even modules should feel free to define their own Stats model
  (so >1 mmap per application thread)

 - eg: foo.eggs.Stats, foo.spam.Stats, and sqlalchemy.Stats

- File structure would be:

 - MMSTATS_PATH environment variable for per application top-level dir
 - Stats.__name__ for per *class* sub-directories
 - Generic field names defined in the class (eg ``response_time`` for web app
   handlers)
 - ``<handler>.<metric>:<value>`` for specific handler's metric's values (eg
   ``index.response_time:Percentile50th``)

This creates a single nested directory structure for each application where
each module, package, and library is free to define it's own mmstat class/file.

Rename Fields to Metrics and rename classes in models.py

For example:

::

    /tmp/some-mmstats-app/sqlalchemy/mmstats-<pid>-<tid> contains:

        connection_foo.url => "sqlite://..."
        users_table.select_time.Percentile50th => 10
        users_table.select_time.Percentile75th => 12

    /tmp/some-mmstats-app/my-app/mmstats-<pid>-<tid> contains:

        index.response_time.Percentile50th => 0.010
        index.response_time.Percentile75th => 0.050
        index.response_time.Percentile99th => 0.150
        login.response_time.Percentile50th => 0.010
        login.response_time.Percentile75th => 0.050


Psuedo-code for my_app/handlers.py:

::

    class Stats(DynaStats):
        response_ok = Counter()
        response_bad = Counter()
        response_time = Timer()

    stats = Stats(groups=['index', 'login'])

    def stats_wrapper(f):
        function_stats = stats.get_group(f.__name__)
        def wrapped(*args, **kwargs):
            ret = f(function_stats, *args, **kwargs)
            if ret.status == 200:
                function_stats.response_ok.inc()
            else:
                function_stats.response_bad.inc()
            return ret

    def index(request):
        my_stats = stats.get_group('index')
        my_stats.reponse_ok.inc()
        stats.index.response_ok.inc()

    @stats_wrapper
    def index(stats, request):
        # implementation left up to the reader
        pass


    @stats_wrapper
    def login(stats, request, username=None):
        # same
        pass

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

*Note:* Lack of atomicity is not a blocker for exposing fields such as Mean,
Median, and Percentiles.

*Solution:* Future versions of the mmstats format should support structs as
values instead of just scalars so that a single write buffer offset can point
to multiple values.

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
