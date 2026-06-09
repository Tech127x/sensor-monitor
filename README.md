### FYI -- This program is built and tested on:
   - Bitfocus Companion BETA >= Companion: v5.0.0+9451 main-28ba9a55a8  
   - OS: Linux (v7.0.11-1-cachyos; x64)  

I am very actively working on this project. If you give it a try, please send me feedback! The more I know from all of you, the better it will become!  I have made many improvements in the last couple days so make sure you're using the latest version and check frequently for updates. Thanks!

# 🌡️ Sensor Monitor for Bitfocus Companion

Real-time hardware monitoring at your fingertips — finally, sensor data that just works.

You're deep in a render, a game, or overclocking experiment. Your CPU is cooking, your GPU fans are screaming, and you have no idea what's actually happening inside your case. You could open a terminal and run `sensors`, squint at the output, and try to remember which `temp1` is which. Or you could glance at your Stream Deck and see everything — CPU temp, coolant temp, fan speeds, voltages — updating live, with friendly names you actually understand.

Sensor Monitor fixes all of this. It discovers every sensor in your system (CPU, GPU, motherboard, NVMe drives, liquid coolers, fan controllers — yes, even that obscure Aquacomputer High Flow Next), pushes their values to Bitfocus Companion custom variables, and lets you build beautiful, informative dashboards on your Stream Deck. All with zero manual config file editing — just click what you want, and it's done.


## ✨ What Makes This Different?

### 🔍 Automatic Discovery — No More Guessing

Sensor Monitor doesn't make you dig through `sensors -j` output or edit YAML by hand. Launch the Terminal UI (`sensor-discovery-tui`) and it instantly finds every sensor on your system — CPU cores, GPU temps, fan speeds, voltages, liquid cooling flow rates, even NVMe drive temperatures. Each sensor gets a human-friendly name (like "CPU CCD1 Temp" instead of `Tccd1`) and a suggested Companion variable name. You just toggle the ones you want and hit save. Done.

### 🖱️ Click to Enable — Seriously, It's That Easy

The discovery table has two columns: **Enabled** and **Configured**. See a sensor you want? Click the "Enabled" column (or press Space) — it flips from "- No" to "✓ Yes". Edit the variable name if you want (or keep the smart default). Then click **Save & Reload**. The sensor is instantly added to your config and the daemon starts pushing its value to Companion. To remove a sensor, just click it again and save — it's removed from your config but your other sensors stay untouched.

### 🧠 Smart Defaults — Sensible From the Start

Brand new sensors get a Companion-safe variable name like `temperature\_coolant` or `fan\_cpu\_fan`. Each sensor's unit (°C, RPM, V, W, dL/h) is automatically detected and included in the Companion value format (e.g., `27.7°C`). No more manually setting formats or worrying about units. And if you want to divide a value (like converting millivolts to volts) or override the unit, the TUI gives you fields for that too.

### ⚡ Real-Time, Always

The daemon polls your sensors every second (configurable) and pushes updates to Companion instantly. Changes appear on your Stream Deck before your eyes can leave the screen. Lost connection to Companion? It automatically reconnects and picks up right where it left off.

### 🐟 Fish-Friendly, Shell-Agnostic

First-class Fish shell support with tab completions and automatic PATH configuration. But bash and zsh users are fully supported too — the pipx installer handles everything. The default config lives at `~/.config/sensor-monitor/sm\_config.yaml` so you never have to think about file paths.


## 🚀 Quick Install

```
\#Install system dependencies (lm-sensors is required)  
  
sudo pacman -S lm\_sensors python-pipx \# Arch / CachyOS  
  
\# or: sudo apt install lm-sensors python3-pipx \# Debian/Ubuntu  
  
\# Install Sensor Monitor via pipx  
  
pipx install --force --editable git+https://github.com/tech127x/sensor-monitor-ds.git  

# That's it! The default config directory is auto-created.


**Note for AMD GPU users:**  
  
install `rocm-smi` separately from your distribution (e.g., `pacman -S rocm-smi-lib`). Sensor Monitor will automatically detect it if present.
```

After install, you have two main commands:

- `sensor-monitor` — Launch the TUI, start/stop/status/test the daemon
- `sensor-discovery-tui` — Interactive sensor configuration (also accessible via `sensor-monitor -T`)
- `sensor-discovery` (optional CLI discovery)


## 🎮 Usage — So Simple You'll Forget It's Running

```
sensor-monitor -T       # Launch the discovery & configuration TUI
sensor-monitor -t       # Test: read sensors, push to Companion once
sensor-monitor -s       # Start daemon in background
sensor-monitor -S       # Check if daemon is running
sensor-monitor -k       # Stop daemon
sensor-monitor -r       # Reload config without restarting
sensor-monitor -f       # Run in foreground (for systemd / debugging)
```

Fish Shell? Add these to your config for even faster access:

```
alias sm="sensor-monitor"  
alias smt="sensor-monitor -T"  
alias sms="sensor-monitor -S"
```


## 🎛️ Stream Deck+ Variable Setup

Sensor Monitor automatically creates Companion custom variables as you enable sensors. You just need to create matching feedback elements on your Stream Deck. For each sensor you enable, a variable is created with the name you chose (e.g.,`temperature\_coolant`). Its value is a formatted string like `27.7°C` or `1459 RPM`.

