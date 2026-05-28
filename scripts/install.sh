#!/usr/bin/env python3
"""Cross-shell installer for Sensor Monitor."""
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent
    venv_dir = root / ".venv"
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    if sys.platform == "win32":
        pip = venv_dir / "Scripts" / "pip"
    else:
        pip = venv_dir / "bin" / "pip"
    
    print("Installing package and dependencies...")
    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(pip), "install", "-e", str(root)], check=True)
    
    print("\nInstallation complete!")
    print("\nTo activate the virtual environment:")
    print("  bash / zsh: source .venv/bin/activate")
    print("  fish:       source .venv/bin/activate.fish")
    print("\nThen run:")
    print("  sensor-discovery-tui   # to configure sensors")
    print("  sensor-monitor start   # to start the daemon")

if __name__ == "__main__":
    main()