#!/bin/bash
# Development Environment Setup Script
# Ensures proper configuration for testing the Acoustic Analysis Tool

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════════"
echo "  Acoustic Analysis Tool - Development Environment Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
echo "➤ Checking Python virtual environment..."
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment not found. Creating .venv...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment found${NC}"
fi

# Determine which venv directory to use
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
else
    VENV_DIR="venv"
fi

# Activate virtual environment
echo "➤ Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install/update dependencies
echo "➤ Installing dependencies..."
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check for DISPLAY variable
echo "➤ Checking display configuration..."
if [ -z "$DISPLAY" ]; then
    echo -e "${YELLOW}⚠ DISPLAY not set, using :99${NC}"
    export DISPLAY=:99
else
    echo -e "${GREEN}✓ DISPLAY=$DISPLAY${NC}"
fi

# Check if X server is running
echo "➤ Checking X server..."
if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ X server running on $DISPLAY${NC}"
else
    echo -e "${RED}✗ X server not running on $DISPLAY${NC}"
    echo "  Start X server with: Xvfb $DISPLAY -screen 0 1280x1024x24 &"
    exit 1
fi

# Check for window manager
echo "➤ Checking window manager..."
WM_RUNNING=false
for wm in xfwm4 openbox fluxbox metacity mutter kwin; do
    if pgrep -x "$wm" >/dev/null; then
        WM_DISPLAY=$(ps eww -C "$wm" 2>/dev/null | grep -o "DISPLAY=[^ ]*" | head -1)
        if [ "$WM_DISPLAY" = "DISPLAY=$DISPLAY" ]; then
            echo -e "${GREEN}✓ Window manager ($wm) running on $DISPLAY${NC}"
            WM_RUNNING=true
            break
        else
            echo -e "${YELLOW}⚠ Window manager ($wm) running on different display: $WM_DISPLAY${NC}"
        fi
    fi
done

if [ "$WM_RUNNING" = "false" ]; then
    echo -e "${YELLOW}⚠ No window manager on $DISPLAY. Starting xfwm4...${NC}"
    if command -v xfwm4 >/dev/null 2>&1; then
        DISPLAY=$DISPLAY xfwm4 >/dev/null 2>&1 &
        sleep 2
        echo -e "${GREEN}✓ Window manager started${NC}"
    else
        echo -e "${YELLOW}⚠ xfwm4 not available. GUI may not work properly.${NC}"
    fi
fi

# Initialize database
echo "➤ Initializing database..."
python -c "from src.models import initialize_database; initialize_database()" >/dev/null 2>&1
echo -e "${GREEN}✓ Database initialized${NC}"

# Check materials database
echo "➤ Checking acoustic materials database..."
if [ -f "materials/acoustic_materials.db" ]; then
    echo -e "${GREEN}✓ Materials database found ($(du -h materials/acoustic_materials.db | cut -f1))${NC}"
else
    echo -e "${YELLOW}⚠ Materials database not found at materials/acoustic_materials.db${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ Environment setup complete!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "To run the application:"
echo "  python src/main.py"
echo ""
echo "To run tests:"
echo "  python test_mvp.py                    # Full test suite"
echo "  python test_project_creation.py       # Project creation test"
echo ""
echo "For more information, see TESTING_GUIDE.md"
echo ""
