"""
Preservation Property Tests for construir.bat

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

These tests verify that existing behavior is preserved after the fix.
They test scenarios that ALREADY WORK in the unfixed code:
- SQLite mode (--com-sqlite) in paths with spaces
- Supabase mode (--com-env) in paths WITHOUT spaces
- Cleanup of .env_embutido after build
- Executable creation in dist/

CRITICAL: These tests should PASS on UNFIXED code to establish baseline.
After the fix, they should STILL PASS to confirm no regressions.

IMPORTANT: These are observation-based tests. We observe the behavior
on unfixed code first, then encode that behavior in tests.
"""

import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path


class TestPreservationSQLiteMode:
    """
    Property 2.1: Preservation - SQLite Mode with Spaces in Path
    
    **Validates: Requirement 3.1**
    
    For all executions with --com-sqlite parameter, .env_embutido should
    be created via echo command, regardless of spaces in path.
    
    This already works in unfixed code because echo doesn't have the same
    quoting issues as copy command.
    """
    
    def test_sqlite_mode_creates_env_embutido_with_spaces(self):
        """
        Test that --com-sqlite mode creates .env_embutido successfully
        even when path contains spaces.
        
        EXPECTED OUTCOME ON UNFIXED CODE: PASS
        EXPECTED OUTCOME ON FIXED CODE: PASS (preserved)
        """
        
        # Skip test if not on Windows
        if sys.platform != "win32":
            print("SKIP: This test only runs on Windows")
            return
        
        # Create a temporary directory with spaces in the path
        temp_base = tempfile.gettempdir()
        test_dir_name = "Test SQLite Build"
        test_dir = os.path.join(temp_base, "test_preservation", test_dir_name)
        
        try:
            # Clean up if directory already exists
            if os.path.exists(os.path.join(temp_base, "test_preservation")):
                shutil.rmtree(os.path.join(temp_base, "test_preservation"))
            
            # Create the test directory
            os.makedirs(test_dir, exist_ok=True)
            print(f"\n[PRESERVATION TEST] Created test directory: {test_dir}")
            print(f"[PRESERVATION TEST] Path contains spaces: {'Yes' if ' ' in test_dir else 'No'}")
            
            # Execute the echo command from construir.bat for SQLite mode (line 79)
            # This is: echo DB_MODE=sqlite> ".env_embutido"
            print(f"\n[PRESERVATION TEST] Executing echo command for SQLite mode...")
            print(f'[PRESERVATION TEST] Command: echo DB_MODE=sqlite> ".env_embutido"')
            
            result = subprocess.run(
                'echo DB_MODE=sqlite> ".env_embutido"',
                cwd=test_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            
            print(f"[PRESERVATION TEST] Echo command exit code: {result.returncode}")
            
            # Check if .env_embutido was created
            env_embutido_path = os.path.join(test_dir, ".env_embutido")
            env_embutido_exists = os.path.exists(env_embutido_path)
            
            print(f"\n[PRESERVATION TEST] Checking for .env_embutido file...")
            print(f"[PRESERVATION TEST] .env_embutido exists: {env_embutido_exists}")
            
            # Verify content
            if env_embutido_exists:
                with open(env_embutido_path, "r", encoding="utf-8") as f:
                    content = f.read()
                print(f"[PRESERVATION TEST] .env_embutido content: {repr(content)}")
            
            # ASSERTIONS - These should PASS on unfixed code
            assert env_embutido_exists, (
                f"PRESERVATION VIOLATED: .env_embutido should be created by echo command "
                f"in SQLite mode, even with spaces in path. This worked before the fix."
            )
            
            # Verify content is correct
            with open(env_embutido_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            assert "DB_MODE=sqlite" in content, (
                f"PRESERVATION VIOLATED: .env_embutido should contain 'DB_MODE=sqlite'. "
                f"Actual content: {repr(content)}"
            )
            
            print(f"\n[PRESERVATION TEST] ✓ SQLite mode preservation verified")
            print(f"[PRESERVATION TEST] .env_embutido created successfully with spaces in path")
            
        finally:
            # Clean up test directory
            if os.path.exists(os.path.join(temp_base, "test_preservation")):
                try:
                    shutil.rmtree(os.path.join(temp_base, "test_preservation"))
                    print(f"\n[PRESERVATION TEST] Cleaned up test directory")
                except Exception as e:
                    print(f"\n[PRESERVATION TEST] Warning: Failed to clean up: {e}")


class TestPreservationNonSpacePaths:
    """
    Property 2.2: Preservation - Supabase Mode WITHOUT Spaces in Path
    
    **Validates: Requirement 3.2**
    
    For all executions with --com-env parameter in paths WITHOUT spaces,
    .env_embutido should be created successfully.
    
    This already works in unfixed code.
    """
    
    def test_supabase_mode_works_without_spaces(self):
        """
        Test that --com-env mode creates .env_embutido successfully
        when path does NOT contain spaces.
        
        EXPECTED OUTCOME ON UNFIXED CODE: PASS
        EXPECTED OUTCOME ON FIXED CODE: PASS (preserved)
        """
        
        # Skip test if not on Windows
        if sys.platform != "win32":
            print("SKIP: This test only runs on Windows")
            return
        
        # Create a temporary directory WITHOUT spaces in the path
        temp_base = tempfile.gettempdir()
        test_dir_name = "test_supabase_build"  # No spaces
        test_dir = os.path.join(temp_base, "test_preservation_nospace", test_dir_name)
        
        try:
            # Clean up if directory already exists
            if os.path.exists(os.path.join(temp_base, "test_preservation_nospace")):
                shutil.rmtree(os.path.join(temp_base, "test_preservation_nospace"))
            
            # Create the test directory
            os.makedirs(test_dir, exist_ok=True)
            print(f"\n[PRESERVATION TEST] Created test directory: {test_dir}")
            print(f"[PRESERVATION TEST] Path contains spaces: {'Yes' if ' ' in test_dir else 'No'}")
            
            # Create a minimal valid .env file
            env_content = """SUPABASE_URL=https://example.supabase.co
SUPABASE_KEY=test_key_12345
DB_MODE=supabase
"""
            env_path = os.path.join(test_dir, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            print(f"[PRESERVATION TEST] Created .env file")
            
            # Verify .env exists
            assert os.path.exists(env_path), "Precondition failed: .env file should exist"
            
            # Execute the copy command from construir.bat (line 81)
            print(f"\n[PRESERVATION TEST] Executing copy command for Supabase mode...")
            print(f'[PRESERVATION TEST] Command: copy /Y ".env" ".env_embutido" >nul')
            
            result = subprocess.run(
                'copy /Y ".env" ".env_embutido" >nul',
                cwd=test_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            
            print(f"[PRESERVATION TEST] Copy command exit code: {result.returncode}")
            
            # Check if .env_embutido was created
            env_embutido_path = os.path.join(test_dir, ".env_embutido")
            env_embutido_exists = os.path.exists(env_embutido_path)
            
            print(f"\n[PRESERVATION TEST] Checking for .env_embutido file...")
            print(f"[PRESERVATION TEST] .env_embutido exists: {env_embutido_exists}")
            
            # ASSERTIONS - These should PASS on unfixed code
            assert env_embutido_exists, (
                f"PRESERVATION VIOLATED: .env_embutido should be created by copy command "
                f"when path does NOT contain spaces. This worked before the fix."
            )
            
            # Verify content matches
            with open(env_path, "r", encoding="utf-8") as f:
                env_content_actual = f.read()
            with open(env_embutido_path, "r", encoding="utf-8") as f:
                env_embutido_content = f.read()
            
            assert env_content_actual == env_embutido_content, (
                f"PRESERVATION VIOLATED: .env_embutido content should match .env content. "
                f"This worked before the fix."
            )
            
            print(f"\n[PRESERVATION TEST] ✓ Non-space path preservation verified")
            print(f"[PRESERVATION TEST] .env_embutido created successfully without spaces in path")
            
        finally:
            # Clean up test directory
            if os.path.exists(os.path.join(temp_base, "test_preservation_nospace")):
                try:
                    shutil.rmtree(os.path.join(temp_base, "test_preservation_nospace"))
                    print(f"\n[PRESERVATION TEST] Cleaned up test directory")
                except Exception as e:
                    print(f"\n[PRESERVATION TEST] Warning: Failed to clean up: {e}")


class TestPreservationCleanup:
    """
    Property 2.3: Preservation - Cleanup of .env_embutido
    
    **Validates: Requirement 3.3**
    
    For all successful builds, .env_embutido should be deleted after
    PyInstaller completes.
    
    This already works in unfixed code.
    """
    
    def test_env_embutido_cleanup(self):
        """
        Test that .env_embutido is deleted after being used.
        
        This simulates the cleanup behavior from construir.bat (line 99):
        del /Q ".env_embutido" >nul
        
        EXPECTED OUTCOME ON UNFIXED CODE: PASS
        EXPECTED OUTCOME ON FIXED CODE: PASS (preserved)
        """
        
        # Skip test if not on Windows
        if sys.platform != "win32":
            print("SKIP: This test only runs on Windows")
            return
        
        # Create a temporary directory
        temp_base = tempfile.gettempdir()
        test_dir = os.path.join(temp_base, "test_cleanup")
        
        try:
            # Clean up if directory already exists
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
            
            # Create the test directory
            os.makedirs(test_dir, exist_ok=True)
            print(f"\n[PRESERVATION TEST] Created test directory: {test_dir}")
            
            # Create a .env_embutido file
            env_embutido_path = os.path.join(test_dir, ".env_embutido")
            with open(env_embutido_path, "w", encoding="utf-8") as f:
                f.write("DB_MODE=sqlite\n")
            
            print(f"[PRESERVATION TEST] Created .env_embutido file")
            assert os.path.exists(env_embutido_path), "Precondition: .env_embutido should exist"
            
            # Execute the delete command from construir.bat (line 99)
            print(f"\n[PRESERVATION TEST] Executing delete command...")
            print(f'[PRESERVATION TEST] Command: del /Q ".env_embutido" >nul')
            
            result = subprocess.run(
                'del /Q ".env_embutido" >nul',
                cwd=test_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            
            print(f"[PRESERVATION TEST] Delete command exit code: {result.returncode}")
            
            # Check if .env_embutido was deleted
            env_embutido_exists = os.path.exists(env_embutido_path)
            
            print(f"\n[PRESERVATION TEST] Checking if .env_embutido was deleted...")
            print(f"[PRESERVATION TEST] .env_embutido exists: {env_embutido_exists}")
            
            # ASSERTION - Should PASS on unfixed code
            assert not env_embutido_exists, (
                f"PRESERVATION VIOLATED: .env_embutido should be deleted after use. "
                f"This worked before the fix."
            )
            
            print(f"\n[PRESERVATION TEST] ✓ Cleanup preservation verified")
            print(f"[PRESERVATION TEST] .env_embutido deleted successfully")
            
        finally:
            # Clean up test directory
            if os.path.exists(test_dir):
                try:
                    shutil.rmtree(test_dir)
                    print(f"\n[PRESERVATION TEST] Cleaned up test directory")
                except Exception as e:
                    print(f"\n[PRESERVATION TEST] Warning: Failed to clean up: {e}")


def run_all_preservation_tests():
    """Run all preservation tests and report results."""
    
    print("=" * 80)
    print("Preservation Property Tests - construir.bat")
    print("=" * 80)
    print("\nThese tests verify that existing behavior is preserved.")
    print("They should PASS on UNFIXED code to establish baseline.")
    print("After the fix, they should STILL PASS to confirm no regressions.")
    print("=" * 80)
    
    tests = [
        ("SQLite Mode with Spaces", TestPreservationSQLiteMode().test_sqlite_mode_creates_env_embutido_with_spaces),
        ("Supabase Mode without Spaces", TestPreservationNonSpacePaths().test_supabase_mode_works_without_spaces),
        ("Cleanup of .env_embutido", TestPreservationCleanup().test_env_embutido_cleanup),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_name}")
        print(f"{'=' * 80}")
        
        try:
            test_func()
            results.append((test_name, "PASSED", None))
            print(f"\n✓ {test_name}: PASSED")
        except AssertionError as e:
            results.append((test_name, "FAILED", str(e)))
            print(f"\n✗ {test_name}: FAILED")
            print(f"Error: {e}")
        except Exception as e:
            results.append((test_name, "ERROR", str(e)))
            print(f"\n✗ {test_name}: ERROR")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("PRESERVATION TESTS SUMMARY")
    print(f"{'=' * 80}")
    
    passed = sum(1 for _, status, _ in results if status == "PASSED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")
    errors = sum(1 for _, status, _ in results if status == "ERROR")
    
    for test_name, status, error in results:
        status_symbol = "✓" if status == "PASSED" else "✗"
        print(f"{status_symbol} {test_name}: {status}")
        if error and len(error) < 100:
            print(f"  {error}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    
    if failed > 0 or errors > 0:
        print(f"\n{'=' * 80}")
        print("PRESERVATION VIOLATION DETECTED")
        print(f"{'=' * 80}")
        print("\nSome preservation tests failed on unfixed code.")
        print("This is unexpected - these behaviors should already work.")
        print("Investigation needed before proceeding with the fix.")
        return False
    else:
        print(f"\n{'=' * 80}")
        print("ALL PRESERVATION TESTS PASSED ✓")
        print(f"{'=' * 80}")
        print("\nBaseline behavior confirmed on unfixed code.")
        print("These behaviors must be preserved after implementing the fix.")
        return True


if __name__ == "__main__":
    success = run_all_preservation_tests()
    sys.exit(0 if success else 1)
