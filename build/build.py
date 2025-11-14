#!/usr/bin/env python3
"""
Build script for Acoustic Analysis Tool Windows executable
Handles version generation, PyInstaller execution, and deployment packaging
"""

import os
import sys
import subprocess
import shutil
import datetime
import hashlib
import platform
from pathlib import Path
import json

class AcousticAnalysisBuilder:
    """Builder for Acoustic Analysis Tool executable"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.absolute()
        self.build_dir = self.project_root / "build"
        self.src_dir = self.project_root / "src"
        self.deploy_dir = self.build_dir / "deploy"
        self.dist_dir = self.project_root / "dist"
        
        # Detect platform
        self.platform = platform.system()  # 'Windows', 'Darwin', or 'Linux'
        self.is_windows = self.platform == 'Windows'
        self.is_macos = self.platform == 'Darwin'
        self.is_linux = self.platform == 'Linux'
        
        # Ensure directories exist
        self.deploy_dir.mkdir(exist_ok=True)
        
        # Build information
        self.build_info = {}
        
        # Production build flag (require database)
        self.production_build = False
        
    def check_database_exists(self):
        """Check if materials database exists and return status"""
        db_path = self.project_root / "materials" / "acoustic_materials.db"
        exists = db_path.exists()
        
        if exists:
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"✓ Materials database found: {size_mb:.2f} MB")
            return True, size_mb
        else:
            print(f"⚠ Warning: Materials database not found at {db_path}")
            if self.production_build:
                raise FileNotFoundError(
                    "Materials database required for production build. "
                    f"Please ensure {db_path} exists on the build machine."
                )
            else:
                print("⚠ Warning: Building without proprietary materials database")
                print("  Development build will use fallback materials")
                print("  For production build, use --production flag")
            return False, 0
        
    def get_git_info(self):
        """Get git commit information"""
        try:
            # Get current commit hash
            commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Get short commit hash
            short_commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.project_root, 
                text=True
            ).strip()
            
            # Get commit count as build number
            build_number = subprocess.check_output(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=self.project_root,
                text=True
            ).strip()
            
            # Get branch name
            try:
                branch = subprocess.check_output(
                    ['git', 'branch', '--show-current'],
                    cwd=self.project_root,
                    text=True
                ).strip()
            except:
                branch = "unknown"
                
            return {
                'commit': commit,
                'short_commit': short_commit,
                'build_number': build_number,
                'branch': branch
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not get git information: {e}")
            # Fallback to timestamp-based build number
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
            return {
                'commit': 'unknown',
                'short_commit': 'unknown',
                'build_number': timestamp,
                'branch': 'unknown'
            }
    
    def generate_version_file(self):
        """Generate version.py file from template with build information"""
        print("Generating version information...")
        
        git_info = self.get_git_info()
        now = datetime.datetime.now()
        
        # Read template
        template_path = self.build_dir / "version_template.py"
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Replace placeholders
        version_content = template_content.replace(
            "{{BUILD_NUMBER}}", git_info['build_number']
        ).replace(
            "{{GIT_COMMIT}}", git_info['commit']
        ).replace(
            "{{BUILD_DATE}}", now.strftime("%Y-%m-%d")
        ).replace(
            "{{BUILD_TIME}}", now.strftime("%H:%M:%S")
        )
        
        # Write to src directory
        version_path = self.src_dir / "version.py"
        with open(version_path, 'w') as f:
            f.write(version_content)
        
        # Store build info
        self.build_info = {
            'version': '1.0.0',
            'build_number': git_info['build_number'],
            'git_commit': git_info['commit'],
            'git_short_commit': git_info['short_commit'],
            'git_branch': git_info['branch'],
            'build_date': now.strftime("%Y-%m-%d"),
            'build_time': now.strftime("%H:%M:%S"),
            'build_timestamp': now.isoformat()
        }
        
        print(f"Version: 1.0.0.{git_info['build_number']}")
        print(f"Git commit: {git_info['short_commit']}")
        print(f"Branch: {git_info['branch']}")
        
    def create_version_info_file(self):
        """Create Windows version info file for executable metadata (Windows only)"""
        if not self.is_windows:
            print("Skipping Windows version info (not on Windows platform)")
            return
            
        print("Creating Windows version info...")
        
        version_info_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=(1, 0, 0, {self.build_info['build_number']}),
prodvers=(1, 0, 0, {self.build_info['build_number']}),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'Acoustic Solutions'),
    StringStruct(u'FileDescription', u'Acoustic Analysis Tool - LEED Acoustic Certification'),
    StringStruct(u'FileVersion', u'1.0.0.{self.build_info['build_number']}'),
    StringStruct(u'InternalName', u'AcousticAnalysisTool'),
    StringStruct(u'LegalCopyright', u'© 2025 Acoustic Solutions'),
    StringStruct(u'OriginalFilename', u'AcousticAnalysisTool.exe'),
    StringStruct(u'ProductName', u'Acoustic Analysis Tool'),
    StringStruct(u'ProductVersion', u'1.0.0.{self.build_info['build_number']}'),
    StringStruct(u'Comments', u'Built from commit {self.build_info['git_short_commit']} on {self.build_info['build_date']}')])
  ]), 
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
        
        version_info_path = self.build_dir / "file_version_info.txt"
        with open(version_info_path, 'w', encoding='utf-8') as f:
            f.write(version_info_content)
            
    def install_build_requirements(self):
        """Install build requirements if needed"""
        print("Checking build requirements...")
        
        try:
            import PyInstaller
            print("PyInstaller already installed")
        except ImportError:
            print("Installing build requirements...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '-r', 
                str(self.build_dir / "requirements-build.txt")
            ])
            
    def clean_build_directories(self):
        """Clean previous build artifacts"""
        print("Cleaning build directories...")
        
        dirs_to_clean = [
            self.project_root / "build" / "AcousticAnalysisTool",
            self.project_root / "dist" / "AcousticAnalysisTool",
            self.dist_dir,
            self.project_root / "__pycache__",
            self.src_dir / "__pycache__"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"Removed {dir_path}")
                
    def run_pyinstaller(self):
        """Run PyInstaller to create executable"""
        print(f"Running PyInstaller for {self.platform}...")
        
        # Select appropriate spec file based on platform
        if self.is_macos:
            spec_file = self.build_dir / "build_spec_macos.py"
        else:
            spec_file = self.build_dir / "build_spec.py"
        
        if not spec_file.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_file}")
        
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(spec_file)
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        try:
            subprocess.check_call(cmd, cwd=self.project_root)
            print("PyInstaller completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"PyInstaller failed with return code {e.returncode}")
            raise
            
    def create_deployment_package(self):
        """Create deployment package with installer scripts"""
        print("Creating deployment package...")
        
        if self.is_macos:
            # macOS .app bundle
            app_source = self.dist_dir / "AcousticAnalysisTool.app"
            if not app_source.exists():
                raise FileNotFoundError(f"Built application not found at {app_source}")
            
            # Copy .app bundle to deploy directory
            app_dest = self.deploy_dir / "AcousticAnalysisTool.app"
            if app_dest.exists():
                shutil.rmtree(app_dest)
            shutil.copytree(app_source, app_dest)
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in app_dest.rglob('*') if f.is_file())
            print(f"Application bundle size: {total_size / (1024*1024):.1f} MB")
            
        else:
            # Windows executable
            exe_source_dir = self.dist_dir / "AcousticAnalysisTool"
            if not exe_source_dir.exists():
                raise FileNotFoundError(f"Built executable not found at {exe_source_dir}")
            
            # Copy executable to deploy directory
            exe_dest = self.deploy_dir / "AcousticAnalysisTool.exe"
            shutil.copy2(exe_source_dir / "AcousticAnalysisTool.exe", exe_dest)
            print(f"Executable size: {exe_dest.stat().st_size / (1024*1024):.1f} MB")
        
        # Create build info file
        build_info_path = self.deploy_dir / "build_info.json"
        with open(build_info_path, 'w') as f:
            json.dump(self.build_info, f, indent=2)
        
        print(f"Deployment package created in {self.deploy_dir}")
        
    def validate_build(self):
        """Validate the built executable"""
        print("Validating build...")
        
        if self.is_macos:
            # Validate macOS .app bundle
            app_path = self.deploy_dir / "AcousticAnalysisTool.app"
            if not app_path.exists():
                raise FileNotFoundError("Built application bundle not found")
            
            # Check for required bundle structure
            executable = app_path / "Contents" / "MacOS" / "AcousticAnalysisTool"
            if not executable.exists():
                raise FileNotFoundError("Application executable not found in bundle")
            
            # Check total bundle size
            total_size = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024*1024)
            
        else:
            # Validate Windows executable
            exe_path = self.deploy_dir / "AcousticAnalysisTool.exe"
            if not exe_path.exists():
                raise FileNotFoundError("Built executable not found")
            
            size_mb = exe_path.stat().st_size / (1024*1024)
        
        # Check file size is reasonable
        if size_mb < 50:  # Minimum expected size
            print(f"Warning: Build size seems small ({size_mb:.1f} MB)")
        elif size_mb > 500:  # Maximum reasonable size
            print(f"Warning: Build size seems large ({size_mb:.1f} MB)")
        else:
            print(f"Build size looks good ({size_mb:.1f} MB)")
            
        print("Build validation completed")
        
    def build(self):
        """Run complete build process"""
        print("=" * 60)
        print(f"Building Acoustic Analysis Tool for {self.platform}")
        if self.production_build:
            print("Production Build Mode: Database required")
        print("=" * 60)
        
        try:
            # Check database first (before any build steps)
            db_exists, db_size = self.check_database_exists()
            
            self.install_build_requirements()
            self.clean_build_directories()
            self.generate_version_file()
            self.create_version_info_file()
            
            # Only proceed with PyInstaller if database check passed
            if self.production_build and not db_exists:
                raise FileNotFoundError(
                    "Production build requires materials database. Build aborted."
                )
            
            self.run_pyinstaller()
            self.create_deployment_package()
            self.validate_build()
            
            # Final database validation
            if db_exists:
                print("\n✓ Materials database successfully bundled")
            else:
                print("\n⚠ Built without proprietary materials database (dev build)")
            
            print("\n" + "=" * 60)
            print("BUILD COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            if self.is_macos:
                print(f"Application: {self.deploy_dir / 'AcousticAnalysisTool.app'}")
            else:
                print(f"Executable: {self.deploy_dir / 'AcousticAnalysisTool.exe'}")
                
            print(f"Platform: {self.platform}")
            print(f"Version: 1.0.0.{self.build_info['build_number']}")
            print(f"Git commit: {self.build_info['git_short_commit']}")
            print(f"Build date: {self.build_info['build_date']} {self.build_info['build_time']}")
            
            print("\nNext steps:")
            if self.is_macos:
                print("1. Test the application on macOS systems")
                print("2. Run ./deploy.sh to create DMG installer")
                print("3. Consider code signing and notarization for distribution")
            else:
                print("1. Test the executable on target Windows systems")
                print("2. Run deploy.bat to create installer package")
                print("3. Distribute to users for testing")
            
            return True
            
        except Exception as e:
            print(f"\nBUILD FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Acoustic Analysis Tool Build Script")
        print("Usage: python build.py [--production]")
        print("\nBuilds executable with:")
        print("- Git-based versioning")
        print("- Bundled databases")
        print("- Professional installer")
        print("\nOptions:")
        print("  --production    Require materials database (fail if missing)")
        print("  --help          Show this help message")
        return
        
    # Check for production flag
    production = '--production' in sys.argv
    
    builder = AcousticAnalysisBuilder()
    builder.production_build = production
    success = builder.build()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()