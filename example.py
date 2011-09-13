import os
import mmstats
import libgettid

class MyStats(mmstats.BaseMmStats):
    pid = mmstats.StaticUIntField(label="sys.pid", value=os.getpid)
    tid = mmstats.StaticInt64Field(label="sys.tid", value=libgettid.gettid)
    uid = mmstats.StaticUInt64Field(label="sys.uid", value=os.getuid)
    gid = mmstats.StaticUInt64Field(label="sys.gid", value=os.getgid)
    errors = mmstats.UIntStat(label="com.urbanairship.app.errors")
    warnings = mmstats.UIntStat(label="com.urbanairship.app.warnings")
    queries = mmstats.UIntStat(label="com.urbanairship.app.queries")
    cache_hits = mmstats.UIntStat(label="com.urbanairship.app.cache_hits")
    cache_misses = mmstats.UIntStat(label="com.urbanairship.app.cache_misses")
    degraded = mmstats.BoolStat(label="com.urbanairship.app.degraded")

stats = MyStats(filename="mmstats-test-mystats")
stats.degraded = True
stats.errors += 1
stats.cache_hits += 1000
stats.queries = 50
