#!/usr/bin/env python3
import argparse
import sys
import os
import signal
import logging
from pathlib import Path
from ..core.monitor import SensorMonitor
from ..utils.daemon import daemonize, acquire_pidfile, release_pidfile
from ..utils.logging import setup_logging

DEFAULT_CONFIG_DIR = Path.home() / '.config' / 'sensor-monitor'
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / 'sm_config.yaml'

def get_default_config():
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return str(DEFAULT_CONFIG_FILE)

def start_daemon(config_file, foreground=False):
    if not os.path.exists(config_file):
        print(f"ERROR: Config file not found: {config_file}")
        print("Run 'sensor-discovery-tui' first to configure sensors")
        sys.exit(1)
    
    setup_logging(config_file, daemon=not foreground)
    mon = SensorMonitor(config_file)
    
    if not mon.mappings:
        logging.error("No sensors configured")
        print("ERROR: No sensors configured!")
        print(f"Config file: {config_file}")
        print("Run 'sensor-discovery-tui' to discover and configure sensors")
        sys.exit(1)
    
    if not foreground:
        print(f"Starting daemon with {len(mon.mappings)} sensors...")
        print(f"Config: {config_file}")
        daemonize()
    
    pidfile = os.path.join(os.path.dirname(os.path.abspath(config_file)), 'sensor_monitor.pid')
    if not acquire_pidfile(pidfile):
        logging.error("Already running")
        print("ERROR: Monitor is already running")
        sys.exit(1)
    
    def shutdown(sig, frame):
        mon.running = False
        release_pidfile(pidfile)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGHUP, lambda s, f: mon.reload_config())
    
    logging.info(f"Starting monitor with {len(mon.mappings)} sensors")
    mon.run()
    release_pidfile(pidfile)

def stop_daemon(config_file):
    pidfile = os.path.join(os.path.dirname(os.path.abspath(config_file)), 'sensor_monitor.pid')
    try:
        with open(pidfile, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped monitor (PID {pid})")
        os.unlink(pidfile)
    except FileNotFoundError:
        print("Monitor is not running (no PID file)")
        sys.exit(1)
    except ProcessLookupError:
        print("Removing stale PID file (process not found)")
        os.unlink(pidfile)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to stop: {e}")
        sys.exit(1)

def reload_daemon(config_file):
    pidfile = os.path.join(os.path.dirname(os.path.abspath(config_file)), 'sensor_monitor.pid')
    try:
        with open(pidfile, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGHUP)
        print(f"Reload signal sent to PID {pid}")
    except FileNotFoundError:
        print("Monitor is not running (no PID file)")
        sys.exit(1)
    except ProcessLookupError:
        print("Removing stale PID file (process not found)")
        os.unlink(pidfile)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to reload: {e}")
        sys.exit(1)

def status(config_file):
    pidfile = os.path.join(os.path.dirname(os.path.abspath(config_file)), 'sensor_monitor.pid')
    print(f"Config file: {config_file}")
    if os.path.exists(pidfile):
        try:
            with open(pidfile, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"Status: Running (PID {pid})")
        except ProcessLookupError:
            print("Status: Not running (stale PID file)")
            os.unlink(pidfile)
        except Exception as e:
            print(f"Status: Error checking - {e}")
    else:
        print("Status: Not running")

def test_once(config_file):
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

def main():
    parser = argparse.ArgumentParser(description="Sensor Monitor for Bitfocus Companion")
    parser.add_argument('-c', '--config', default=None,
                       help=f'Path to configuration file (default: {DEFAULT_CONFIG_FILE})')
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command to execute')
    
    start_parser = subparsers.add_parser('start', help='Start the monitor daemon')
    start_parser.add_argument('--foreground', action='store_true', help='Run in foreground')
    
    subparsers.add_parser('stop', help='Stop the monitor daemon')
    subparsers.add_parser('reload', help='Reload the monitor configuration')
    subparsers.add_parser('status', help='Check if the monitor is running')
    subparsers.add_parser('test', help='Test sensor readings once')
    
    args = parser.parse_args()
    
    if args.config is None:
        config_file = get_default_config()
    else:
        config_file = os.path.abspath(args.config)
    
    if args.command == 'start':
        start_daemon(config_file, foreground=args.foreground)
    elif args.command == 'stop':
        stop_daemon(config_file)
    elif args.command == 'reload':
        reload_daemon(config_file)
    elif args.command == 'status':
        status(config_file)
    elif args.command == 'test':
        test_once(config_file)

if __name__ == '__main__':
    main()