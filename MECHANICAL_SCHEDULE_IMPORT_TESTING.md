# Mechanical Schedule Import Testing Guide

## Overview

This document outlines test cases for the new Mechanical Schedule Import Wizard. Each test case verifies specific functionality and edge cases.

## Test Setup

### Prerequisites
- Python 3.8+ with virtual environment activated
- All dependencies installed (see `requirements.txt`)
- Sample mechanical schedule files in various formats
- Test database with clean state

### Test Files Required
1. **TC1_bordered_table.png** - Clear bordered table with 8-band frequency data
2. **TC2_borderless_table.pdf** - Table without visible grid lines
3. **TC3_poor_quality.jpg** - Faded/skewed low-resolution scan
4. **TC4_multipage.pdf** - Schedule spanning 2+ pages
5. **TC5_partial_table.png** - Large table for partial region selection
6. **TC6_missing_bands.pdf** - Table with only 4 of 8 frequency bands
7. **TC7_duplicates.png** - Table with duplicate unit names

---

## Test Cases

### TC1: Simple Bordered Table
**Objective**: Verify basic table extraction with clear grid lines

**Test Steps**:
1. Launch application and open Component Library
2. Click "Import Schedule Wizard..."
3. Load `TC1_bordered_table.png`
4. Proceed to "Detect Tables" step
5. Click "Run Detection"
6. Verify table is auto-detected with confidence >= 75%
7. Proceed to "Select Region" step
8. Click detected table region to select it
9. Proceed to "Extract Data" step
10. Wait for OCR extraction to complete
11. Proceed to "Preview & Validate" step
12. Verify:
    - All unit names extracted correctly
    - All 8 frequency bands per row present
    - No validation errors
    - Confidence scores displayed
13. Click "Next" to confirm import
14. Verify units appear in Component Library list

**Expected Results**:
- Auto-detection finds table (87%+ confidence)
- OCR extraction accuracy >= 95%
- No validation errors
- All units imported successfully

**Pass Criteria**: 
- ✓ All units extracted with correct names
- ✓ All frequency values present and numeric
- ✓ No errors or warnings

---

### TC2: Borderless Table
**Objective**: Verify table structure detection without visible borders

**Test Steps**:
1. Open Import Wizard
2. Load `TC2_borderless_table.pdf`
3. Run auto-detection
4. If detection fails (expected), manually draw selection rectangle
5. Extract data
6. Open "Configure Column Mapping..."
7. Verify auto-mapping detects:
    - Unit name column
    - Unit type column
    - 8 frequency bands
8. Adjust mapping manually if needed
9. Complete import

**Expected Results**:
- Table Transformer may not detect borderless tables reliably
- Manual selection works correctly
- Column mapping successfully identifies structure
- Extraction accuracy >= 85% (lower than bordered)

**Pass Criteria**:
- ✓ Manual selection captures table region
- ✓ Column mapping identifies frequency bands
- ✓ Units imported with acceptable accuracy

---

### TC3: Poor Quality Scan
**Objective**: Verify PaddleOCR handles challenging image quality

**Test Steps**:
1. Open Import Wizard
2. Load `TC3_poor_quality.jpg`
3. Run auto-detection
4. Proceed with extraction
5. In Preview & Validate step:
    - Check confidence scores (expect many yellow/red cells)
    - Verify auto-fix suggestions appear
    - Click "Auto-Fix Issues"
    - Manually correct remaining errors
6. Complete import

**Expected Results**:
- PaddleOCR significantly outperforms Tesseract
- Many low-confidence cells flagged
- Auto-fix corrects common OCR errors (O→0, l→1)
- User can manually correct remaining errors before import

**Pass Criteria**:
- ✓ PaddleOCR accuracy >= 70% (vs ~50% for Tesseract)
- ✓ Auto-fix improves accuracy by 10-15%
- ✓ User can edit errors in preview
- ✓ No corrupted data imported

---

### TC4: Multi-Page PDF
**Objective**: Verify page-by-page processing

**Test Steps**:
1. Open Import Wizard
2. Load `TC4_multipage.pdf`
3. In "Load File" step, verify page selector shows "Page 1 of 3"
4. Select page 1, run detection, select region, extract
5. Import page 1 units
6. Repeat wizard for pages 2 and 3
7. Verify all units from all pages imported

**Expected Results**:
- Page selector allows navigation
- Each page processed independently
- No duplicate imports
- Total unit count = sum of all pages

**Pass Criteria**:
- ✓ Page navigation works correctly
- ✓ All pages processed successfully
- ✓ No duplicates or missing units

