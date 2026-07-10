"""
test_environment.py — Verify Python environment is ready for Phase 2 development.

This script checks that all required dependencies are installed and importable.

Usage:
    python test_environment.py

Expected output:
    ✓ All dependencies imported successfully
    ✗ Missing dependencies with installation instructions
"""

import sys
from importlib import import_module


def test_import(module_name: str, display_name: str = None) -> bool:
    """Test importing a module and report the result."""
    if display_name is None:
        display_name = module_name
    
    try:
        module = import_module(module_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"  ✓ {display_name:<25} (v{version})")
        return True
    except ImportError as e:
        print(f"  ✗ {display_name:<25} MISSING: {e}")
        return False


def main():
    """Test all Phase 2 dependencies."""
    print("\n" + "=" * 70)
    print("PHASE 2 ENVIRONMENT VERIFICATION")
    print("=" * 70 + "\n")
    
    print("Testing core dependencies:\n")
    
    dependencies = [
        # (module_name, display_name)
        ('serial', 'pyserial'),
        ('pyshimmer', 'pyshimmer'),
        ('pylsl', 'pylsl (LSL)'),
        ('numpy', 'numpy'),
        ('scipy', 'scipy'),
        ('pytest', 'pytest'),
    ]
    
    results = []
    for module_name, display_name in dependencies:
        results.append(test_import(module_name, display_name))
    
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("-" * 70)
    print(f"Results: {passed}/{total} dependencies available\n")
    
    if passed == total:
        print("✓ Environment verification PASSED")
        print("\nAll required dependencies are installed.")
        print("You can proceed with Phase 2 implementation.")
        
        # Additional pyshimmer info
        try:
            import pyshimmer
            print(f"\npyshimmer version: {pyshimmer.__version__ if hasattr(pyshimmer, '__version__') else 'unknown'}")
            
            # Check for Shimmer3R support
            from pyshimmer.dev.revisions import Shimmer3RRevision, RevisionRegistry, HardwareVersion
            print("✓ Shimmer3R revision class found")
            
            # Try to get the revision
            try:
                rev = RevisionRegistry.get_revision(HardwareVersion.SHIMMER3R)
                print(f"✓ Shimmer3R revision registered: {rev}")
            except Exception as e:
                print(f"⚠ Shimmer3R revision lookup failed: {e}")
                
        except ImportError:
            pass
        
        return 0
    else:
        print("✗ Environment verification FAILED")
        print("\nMissing dependencies. Install with:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        print("  pip install pyshimmer pyserial pylsl numpy scipy pytest")
        return 1


if __name__ == '__main__':
    sys.exit(main())
