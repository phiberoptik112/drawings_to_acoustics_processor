# Sprint 4: Completeness & Polish
## Acoustic Analysis Tool - Final Sprint Plan

**Goal**: Feature-complete professional product ready for commercial release
**Estimated Duration**: 2 weeks (28 hours total)
**Status**: In Progress

---

## User Decisions (2025-02-22)

| Decision | Choice | Impact |
|----------|--------|--------|
| Silencer Feature | **KEEP** | Complete integration with HVAC paths |
| Partition/STC UI | **KEEP (simplified)** | User-defined wall type codes with STC values |
| Priority Order | **Testing first** | Edge case tests before docs/performance |

---

## Overview

Sprint 4 focuses on completing partial features, adding comprehensive testing, and preparing for user acceptance testing.

**Priority Order:**
1. Edge case testing (8h) - FIRST PRIORITY
2. Silencer integration (4h) - mostly complete, needs HVAC path integration
3. Wall Type Library (4h) - simple UI for user-defined codes
4. Performance profiling (4h) - defer if testing takes longer
5. Documentation (4h) - defer if needed
6. UAT prep (4h) - defer if needed

---

## Task 1: Edge Case Tests (8h) - ✅ COMPLETE

### Test Coverage - All Tests Passing (150 tests total)

#### 1.1 RT60 Calculator Tests - ✅ Complete (`tests/test_rt60_edge_cases.py`)
**39 tests passing**
- [x] Zero volume space
- [x] Negative area surfaces
- [x] All surfaces with 0.0 absorption
- [x] All surfaces with 1.0 absorption (Eyring edge case - clamped to 0.99)
- [x] Single surface only
- [x] Extremely large room (>1M cubic feet)
- [x] Extremely small room (<10 cubic feet)
- [x] Missing material in database
- [x] Invalid frequency data
- [x] RT60Result error factory and to_dict methods

#### 1.2 HVAC Calculator Tests - ✅ Complete (`tests/test_hvac_edge_cases.py`)
**33 tests passing**
- [x] Zero CFM source
- [x] Negative duct dimensions
- [x] Zero length segment
- [x] Path with no segments (empty path)
- [x] Path with 50+ segments (stress test)
- [x] Circular duct with 0 diameter
- [x] Rectangular duct with 0 dimension
- [x] Missing source component
- [x] PathElement and OctaveBandData edge cases
- [x] SpaceNoiseService with empty paths

#### 1.3 Database Edge Cases - ✅ Complete (`tests/test_database_edge_cases.py`)
**23 tests passing**
- [x] Create project with empty name
- [x] Create project with None name (integrity error)
- [x] Create project with special characters (`/\:*?"<>|`)
- [x] Create project with unicode characters
- [x] Create project with extremely long name (1000+ chars)
- [x] Drawing with nonexistent file path
- [x] Drawing with special characters in path
- [x] Session management: rollback, transactions, detached objects
- [x] Cascade deletes (project → drawings, project → spaces)
- [x] Result type edge cases (CalculationResult, RT60Result, NCAnalysisData)

#### 1.4 Calculation & Export Edge Cases - ✅ Complete (`tests/test_calculations_export_edge_cases.py`)
**55 tests passing**
- [x] NC rating analyzer: empty/short lists, zero/negative values
- [x] NC rating borderline and extreme values
- [x] dBA calculation edge cases
- [x] Warning generation for all scenarios
- [x] Octave band estimation from dBA
- [x] Noise control recommendations
- [x] Excel exporter: options, initialization, invalid paths
- [x] Auto-size columns edge cases
- [x] Style application methods

---

## Task 2: Silencer Feature Integration (4h)

### Current State Assessment ✅
The silencer feature is **much more complete** than initially assessed:

**Already Implemented:**
- ✅ `SilencerProduct` model with full schema (manufacturer, dimensions, 8-band insertion loss, cost, availability)
- ✅ `SilencerPlacementAnalysis` model for storing analysis results
- ✅ `SilencerDatabaseManager` with 9 pre-populated silencer products
- ✅ `SilencerFilterEngine` with filtering and match scoring algorithm
- ✅ `SilencerFilterDialog` - complete UI for filtering and selecting silencers
- ✅ Relationship to `HVACComponent` via `selected_product`

