# Proprietary Materials Database Guide

Complete guide for handling proprietary materials databases in development, build, and distribution workflows.

## Table of Contents

- [Overview](#overview)
- [Current Setup](#current-setup)
- [Database Bundling](#database-bundling)
- [Setup Options](#setup-options)
  - [Option 1: Replace Existing Database](#option-1-replace-existing-database-recommended)
  - [Option 2: Use Both Databases](#option-2-use-both-databases)
  - [Option 3: Separate Proprietary Folder](#option-3-separate-proprietary-folder)
  - [Option 4: Build Machine Only](#option-4-build-machine-only-recommended-for-teams)
- [Best Practices](#best-practices)
- [Build Machine Only Workflow](#build-machine-only-workflow)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Acoustic Analysis Tool uses a **SQLite database** (`acoustic_materials.db`) containing proprietary acoustic materials data. This guide explains how to:

- Keep proprietary data **out of version control**
- Bundle the database into **distributed executables**
- Support multiple development workflows
- Protect sensitive material data

### Key Principles

✅ **Proprietary data stays out of git** (excluded via `.gitignore`)  
✅ **Database bundled at build time** (included in executable)  
✅ **Application works without database** (falls back to basic materials)  
✅ **Build process validates database** (warns if missing)  

---

## Current Setup

### Git Exclusion (Already Configured)

Your `.gitignore` file excludes the materials database from version control:

```gitignore
# Database files (lines 42-45)
*.db
*.sqlite
*.sqlite3

# Materials folder (line 72)
materials/
```

**Result:**
- ✅ Proprietary database never committed to git
- ✅ Never pushed to GitHub
- ✅ Stays only on local machines

### Build-Time Bundling (Already Configured)

Both `build_spec.py` (Windows) and `build_spec_macos.py` (macOS) bundle the database:

```python
datas = [
    # Bundle the acoustic materials database
    (str(materials_path / "acoustic_materials.db"), "materials"),
]
```

**Result:**
- ✅ Database included in built executable
- ✅ Users get full proprietary data
- ✅ No external database file required

### Application Fallback (Already Implemented)

The application handles missing databases gracefully:

```python
# In src/data/materials.py
if not os.path.exists(db_path):
    print(f"Warning: Materials database not found at {db_path}, using fallback materials")
    return get_fallback_materials()
```

**Result:**
- ✅ Application works without database (uses fallback)
- ✅ Build can succeed without database (for development)
- ✅ Proper database required for production builds

---

## Database Bundling

### How It Works

```
┌─────────────────────────────────────────┐
│ 1. Development                         │
│    materials/acoustic_materials.db      │
│    (Your proprietary database)          │
│                                         │
│    ❌ NOT in git (excluded)             │
│    ✅ On your machine only               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. Build Process                        │
│    ./build/build.sh                     │
│                                         │
│    PyInstaller:                         │
│    ✅ Checks if database exists         │
│    ✅ Warns if missing (dev builds)     │
│    ✅ Bundles database into executable   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. Distributed Application              │
│    AcousticAnalysisTool.app             │
│      /Contents/Resources/materials/     │
│         acoustic_materials.db           │
│                                         │
│    ✅ Database embedded in app          │
│    ✅ Users get proprietary data        │
│    ❌ Source not exposed                │
└─────────────────────────────────────────┘
```

### Database Details

**File:** `materials/acoustic_materials.db`  
**Type:** SQLite3 database  
**Size:** ~300 KB (typical)  
**Format:** SQLite3 with `acoustic_materials` table

**Table Structure:**
```sql
CREATE TABLE acoustic_materials (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    coeff_125 REAL,
    coeff_250 REAL,
    coeff_500 REAL,
    coeff_1000 REAL,
    coeff_2000 REAL,
    coeff_4000 REAL,
    nrc REAL,
    created_at TIMESTAMP
);
```

---

## Setup Options

### Option 1: Replace Existing Database (Recommended)

**Best for:** Single developer or small team where everyone has access to proprietary data.

**Steps:**

1. **Place your proprietary database:**
   ```bash
   # Place your database file at:
   materials/acoustic_materials.db
   
   # Or if it has a different name:
   cp your_proprietary_db.db materials/acoustic_materials.db
   ```

2. **Build as normal:**
   ```bash
   ./build/build.sh
   ```

3. **Result:** Your proprietary database is bundled in the executable.

**Pros:**
- ✅ Simple setup
- ✅ Works immediately
- ✅ No code changes needed

**Cons:**
- ❌ Everyone needs access to proprietary data
- ❌ Database must be shared securely

---

### Option 2: Use Both Databases

**Best for:** When you want standard materials + proprietary additions.

**Steps:**

1. **Place databases in materials folder:**
   ```bash
   materials/
     acoustic_materials.db          # Standard materials
     proprietary_materials.db       # Your proprietary materials
   ```

2. **Update build specs** (see code example below)

3. **Update application code** to load from both databases

**Code Example:**
```python
# In build_spec.py and build_spec_macos.py
datas = [
    (str(materials_path / "acoustic_materials.db"), "materials"),
    (str(materials_path / "proprietary_materials.db"), "materials"),
]
```

**Pros:**
- ✅ Separates standard and proprietary data
- ✅ Can update proprietary data independently

**Cons:**
- ❌ Requires code changes
- ❌ More complex application logic

---

### Option 3: Separate Proprietary Folder

**Best for:** Clear separation of proprietary data.

**Steps:**

1. **Create proprietary folder:**
   ```bash
   mkdir proprietary
   ```

2. **Update `.gitignore`:**
   ```gitignore
   # Proprietary data (never commit)
   proprietary/
   ```

3. **Place your database:**
   ```bash
   proprietary/materials.db
   ```

4. **Update build specs** to reference proprietary folder

**Code Example:**
```python
# In build_spec.py and build_spec_macos.py
proprietary_path = project_root / "proprietary"

datas = [
    (str(materials_path / "acoustic_materials.db"), "materials"),
    (str(proprietary_path / "materials.db"), "materials"),
]
```

**Pros:**
- ✅ Clear separation
- ✅ Explicit exclusion from git
- ✅ Easy to locate proprietary data

**Cons:**
- ❌ Requires code changes
- ❌ More complex folder structure

---

### Option 4: Build Machine Only (Recommended for Teams)

**Best for:** Teams where only the build machine has proprietary data.

**Workflow:**
- ✅ Developers work without proprietary database (uses fallback)
- ✅ Only release build machine has full database
- ✅ Build process validates database presence
- ✅ Production builds fail if database missing

**Current Implementation:**

The build system now supports this workflow:

1. **Development builds** (without database):
   ```bash
   ./build/build.sh
   # Warning: Materials database not found at materials/acoustic_materials.db
   # Warning: Building without proprietary materials database
   # Build continues with fallback materials
   ```

2. **Production builds** (with database):
   ```bash
   # On build machine with database:
   ./build/build.sh
   # ✓ Materials database found: 0.29 MB
   # ✓ Bundling materials database...
   # Build succeeds with full database
   ```

**Pros:**
- ✅ Developers don't need proprietary access
- ✅ Proprietary data only on secure build machine
- ✅ Clear separation of dev and production builds
- ✅ Build validates database presence

**Cons:**
- ⚠️ Developers test with limited materials
- ⚠️ Must coordinate build machine access

**Implementation Details:**

The build system automatically:
- ✅ Checks if database exists before building
- ✅ Warns if database missing (allows dev builds)
- ✅ Fails production builds if database missing (with `--production` flag)
- ✅ Validates bundled database in final executable

---

## Best Practices

### Security Best Practices

#### ✅ What's Protected

1. **Source Database File**
   - Excluded from git
   - Stays on local machines only
   - Never committed to version control

2. **Git Repository**
   - No proprietary data in git history
   - Safe to share publicly
   - No risk of accidental exposure

#### ⚠️ What's NOT Protected

1. **Bundled Database**
   - Extracted from executable by determined users
   - Standard SQLite3 format (readable)
   - Not encrypted

2. **Distributed Application**
   - Contains full database
   - Users have access to material data
   - Consider if this meets your requirements

### If You Need Stronger Protection

**Option 1: Encrypt the Database**
```python
# Use SQLCipher instead of SQLite3
from pysqlcipher3 import dbapi2 as sqlite3
conn = sqlite3.connect('materials.db')
conn.execute("PRAGMA key='your-encryption-key'")
```

**Option 2: Obfuscate Data**
- Store materials with encoded names
- Decrypt on-the-fly in application
- Add license key requirement

**Option 3: Server-Side Database**
- Keep proprietary data on your server
- App fetches data via authenticated API
- Never distributes full database

**Option 4: License-Based Access**
- Include obfuscated data in app
- Require license key to unlock
- Track usage via license server

### Development Best Practices

#### For Individual Developers

1. **Keep database local:**
   - Never commit to git
   - Store in secure location
   - Back up regularly

2. **Test builds:**
   - Verify database bundling works
   - Test with and without database
   - Confirm fallback materials work

#### For Teams

1. **Use Build Machine Only:**
   - Developers use fallback materials
   - Only build machine has full database
   - Clear separation of environments

2. **Secure Build Machine:**
   - Limit access to authorized users
   - Use encrypted storage for database
   - Audit build machine access

3. **Document Database Location:**
   - Clear instructions for build setup
   - Secure transfer methods
   - Version tracking for database

---

## Build Machine Only Workflow

### Overview

This workflow separates development from production:

```
┌─────────────────────────────────────────┐
│ Developer Machines                      │
│                                         │
│ ✅ Clone repo from GitHub               │
│ ✅ No proprietary database              │
│ ✅ Uses fallback materials              │
│ ✅ Can build for testing                │
└─────────────────────────────────────────┘
                  ↓
         Push code to GitHub
                  ↓
┌─────────────────────────────────────────┐
│ Build Machine (Secure)                   │
│                                         │
│ ✅ Has proprietary database             │
│ ✅ Pulls latest code                    │
│ ✅ Builds production executable         │
│ ✅ Includes full database               │
└─────────────────────────────────────────┘
                  ↓
         Distribute executable
```

### Setup Instructions

#### 1. Developer Machine Setup

**Initial setup:**
```bash
# Clone repository
git clone <repository-url>
cd drawings_to_acoustics_processor

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r build/requirements-build.txt
```

**Development workflow:**
```bash
# Database is NOT present (by design)
ls materials/acoustic_materials.db
# No such file or directory

# Build works (uses fallback materials)
./build/build.sh
# Warning: Materials database not found
# Warning: Building without proprietary materials database
# Build continues...

# Application works with fallback materials
open build/deploy/AcousticAnalysisTool.app
```

**Result:**
- ✅ Developers can work without proprietary data
- ✅ Builds succeed with fallback materials
- ✅ Application functional for testing UI/features
- ⚠️ Limited materials available (fallback only)

#### 2. Build Machine Setup

**Initial setup:**
```bash
# Clone repository
git clone <repository-url>
cd drawings_to_acoustics_processor

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r build/requirements-build.txt

# Transfer proprietary database (secure method)
# Option 1: Secure file transfer (SFTP, SCP, etc.)
scp proprietary_db.db materials/acoustic_materials.db

# Option 2: Encrypted USB drive
# Option 3: Secure cloud storage with authentication

# Verify database exists
ls -lh materials/acoustic_materials.db
# Should show ~300 KB file
```

**Production build workflow:**
```bash
# Pull latest code
git pull origin main

# Verify database present
ls materials/acoustic_materials.db
# acoustic_materials.db

# Build production executable
./build/build.sh

# Build output:
# ✓ Materials database found: 0.29 MB
# ✓ Bundling materials database...
# ✓ Build size looks good (150-200 MB)

# Verify database in built app
find build/deploy/AcousticAnalysisTool.app -name "*.db"
# build/deploy/AcousticAnalysisTool.app/Contents/Resources/materials/acoustic_materials.db

# Create installer
./build/deploy.sh
```

**Result:**
- ✅ Production executable includes full database
- ✅ All 1,383+ materials available
- ✅ Ready for distribution

### Security Considerations

#### Database Storage on Build Machine

1. **File System Security:**
   ```bash
   # Restrict file permissions
   chmod 600 materials/acoustic_materials.db
   
   # Restrict directory access
   chmod 700 materials/
   ```

2. **Encrypted Storage:**
   - Store database on encrypted disk
   - Use full-disk encryption (FileVault, BitLocker)
   - Consider encrypted volume for materials folder

3. **Access Control:**
   - Limit build machine access
   - Use strong authentication
   - Audit access logs

#### Database Transfer

**Secure Transfer Methods:**

1. **SSH/SCP:**
   ```bash
   scp -i keyfile.pem proprietary.db user@build-machine:/path/materials/acoustic_materials.db
   ```

2. **SFTP:**
   - Use SFTP client with encryption
   - Require key-based authentication
   - Use VPN if transferring over internet

3. **Encrypted USB:**
   - Use encrypted USB drive
   - Physical transfer (most secure)
   - One-time setup

4. **Secure Cloud Storage:**
   - Use encrypted cloud storage (AWS S3 with encryption)
   - Require authentication
   - Download on build machine only

### Build Script Enhancements

The build system now includes:

**Automatic Database Validation:**
- Checks if database exists before build
- Warns if missing (allows dev builds)
- Validates database in final executable

**Production Build Flag:**
- Use `--production` flag to fail if database missing
- Ensures production builds always have database
- Prevents accidental release without database

**Example:**
```bash
# Development build (database optional)
./build/build.sh
# Warning: Database missing, continuing with fallback...

# Production build (database required)
./build/build.sh --production
# Error: Database required for production build
# Build failed
```

---

## Troubleshooting

### Common Issues

#### Issue: "Database not found" during build

**Symptoms:**
```
Warning: Materials database not found at materials/acoustic_materials.db
Warning: Building without proprietary materials database
```

**Solution:**
- **For development:** This is expected and okay
- **For production:** Ensure database is present:
  ```bash
  ls materials/acoustic_materials.db
  # If missing, transfer database to build machine
  ```

#### Issue: Build fails with database error

**Symptoms:**
```
FileNotFoundError: materials/acoustic_materials.db
```

**Solution:**
- Check database file exists: `ls materials/acoustic_materials.db`
- Verify file permissions: `chmod 644 materials/acoustic_materials.db`
- Check file is valid SQLite: `sqlite3 materials/acoustic_materials.db "SELECT 1;"`

#### Issue: Database not bundled in executable

**Symptoms:**
- Built app works but has no materials
- Database file missing from app bundle

**Solution:**
1. Check build spec includes database:
   ```python
   datas = [
       (str(materials_path / "acoustic_materials.db"), "materials"),
   ]
   ```

2. Verify database exists during build:
   ```bash
   ls materials/acoustic_materials.db
   ```

3. Check build output for bundling messages:
   ```
   ✓ Materials database found: 0.29 MB
   ✓ Bundling materials database...
   ```

#### Issue: Application works but materials missing

**Symptoms:**
- App launches but material library is empty
- "No materials found" error

**Solution:**
1. Check database in app bundle:
   ```bash
   # macOS:
   find AcousticAnalysisTool.app -name "*.db"
   
   # Windows:
   # Check dist/AcousticAnalysisTool/materials/
   ```

2. Verify database path resolution:
   ```python
   from utils import get_materials_database_path
   print(get_materials_database_path())
   ```

3. Check application logs for database errors

#### Issue: Git accidentally tracks database

**Symptoms:**
```
git status shows materials/acoustic_materials.db
```

**Solution:**
1. Verify `.gitignore` excludes it:
   ```gitignore
   *.db
   materials/
   ```

2. Remove from git (but keep local file):
   ```bash
   git rm --cached materials/acoustic_materials.db
   git commit -m "Remove database from git tracking"
   ```

3. Verify it's now ignored:
   ```bash
   git status
   # Should NOT show materials/acoustic_materials.db
   ```

### Verification Steps

**Check Database Exclusion:**
```bash
# Should NOT show database
git status | grep materials

# Should NOT track database
git ls-files | grep "\.db$"
```

**Check Database Bundling:**
```bash
# After build, verify database in app:
# macOS:
find build/deploy/AcousticAnalysisTool.app -name "*.db"

# Should show:
# build/deploy/AcousticAnalysisTool.app/Contents/Resources/materials/acoustic_materials.db
```

**Test Application:**
```bash
# Launch built app
open build/deploy/AcousticAnalysisTool.app  # macOS
# or
build\deploy\AcousticAnalysisTool.exe       # Windows

# Check materials library loads
# Should show 1,383+ materials if database bundled
```

---

## Summary

### Current Setup ✅

- ✅ **Git exclusion:** Database not tracked by git
- ✅ **Build-time bundling:** Database included in executable
- ✅ **Application fallback:** Works without database (dev)
- ✅ **Build validation:** Checks database presence

### Recommended Workflow

**For Teams: Build Machine Only**
- ✅ Developers work without proprietary database
- ✅ Only build machine has full database
- ✅ Production builds validate database
- ✅ Clear separation of environments

### Next Steps

1. **If using Build Machine Only:**
   - Set up build machine with database
   - Configure secure database transfer
   - Test production build

2. **If using single developer:**
   - Place database in `materials/` folder
   - Build normally
   - Verify database bundled

3. **For enhanced security:**
   - Consider database encryption
   - Implement license-based access
   - Evaluate server-side database

---

**Last Updated:** 2025-01-29  
**Version:** 1.0.0  
**Workflow:** Build Machine Only