**Example Stream Deck+ button setup:**

1. Create a new button, set it to "Custom Variable" type

2. Variable name: `temperature\_coolant`

3. The button will display whatever the daemon pushes — e.g., `27.7°C`

**Example layout:**

- Top row: CPU temp, GPU temp, Coolant temp

- Middle: Fan speeds, pump speed

- Bottom: Voltages (+12V, +5V, VCore)

All values update every second — no manual refreshing.


## 🔧 Configuration — No Text Editors Needed

Run the interactive TUI:

```
sensor-monitor -T
# or
sensor-discovery-tui
```

### What you'll see

- A loading screen ("🔍 Discovering Sensors…") while it scans your hardware (may take a few seconds on systems with many sensors)

- A table of every sensor found, with columns: **Enabled**, **Configured**, reading, unit, chip, and label

- A detail panel at the bottom showing:
  - Sensor info (number, name, chip, sensor group)
  - Status (Enabled, Configured, pending changes)
  - **Companion value preview** — shows exactly what will be sent to Companion (e.g., `quadro_fan_1 = 2081`)
  - Editable fields: **variable name**, **divide by**, and **unit override**

### To add a sensor:

1. Find it in the table (use `/` to filter)

2. Click the **Enabled** column (or press Space) to toggle it to "✓ Yes"

3. Optionally tweak the variable name or unit in the detail panel

4. Click **Save & Reload** — the sensor is added to your config and the daemon picks it up immediately

### To remove a sensor:

1. Find the configured sensor (shows "Configured: ✓ Yes")

2. Click its Enabled column to mark it for removal (status shows "Will be REMOVED on next save")

3. Click **Save & Reload**

### Editing variable names

- Press **Tab** or **Enter** after editing the variable name — it's **auto-sanitized** (invalid characters replaced with underscores, hyphens converted)
- Press **Tab** to cycle through fields: Variable name → Divide by → Unit

### Removing the unit suffix

By default, Companion values include the unit suffix (e.g., `2105RPM`). To send bare numbers:

1. Select the sensor in the table
2. Delete the unit text in the **Unit** field
3. Click **Save & Reload**

The Companion value will now be just the number (e.g., `2105`).

### Buttons

| Button | Action |
|---|---|
| **Sensor default** | Reset variable name, divide by, and unit to defaults |
| **Save changes** | Write config to disk |
| **Save & Reload** | Write config and tell the running daemon to reload |
| **Exit** | Close the TUI |

### Keyboard shortcuts

| Key | Action |
|---|---|
| `/` | Focus the filter/search box |
| `Space` | Toggle selected sensor on/off |
| `a` | Enable all sensors |
| `z` | Disable all sensors |
| `o` / `g` / `c` / `i` / `p` / `u` / `v` / `n` / `b` | Sort by various columns |
| `r` | Reverse sort order |
| `q` | Quit |

All settings are stored in `~/.config/sensor-monitor/sm\_config.yaml`. You can edit it manually if you prefer, but you'll rarely need to.


## 📊 Requirements

- Linux with lm-sensors (`sensors` command)

- Python 3.9+

- pipx (recommended) or pip

- Bitfocus Companion with TCP API enabled (default port 8000)

- Optional: nvidia-smi for NVIDIA GPU monitoring, rocm-smi for AMD GPUs, smartctl for disk temperatures, nvme-cli for NVMe drive temperatures.


## 🆘 Troubleshooting

| Problem | Solution |
| - | - |
| "No sensors configured" when testing | Run `sensor-discovery-tui` and enable some sensors, then Save & Reload |
| Daemon won't start | Check `sensor-monitor status` — if it says already running, `stop` first |
| Variable not showing in Companion | Ensure Companion's HTTP API is enabled on port 8000 and reachable. Run `sensor-monitor test` to see connection status |
| Sensor values missing in TUI | Run `sensors -j` in a terminal — if it hangs, there may be a kernel driver issue. The TUI has a 30‑second timeout; adjust if needed |
| "libsensors not available" message | Normal — falls back to `sensors -j` subprocess which works perfectly |
| Config file not found | Default is `~/.config/sensor-monitor/sm\_config.yaml`. Use `-c` flag to specify a custom path |



## 📦 Updating

```
pipx upgrade sensor-monitor  
  
\# or if installed from git:  
  
cd ~/sensor-monitor-ds && git pull && pipx install --force --editable .  
sensor-monitor reload \# tell the running daemon to pick up any changes
```


## 🗑️ Uninstall

```
sensor-monitor stop  
pipx uninstall sensor-monitor  
rm -rf ~/.config/sensor-monitor
```


## 📝 License

MIT — use it, modify it, share it. Just give credit!


**Made with ❤️ for the CachyOS community, Bitfocus Companion users, and Stream Deck enthusiasts everywhere!**

If you find this project useful, consider supporting my work. Thanks!

[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/tech127x)


## Disclaimer

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

**Use at your own risk.** This software interacts directly with system hardware. Please ensure you understand the implications of monitoring and potentially controlling hardware sensors. The author assumes no responsibility for any damage or data loss.