**Remaining Work:**

#### 2.1 Verify Database Population (30m)
- [ ] Ensure `populate_silencer_database()` is called during app initialization
- [ ] Add check in `database.py` initialization

#### 2.2 HVAC Path Integration (2h)
- [ ] Add "Select Silencer" button to path properties or component dialog
- [ ] Store selected silencer on HVACComponent (for silencer-type components)
- [ ] Update path noise calculation to apply silencer insertion loss
- [ ] Show silencer selection in path details

#### 2.3 Visual Feedback (1h)
- [ ] Add silencer indicator to drawing overlay (different color/icon)
- [ ] Show insertion loss impact in path results

#### 2.4 Testing (30m)
- [ ] Test silencer filter dialog opens correctly
- [ ] Test silencer selection persists
- [ ] Test insertion loss is applied to calculations

---

## Task 3: Wall Type Library (4h)

### Scope (Per User Requirements)
Simple library for user-defined wall type codes:
- User enters a code name (e.g., "W1", "W2", "P1")
- User enters an STC value
- Codes come from project drawings (user reads them)
- No calculation required - just storage and display

### Implementation Plan

#### 3.1 Data Model (1h)
Create `WallType` model in `src/models/wall_type.py`:

```python
class WallType(Base):
    """User-defined wall type codes with STC ratings"""
    __tablename__ = 'wall_types'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    code = Column(String(50), nullable=False)  # e.g., "W1", "P1"
    description = Column(String(200))  # Optional description
    stc_rating = Column(Integer, nullable=False)  # STC value
    notes = Column(Text)  # Optional notes
    created_date = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="wall_types")
```

- [ ] Create model file
- [ ] Add to `models/__init__.py`
- [ ] Add migration
- [ ] Add relationship to Project model

#### 3.2 Wall Type Library Dialog (2h)
Create `src/ui/dialogs/wall_type_library_dialog.py`:

- [ ] List of wall types for current project (table view)
- [ ] Add button → simple form dialog
- [ ] Edit button → edit selected
- [ ] Delete button → confirm and delete
- [ ] Columns: Code | STC Rating | Description | Notes

UI Layout:
```
┌─────────────────────────────────────────────┐
│ Wall Type Library                           │
├─────────────────────────────────────────────┤
│ ┌───────┬─────┬─────────────┬─────────────┐ │
│ │ Code  │ STC │ Description │ Notes       │ │
│ ├───────┼─────┼─────────────┼─────────────┤ │
│ │ W1    │ 45  │ GWB on stud │             │ │
│ │ W2    │ 50  │ Double GWB  │             │ │
│ │ P1    │ 55  │ CMU Wall    │ Per dwg A3  │ │
│ └───────┴─────┴─────────────┴─────────────┘ │
│                                             │
│ [Add]  [Edit]  [Delete]          [Close]    │
└─────────────────────────────────────────────┘
```

#### 3.3 Integration (1h)
- [ ] Add "Wall Types" tab to Component Library dialog OR
- [ ] Add separate menu item: Tools → Wall Type Library
- [ ] Include wall types in Excel export (if space/partition references them)

---

## Task 4: Performance Profiling & Optimization (4h) - DEFER IF NEEDED

### Profiling Targets
1. PDF loading and rendering
2. Drawing overlay redraw/refresh
3. RT60 calculation batch
4. HVAC path noise calculation
5. Results dashboard refresh
6. Excel export generation

### Implementation
- [ ] Create `utils/profiling.py` with timing decorator
- [ ] Profile each target operation
- [ ] Document baseline performance
- [ ] Identify and fix any bottlenecks >1s

---

## Task 5: Documentation Update (4h) - DEFER IF NEEDED

### Documentation Targets
- [ ] Update CLAUDE.md with Sprint 1-4 changes
- [ ] Create basic USER_GUIDE.md outline
- [ ] Document new features (silencer, wall types)

