====
TODO
====

There's always bugs to fix: https://github.com/schmichael/mmstats/issues/

* Add API to dynamically add fields to MmStat classes
* Percentiles
* Time based windows for moving averages (eg last 60 seconds)
* Multiple exposed fields (average, mean, and percentiles) from 1 model field
* Add alternative procedural writer API (vs existing declarative models)
* Test severity of race conditions (especially: byte value indicating write
  buffer)
* Test performance
* Vary filename based on class name
* Improve mmash (better live graphing, read from multiple paths, etc)
* Include semantic metadata with field types (eg to differentiate an int that's
  a datetime from an int that's a counter)
* Logo
