import os
import sys
import fcntl

def daemonize():
    try:
        if os.fork() > 0:
            os._exit(0)
    except OSError as e:
        sys.stderr.write(f"First fork failed: {e}\n")
        sys.exit(1)
    os.setsid()
    os.umask(0)
    try:
        if os.fork() > 0:
            os._exit(0)
    except OSError as e:
        sys.stderr.write(f"Second fork failed: {e}\n")
        sys.exit(1)
    sys.stdout.flush()
    sys.stderr.flush()
    with open('/dev/null', 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open('/dev/null', 'a+') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

def acquire_pidfile(pidfile: str) -> bool:
    try:
        fd = open(pidfile, 'w')
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        return True
    except:
        return False

def release_pidfile(pidfile: str):
    try:
        if os.path.exists(pidfile):
            os.unlink(pidfile)
    except:
        pass