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


