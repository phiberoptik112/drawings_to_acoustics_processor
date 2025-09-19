# Enhanced Calculator Flow Tracer - Implementation Guide

## Overview

The Enhanced Calculator Flow Tracer provides comprehensive validation and tracing for ALL calculation modules in the HVAC acoustics system. It validates data in/out of every calculator and ensures correct calculator selection throughout the program flow.

## Key Features

### 🔍 **Comprehensive Calculator Coverage**
- Traces all 16+ calculator modules in the system
- Validates input parameters and output results for each calculator
- Monitors calculator selection decisions and reasoning

### 📊 **Multi-Level Tracing**
- **SUMMARY**: Basic flow completion and error summary
- **DETAILED**: Method calls, validation results, decision points
- **FULL**: Complete parameter traces, data transformations, call stacks

### ✅ **Input/Output Validation**
- Parameter range checking for all calculator methods
- Detection of NaN, infinite, and out-of-range values
- Validation of octave band spectra and NC ratings
- Calculator-specific validation rules

### 🎯 **Calculator Selection Tracing**
- Logs decision logic for which calculator to use
- Tracks branching paths (e.g., "circular vs rectangular duct calculator")
- Identifies fallback calculator usage and mismatches

### ⚡ **Performance Monitoring**
- Execution time tracking for all calculator calls
- Identification of slow calculations (>100ms)
- Calculator usage statistics and patterns

## Quick Setup

### 1. Enable Enhanced Tracing
```python
from calculations.calculator_tracer_integration import quick_setup_calculator_tracing

# This automatically:
# - Enables tracing on all calculators
# - Applies validation decorators
# - Sets up enhanced logging
quick_setup_calculator_tracing()
```

### 2. Environment Variables
```bash
# Enable tracing
export HVAC_CALC_TRACE=1

# Set trace detail level
export HVAC_TRACE_LEVEL=DETAILED  # OPTIONS: SUMMARY, DETAILED, FULL

# Enable existing debug output (works alongside enhanced tracing)
export HVAC_DEBUG_EXPORT=1
```

### 3. Run Your Calculations
```python
# Your existing code will now be automatically traced
from calculations.hvac_noise_engine import HVACNoiseEngine

engine = HVACNoiseEngine()
result = engine.calculate_path_noise(path_elements)

# All calculator calls within this flow are now traced and validated
```

## Enhanced Output Examples

### Calculator Method Tracing
```
[CALC_TRACE] rectangular_duct:get_2inch_lining_attenuation → ENTER {"width": 24.0, "height": 12.0, "length": 10.5}
[CALC_VALIDATE] ✓ Input parameters within valid ranges
[CALC_TRACE] rectangular_duct:get_2inch_lining_attenuation → SUCCESS spectrum[avg=4.2dB]
[CALC_VALIDATE] ✓ Output frequency bands complete, values reasonable
```

### Flow-Level Tracing
```
[CALC_FLOW_START] path_noise_12345 at 1625123456.789
[CALC_DECISION] path_noise_12345: calculator_selection -> rectangular_duct (Rectangular geometry detected)
[CALC_TRANSFORM] path_noise_12345: element_processing by duct_processor
[CALC_FLOW_END] path_noise_12345 completed in 45.2ms with 8 calculator calls
```

### Validation Errors
```
[CALC_INPUT_ERROR] rectangular_duct:get_2inch_lining_attenuation → Parameter width value -5.0 outside expected range [6.0, 48.0]
[CALC_OUTPUT_ERROR] junction_elbow:calculate_junction_noise_spectrum → Octave band 2 (250Hz) is NaN
```

## Detailed Implementation

### Calculator Registration

The system automatically registers all calculator types:

```python
class CalculatorType(Enum):
    CIRCULAR_DUCT = "circular_duct"
    RECTANGULAR_DUCT = "rectangular_duct"
    FLEX_DUCT = "flex_duct"
    JUNCTION_ELBOW = "junction_elbow"
    ELBOW_TURNING_VANE = "elbow_turning_vane"
    RECTANGULAR_ELBOW = "rectangular_elbow"
    RECEIVER_ROOM_CORRECTION = "receiver_room_correction"
    END_REFLECTION = "end_reflection"
    RT60 = "rt60"
    ENHANCED_RT60 = "enhanced_rt60"
    NC_RATING = "nc_rating"
    TREATMENT_ANALYZER = "treatment_analyzer"
    SURFACE_AREA = "surface_area"
    HVAC_NOISE_ENGINE = "hvac_noise_engine"
    PATH_DATA_BUILDER = "path_data_builder"
    HVAC_PATH = "hvac_path"
```

### Validation Rules

Each calculator has specific validation rules:

```python
"get_2inch_lining_attenuation": {
    "required_params": ["width", "height", "length"],
    "expected_output": "octave_band_spectrum",
    "param_ranges": {
        "width": (6.0, 48.0),
        "height": (6.0, 144.0),
        "length": (0.1, 1000.0)
    }
}
```

### Flow Tracking

Complete calculation flows are tracked:

```python
# Start a flow
flow_tracer.start_flow("hvac_path_analysis")

# Log decision points
flow_tracer.log_decision_point(
    "hvac_path_analysis",
    "duct_calculator_selection",
    {"geometry_type": "rectangular", "has_lining": True},
    "rectangular_duct_2inch",
    "Selected 2-inch lined rectangular duct calculator"
)

# Log data transformations
flow_tracer.log_data_transformation(
    "hvac_path_analysis",
    "spectrum_processing",
    input_spectrum,
    output_spectrum,
    "duct_attenuation_processor"
)

# End the flow
flow_tracer.end_flow("hvac_path_analysis", final_result)
```

