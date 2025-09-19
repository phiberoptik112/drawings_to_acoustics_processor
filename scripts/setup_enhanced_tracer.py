#!/usr/bin/env python3
"""
Setup script for Enhanced Calculator Flow Tracer components.
Creates the necessary tracer files if they don't exist and validates the setup.
"""

import os
import sys
from pathlib import Path

def check_tracer_components():
    """Check if enhanced tracer components exist."""
    script_dir = Path(__file__).parent.parent
    calc_dir = script_dir / "src" / "calculations"

    components = {
        "calculator_flow_tracer.py": "Main calculator flow tracing system",
        "calculator_tracer_integration.py": "Integration layer for existing calculators",
        "enable_enhanced_tracing.py": "Simple activation interface"
    }

    print("Enhanced Calculator Flow Tracer Setup Check")
    print("=" * 50)
    print(f"Checking directory: {calc_dir}")
    print()

    missing_components = []
    present_components = []

    for component, description in components.items():
        component_path = calc_dir / component
        if component_path.exists():
            present_components.append(f"✓ {component} - {description}")
        else:
            missing_components.append(f"✗ {component} - {description}")

    # Show status
    if present_components:
        print("Present Components:")
        for component in present_components:
            print(f"  {component}")
        print()

    if missing_components:
        print("Missing Components:")
        for component in missing_components:
            print(f"  {component}")
        print()

        print("SETUP REQUIRED:")
        print("The Enhanced Calculator Flow Tracer components need to be installed.")
        print("These components were designed by the code-reviewer agent but need to be implemented.")
        print()
        print("Next Steps:")
        print("1. Implement the calculator_flow_tracer.py module")
        print("2. Implement the calculator_tracer_integration.py module")
        print("3. Implement the enable_enhanced_tracing.py module")
        print("4. Run this setup script again to verify installation")
        print()
        return False
    else:
        print("✓ All Enhanced Calculator Flow Tracer components are present!")
        print()

        # Test basic import (skip database loading)
        try:
            sys.path.insert(0, str(calc_dir.parent))

            # Set flag to skip database loading during setup validation
            os.environ["SKIP_DATABASE_INIT"] = "1"

            from calculations.enable_enhanced_tracing import enable_enhanced_calculator_tracing
            print("✓ Enhanced tracing module imports successfully")

            # Test activation (dry run) - don't actually enable, just verify interface
            print("✓ Enhanced tracing activation interface available")
            print()
            print("SETUP COMPLETE: Enhanced Calculator Flow Tracer is ready to use!")

            # Clean up environment flag
            os.environ.pop("SKIP_DATABASE_INIT", None)
            return True

        except ImportError as e:
            print(f"✗ Import test failed: {e}")
            print("The tracer files exist but may have implementation issues.")
            # Clean up environment flag on error
            os.environ.pop("SKIP_DATABASE_INIT", None)
            return False

def create_minimal_tracer_stubs():
    """Create minimal tracer stubs if components don't exist."""
    script_dir = Path(__file__).parent.parent
    calc_dir = script_dir / "src" / "calculations"

    # Ensure calculations directory exists
    calc_dir.mkdir(parents=True, exist_ok=True)

    # Create enable_enhanced_tracing.py stub
    enable_tracing_stub = calc_dir / "enable_enhanced_tracing.py"
    if not enable_tracing_stub.exists():
        enable_tracing_stub.write_text('''"""
Minimal stub for Enhanced Calculator Flow Tracer activation.
This is a placeholder - implement the full enhanced tracer system.
"""

def enable_enhanced_calculator_tracing():
    """Minimal stub for enhanced calculator tracing activation."""
    import os
    if os.environ.get('HVAC_ENHANCED_TRACING') == '1':
        print("Enhanced Calculator Flow Tracer: Minimal stub mode")
        print("Note: Full enhanced tracing system needs implementation")
    return True
''')
        print(f"Created minimal stub: {enable_tracing_stub}")

def main():
    """Main setup function."""
    print("Enhanced Calculator Flow Tracer Setup")
    print("=" * 40)

    success = check_tracer_components()

    if not success:
        print("Creating minimal stubs for basic functionality...")
        create_minimal_tracer_stubs()
        print()
        print("Minimal stubs created. The application will run but with limited tracing.")
        print("Implement the full Enhanced Calculator Flow Tracer for complete functionality.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)