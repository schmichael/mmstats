import errno
import os
import sys


from mmstats import reader as mmstats_reader


def clean(files):
    alive, removed = 0, 0
    for fn in files:
        sys.stdout.flush()
        if os.path.isdir(fn):
            continue

        try:
            reader = mmstats_reader.MmStatsReader.from_file(fn)
        except mmstats_reader.InvalidMmStatsVersion:
            print 'Invalid file: %s' % fn
            continue
        except IOError as e:
            if e.errno == errno.EACCES:
                print 'Permission denied: %s' % fn
            # Other IOErrors aren't even worth mentioning
            continue

        pid = None
        for k, v in reader:
            if k.endswith('sys.pid'):
                pid = v

        if pid is None:
            print 'File has no sys.pid entry: %s' % fn
            continue

        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.EPERM:
                print ('PID %d is alive but owned by another user, skipping.'
                        % pid)
                continue
            elif e.errno == errno.ESRCH:
                # 'No such process' means we can safely delete this stale pid
                print 'PID %d not found. Deleting %s' % (pid, fn)
            else:
                # Don't assume it's safe to continue after other OSErrors
                raise
        else:
            # PID is alive and well, leave it alone
            alive += 1
            continue

        try:
            os.remove(fn)
            removed += 1
        except OSError as e:
            print('Could not remove %s: %s' % (fn, str(e)))
    print 'Removed %d  -  %d alive' % (removed, alive)


def cli():
    if len(sys.argv) == 1:
        print 'usage: %s MMSTAT_FILES' % os.path.basename(sys.argv[0])
    else:
        clean(sys.argv[1:])


if __name__ == '__main__':
    cli()