---

### TC5: Partial Region Selection
**Objective**: Verify selective import from large table

**Test Steps**:
1. Open Import Wizard
2. Load `TC5_partial_table.png` (contains 20 units)
3. Skip auto-detection
4. Manually draw rectangle around rows 5-7 only
5. Extract data
6. Verify only 3 rows extracted
7. Complete import

**Expected Results**:
- Region selector allows precise control
- Only selected region extracted
- No data from outside selection

**Pass Criteria**:
- ✓ Manual selection captures only desired rows
- ✓ Exactly 3 units imported (not 20)
- ✓ Extracted units are rows 5-7

---

### TC6: Missing Frequency Bands
**Objective**: Verify handling of incomplete data

**Test Steps**:
1. Open Import Wizard
2. Load `TC6_missing_bands.pdf` (only has 63, 125, 500, 1000 Hz)
3. Extract data
4. In Preview & Validate:
    - Verify validation warnings for missing bands
    - Check that existing bands are correctly mapped
    - Open "Configure Column Mapping..."
    - Verify only 4 bands mapped
5. Deselect validation checkbox "Highlight missing values"
6. Complete import with partial data

**Expected Results**:
- Validation detects missing frequency data
- User warned but can proceed
- Imported units have NULL for missing bands
- Database accepts partial frequency data

**Pass Criteria**:
- ✓ Validation flags missing data
- ✓ Import succeeds with warnings
- ✓ Existing bands stored correctly
- ✓ Missing bands stored as NULL

---

### TC7: Duplicate Unit Names
**Objective**: Verify duplicate detection and handling

**Test Steps**:
1. Open Import Wizard
2. Pre-create unit "AHU-1" in database
3. Load `TC7_duplicates.png` (contains "AHU-1" twice)
4. Extract data
5. In Preview & Validate:
    - Verify duplicate warnings appear
    - Verify existing unit "AHU-1" flagged
6. Rename one duplicate to "AHU-1A" in table
7. Deselect the other duplicate row (uncheck Include)
8. Complete import with conflict resolution

**Expected Results**:
- Validation detects duplicates within import
- Validation detects conflicts with existing database
- User can rename or exclude duplicates
- Import succeeds without database conflicts

**Pass Criteria**:
- ✓ Duplicate detection works correctly
- ✓ User can resolve duplicates before import
- ✓ No database constraint errors
- ✓ Final database has unique unit names

---

## Performance Tests

### PT1: Large Table Performance
**Test Data**: 100-unit table (100 rows × 26 columns)

**Metrics to Measure**:
- Auto-detection time: Should be < 5 seconds
- OCR extraction time: Should be < 30 seconds
- Preview rendering: Should be instantaneous
- Total import time: Should be < 2 minutes

**Pass Criteria**:
- ✓ Process completes in < 2 minutes total
- ✓ UI remains responsive throughout
- ✓ Progress indicators update correctly

### PT2: OCR Engine Comparison
**Test Data**: TC3_poor_quality.jpg

**Test Each Engine**:
1. Configure Settings: Select Tesseract only
2. Run import, measure accuracy and time
3. Repeat with EasyOCR
4. Repeat with PaddleOCR

**Expected Results**:
| Engine | Accuracy | Speed |
|--------|----------|-------|
| Tesseract | 50-60% | Fastest (5s) |
| EasyOCR | 75-85% | Medium (12s) |
| PaddleOCR | 90-95% | Slower (20s) |

**Pass Criteria**:
- ✓ PaddleOCR achieves highest accuracy
- ✓ All engines complete in < 30s
- ✓ Fallback chain works automatically

---

## Integration Tests

### IT1: End-to-End Workflow
**Objective**: Complete realistic import scenario

**Scenario**:
1. User receives mechanical schedule PDF from vendor
2. Opens Component Library
3. Clicks "Import Schedule Wizard..."
4. Loads PDF
5. Auto-detection finds table
6. Clicks detected region
7. Extraction runs
8. Reviews preview, fixes 3 OCR errors
9. Configures column mapping
10. Validates data (2 warnings: acceptable)
11. Confirms import
12. Verifies units in library list
13. Opens one unit to check frequency preview
14. Frequency data correctly displayed

**Pass Criteria**:
- ✓ Complete workflow intuitive and smooth
- ✓ No crashes or errors
- ✓ Data correctly stored in database
- ✓ Units usable in downstream workflows

### IT2: Settings Persistence
**Objective**: Verify settings are saved and loaded

