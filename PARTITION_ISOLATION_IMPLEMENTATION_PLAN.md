# Partition Isolation Feature Implementation Plan

## Overview

This feature adds the ability to assign partition assemblies with STC ratings to each space for LEED Sound Transmission compliance documentation.

## Key Requirements

### 1. Project-Level Partition Types Library
- Store partition assembly types (e.g., K11 = STC 50)
- Independent of drawing sets - saved to project
- Can import a reference PDF showing partition details
- PDF displayed when assigning partitions for engineer reference

### 2. Enhanced Space Properties
New space fields:
- **Room ID**: Alphanumeric identifier (e.g., "105")
- **Location**: Building level/zone (e.g., "Level 1")
- **Space Type**: Classification (e.g., "Classroom")

### 3. Partition Isolation Interface (per Space)
Table with columns:
- Assembly ID (dropdown from partition types library)
- Assembly Description (auto-populated from library)
- Assembly Location (Wall, Floor, Ceiling)
- Adjacent Space Type (dropdown/text)
- Minimum Required STC Rating
- Partition STC Rating (from library)
- Compliance Status (Yes/No - auto-calculated)

### 4. LEED Export Format
Output columns:
- Room ID
- Assembly ID
- Assembly Description
- Assembly Location
- Space Type
- Adjacent Space Type
- Minimum Required STC Rating
- STC Rating
- Sound Transmission Compliance (Yes/No)

---

## Database Schema Changes

### New Model: `PartitionType` (Project-level partition library)

```python
# src/models/partition.py

class PartitionType(Base):
    """Partition type/assembly definition stored at project level"""
    __tablename__ = 'partition_types'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    # Assembly identification
    assembly_id = Column(String(50), nullable=False)  # e.g., "K11", "P3"
    description = Column(Text)  # e.g., "5/8" GWB both sides, 3-5/8" metal studs"
    
    # STC rating
    stc_rating = Column(Integer)  # e.g., 50
    
    # Data source reference
    source_document = Column(String(255))  # e.g., "A6.1", "Partition Schedule"
    notes = Column(Text)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="partition_types")
    space_partitions = relationship("SpacePartition", back_populates="partition_type")
```

### New Model: `PartitionScheduleDocument` (Reference PDF)

```python
class PartitionScheduleDocument(Base):
    """Reference PDF document for partition schedule (project-level)"""
    __tablename__ = 'partition_schedule_documents'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # File paths
    file_path = Column(String(1000))  # External PDF path
    managed_file_path = Column(String(1000))  # Project-managed copy
    
    # Optional: specific page bookmark
    page_number = Column(Integer, default=1)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="partition_schedule_documents")
```

### New Model: `SpacePartition` (Individual partition per space)

```python
class SpacePartition(Base):
    """Individual partition assignment for a space"""
    __tablename__ = 'space_partitions'
    
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), nullable=False)
    partition_type_id = Column(Integer, ForeignKey('partition_types.id'), nullable=True)
    
    # Assembly location in space
    assembly_location = Column(String(50))  # 'Wall', 'Floor', 'Ceiling'
    
    # Adjacent space information
    adjacent_space_type = Column(String(100))  # e.g., "Corridor", "Classroom"
    adjacent_space_id = Column(Integer, ForeignKey('spaces.id'), nullable=True)  # Optional link
    
    # STC requirements
    minimum_stc_required = Column(Integer)  # Minimum required STC
    
    # Override for actual STC (if different from partition_type)
    stc_rating_override = Column(Integer, nullable=True)
    
    # Compliance notes
    notes = Column(Text)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    space = relationship("Space", back_populates="partitions", foreign_keys=[space_id])
    partition_type = relationship("PartitionType", back_populates="space_partitions")
    adjacent_space = relationship("Space", foreign_keys=[adjacent_space_id])
    
    @property
    def effective_stc_rating(self):
        """Get actual STC rating (override or from partition type)"""
        if self.stc_rating_override:
            return self.stc_rating_override
        if self.partition_type:
            return self.partition_type.stc_rating
        return None
    
    @property
    def is_compliant(self):
        """Check if partition meets minimum STC requirement"""
        stc = self.effective_stc_rating
        if stc is None or self.minimum_stc_required is None:
            return None
        return stc >= self.minimum_stc_required
```

### Updates to `Space` Model

Add new fields to existing Space model:

```python
# Add to src/models/space.py - Space class

# Space identification for LEED compliance
room_id = Column(String(50))  # e.g., "105", "A-201"
location_in_project = Column(String(100))  # e.g., "Level 1", "Ground Floor"
space_type = Column(String(100))  # e.g., "Classroom", "Office", "Corridor"

# Relationships - add partition relationship
partitions = relationship("SpacePartition", back_populates="space", 
                         foreign_keys="SpacePartition.space_id",
                         cascade="all, delete-orphan")
```

