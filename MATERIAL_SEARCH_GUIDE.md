# Material Search System Guide

## Overview

The new Material Search System provides advanced material selection capabilities with frequency-specific analysis and treatment recommendations. This system helps identify optimal acoustic materials based on treatment deficiencies and frequency response requirements.

## Features

### 🔍 **Advanced Material Search Engine**
- **Text Search**: Find materials by name or description
- **Frequency-Specific Search**: Search by absorption coefficients at specific frequencies (125Hz - 4000Hz)
- **Category Filtering**: Filter by ceiling, wall, or floor materials
- **Treatment-Optimized Ranking**: Rank materials by their effectiveness at solving RT60 problems

### 📊 **Interactive Frequency Analysis**
- **Visual RT60 Curves**: Interactive frequency response graphs showing current vs. target RT60
- **Mouse-Over Selection**: Click on frequency points to search for materials optimized at that frequency
- **Problem Frequency Highlighting**: Automatically highlights frequencies needing treatment
- **Real-Time Material Ranking**: Materials are re-ranked as you select different frequencies

### 🎯 **Treatment Deficiency Analysis**
- **Gap Analysis**: Identifies frequency ranges where RT60 is above or below target
- **Treatment Urgency Classification**: Rates treatment needs as critical, high, medium, or low
- **Optimal Material Recommendations**: Suggests best materials for each surface type
- **Performance Impact Prediction**: Estimates RT60 improvement from material changes

### 🏗️ **Professional Material Database**
- **1,339+ Materials**: Comprehensive database with frequency-dependent absorption coefficients
- **NRC Values**: Noise Reduction Coefficient data for all materials
- **Category Organization**: Materials organized by ceiling (271), wall (952), and floor (116) types
- **Professional Sources**: Data from industry-standard acoustic material manufacturers

## How to Use

### 1. Basic Material Search

#### From Room Properties Dialog:
1. Open the Room Properties dialog when creating a new space
2. Go to the "Surface Materials" tab
3. Click the **"🔍 Advanced Material Search"** button
4. This opens the comprehensive material search interface

#### Search Methods:
- **Text Search**: Type keywords like "acoustic", "carpet", or "tile"
- **Category Filter**: Select "Ceiling", "Wall", or "Floor" to narrow results
- **Treatment Mode**: Check "Treatment Mode" to find materials that solve specific RT60 problems

### 2. Frequency-Based Analysis

#### Interactive Frequency Graph:
1. The graph shows current RT60 vs. target RT60 across frequencies
2. **Problem frequencies** are highlighted in orange
3. **Click on any frequency point** to search for materials optimized at that frequency
4. Materials are automatically ranked by their absorption at the selected frequency

#### Reading the Graph:
- **Red line**: Current RT60 values
- **Green dashed line**: Target RT60
- **Orange circles**: Problem frequencies (>0.2s deviation from target)
- **Blue circles**: Selected frequency for material search

### 3. Treatment Mode

#### Automatic Problem Detection:
1. Enable "Treatment Mode" checkbox
2. The system analyzes your current space configuration
3. Identifies problem frequencies and suggests optimal materials
4. Materials are ranked by their effectiveness at solving RT60 gaps

#### Treatment Analysis Results:
- **Treatment Urgency**: Critical, High, Medium, or Low
- **Problem Frequencies**: Specific frequencies needing attention
- **Surface Recommendations**: Best materials for each surface type
- **Expected Improvements**: Predicted RT60 reduction from material changes

### 4. Material Selection and Application

#### Selecting Materials:
1. Browse the ranked material list on the right side
2. Materials are color-coded by performance:
   - **Green**: Excellent absorption (α ≥ 0.8)
   - **Yellow**: Good absorption (α ≥ 0.5)
   - **Orange**: Fair absorption (α ≥ 0.2)
   - **Red**: Poor absorption (α < 0.2)

#### Applying Materials:
1. Click on a material to select it
2. Choose which surface type (ceiling, wall, floor) to apply it to
3. Click "Apply Material" to add it to your space
4. The material is automatically selected in the room properties dialog

### 5. Advanced Features

#### Material Comparison:
1. Select multiple materials for different surfaces
2. View side-by-side frequency response comparison
3. See combined performance impact
4. Analyze effectiveness across the frequency spectrum

#### Treatment Analysis Tab:
1. **Surface Type Selection**: Choose which surfaces to optimize
2. **Comprehensive Analysis**: Get detailed treatment recommendations
3. **Implementation Priority**: See which changes will have the most impact
4. **Performance Predictions**: Estimate RT60 improvements before making changes

## Understanding the Results

### Material Performance Metrics

#### **NRC (Noise Reduction Coefficient)**
- Single-number rating averaging absorption at 250, 500, 1000, and 2000 Hz
- Scale: 0.0 (reflective) to 1.0 (completely absorptive)
- Used for quick comparison between materials

#### **Frequency-Specific Coefficients**
- Absorption values at 125, 250, 500, 1000, 2000, and 4000 Hz
- More detailed than NRC for specific frequency problems
- Critical for addressing speech clarity or music performance issues

#### **Treatment Score**
- Custom scoring system (0-1) indicating effectiveness at solving RT60 problems
- Considers current RT60 gap, material performance, and available surface area
- Higher scores indicate better treatment solutions

### Treatment Urgency Levels

- **Critical**: Average severity > 60% or max gap > 0.5s
- **High**: Average severity > 40% or max gap > 0.3s  
- **Medium**: Average severity > 20% or max gap > 0.15s
- **Low**: Minor deviations from target RT60

## Integration Points

### Existing Workflows
The material search system integrates seamlessly with existing workflows:

1. **Room Properties Dialog**: Direct access via "Advanced Material Search" button
2. **Space Edit Dialog**: Available when modifying existing spaces
3. **Results Dashboard**: "Optimize Materials" feature for performance improvement
4. **Excel Export**: Material recommendations included in reports

### Database Integration
- Automatically uses the existing `acoustic_materials.db` with 1,339+ materials
- Fallback to standard materials if database unavailable
- Maintains compatibility with existing RT60 calculation engine

## Tips for Best Results

### 1. Problem Identification
- Always run treatment analysis before selecting materials
- Focus on frequencies with the largest RT60 gaps first
- Consider speech intelligibility (500-2000 Hz) vs. music (125-4000 Hz) requirements

### 2. Material Selection
- Use treatment mode for systematic problem-solving
- Consider practical installation constraints (ceiling vs. wall accessibility)
- Balance acoustic performance with aesthetic requirements

### 3. Surface Prioritization
- **Ceiling**: Often most effective for RT60 reduction
- **Walls**: Important for speech clarity and echo control  
- **Floor**: Significant impact but limited material options

### 4. Performance Validation
- Use the comparison tab to verify material choices
- Check frequency response curves for balanced performance
- Consider running simulation before making final decisions

## Technical Details

### Search Engine Capabilities
- SQLite database queries with frequency-specific filtering
- Real-time material ranking algorithms
- Multi-criteria optimization (absorption, cost-effectiveness, availability)
- Background processing for responsive user interface

### Calculation Methods
- Sabine and Eyring RT60 formulas with frequency-dependent coefficients
- Treatment gap analysis using acoustic principles
- Performance prediction based on surface area and material properties
- Statistical analysis of material effectiveness across frequency spectrum

---

This advanced material search system transforms acoustic design from guesswork into data-driven decision making, helping achieve optimal room acoustics with professional-grade material selection.