**Steps**:
1. Open OCR Settings dialog
2. Change preferred engine to PaddleOCR
3. Change confidence threshold to 65%
4. Enable auto-fix
5. Save settings
6. Close application
7. Reopen application
8. Open OCR Settings
9. Verify all settings persisted

**Pass Criteria**:
- ✓ Settings saved to disk
- ✓ Settings loaded on application start
- ✓ Settings apply to wizard behavior

---

## Regression Tests

### RT1: Legacy Import Still Works
**Objective**: Ensure old code paths still function

**Steps**:
1. Call `import_mechanical_schedule_from_image()` directly
2. Call `import_mechanical_schedule_from_pdf()` directly
3. Verify both complete successfully

**Pass Criteria**:
- ✓ Legacy methods still functional
- ✓ Backward compatibility maintained

### RT2: Existing Units Unchanged
**Objective**: Verify import doesn't corrupt existing data

**Steps**:
1. Create 5 test units manually
2. Run import wizard to add 5 more
3. Verify original 5 units unchanged
4. Verify new 5 units added correctly

**Pass Criteria**:
- ✓ Existing units unaffected
- ✓ Database integrity maintained
- ✓ Total unit count = 10

---

## Manual Testing Checklist

### UI/UX Tests
- [ ] All buttons have clear labels
- [ ] Tooltips provide helpful information
- [ ] Progress indicators show during long operations
- [ ] Error messages are user-friendly
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Dialog can be resized
- [ ] Column mapping dialog is intuitive
- [ ] Preview table supports sorting/filtering
- [ ] Confidence colors are distinguishable
- [ ] High DPI displays render correctly

### Edge Cases
- [ ] Empty image file
- [ ] Corrupted PDF
- [ ] PDF with no tables
- [ ] Image with multiple tables
- [ ] Table with merged cells
- [ ] Rotated image (90°, 180°, 270°)
- [ ] Very large image (10MB+)
- [ ] Unicode characters in unit names
- [ ] Negative frequency values
- [ ] Out-of-range values (>150 dB)

---

## Automated Test Scripts

### Example: Test TC1 with pytest

```python
def test_tc1_bordered_table(tmp_path):
    """Test simple bordered table import"""
    # Setup
    wizard = MechanicalScheduleImportWizard(project_id=1)
    test_image = "tests/data/TC1_bordered_table.png"
    
    # Load file
    wizard._load_file(test_image)
    assert wizard.loaded_pixmap is not None
    
    # Run detection
    from calculations.table_detection import detect_tables_in_image
    image = cv2.imread(test_image)
    detections = detect_tables_in_image(image)
    
    assert len(detections) >= 1
    assert detections[0].confidence >= 0.75
    
    # Extract data
    from calculations.enhanced_ocr import extract_table_with_confidence
    result = extract_table_with_confidence(image)
    
    assert len(result.rows) >= 1
    assert result.average_confidence >= 0.9
    
    # Validate
    from calculations.schedule_validator import ScheduleValidator
    validator = ScheduleValidator()
    
    for i, row in enumerate(result.rows):
        issues = validator.validate_mechanical_unit_row(
            row, i, wizard.column_mapping
        )
        assert len([iss for iss in issues if iss.severity == ValidationSeverity.ERROR]) == 0
```

---

## Success Metrics

### Quantitative Metrics
- **OCR Accuracy**: >= 90% for bordered tables, >= 75% for borderless
- **Import Speed**: < 2 minutes for 100 units
- **User Actions**: < 10 clicks from start to completion
- **Error Rate**: < 5% validation errors on typical schedules
- **Crash Rate**: 0 crashes during testing

### Qualitative Metrics
- **Ease of Use**: Users can complete import without documentation
- **Error Recovery**: Users can fix OCR errors without re-importing
- **Confidence**: Users trust the validation system
- **Flexibility**: Supports variety of table formats and layouts

---

## Bug Tracking

### Known Issues
1. **Issue**: Table Transformer requires ~100MB model download on first use
   - **Workaround**: Show progress dialog during download
   - **Status**: Documented

2. **Issue**: PaddleOCR may be slow on CPU-only systems
   - **Workaround**: Use EasyOCR or Tesseract fallback
   - **Status**: Working as designed

3. **Issue**: Column mapping auto-detection may fail on unusual layouts
   - **Workaround**: Manual mapping always available
   - **Status**: Acceptable limitation

---

## Conclusion

Complete all test cases above to verify the Mechanical Schedule Import Wizard is production-ready. Document any failures and create bug reports for issues requiring fixes before release.