### Updates to `Project` Model

Add relationships:

```python
# Add to src/models/project.py - Project class

# Partition types library and reference documents
partition_types = relationship("PartitionType", back_populates="project", 
                              cascade="all, delete-orphan")
partition_schedule_documents = relationship("PartitionScheduleDocument", 
                                           back_populates="project",
                                           cascade="all, delete-orphan")
```

---

## UI Components

### 1. Partition Types Library Dialog

**Location**: `src/ui/dialogs/partition_types_dialog.py`

Features:
- Table view of all partition types for project
- Add/Edit/Delete partition types
- Import reference PDF button
- PDF preview pane (shows partition schedule)
- Bulk import from CSV option

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Partition Types Library                                          [x]   │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────┐ ┌───────────────────────────────────┐ │
│ │ Reference PDF                 │ │ Partition Types                   │ │
│ │ ┌─────────────────────────┐   │ │ ┌─────┬──────────────────┬─────┐ │ │
│ │ │                         │   │ │ │ ID  │ Description      │ STC │ │ │
│ │ │    [PDF Preview]        │   │ │ ├─────┼──────────────────┼─────┤ │ │
│ │ │                         │   │ │ │ K11 │ 5/8" GWB both... │ 50  │ │ │
│ │ │                         │   │ │ │ K12 │ Double GWB...    │ 55  │ │ │
│ │ │                         │   │ │ │ P3  │ CMU partition    │ 45  │ │ │
│ │ └─────────────────────────┘   │ │ └─────┴──────────────────┴─────┘ │ │
│ │ [📄 Import PDF] [Page: ▼]     │ │                                   │ │
│ └───────────────────────────────┘ │ [➕ Add] [✏️ Edit] [🗑️ Delete]   │ │
│                                   └───────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                                                    [Save] [Cancel]      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Space Edit Dialog - Enhanced with Partitions Tab

**Modify**: `src/ui/dialogs/space_edit_dialog.py`

Add new tab: "Partition Isolation"

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Edit Space: Conference Room 105                                  [x]   │
├─────────────────────────────────────────────────────────────────────────┤
│ [Basic Properties] [Surface Materials] [Partition Isolation] [Calcs]   │
├─────────────────────────────────────────────────────────────────────────┤
│ Space Identification                                                    │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Room ID: [105        ]  Location: [Level 1    ▼]                   │ │
│ │ Space Type: [Conference Room ▼]                                     │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ Partition Assignments                          [📋 Open Partition Library] │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Location │ Assem. ID │ Description    │ Adjacent  │ Min STC│ STC │✓│ │
│ ├──────────┼───────────┼────────────────┼───────────┼────────┼─────┼─┤ │
│ │ Wall     │ K11   [▼] │ 5/8" GWB both  │ Corridor  │ 45     │ 50  │✓│ │
│ │ Wall     │ K12   [▼] │ Double GWB     │ Classroom │ 50     │ 55  │✓│ │
│ │ Floor    │ P3    [▼] │ 6" concrete    │ Below     │ 50     │ 52  │✓│ │
│ │ Ceiling  │ C2    [▼] │ ACT w/ plenum  │ Above     │ 35     │ 40  │✓│ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ [➕ Add Partition] [🗑️ Remove Selected]                                │
│                                                                         │
│ ┌─ Compliance Summary ─────────────────────────────────────────────────┐│
│ │ ✅ 4/4 partitions meet minimum STC requirements                      ││
│ └─────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────┤
│                         [Save Changes] [Save and Close] [Cancel]        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Add "Partitions" Access to Project Dashboard

Add button/menu to access Partition Types Library from project dashboard:
- Menu: Project → Partition Types Library
- Or button in project settings area

---

## File Structure

### New Files to Create

```
src/models/partition.py                    # New model definitions
src/models/migrate_partition_schema.py     # Database migration
src/ui/dialogs/partition_types_dialog.py   # Partition library management
src/ui/widgets/partition_pdf_viewer.py     # Embedded PDF viewer for reference
src/ui/widgets/partition_table_widget.py   # Partition assignments table
src/data/partition_stc_standards.py        # Standard STC requirements by space type
```

### Files to Modify

```
src/models/__init__.py                     # Add partition imports
src/models/project.py                      # Add relationships
src/models/space.py                        # Add new fields and relationships
src/models/database.py                     # Add migration import
src/ui/dialogs/space_edit_dialog.py        # Add Partition Isolation tab
src/data/excel_exporter.py                 # Update LEED Sound Transmission
src/ui/project_dashboard.py                # Add access to partition library
```

