# Partition Isolation Feature - Quick Start Guide

## Overview

The Partition Isolation feature allows you to assign partition assemblies with STC (Sound Transmission Class) ratings to each space for LEED Sound Transmission compliance documentation.

## Key Features

### 1. Project-Level Partition Types Library
- Store and manage partition assembly types (e.g., K11 = STC 50)
- Import a reference PDF showing the project's partition details
- View the PDF while assigning partitions

### 2. Enhanced Space Properties
Each space now includes:
- **Room ID**: Alphanumeric identifier (e.g., "105")
- **Location**: Building level/zone (e.g., "Level 1")  
- **Space Type**: Classification (e.g., "Classroom")

### 3. Partition Isolation Interface
For each space, you can assign multiple partitions with:
- Assembly ID (from library)
- Assembly Location (Wall, Floor, Ceiling)
- Adjacent Space Type
- Minimum Required STC Rating
- Partition STC Rating
- Automatic Compliance Calculation

### 4. LEED Export
The Excel export now includes actual partition data:
- Room ID
- Assembly ID & Description
- Assembly Location
- Space Type & Adjacent Space Type
- Min Required STC vs. Actual STC
- Compliance Status (Yes/No)

---

## How to Use

### Step 1: Set Up Partition Types Library

1. Open a project
2. Edit any space to access the **Partition Isolation** tab
3. Click **📋 Open Partition Types Library**
4. (Optional) Click **📄 Import PDF** to add your partition schedule drawing
5. Add partition types:
   - Click **➕ Add**
   - Enter Assembly ID (e.g., "K11")
   - Enter Description (e.g., "5/8" GWB both sides, 3-5/8" metal studs")
   - Enter STC Rating (e.g., 50)
   - Click **Save**

### Step 2: Configure Space Identification

In the **Basic Properties** tab of the Space Edit dialog:
1. Set **Room ID** (e.g., "105")
2. Set **Location** (e.g., "Level 1")
3. Set **Space Type** (e.g., "Classroom")

### Step 3: Assign Partitions to Space

1. Go to the **Partition Isolation** tab
2. Click **➕ Add Partition**
3. Select:
   - **Assembly Type** from the library dropdown
   - **Assembly Location** (Wall, Floor, Ceiling)
   - **Adjacent Space Type** (e.g., "Corridor")
4. Set **Minimum Required STC** (or use **Auto** to calculate based on space types)
5. Click **Save**

### Step 4: Review Compliance

- The partition table shows compliance status for each partition
- ✅ Green = Meets or exceeds minimum STC
- ❌ Red = Below minimum STC
- The **Compliance Summary** shows overall status

### Step 5: Export LEED Report

1. Go to **Results Analysis** tab
2. Click **📊 Export to Excel**
3. The **LEED - Sound Transmission** sheet will contain your partition data

---

## STC Auto-Suggest

The system includes standard STC requirements based on space type adjacencies:

| Space Type | Adjacent Type | Min STC |
|------------|---------------|---------|
| Classroom | Corridor | 45 |
| Classroom | Classroom | 50 |
| Classroom | Mechanical Room | 55 |
| Office | Corridor | 40 |
| Office | Conference Room | 50 |
| Conference Room | Corridor | 45 |
| Patient Room | Patient Room | 50 |
| Hotel Room | Hotel Room | 50 |

Click the **✨ Auto-Suggest Min STC** button to automatically fill minimum STC values.

---

## Database Fields

### Space Table (new columns)
- `room_id`: Space identifier for LEED
- `location_in_project`: Building level/zone
- `space_type`: Space classification

### PartitionType Table (new)
- `assembly_id`: Partition type ID (e.g., "K11")
- `description`: Full description
- `stc_rating`: STC rating
- `source_document`: Reference document

### SpacePartition Table (new)
- `space_id`: Associated space
- `partition_type_id`: Selected partition type
- `assembly_location`: Wall/Floor/Ceiling
- `adjacent_space_type`: Adjacent space classification
- `minimum_stc_required`: Required minimum STC
- `stc_rating_override`: Optional override value

---

## File Locations

```
src/models/partition.py                    # Database models
src/models/migrate_partition_schema.py     # Database migration
src/data/partition_stc_standards.py        # STC standards library
src/ui/dialogs/partition_types_dialog.py   # Partition library dialog
src/ui/dialogs/partition_edit_dialog.py    # Partition assignment dialog
src/ui/dialogs/space_edit_dialog.py        # Updated with partition tab
src/data/excel_exporter.py                 # Updated LEED export
```

