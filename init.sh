#!/usr/bin/env bash
set -euo pipefail

# Determine project root as the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default to enabling HVAC debug export unless already set by caller
export HVAC_DEBUG_EXPORT="${HVAC_DEBUG_EXPORT:-1}"
export HVAC_USE_PATH_DATA_BUILDER="${HVAC_USE_PATH_DATA_BUILDER:-1}"
# Activate virtual environment if present
VENV_ACTIVATE="${SCRIPT_DIR}/.venv/bin/activate"
if [[ -f "${VENV_ACTIVATE}" ]]; then
    # shellcheck disable=SC1090
    source "${VENV_ACTIVATE}"
else
    echo "Warning: virtual environment not found at ${VENV_ACTIVATE}" >&2
fi

echo "HVAC_DEBUG_EXPORT=${HVAC_DEBUG_EXPORT}"
echo "Using python: $(command -v python)"

# Run the application
exec python "${SCRIPT_DIR}/src/main.py"