---

## Standard STC Requirements Reference

Default minimum STC requirements by space type adjacency:

```python
# src/data/partition_stc_standards.py

STC_REQUIREMENTS = {
    # Office spaces
    ('office', 'office'): 45,
    ('office', 'corridor'): 40,
    ('office', 'conference'): 50,
    
    # Educational
    ('classroom', 'classroom'): 50,
    ('classroom', 'corridor'): 45,
    ('classroom', 'mechanical'): 55,
    
    # Healthcare
    ('exam_room', 'exam_room'): 50,
    ('exam_room', 'corridor'): 45,
    ('exam_room', 'waiting'): 50,
    
    # Residential
    ('unit', 'unit'): 50,
    ('unit', 'corridor'): 45,
    ('unit', 'mechanical'): 55,
    
    # Assembly
    ('theater', 'lobby'): 55,
    ('theater', 'mechanical'): 60,
    
    # General defaults
    ('default', 'default'): 45,
    ('default', 'mechanical'): 50,
    ('default', 'corridor'): 40,
}

def get_minimum_stc(space_type: str, adjacent_type: str) -> int:
    """Get recommended minimum STC rating for adjacency"""
    key = (space_type.lower(), adjacent_type.lower())
    if key in STC_REQUIREMENTS:
        return STC_REQUIREMENTS[key]
    
    # Try with defaults
    for default_key in [(space_type.lower(), 'default'), ('default', adjacent_type.lower()), ('default', 'default')]:
        if default_key in STC_REQUIREMENTS:
            return STC_REQUIREMENTS[default_key]
    
    return 45  # Fallback
```

---

## Implementation Order

### Phase 1: Database Models (Priority: High)
1. ✅ Create `src/models/partition.py` with all models
2. ✅ Update `src/models/space.py` with new fields
3. ✅ Update `src/models/project.py` with relationships
4. ✅ Create migration script `src/models/migrate_partition_schema.py`
5. ✅ Update `src/models/__init__.py` and `src/models/database.py`

### Phase 2: STC Standards Library (Priority: Medium)
1. ✅ Create `src/data/partition_stc_standards.py`

### Phase 3: Partition Types Library UI (Priority: High)
1. ✅ Create `src/ui/dialogs/partition_types_dialog.py`
2. ✅ Create PDF viewer widget for reference documents
3. ✅ Add access from project dashboard

### Phase 4: Space Edit Dialog Enhancement (Priority: High)
1. ✅ Create partition table widget
2. ✅ Add "Partition Isolation" tab to space_edit_dialog.py
3. ✅ Add space identification fields (Room ID, Location, Space Type)
4. ✅ Implement partition assignment with dropdown from library

### Phase 5: Excel Export (Priority: Medium)
1. ✅ Update `src/data/excel_exporter.py` LEED Sound Transmission sheet
2. ✅ Populate actual partition data from SpacePartition model

### Phase 6: Testing & Refinement
1. Create test cases
2. Test end-to-end workflow
3. Refine UI based on usage

---

## LEED Export Output Format

The enhanced LEED Sound Transmission sheet will output:

| Room ID | Assem. ID | Assem Description | Assembly Location | Space Type | Adjacent Space Type | Min Required STC | STC Rating | Compliance |
|---------|-----------|-------------------|-------------------|------------|---------------------|------------------|------------|------------|
| 105 | K11 | 5/8" GWB both sides... | Wall | Conference Room | Corridor | 45 | 50 | Yes |
| 105 | K12 | Double GWB... | Wall | Conference Room | Classroom | 50 | 55 | Yes |
| 105 | P3 | 6" concrete slab | Floor | Conference Room | Below | 50 | 52 | Yes |
| 201 | K11 | 5/8" GWB both sides... | Wall | Office | Corridor | 40 | 50 | Yes |

---

## Notes

### Design Decisions
1. **Project-level partition library**: Partition types are stored at project level, not drawing set level, because partition assemblies typically apply across all phases of a project.

2. **Reference PDF**: The partition schedule PDF is for engineer reference when assigning partitions - it displays alongside the partition assignment interface.

3. **Compliance auto-calculation**: The compliance column auto-calculates Yes/No based on comparing STC rating to minimum required.

4. **Adjacent space linking**: Option to link to actual adjacent space in database OR just enter type as text - supports both workflows.

### Future Enhancements
- OCR of partition schedule PDFs to auto-populate partition types
- Visual partition assignment on floor plan drawings
- IIC (Impact Insulation Class) ratings for floor assemblies
- Multiple acoustic ratings (STC, OITC, NIC, etc.)

