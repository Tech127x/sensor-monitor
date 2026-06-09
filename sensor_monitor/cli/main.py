#!/usr/bin/env python3
"""Sensor Monitor CLI - flat action flags like volume-monitor."""

import argparse
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from ..core.monitor import SensorMonitor
from ..utils.logging import setup_logging

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "sensor-monitor"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "sm_config.yaml"


def get_default_config() -> str:
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return str(DEFAULT_CONFIG_FILE)


def _get_pidfile(config_file: str) -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(config_file)), "sensor_monitor.pid"
    )


def _read_pid(pidfile: str) -> int | None:
    try:
        with open(pidfile, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def start_daemon(config_file: str, foreground: bool = False) -> None:
    if not os.path.exists(config_file):
        print(f"ERROR: Config file not found: {config_file}")
        print("Run 'sensor-discovery-tui' first to configure sensors")
        sys.exit(1)

    pidfile = _get_pidfile(config_file)

    # Check if already running
    pid = _read_pid(pidfile)
    if pid and _is_running(pid):
        print(f"ERROR: Daemon already running with PID {pid}")
        sys.exit(1)
    elif pid:
        # Stale PID file
        try:
            os.unlink(pidfile)
        except OSError:
            pass

    if not foreground:
        # Launch detached background process
        cmd = [sys.executable, "-m", "sensor_monitor.cli.main", "-f", "-c", config_file]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        import time

        # Wait up to 10 seconds for the PID file to appear
        for _ in range(50):
            time.sleep(0.2)
            if os.path.exists(pidfile):
                print(f"Started daemon (PID {proc.pid})")
                return
        # Capture any error output from the failed process
        _, stderr = proc.communicate(timeout=1)
        if stderr:
            print(f"Daemon failed to start:\n{stderr.decode().strip()}")
        else:
            print("Daemon failed to start for an unknown reason.")
        sys.exit(1)

    # Foreground mode
    setup_logging(config_file, daemon=False)
    mon = SensorMonitor(config_file)

    if not mon.mappings:
        logging.error("No sensors configured")
        print("ERROR: No sensors configured!")
        print(f"Config file: {config_file}")
        print("Run 'sensor-discovery-tui' to discover and configure sensors")
        sys.exit(1)

    # Acquire PID file lock
    try:
        fd = open(pidfile, "w")
        import fcntl

        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
    except (IOError, OSError):
        print("ERROR: Could not acquire PID file lock")
        sys.exit(1)

    def shutdown(sig, frame):
        mon.running = False
        try:
            os.unlink(pidfile)
        except OSError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGHUP, lambda s, f: mon.reload_config())

    logging.info(f"Starting monitor with {len(mon.mappings)} sensors")
    try:
        mon.run()
    finally:
        try:
            os.unlink(pidfile)
        except OSError:
            pass


def stop_daemon(config_file: str) -> None:
    pidfile = _get_pidfile(config_file)
    pid = _read_pid(pidfile)
    if not pid:
        print("Monitor is not running (no PID file)")
        sys.exit(1)
    if not _is_running(pid):
        print("Removing stale PID file (process not found)")
        try:
            os.unlink(pidfile)
        except OSError:
            pass
        sys.exit(1)
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped monitor (PID {pid})")
        # The daemon's shutdown handler may have already deleted the PID file
        try:
            os.unlink(pidfile)
        except OSError:
            pass
    except Exception as e:
        print(f"Failed to stop: {e}")
        sys.exit(1)


def reload_daemon(config_file: str) -> None:
    pidfile = _get_pidfile(config_file)
    pid = _read_pid(pidfile)
    if not pid:
        print("Monitor is not running (no PID file)")
        sys.exit(1)
    if not _is_running(pid):
        print("Removing stale PID file (process not found)")
        os.unlink(pidfile)
        sys.exit(1)
    try:
        os.kill(pid, signal.SIGHUP)
        print(f"Reload signal sent to PID {pid}")
    except Exception as e:
        print(f"Failed to reload: {e}")
        sys.exit(1)


def status(config_file: str) -> None:
    pidfile = _get_pidfile(config_file)
    print(f"Config file: {config_file}")
    pid = _read_pid(pidfile)
    if not pid:
        print("Status: Not running")
        return
    if _is_running(pid):
        print(f"Status: Running (PID {pid})")
    else:
        print("Status: Not running (stale PID file)")
        os.unlink(pidfile)


def test_once(config_file: str) -> None:
    if not os.path.exists(config_file):
        print(f"ERROR: Config file not found: {config_file}")
        print("Run 'sensor-discovery-tui' to configure sensors first")
        sys.exit(1)

    setup_logging(config_file, daemon=False)
    mon = SensorMonitor(config_file)
    print(f"Loaded {len(mon.mappings)} sensor mappings")
    print(f"Companion: {mon.companion.base_url}")
    print(f"Update interval: {mon.update_interval}s")

    if len(mon.mappings) == 0:
        print("\nWARNING: No sensors configured!")
        print("Run 'sensor-discovery-tui' to discover and configure sensors")
        return

    if not mon.companion.ensure_connected():
        print("WARNING: Cannot connect to Companion")
    else:
        print("Connected to Companion")

    print("\nReading sensors...")
    updated = mon.update_variables()
    print(f"Updated {updated}/{len(mon.mappings)} variables")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sensor Monitor for Bitfocus Companion",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help=f"Path to configuration file (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable verbose debug logging"
    )

    # Action flags (mutually exclusive group)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "-s",
        "--start",
        action="store_true",
        help="Start monitor in background (daemon mode)",
    )
    action_group.add_argument(
        "-f",
        "--start-foreground",
        action="store_true",
        help="Start monitor in foreground",
    )
    action_group.add_argument(
        "-k", "--stop", action="store_true", help="Stop running monitor"
    )
    action_group.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Reload configuration of running monitor",
    )
    action_group.add_argument(
        "-S", "--status", action="store_true", help="Check if monitor is running"
    )
    action_group.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Test sensor readings once (no daemon)",
    )
    parser.add_argument(
        "-T",
        "--tui",
        action="store_true",
        help="Launch the sensor discovery TUI",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Determine config file
    if args.config:
        config_file = os.path.abspath(args.config)
    else:
        config_file = get_default_config()

    # Handle debug flag (set logging level)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # Dispatch actions
    if args.start:
        start_daemon(config_file, foreground=False)
    elif args.start_foreground:
        start_daemon(config_file, foreground=True)
    elif args.stop:
        stop_daemon(config_file)
    elif args.reload:
        reload_daemon(config_file)
    elif args.status:
        status(config_file)
    elif args.test:
        test_once(config_file)
    elif args.tui:
        # Strip the --tui flag from argv before launching the TUI
        # so its own parser doesn't choke on the unknown argument
        cleaned_argv = [sys.argv[0]] + [
            a for a in sys.argv[1:] if a not in ("-T", "--tui")
        ]
        old_argv, sys.argv = sys.argv, cleaned_argv
        try:
            from sensor_monitor.tui.discovery_tui import main as tui_main

            tui_main()
        finally:
            sys.argv = old_argv
    else:
        # Should not happen due to mutually exclusive group, but fallback
        parser.print_help()


if __name__ == "__main__":
    main()
