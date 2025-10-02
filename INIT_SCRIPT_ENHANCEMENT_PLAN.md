# Init.sh Enhancement Plan for Enhanced Calculator Flow Tracer

## Current init.sh Analysis

The existing `init.sh` script provides:
- Virtual environment activation
- Environment variable setup (`HVAC_DEBUG_EXPORT`, `HVAC_USE_PATH_DATA_BUILDER`)
- Application execution

## Enhanced Flow Tracer Requirements

Based on the designed Enhanced Calculator Flow Tracer, the setup needs:
1. **New Environment Variables** for tracer configuration
2. **Automatic Instrumentation** of calculator modules
3. **Validation Setup** for calculator input/output
4. **Debug Output Configuration** with structured logging

## Proposed init.sh Modifications

### 1. New Environment Variables

```bash
# Enhanced Calculator Flow Tracer Configuration
export HVAC_ENHANCED_TRACING="${HVAC_ENHANCED_TRACING:-1}"
export HVAC_CALCULATOR_VALIDATION="${HVAC_CALCULATOR_VALIDATION:-1}"
export HVAC_TRACE_LEVEL="${HVAC_TRACE_LEVEL:-INFO}"  # DEBUG, INFO, WARNING, ERROR
export HVAC_TRACE_OUTPUT="${HVAC_TRACE_OUTPUT:-console}"  # console, file, both
export HVAC_TRACE_FILE="${HVAC_TRACE_FILE:-debug_trace.log}"
```

### 2. Conditional Tracer Setup

```bash
# Enhanced Calculator Flow Tracer Setup
if [[ "${HVAC_ENHANCED_TRACING}" == "1" ]]; then
    echo "Enabling Enhanced Calculator Flow Tracer..."
    export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

    # Pre-validate tracer components exist
    TRACER_FILES=(
        "${SCRIPT_DIR}/src/calculations/calculator_flow_tracer.py"
        "${SCRIPT_DIR}/src/calculations/calculator_tracer_integration.py"
        "${SCRIPT_DIR}/src/calculations/enable_enhanced_tracing.py"
    )

    for file in "${TRACER_FILES[@]}"; do
        if [[ ! -f "${file}" ]]; then
            echo "Warning: Enhanced tracer file not found: ${file}" >&2
            echo "Run setup to install enhanced tracer components" >&2
            exit 1
        fi
    done

    echo "✓ Enhanced Calculator Flow Tracer components verified"
    echo "  Tracing Level: ${HVAC_TRACE_LEVEL}"
    echo "  Output Mode: ${HVAC_TRACE_OUTPUT}"
    if [[ "${HVAC_TRACE_OUTPUT}" != "console" ]]; then
        echo "  Log File: ${HVAC_TRACE_FILE}"
    fi
fi
```

### 3. Setup Mode for First-Time Installation

```bash
# Check for setup mode
if [[ "${1:-}" == "setup" ]]; then
    echo "Running Enhanced Calculator Flow Tracer setup..."

    # Create tracer components if they don't exist
    python "${SCRIPT_DIR}/scripts/setup_enhanced_tracer.py" || {
        echo "Failed to setup enhanced tracer components" >&2
        exit 1
    }

    echo "✓ Enhanced Calculator Flow Tracer setup complete"
    echo "Run './init.sh' to start with enhanced tracing enabled"
    exit 0
fi
```

### 4. Runtime Tracer Activation

```bash
# Pre-flight tracer activation
if [[ "${HVAC_ENHANCED_TRACING}" == "1" ]]; then
    echo "Activating Enhanced Calculator Flow Tracer..."
    python -c "
from src.calculations.enable_enhanced_tracing import enable_enhanced_calculator_tracing
enable_enhanced_calculator_tracing()
print('✓ Enhanced Calculator Flow Tracer activated')
" || {
        echo "Failed to activate enhanced tracing - falling back to standard mode" >&2
        export HVAC_ENHANCED_TRACING=0
    }
fi
```

## Complete Enhanced init.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# Determine project root as the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for setup mode
if [[ "${1:-}" == "setup" ]]; then
    echo "Running Enhanced Calculator Flow Tracer setup..."

    # Create tracer components if they don't exist
    python "${SCRIPT_DIR}/scripts/setup_enhanced_tracer.py" || {
        echo "Failed to setup enhanced tracer components" >&2
        exit 1
    }

    echo "✓ Enhanced Calculator Flow Tracer setup complete"
    echo "Run './init.sh' to start with enhanced tracing enabled"
    exit 0
fi

# Default environment variables for existing functionality
export HVAC_DEBUG_EXPORT="${HVAC_DEBUG_EXPORT:-1}"
export HVAC_USE_PATH_DATA_BUILDER="${HVAC_USE_PATH_DATA_BUILDER:-1}"

# Enhanced Calculator Flow Tracer Configuration
export HVAC_ENHANCED_TRACING="${HVAC_ENHANCED_TRACING:-1}"
export HVAC_CALCULATOR_VALIDATION="${HVAC_CALCULATOR_VALIDATION:-1}"
export HVAC_TRACE_LEVEL="${HVAC_TRACE_LEVEL:-INFO}"
export HVAC_TRACE_OUTPUT="${HVAC_TRACE_OUTPUT:-console}"
export HVAC_TRACE_FILE="${HVAC_TRACE_FILE:-debug_trace.log}"

