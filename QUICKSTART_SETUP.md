# 🚀 Quick Start

## First Time Setup

### Mac/Linux
```bash
./setup.sh
```

### Windows
```batch
setup.bat
```

This will:
- ✓ Check Python version (3.8+ required)
- ✓ Create virtual environment
- ✓ Install all dependencies
- ✓ Create data directories
- ✓ Verify installation

## Running the Application

### Streamlit Web Interface (Recommended)

**Mac/Linux:**
```bash
./start.sh
```

**Windows:**
```batch
start.bat
```

The browser will open automatically at http://localhost:8502

### Command Line Interface

**Mac/Linux:**
```bash
source venv/bin/activate
python main.py recipe sample --symbol AAPL
```

**Windows:**
```batch
venv\Scripts\activate.bat
python main.py recipe sample --symbol AAPL
```

## Troubleshooting

**Virtual environment issues:**
```bash
# Mac/Linux
rm -rf venv
./setup.sh

# Windows
rmdir /s /q venv
setup.bat
```

**Package installation fails:**
```bash
# Upgrade pip first
python -m pip install --upgrade pip
./setup.sh  # or setup.bat on Windows
```

**DuckDB lock error:**
- Close CLI before starting Streamlit (or vice versa)
- Only one instance can access the database at a time

## Requirements

- Python 3.8 or higher
- pip (included with Python)
- Internet connection (for installation)

## Project Structure

```
wawastock/
├── setup.sh / setup.bat    # Setup script
├── start.sh / start.bat    # Launch script
├── main.py                 # CLI entry point
├── streamlit_app.py        # Web interface
├── requirements.txt        # Dependencies
├── engines/               # Core engines
├── strategies/            # Trading strategies
├── recipes/               # Strategy recipes
└── data/                  # Data storage
```