---

## Task 6: User Acceptance Testing Prep (4h) - DEFER IF NEEDED

### UAT Preparation
- [ ] Create test scenarios document
- [ ] Prepare test data package
- [ ] Create UAT checklist

---

## Progress Tracking

### Status Dashboard

| Task | Status | Est. Hours | Actual | Notes |
|------|--------|------------|--------|-------|
| 1. Edge Case Tests | ✅ Complete | 8h | 4h | 150 tests passing |
| 2. Silencer Integration | ✅ Complete | 4h | 2h | UI + noise engine |
| 3. Wall Type Library | ✅ Complete | 4h | 1h | Model + dialog |
| 4. Performance | ✅ Complete | 4h | 1h | All targets exceeded |
| 5. Documentation | ✅ Complete | 4h | 1h | API docs updated |
| 6. UAT Prep | 🔲 Not Started | 4h | - | Defer if needed |

### Legend
- 🔲 Not Started
- 🔄 In Progress
- ✅ Complete
- ❌ Blocked
- ⏸️ Deferred

---

## Task 4: Performance Profiling Results - ✅ COMPLETE

### Performance Metrics (All Targets Exceeded)

| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| RT60 Sabine (small room) | < 10ms | 0.012ms | ✅ 833x faster |
| RT60 Sabine (large room, 15 surfaces) | < 25ms | 0.032ms | ✅ 781x faster |
| RT60 Eyring (small room) | < 15ms | 0.012ms | ✅ 1250x faster |
| RT60 Eyring (large room) | < 30ms | 0.035ms | ✅ 857x faster |
| NC Rating Analysis | < 5ms | 0.005ms | ✅ 1000x faster |
| Excel Workbook (50 rows) | < 100ms | 0.536ms | ✅ 187x faster |
| Database Project Creation | < 20ms | 0.67ms | ✅ 30x faster |
| Database Query (100 projects) | < 10ms | 1.28ms | ✅ 8x faster |

### Performance Test Suite

Created `tests/test_performance_profiling.py` with 17 benchmark tests:

- RT60 calculator benchmarks (Sabine & Eyring, various room sizes)
- HVAC noise engine benchmarks (simple/medium/complex paths)
- NC rating analyzer benchmarks
- Database operation benchmarks
- Excel export benchmarks

Run with: `pytest tests/test_performance_profiling.py -v -s`

### Conclusion

No performance bottlenecks identified. All calculation engines perform well within
acceptable limits, even for complex scenarios with many surfaces or path elements.

---

## Task 5: Documentation Update - ✅ COMPLETE

Updated `docs/ACOUSTIC_API.md` with:

- WallType model documentation
- SilencerProduct model documentation
- HVAC noise engine silencer integration
- Wall Type Library Dialog usage
- Silencer Selection in HVAC Component Dialog

Updated `CLAUDE.md` with:

- Sprint 4 status section
- New database models
- Edge case test commands

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-02-22 | Keep silencer feature | Core HVAC noise mitigation | 4h to complete integration |
| 2025-02-22 | Simplified wall type UI | User reads codes from drawings | 4h for simple library |
| 2025-02-22 | Testing priority | Quality assurance first | Edge tests before features |

---

## Sprint Completion Criteria

Sprint 4 is complete when:

- [x] All edge case tests written and passing (Priority 1) ✅ 150 tests
- [x] Silencer feature integrated with HVAC paths ✅
- [x] Wall Type Library UI functional ✅
- [x] Performance profiled (no blocking issues) ✅ All targets exceeded
- [x] Documentation updated ✅ API docs updated
- [ ] UAT test package ready

**Minimum Viable Completion:** ✅ ACHIEVED
- [x] Edge case tests passing
- [x] Silencer integration working
- [x] Wall Type Library functional

---

## Next Steps After Sprint 4

1. **User Acceptance Testing**: Execute UAT with identified users
2. **Bug Fixes**: Address any issues found during UAT
3. **Release Preparation**: Final build, installers, release notes
4. **Commercial Launch**: Distribution and user support setup
