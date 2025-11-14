# Build Machine Only - Setup Verification

This document verifies that the codebase is properly configured for the "Build Machine Only" workflow where developers work without proprietary databases.

## ✅ Verification Checklist

### 1. Git Exclusion Configuration

**Status:** ✅ Configured

**.gitignore** excludes proprietary database:
```gitignore
# Database files
*.db
*.sqlite
*.sqlite3

# Materials folder
materials/
```

**Verification:**
```bash
# Should NOT show database in git status
git status | grep materials
# Should be empty

# Should NOT track database files
git ls-files | grep "\.db$"
# Should be empty
```

### 2. Build System - Database Handling

**Status:** ✅ Configured

**build.py** checks for database:
- ✅ `check_database_exists()` method added
- ✅ Warns if missing (dev builds)
- ✅ Fails if missing (production builds with `--production`)
- ✅ Reports database status during build

**build_spec.py & build_spec_macos.py:**
- ✅ Check if database exists before bundling
- ✅ Only include database if present
- ✅ Print clear warnings if missing

**Verification:**
```bash
# Test without database (should work)
rm -f materials/acoustic_materials.db
./build/build.sh
# Should show: Warning: Materials database not found
# Build should continue with fallback materials

# Test with --production flag (should fail)
./build/build.sh --production
# Should fail: Materials database required for production build
```

### 3. Application Fallback Support

**Status:** ✅ Already Implemented

**src/data/materials.py:**
- ✅ `load_materials_from_database()` handles missing database
- ✅ Falls back to `get_fallback_materials()`
- ✅ Application works without database

**Verification:**
```bash
# Application should work with fallback materials
python -c "
from src.data.materials import load_materials_from_database
materials = load_materials_from_database()
print(f'Loaded {len(materials)} materials (with fallback)')
"
```

### 4. Build Scripts - Production Flag Support

**Status:** ✅ Configured

**build.sh:**
- ✅ Supports `--production` flag
- ✅ Passes flag to build.py

**build.bat:**
- ✅ Supports `--production` flag
- ✅ Passes flag to build.py

**Usage:**
```bash
# Development build (database optional)
./build/build.sh

# Production build (database required)
./build/build.sh --production

# Windows
build\build.bat --production
```

### 5. Documentation

**Status:** ✅ Complete

**Files Created:**
- ✅ `PROPRIETARY_DATABASE_GUIDE.md` - Comprehensive guide
- ✅ `BUILD_MACHINE_ONLY_SETUP.md` - This verification document

---

## Workflow Verification

### Developer Machine Workflow

**Step 1: Clone Repository**
```bash
git clone <repository-url>
cd drawings_to_acoustics_processor
```

**Step 2: Setup Environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r build/requirements-build.txt
```

**Step 3: Verify Database Not Present**
```bash
ls materials/acoustic_materials.db
# Should show: No such file or directory
```

**Step 4: Build (Development Mode)**
```bash
./build/build.sh
# Expected output:
# ⚠ Warning: Materials database not found at ...
# ⚠ Warning: Building without proprietary materials database
# Build continues...
# ⚠ Built without proprietary materials database (dev build)
```

**Step 5: Test Application**
```bash
# Application should work with fallback materials
open build/deploy/AcousticAnalysisTool.app
# Material library should have limited materials (fallback)
```

**Result:** ✅ Developer can work and test without proprietary database

---

### Build Machine Workflow

**Step 1: Setup Build Machine**
```bash
git clone <repository-url>
cd drawings_to_acoustics_processor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r build/requirements-build.txt
```

**Step 2: Transfer Proprietary Database**
```bash
# Secure transfer method (choose one):
# Option A: SCP
scp proprietary_db.db build-machine:/path/materials/acoustic_materials.db

# Option B: Encrypted USB
# Physical transfer

# Option C: Secure cloud storage
# Download from encrypted storage
```

**Step 3: Verify Database Present**
```bash
ls -lh materials/acoustic_materials.db
# Should show: acoustic_materials.db (~300 KB)
```

**Step 4: Build (Production Mode)**
```bash
./build/build.sh --production
# Expected output:
# Production build mode: Database required
# ✓ Materials database found: 0.29 MB
# ✓ Bundling materials database...
# ✓ Materials database successfully bundled
```

**Step 5: Verify Database in Build**
```bash
# macOS:
find build/deploy/AcousticAnalysisTool.app -name "*.db"
# Should show: build/deploy/AcousticAnalysisTool.app/Contents/Resources/materials/acoustic_materials.db

# Windows:
# Check dist/AcousticAnalysisTool/materials/
```

**Result:** ✅ Production build includes full proprietary database

---

## Testing Commands

### Test 1: Development Build (No Database)
```bash
# Remove database if exists
rm -f materials/acoustic_materials.db

