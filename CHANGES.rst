History
=======

0.6.1 "MANIFEST.out" released 2012-03-08
----------------------------------------

* Fix packaging issue

0.6.0 "PyCon 2012" released 2012-03-08
--------------------------------------

* [API CHANGE] - MovingAverageField's kwarg changed from window_size => size
* Refactored __init__.py into fields, models, and default (and imported public
  bits into __init__)
* Added TimerField (MovingAverageField + context manager)
* Added docs (don't get too excited, just a start)

0.5.0 "100% More Average" released 2012-02-25
---------------------------------------------

* [API CHANGE] - RunningAverage field is now AverageField
* Added MovingAverageField with window_size=100 parameter
* Tests can now be run via "python setup.py test"

0.4.1 "Derpstats" released 2012-01-31
-------------------------------------

* Fixed pollstats
* Updated README slightly

0.4.0 "On the Road to Pycon" released 2012-01-17
------------------------------------------------

* Added clean module and cleanstats script to clean stale mmstat files
* Added path kwarg to MmStats class to allow easy path overriding
* Added StringField for UTF-8 encoded strings
* Added StaticFloatField & StaticDoubleField
* Added created UNIX timestamp (sys.created) to default MmStats class
* Moved all modules into mmstats package
* Fixed mmash template packaging
* Fixed test mmstat file cleanup
* Refactored reading code into mmstats.reader module

0.3.12 "Meow" released 2011-11-29
---------------------------------

* Use ctypes.get_errno() instead of Linux specific wrapper

0.3.11 "Rawr" released 2011-11-29
---------------------------------

* Fix libc loading on OSX

0.3.10 "π²" released 2011-11-28
-------------------------------

* PyPy support (switched from ctypes._CData.from_buffer to .from_address)
* Multiple calls to MmStats().remove() no longer error (makes testing easier)

0.3.9 "MLIT" released 1970-01-01
--------------------------------

* Mistag of 0.3.8

0.3.8 "Hapiness" released 2011-11-20
------------------------------------

* Allow filename templating with %PID% and %TID% placeholders
* Allow setting filename template via MMSTATS_FILES environment variable
* Improved docs slightly
* Fixed Ctrl-Cing run_flask_example script
* Fixed 64 bit integer fields on 32 bit platforms
* Fixed StaticInt64Field (was actually a uint64 field before)
* Fixed slurpstats debug output (always showed first 40 bytes of file)
* Strip newlines from org.python.version

0.3.7 "Depressive Realism is for Winners" released 2011-11-17
-------------------------------------------------------------

* Add pollstats utility (similar to dstat/vmstat)
* Cleanup development/testing section of the README
* Slight improvements to basic flask integration example

0.3.6 "The M is for Mongo" released 2011-11-09
----------------------------------------------

* Allow setting the value of CounterFields

0.3.5 "Ornery Orangutan" released 2011-10-20
--------------------------------------------

* Added a running average field
* Made mmash more configurable and added a console entry point
* Updated TODO
