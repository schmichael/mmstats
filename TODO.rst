====
TODO
====

* Add every simple type (strings, ints, floats, bools, etc)
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
