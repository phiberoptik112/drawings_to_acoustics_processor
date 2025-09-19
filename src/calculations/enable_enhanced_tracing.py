"""
Enable Enhanced Calculator Tracing - Simple integration script
Add this import to enable comprehensive calculator validation and tracing
"""

import os
import sys

def enable_enhanced_calculator_tracing():
    """
    Enable enhanced calculator tracing with one function call
    Call this at the start of your application or debugging session
    """

    print("🔍 Enabling Enhanced Calculator Tracing...")

    try:
        # Set environment variables for tracing
        os.environ["HVAC_CALC_TRACE"] = "1"
        os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"

        # Import and setup the integration
        from .calculator_tracer_integration import tracer_integration
        from .calculator_flow_tracer import flow_tracer

        # Instrument all calculators
        print("📊 Instrumenting calculator modules...")
        results = tracer_integration.instrument_all_calculators()

        # Apply enhanced instrumentation to HVAC noise engine
        print("🔧 Applying enhanced instrumentation to HVACNoiseEngine...")
        tracer_integration.instrument_hvac_noise_engine_specifically()

        # Report results
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        print(f"✅ Enhanced calculator tracing enabled!")
        print(f"📈 Instrumented {success_count}/{total_count} calculator classes")
        print(f"🎯 Trace level: DETAILED")
        print(f"💡 Use HVAC_TRACE_LEVEL=FULL for maximum detail")
        print(f"💡 Use HVAC_TRACE_LEVEL=SUMMARY for minimal output")

        # Show which calculators are instrumented
        instrumented = [name for name, success in results.items() if success]
        if instrumented:
            print(f"🔧 Instrumented calculators:")
            for calc_name in instrumented[:5]:  # Show first 5
                print(f"  • {calc_name}")
            if len(instrumented) > 5:
                print(f"  • ... and {len(instrumented) - 5} more")

        return True

    except ImportError as e:
        print(f"❌ Could not import tracer modules: {e}")
        print("💡 Make sure all tracer files are in the calculations directory")
        return False

    except Exception as e:
        print(f"❌ Failed to enable enhanced tracing: {e}")
        import traceback
        traceback.print_exc()
        return False


def quick_trace_test():
    """
    Run a quick test to verify tracing is working
    """
    print("\n🧪 Running quick trace test...")

    try:
        from .rectangular_duct_calculations import RectangularDuctCalculator

        # This should be traced if tracing is enabled
        calc = RectangularDuctCalculator()
        result = calc.get_2inch_lining_attenuation(width=24, height=12, length=10.5)

        print(f"✅ Test calculation completed: {[f'{x:.1f}' for x in result]}")

        # Check if we got any trace data
        from .calculator_flow_tracer import get_calculator_usage_report
        report = get_calculator_usage_report()

        if report['total_calls'] > 0:
            print(f"✅ Tracing is working! {report['total_calls']} calls traced")
            return True
        else:
            print("⚠️ No trace calls detected - tracing may not be fully active")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def disable_enhanced_calculator_tracing():
    """
    Disable enhanced calculator tracing
    """
    print("🔕 Disabling Enhanced Calculator Tracing...")

    # Remove environment variables
    os.environ.pop("HVAC_CALC_TRACE", None)
    os.environ.pop("HVAC_TRACE_LEVEL", None)

    try:
        from .calculator_flow_tracer import disable_calculator_tracing
        disable_calculator_tracing()
        print("✅ Enhanced calculator tracing disabled")
        return True
    except Exception as e:
        print(f"⚠️ Could not fully disable tracing: {e}")
        return False


# Auto-enable tracing when this module is imported if environment variable is set
if os.environ.get("AUTO_ENABLE_CALC_TRACE", "").lower() in {"1", "true", "yes", "on"}:
    enable_enhanced_calculator_tracing()


# Convenience functions for common debugging scenarios
def debug_calculation_accuracy():
    """Enable tracing optimized for debugging calculation accuracy"""
    os.environ["HVAC_TRACE_LEVEL"] = "FULL"
    return enable_enhanced_calculator_tracing()


def debug_performance():
    """Enable tracing optimized for performance analysis"""
    os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"
    return enable_enhanced_calculator_tracing()


def debug_calculator_selection():
    """Enable tracing optimized for debugging calculator selection logic"""
    os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"
    enable_enhanced_calculator_tracing()

    print("\n💡 Calculator selection debugging enabled!")
    print("🔍 Look for [CALC_DECISION] messages in the output")
    print("🎯 These show which calculator was chosen and why")


if __name__ == "__main__":
    # When run as a script, enable tracing and run test
    success = enable_enhanced_calculator_tracing()
    if success:
        quick_trace_test()

        print("\n📋 USAGE EXAMPLES:")
        print("="*50)
        print("# In your Python code:")
        print("from calculations.enable_enhanced_tracing import enable_enhanced_calculator_tracing")
        print("enable_enhanced_calculator_tracing()")
        print("")
        print("# For specific debugging scenarios:")
        print("from calculations.enable_enhanced_tracing import debug_calculation_accuracy")
        print("debug_calculation_accuracy()  # Full detail tracing")
        print("")
        print("# Environment variable approach:")
        print("export HVAC_CALC_TRACE=1")
        print("export HVAC_TRACE_LEVEL=DETAILED")
        print("python your_script.py")
        print("")
        print("# Auto-enable on import:")
        print("export AUTO_ENABLE_CALC_TRACE=1")
        print("# Then any import will automatically enable tracing")