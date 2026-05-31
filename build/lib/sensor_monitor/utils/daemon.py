import os
import fcntl

def acquire_pidfile(pidfile: str) -> bool:
    """Try to lock and write the PID file. Returns True if successful."""
    try:
        fd = open(pidfile, 'w')
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        # Keep the file open to hold the lock
        return True
    except (IOError, OSError):
        return False

def release_pidfile(pidfile: str):
    """Remove the PID file (best effort)."""
    try:
        if os.path.exists(pidfile):
            os.unlink(pidfile)
    except:
        pass

def write_pidfile(pidfile: str):
    """Write PID without locking (used by subprocess daemon)."""
    with open(pidfile, 'w') as f:
        f.write(str(os.getpid()))