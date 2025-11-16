#!/bin/bash
# WawaStock - Setup Script
# This script sets up the Python virtual environment and installs all dependencies

set -e  # Exit on error

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════╗"
echo "║     WawaStock - Setup & Installation Script       ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
print_info "Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed!"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-venv python3-pip"
    echo "  Other: Visit https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

print_success "Found Python $PYTHON_VERSION"

# Check if Python version is 3.8 or higher
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check if pip is available
if ! python3 -m pip --version &> /dev/null; then
    print_error "pip is not available!"
    echo ""
    echo "Please install pip:"
    echo "  macOS/Linux: python3 -m ensurepip --upgrade"
    echo "  Or download get-pip.py from https://bootstrap.pypa.io/get-pip.py"
    exit 1
fi

print_success "pip is available"
echo ""

# Remove old virtual environment if it exists and is broken
if [ -d "venv" ]; then
    print_info "Found existing virtual environment..."
    
    # Test if venv is working
    if ! ./venv/bin/python --version &> /dev/null; then
        print_warning "Virtual environment appears to be broken. Removing..."
        rm -rf venv
    else
        print_success "Virtual environment is working. Skipping creation..."
        SKIP_VENV_CREATE=1
    fi
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment!"
        echo ""
        echo "You may need to install venv:"
        echo "  Ubuntu/Debian: sudo apt-get install python3-venv"
        exit 1
    fi
    
    print_success "Virtual environment created"
elif [ -z "$SKIP_VENV_CREATE" ]; then
    print_success "Using existing virtual environment"
fi

echo ""

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment!"
    exit 1
fi

print_success "Virtual environment activated"
echo ""

# Upgrade pip, setuptools, and wheel
print_info "Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel --quiet

if [ $? -ne 0 ]; then
    print_warning "Failed to upgrade pip/setuptools/wheel (continuing anyway...)"
else
    print_success "pip, setuptools, and wheel upgraded"
fi

echo ""

# Install requirements
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found!"
    exit 1
fi

print_info "Installing Python packages from requirements.txt..."
echo ""

# Install with progress
python -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    print_error "Failed to install some packages!"
    echo ""
    echo "Common fixes:"
    echo "  1. Check your internet connection"
    echo "  2. Try: pip install --upgrade pip"
    echo "  3. Try installing packages individually"
    exit 1
fi

echo ""
print_success "All packages installed successfully!"
echo ""

# Create necessary directories
print_info "Creating data directories..."
mkdir -p data/parquet data/processed logs

print_success "Data directories created"
echo ""

# Test imports
print_info "Testing critical imports..."

python -c "
import sys
errors = []

packages = [
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('backtrader', 'backtrader'),
    ('streamlit', 'streamlit'),
    ('plotly', 'plotly'),
    ('yfinance', 'yfinance'),
    ('duckdb', 'duckdb'),
]

for name, module in packages:
    try:
        __import__(module)
        print(f'  ✓ {name}')
    except ImportError as e:
        print(f'  ✗ {name}: {e}')
        errors.append(name)

if errors:
    print(f'\nFailed to import: {', '.join(errors)}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    print_error "Some packages failed to import!"
    exit 1
fi

echo ""
print_success "All critical packages imported successfully!"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════╗"
echo "║              Setup Complete! 🎉                    ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the application:"
echo "     ${GREEN}./start.sh${NC}"
echo ""
echo "  2. Or manually activate the environment:"
echo "     ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "  3. Run CLI commands:"
echo "     ${GREEN}python main.py recipe sample --symbol AAPL${NC}"
echo ""
echo "  4. Run Streamlit interface:"
echo "     ${GREEN}streamlit run streamlit_app.py${NC}"
echo ""
print_success "Virtual environment is ready to use!"
echo ""
