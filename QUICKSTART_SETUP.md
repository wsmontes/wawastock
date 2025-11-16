# 🚀 Quick Start – Environment Setup

Use this guide the first time you clone the repo or whenever you need to rebuild your environment.

## 1. Run the Setup Script

### macOS / Linux
```bash
./setup.sh
```

### Windows
```batch
setup.bat
```

The script will:

- ✓ Verify Python ≥ 3.8
- ✓ Create/refresh the `venv/` virtual environment
- ✓ Install `requirements.txt`
- ✓ Create `data/processed`, `data/parquet`, and `logs/`
- ✓ Validate key imports (backtrader, duckdb, pandas, Streamlit)

> Tip: rerun the script whenever dependencies change; it’s idempotent.

## 2. Activate the Virtual Environment

```bash
# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Keep the terminal active while running CLI commands or Streamlit.

## 3. Launch an Interface

### Streamlit UI (recommended for demos)

```bash
./start.sh        # start.bat on Windows
```

Your browser opens to http://localhost:8502 with the Backtest Runner and companion pages.

### Command-line sample

```bash
python main.py run-recipe --name sample --symbol AAPL --start 2022-01-01 --end 2022-12-31
```

## 4. Common Issues & Fixes

| Issue | Symptoms | Fix |
|-------|----------|-----|
| Virtualenv corruption | `ModuleNotFoundError`, odd pip state | Delete `venv/` then rerun `./setup.sh` (or `setup.bat`). |
| Pip install failures | SSL / wheel build errors | `python -m pip install --upgrade pip` then rerun setup. |
| DuckDB lock | "Database is locked" when running CLI + Streamlit together | Close Streamlit before running heavy CLI jobs, or stagger commands. |
| Missing data | `FileNotFoundError: data/processed/SYMBOL.parquet` | Use `python main.py fetch-data ...` or scripts under `scripts/` to seed data. |

## 5. Requirements Checklist

- Python 3.8+
- pip (bundled with Python)
- Internet connection for package/data downloads
- ~2 GB disk space for sample data + env

## 6. Project Landmarks

```

├── setup.sh / setup.bat      # Environment automation
├── start.sh / start.bat      # Streamlit launcher
├── main.py                   # CLI entry point
├── engines/                  # Core engines (data, backtest, indicators, report)
├── strategies/               # Trading strategies
├── recipes/                  # Full workflows
├── streamlit_pages/          # Streamlit multi-page app
├── streamlit_components/     # Reusable UI widgets
├── scripts/                  # Data utilities
└── data/                     # Parquet + DuckDB storage
```

## 7. Next Steps

- Head to `QUICKSTART.md` for a strategy-by-strategy guide.
- Open `docs/STRATEGIES.md` to understand each recipe’s logic and parameters.
- Read `docs/LOGGING.md` if you want to customize the Rich/Loguru output right away.
├── strategies/            # Trading strategies