## Integration with Existing Code

### Automatic Integration

The tracer automatically instruments existing calculator classes:

```python
# Your existing calculator code
class RectangularDuctCalculator:
    def get_2inch_lining_attenuation(self, width, height, length):
        # Original implementation
        return result

# After integration setup - this method is automatically traced
calc = RectangularDuctCalculator()
result = calc.get_2inch_lining_attenuation(24, 12, 10.5)
# ↑ This call is now automatically traced and validated
```

### Manual Decorator Application

For new calculator methods:

```python
from calculations.calculator_flow_tracer import calculator_method_tracer, CalculatorType

class MyNewCalculator:
    @calculator_method_tracer(CalculatorType.MY_CALCULATOR)
    def my_calculation_method(self, param1, param2):
        # Your calculation logic
        return result
```

## Enhanced Debugging for Current Issues

### 1. Calculator Selection Problems

```python
# The tracer will show exactly which calculator is selected and why
[CALC_DECISION] path_analysis: calculator_selection -> junction_elbow
    Options: {"available": ["junction_elbow", "rectangular_elbow"]}
    Chosen: junction_elbow
    Reasoning: Junction type BRANCH_TAKEOFF_90 requires specialized calculation
```

### 2. Data Validation Issues

```python
# Invalid input detection
[CALC_INPUT_ERROR] rectangular_duct:get_2inch_lining_attenuation
    → Missing required parameter: length
    → Parameter width value 200.0 outside expected range [6.0, 48.0]

# Output validation
[CALC_OUTPUT_ERROR] junction_elbow:calculate_junction_noise_spectrum
    → Octave band 3 (500Hz) value 150.2 seems unrealistic
    → Dictionary key 'main_duct' band 5 has invalid value: NaN
```

### 3. Performance Issues

```python
[CALC_PERFORMANCE] Slow calculator calls detected:
    → circular_duct:get_unlined_attenuation: 245.3ms (called 15 times)
    → junction_elbow:calculate_junction_noise_spectrum: 156.7ms (called 3 times)
```

## Usage Scenarios

### Scenario 1: Debugging Calculation Accuracy

```python
# Enable detailed tracing
os.environ["HVAC_CALC_TRACE"] = "1"
os.environ["HVAC_TRACE_LEVEL"] = "FULL"

# Run your calculation
result = hvac_engine.calculate_path_noise(elements)

# Review the complete trace to identify issues
report = get_calculator_usage_report()
print(f"Validation errors: {report['validation_summary']['by_severity']}")
```

### Scenario 2: Verifying Calculator Selection

```python
# Enable decision point logging
os.environ["HVAC_TRACE_LEVEL"] = "DETAILED"

# Run calculation and check decision log
flow_tracer.start_flow("verification_test")
result = calculate_something()
flow_tracer.end_flow("verification_test")

# The console output will show all calculator selection decisions
```

### Scenario 3: Performance Optimization

```python
# Run calculations with performance monitoring
quick_setup_calculator_tracing()

# Perform your normal operations
for path in paths:
    result = engine.calculate_path_noise(path.elements)

# Analyze performance
report = get_calculator_usage_report()
performance = report['performance_summary']
print(f"Average execution time: {performance['avg_execution_time_ms']:.2f}ms")
print(f"Slow calls: {performance['slow_calls']}")
```

## Integration Checklist

- [ ] Run `quick_setup_calculator_tracing()` at application startup
- [ ] Set appropriate environment variables for trace level
- [ ] Add flow tracking to key calculation entry points
- [ ] Review validation errors and warnings in debug output
- [ ] Monitor performance metrics for optimization opportunities
- [ ] Use decision point logging to verify calculator selection logic

## Troubleshooting

### Common Issues

1. **No trace output**: Check `HVAC_CALC_TRACE=1` environment variable
2. **Missing validations**: Ensure calculators are properly instrumented with `quick_setup_calculator_tracing()`
3. **Performance impact**: Use `HVAC_TRACE_LEVEL=SUMMARY` for production
4. **Import errors**: Make sure all calculator modules are available in the Python path

### Debug Commands

```python
# Check integration status
from calculations.calculator_tracer_integration import tracer_integration
status = tracer_integration.get_integration_status()
print(f"Instrumented calculators: {status['instrumented_classes']}")

# Get comprehensive usage report
report = get_calculator_usage_report()
print(json.dumps(report, indent=2))

# Run demonstration
from calculations.demo_enhanced_flow_tracer import run_comprehensive_demo
run_comprehensive_demo()
```

## Benefits

### Immediate Problem Resolution
- **Identify wrong calculator usage**: See exactly which calculator is being called for each element
- **Detect parameter issues**: Catch invalid inputs before they cause errors
- **Validate results**: Ensure output data integrity across all calculators

### Long-term Maintenance
- **Performance monitoring**: Track calculation efficiency and identify bottlenecks
- **Code quality**: Ensure all calculators follow validation standards
- **Debugging efficiency**: Quickly isolate calculator-specific issues

### Development Support
- **New calculator integration**: Automatic validation for new calculator modules
- **Regression testing**: Comprehensive validation ensures changes don't break existing calculations
- **Documentation**: Auto-generated usage patterns and performance profiles

This enhanced flow tracer provides the comprehensive validation and debugging capabilities needed to ensure all calculator modules work correctly and efficiently throughout the HVAC acoustics analysis system.