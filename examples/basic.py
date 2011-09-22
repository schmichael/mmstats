import os
import mmstats
import libgettid


class MyStats(mmstats.BaseMmStats):
    pid = mmstats.StaticUIntField(label="sys.pid", value=os.getpid)
    tid = mmstats.StaticInt64Field(label="sys.tid", value=libgettid.gettid)
    uid = mmstats.StaticUInt64Field(label="sys.uid", value=os.getuid)
    gid = mmstats.StaticUInt64Field(label="sys.gid", value=os.getgid)
    errors = mmstats.UIntField(label="com.urbanairship.app.errors")
    warnings = mmstats.UIntField(label="com.urbanairship.app.warnings")
    queries = mmstats.UIntField(label="com.urbanairship.app.queries")
    cache_hits = mmstats.UIntField(label="com.urbanairship.app.cache_hits")
    cache_misses = mmstats.UIntField(label="com.urbanairship.app.cache_misses")
    degraded = mmstats.BoolField(label="com.urbanairship.app.degraded")
    foo = mmstats.StaticTextField(
        label="com.idealist.app.name", value="webapp")

stats = MyStats(filename="mmstats-test-mystats")
stats.degraded = True
stats.errors += 1
stats.cache_hits += 1000
assert stats.cache_hits == 1000