# Activate virtual environment if present
VENV_ACTIVATE="${SCRIPT_DIR}/.venv/bin/activate"
if [[ -f "${VENV_ACTIVATE}" ]]; then
    # shellcheck disable=SC1090
    source "${VENV_ACTIVATE}"
else
    echo "Warning: virtual environment not found at ${VENV_ACTIVATE}" >&2
fi

echo "Environment Configuration:"
echo "  HVAC_DEBUG_EXPORT=${HVAC_DEBUG_EXPORT}"
echo "  HVAC_USE_PATH_DATA_BUILDER=${HVAC_USE_PATH_DATA_BUILDER}"

# Enhanced Calculator Flow Tracer Setup
if [[ "${HVAC_ENHANCED_TRACING}" == "1" ]]; then
    echo "  HVAC_ENHANCED_TRACING=${HVAC_ENHANCED_TRACING}"
    echo "Enabling Enhanced Calculator Flow Tracer..."
    export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

    # Pre-validate tracer components exist
    TRACER_FILES=(
        "${SCRIPT_DIR}/src/calculations/calculator_flow_tracer.py"
        "${SCRIPT_DIR}/src/calculations/calculator_tracer_integration.py"
        "${SCRIPT_DIR}/src/calculations/enable_enhanced_tracing.py"
    )

    MISSING_FILES=()
    for file in "${TRACER_FILES[@]}"; do
        if [[ ! -f "${file}" ]]; then
            MISSING_FILES+=("$(basename "${file}")")
        fi
    done

    if [[ ${#MISSING_FILES[@]} -gt 0 ]]; then
        echo "Warning: Enhanced tracer files not found: ${MISSING_FILES[*]}" >&2
        echo "Run './init.sh setup' to install enhanced tracer components" >&2
        echo "Falling back to standard debugging mode..." >&2
        export HVAC_ENHANCED_TRACING=0
    else
        echo "✓ Enhanced Calculator Flow Tracer components verified"
        echo "  Tracing Level: ${HVAC_TRACE_LEVEL}"
        echo "  Output Mode: ${HVAC_TRACE_OUTPUT}"
        if [[ "${HVAC_TRACE_OUTPUT}" != "console" ]]; then
            echo "  Log File: ${HVAC_TRACE_FILE}"
        fi

        # Pre-flight tracer activation
        echo "Activating Enhanced Calculator Flow Tracer..."
        python -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}/src')
from calculations.enable_enhanced_tracing import enable_enhanced_calculator_tracing
enable_enhanced_calculator_tracing()
print('✓ Enhanced Calculator Flow Tracer activated')
" || {
            echo "Failed to activate enhanced tracing - falling back to standard mode" >&2
            export HVAC_ENHANCED_TRACING=0
        }
    fi
fi

echo "Using python: $(command -v python)"
echo "Starting Acoustic Analysis Tool..."

# Run the application
exec python "${SCRIPT_DIR}/src/main.py"
```

## New Setup Script Required

Create `scripts/setup_enhanced_tracer.py`:

```python
#!/usr/bin/env python3
"""
Setup script for Enhanced Calculator Flow Tracer components.
Creates the necessary tracer files if they don't exist.
"""

import os
import sys
from pathlib import Path

def create_tracer_components():
    """Create enhanced tracer components from templates or defaults."""
    script_dir = Path(__file__).parent.parent
    calc_dir = script_dir / "src" / "calculations"

    # Ensure calculations directory exists
    calc_dir.mkdir(parents=True, exist_ok=True)

    components = [
        "calculator_flow_tracer.py",
        "calculator_tracer_integration.py",
        "enable_enhanced_tracing.py"
    ]

    missing_components = []
    for component in components:
        if not (calc_dir / component).exists():
            missing_components.append(component)

    if missing_components:
        print(f"Missing enhanced tracer components: {missing_components}")
        print("Please ensure the Enhanced Calculator Flow Tracer files are installed.")
        return False

    print("✓ All enhanced tracer components are present")
    return True

if __name__ == "__main__":
    success = create_tracer_components()
    sys.exit(0 if success else 1)
```

## Usage Examples

### Standard Usage (Enhanced Tracing Enabled)
```bash
./init.sh
```

### First-Time Setup
```bash
./init.sh setup
```

### Custom Trace Configuration
```bash
HVAC_TRACE_LEVEL=DEBUG HVAC_TRACE_OUTPUT=file ./init.sh
```

### Disable Enhanced Tracing
```bash
HVAC_ENHANCED_TRACING=0 ./init.sh
```

## Benefits

1. **Automatic Setup**: One-command initialization of enhanced tracing
2. **Fallback Safety**: Graceful degradation if tracer components missing
3. **Flexible Configuration**: Environment variables for customization
4. **Zero Manual Steps**: No manual import or setup required in application code
5. **Development Ready**: Immediate access to enhanced debugging capabilities

## Implementation Steps

1. **Update init.sh** with enhanced tracer configuration
2. **Create setup script** for tracer component installation
3. **Add environment variable documentation** to project README
4. **Test fallback behavior** when tracer components are missing
5. **Verify integration** with existing debugging infrastructure