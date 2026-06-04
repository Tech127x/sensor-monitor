# Contributing to Sensor Monitor

First off, thanks for taking the time to contribute! 🎉

## How to contribute

### Reporting bugs

Open an issue on GitHub with:

- A clear title and description
- Steps to reproduce
- Your system info (OS, Python version, lm-sensors output)
- The output of `sensor-monitor -S` and `sensor-monitor -t`

### Suggesting features

Open an issue labeled `enhancement` with:

- What you're trying to achieve
- Why the current approach doesn't work
- A rough idea of how it could work

### Pull requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run existing tests: `pytest tests/`
5. Run linting: `black . && mypy sensor_monitor/`
6. Commit with a clear message
7. Push and open a PR

### Development setup

```sh
git clone https://github.com/your-username/sensor-monitor-ds.git
cd sensor-monitor-ds
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Code style

- Format with **black**
- Type-check with **mypy** (strict-ish, we tolerate some bare `except` warnings)
- Keep variable names descriptive but concise
- PRs that also clean up diagnostics (warnings/errors) are especially welcome

## Questions?

Open a discussion or reach out through the issue tracker.
