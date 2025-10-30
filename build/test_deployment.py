#!/usr/bin/env python3
"""
Deployment validation tests for Acoustic Analysis Tool
Tests both the build process and the resulting executable
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
import tempfile
import sqlite3


class DeploymentTester:
    """Tests for validating deployment build and functionality"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.absolute()
        self.build_dir = self.project_root / "build"
        self.deploy_dir = self.build_dir / "deploy"
        self.exe_path = self.deploy_dir / "AcousticAnalysisTool.exe"
        self.test_results = []
        
    def log_test(self, test_name, passed, details=""):
        """Log a test result"""
        status = "PASS" if passed else "FAIL"
        result = {
            'test': test_name,
            'status': status,
            'passed': passed,
            'details': details
        }
        self.test_results.append(result)
        print(f"[{status}] {test_name}: {details}")
        
    def test_build_artifacts_exist(self):
        """Test that all expected build artifacts exist"""
        print("\n=== Testing Build Artifacts ===")
        
        # Check main executable
        if self.exe_path.exists():
            size_mb = self.exe_path.stat().st_size / (1024 * 1024)
            self.log_test("Executable exists", True, f"Size: {size_mb:.1f} MB")
            
            # Check reasonable size bounds
            if size_mb < 30:
                self.log_test("Executable size check", False, f"Too small: {size_mb:.1f} MB")
            elif size_mb > 800:
                self.log_test("Executable size check", False, f"Too large: {size_mb:.1f} MB")
            else:
                self.log_test("Executable size check", True, f"Reasonable size: {size_mb:.1f} MB")
        else:
            self.log_test("Executable exists", False, f"Not found at {self.exe_path}")
            
        # Check build info
        build_info_path = self.deploy_dir / "build_info.json"
        if build_info_path.exists():
            try:
                with open(build_info_path) as f:
                    build_info = json.load(f)
                self.log_test("Build info exists", True, f"Version: {build_info.get('version', 'unknown')}")
                
                # Validate build info contents
                required_keys = ['version', 'build_number', 'git_commit', 'build_date']
                missing_keys = [key for key in required_keys if key not in build_info]
                if missing_keys:
                    self.log_test("Build info complete", False, f"Missing: {missing_keys}")
                else:
                    self.log_test("Build info complete", True, "All required fields present")
                    
            except json.JSONDecodeError as e:
                self.log_test("Build info valid", False, f"Invalid JSON: {e}")
        else:
            self.log_test("Build info exists", False, "build_info.json not found")
            
        # Check batch scripts
        expected_files = [
            ("build.bat", "Build script"),
            ("deploy.bat", "Deployment script"),
            ("deploy/README_INSTALL.txt", "Installation instructions")
        ]
        
        for filename, description in expected_files:
            file_path = self.build_dir / filename
            exists = file_path.exists()
            self.log_test(f"{description} exists", exists, 
                        f"Found at {file_path}" if exists else f"Missing: {file_path}")
                        
    def test_bundled_resources(self):
        """Test that resources are properly bundled (requires running executable)"""
        print("\n=== Testing Bundled Resources ===")
        
        if not self.exe_path.exists():
            self.log_test("Bundled resources test", False, "Executable not found, skipping")
            return
            
        # We can't easily test bundled resources without running the app,
        # but we can check if the source materials database exists
        materials_db = self.project_root / "materials" / "acoustic_materials.db"
        if materials_db.exists():
            try:
                # Test database connectivity
                conn = sqlite3.connect(materials_db)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM acoustic_materials")
                count = cursor.fetchone()[0]
                conn.close()
                
                self.log_test("Materials database", True, f"{count} materials found")
                
                # Check reasonable material count
                if count < 1000:
                    self.log_test("Materials database size", False, f"Only {count} materials, expected 1000+")
                else:
                    self.log_test("Materials database size", True, f"{count} materials (good)")
                    
            except Exception as e:
                self.log_test("Materials database", False, f"Database error: {e}")
        else:
            self.log_test("Materials database", False, "acoustic_materials.db not found")
            
    def test_executable_properties(self):
        """Test executable file properties (Windows-specific)"""
        print("\n=== Testing Executable Properties ===")
        
        if not self.exe_path.exists():
            self.log_test("Executable properties test", False, "Executable not found, skipping")
            return
            
        # Test if file is actually executable
        import stat
        file_stat = self.exe_path.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IEXEC)
        self.log_test("File is executable", is_executable, "Has execute permissions" if is_executable else "No execute permissions")
        
        # Check file signature (basic)
        with open(self.exe_path, 'rb') as f:
            header = f.read(2)
            
        if header == b'MZ':
            self.log_test("Valid PE executable", True, "Has valid PE header")
        else:
            self.log_test("Valid PE executable", False, f"Invalid header: {header}")
            
    def test_version_consistency(self):
        """Test version consistency across build artifacts"""
        print("\n=== Testing Version Consistency ===")
        
        versions_found = {}
        
        # Check build_info.json
        build_info_path = self.deploy_dir / "build_info.json"
        if build_info_path.exists():
            try:
                with open(build_info_path) as f:
                    build_info = json.load(f)
                versions_found['build_info'] = build_info.get('version', 'unknown')
            except Exception as e:
                self.log_test("Version from build_info", False, f"Error reading: {e}")
                
        # Check version.py if it exists
        version_py_path = self.project_root / "src" / "version.py"
        if version_py_path.exists():
            try:
                with open(version_py_path) as f:
                    content = f.read()
                    # Extract version from content
                    for line in content.split('\n'):
                        if 'VERSION_MAJOR' in line and '=' in line:
                            major = line.split('=')[1].strip()
                        if 'VERSION_MINOR' in line and '=' in line:
                            minor = line.split('=')[1].strip()
                        if 'VERSION_PATCH' in line and '=' in line:
                            patch = line.split('=')[1].strip()
                    versions_found['version_py'] = f"{major}.{minor}.{patch}"
            except Exception as e:
                self.log_test("Version from version.py", False, f"Error reading: {e}")
                
        # Check consistency
        if len(versions_found) > 1:
            unique_versions = set(versions_found.values())
            if len(unique_versions) == 1:
                version = list(unique_versions)[0]
                self.log_test("Version consistency", True, f"All sources report v{version}")
            else:
                self.log_test("Version consistency", False, f"Inconsistent versions: {versions_found}")
        elif len(versions_found) == 1:
            version = list(versions_found.values())[0]
            self.log_test("Version found", True, f"Version: {version}")
        else:
            self.log_test("Version information", False, "No version information found")
            
    def test_startup_simulation(self):
        """Simulate application startup without GUI (if possible)"""
        print("\n=== Testing Startup Simulation ===")
        
        if not self.exe_path.exists():
            self.log_test("Startup simulation", False, "Executable not found, skipping")
            return
            
        # Create a temporary directory for test data
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to start the application with a timeout
            try:
                # Start the process but kill it quickly since we can't interact with GUI
                process = subprocess.Popen([str(self.exe_path)], 
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         cwd=temp_dir)
                
                # Wait a short time to see if it starts
                time.sleep(3)
                
                # Check if process is still running (good sign)
                if process.poll() is None:
                    # Process is running, terminate it
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                        self.log_test("Application startup", True, "Started successfully")
                    except subprocess.TimeoutExpired:
                        process.kill()
                        self.log_test("Application startup", True, "Started but required force kill")
                else:
                    # Process exited
                    stdout, stderr = process.communicate()
                    if process.returncode == 0:
                        self.log_test("Application startup", True, "Exited cleanly")
                    else:
                        error_msg = stderr.decode('utf-8', errors='ignore')[:200]
                        self.log_test("Application startup", False, f"Exit code {process.returncode}: {error_msg}")
                        
            except Exception as e:
                self.log_test("Application startup", False, f"Failed to start: {e}")
                
    def test_dependencies_check(self):
        """Check for common deployment issues"""
        print("\n=== Testing Dependencies ===")
        
        if not self.exe_path.exists():
            self.log_test("Dependencies test", False, "Executable not found, skipping")
            return
            
        # Check for common missing DLL issues by examining error patterns
        # This is a basic check - real testing would require running on target machines
        
        # Check if PyInstaller spec includes all necessary hidden imports
        spec_path = self.build_dir / "build_spec.py"
        if spec_path.exists():
            with open(spec_path) as f:
                spec_content = f.read()
                
            required_modules = [
                'PySide6.QtCore',
                'PySide6.QtWidgets',
                'PySide6.QtGui',
                'sqlalchemy',
                'numpy',
                'openpyxl'
            ]
            
            missing_modules = []
            for module in required_modules:
                if module not in spec_content:
                    missing_modules.append(module)
                    
            if missing_modules:
                self.log_test("Hidden imports complete", False, f"Missing: {missing_modules}")
            else:
                self.log_test("Hidden imports complete", True, "All critical modules included")
        else:
            self.log_test("Spec file check", False, "build_spec.py not found")
            
    def run_all_tests(self):
        """Run all deployment validation tests"""
        print("="*60)
        print("ACOUSTIC ANALYSIS TOOL - DEPLOYMENT VALIDATION TESTS")
        print("="*60)
        
        test_methods = [
            self.test_build_artifacts_exist,
            self.test_bundled_resources,
            self.test_executable_properties,
            self.test_version_consistency,
            self.test_dependencies_check,
            self.test_startup_simulation,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(f"{test_method.__name__}", False, f"Test crashed: {e}")
                
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed_tests = [t for t in self.test_results if t['passed']]
        failed_tests = [t for t in self.test_results if not t['passed']]
        
        print(f"Total tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if failed_tests:
            print("\nFAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
                
        success_rate = len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        
        # Save results
        results_path = self.deploy_dir / "test_results.json"
        try:
            with open(results_path, 'w') as f:
                json.dump({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_tests': len(self.test_results),
                    'passed_tests': len(passed_tests),
                    'failed_tests': len(failed_tests),
                    'success_rate': success_rate,
                    'results': self.test_results
                }, f, indent=2)
            print(f"\nTest results saved to: {results_path}")
        except Exception as e:
            print(f"Warning: Could not save test results: {e}")
            
        return len(failed_tests) == 0


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Acoustic Analysis Tool Deployment Validation Tests")
        print("Usage: python test_deployment.py")
        print("\nTests the built executable for common deployment issues.")
        print("Run this after building the executable with build.py")
        return
        
    tester = DeploymentTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! The deployment is ready for distribution.")
    else:
        print("\n⚠️  Some tests failed. Review the results above before distributing.")
        
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()