# Build without database
./build/build.sh

# Should:
# - Show warning about missing database
# - Continue with build
# - Complete successfully
# - Note: "Built without proprietary materials database (dev build)"
```

### Test 2: Production Build (No Database) - Should Fail
```bash
# Ensure database is missing
rm -f materials/acoustic_materials.db

# Attempt production build
./build/build.sh --production

# Should:
# - Show warning about missing database
# - Fail with error: "Materials database required for production build"
# - Exit with error code
```

### Test 3: Production Build (With Database) - Should Succeed
```bash
# Ensure database exists
ls materials/acoustic_materials.db

# Production build
./build/build.sh --production

# Should:
# - Show: "✓ Materials database found: X.XX MB"
# - Include database in bundle
# - Complete successfully
# - Note: "✓ Materials database successfully bundled"
```

### Test 4: Verify Database Bundling
```bash
# After successful build, verify database in app
# macOS:
find build/deploy/AcousticAnalysisTool.app -name "*.db"

# Should show:
# build/deploy/AcousticAnalysisTool.app/Contents/Resources/materials/acoustic_materials.db

# Check database is valid
sqlite3 build/deploy/AcousticAnalysisTool.app/Contents/Resources/materials/acoustic_materials.db "SELECT COUNT(*) FROM acoustic_materials;"
# Should show material count (e.g., 1383)
```

---

## Configuration Summary

### Current Configuration

| Component | Status | Notes |
|-----------|--------|-------|
| Git Exclusion | ✅ | `.gitignore` excludes `*.db` and `materials/` |
| Build Check | ✅ | `build.py` checks database presence |
| Build Specs | ✅ | Conditionally include database if exists |
| Application Fallback | ✅ | Uses `get_fallback_materials()` if missing |
| Production Flag | ✅ | `--production` flag enforces database requirement |
| Documentation | ✅ | Complete guide created |

### Build System Behavior

| Scenario | Database Present | Build Command | Result |
|----------|-----------------|---------------|--------|
| Dev Build | ❌ No | `./build/build.sh` | ✅ Succeeds with warning |
| Dev Build | ✅ Yes | `./build/build.sh` | ✅ Succeeds, bundles database |
| Prod Build | ❌ No | `./build/build.sh --production` | ❌ Fails with error |
| Prod Build | ✅ Yes | `./build/build.sh --production` | ✅ Succeeds, bundles database |

---

## Security Considerations

### ✅ What's Protected

1. **Source Database**
   - Not in git repository
   - Stays on local machines/build machine only
   - Never committed to version control

2. **Repository Safety**
   - Can share repository publicly
   - No proprietary data exposure risk

### ⚠️ What's NOT Protected

1. **Bundled Database**
   - Users can extract from executable
   - Standard SQLite3 format (readable)
   - Not encrypted

2. **Distributed Application**
   - Contains full database
   - Users have access to material data

### Recommendations

For stronger protection, consider:
- Database encryption (SQLCipher)
- License-based access control
- Server-side database with API
- Obfuscation techniques

See `PROPRIETARY_DATABASE_GUIDE.md` for details.

---

## Next Steps

### Immediate Actions

1. **Verify Setup:**
   ```bash
   # Test development build without database
   rm -f materials/acoustic_materials.db
   ./build/build.sh
   
   # Should succeed with warnings
   ```

2. **Document Database Location:**
   - Record secure storage location
   - Document transfer methods
   - Create secure access procedures

3. **Set Up Build Machine:**
   - Configure secure build machine
   - Transfer proprietary database
   - Test production build

### Future Enhancements

1. **Automated Database Validation:**
   - Add database schema validation
   - Verify material count
   - Check data integrity

2. **Build Automation:**
   - CI/CD pipeline integration
   - Automated production builds
   - Secure database deployment

3. **Enhanced Security:**
   - Database encryption
   - License-based access
   - Audit logging

---

## Troubleshooting

### Issue: Build fails even without --production

**Check:**
```bash
# Verify build spec files handle missing database
grep -A 5 "if db_path.exists()" build/build_spec.py
# Should show conditional inclusion
```

### Issue: Database bundled even when missing

**Check:**
```bash
# Verify build specs check for existence
python3 -c "
from pathlib import Path
db_path = Path('materials/acoustic_materials.db')
print(f'Database exists: {db_path.exists()}')
"
```

### Issue: Production build succeeds without database

**Check:**
```bash
# Verify --production flag is passed
./build/build.sh --production 2>&1 | grep -i "production"
# Should show: "Production build mode: Database required"
```

---

**Setup Verified:** 2025-01-29  
**Status:** ✅ Ready for Build Machine Only Workflow  
**Version:** 1.0.0

