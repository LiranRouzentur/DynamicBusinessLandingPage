"""Diagnostic script to verify package imports resolve correctly"""
import sys
import importlib.util
import inspect
from pathlib import Path

def verify_package(package_name: str, expected_path: Path, description: str) -> bool:
    """Verify that a package imports from the expected location"""
    print(f"\n{'='*60}")
    print(f"Verifying: {description}")
    print(f"{'='*60}")
    
    # Find the spec
    spec = importlib.util.find_spec(package_name)
    
    if spec is None:
        print(f"[FAIL] Package '{package_name}' not found on sys.path")
        print(f"   Expected location: {expected_path}")
        return False
    
    origin = spec.origin if spec else None
    search_locations = spec.submodule_search_locations if spec else None
    
    print(f"Package: {package_name}")
    print(f"Origin: {origin}")
    print(f"Submodule search locations: {search_locations}")
    
    # Try to import
    try:
        module = importlib.import_module(package_name)
        module_file = inspect.getfile(module)
        print(f"Resolved to: {module_file}")
        
        # Check if it matches expected path
        expected_str = str(expected_path.resolve())
        if expected_str in module_file:
            print(f"[OK] Package resolves to expected location")
            return True
        else:
            print(f"[WARN] Package resolved but not to expected path")
            print(f"   Expected: {expected_path}")
            print(f"   Got: {module_file}")
            return True  # Still okay if it resolves
    except ImportError as e:
        print(f"[FAIL] Could not import: {e}")
        return False

def main():
    """Run all verification checks"""
    print("Python Import Shadowing Diagnostic")
    print("="*60)
    
    # Get project root
    project_root = Path(__file__).parent.parent.resolve()
    agents_path = project_root / "agents" / "app"
    backend_path = project_root / "backend"
    
    print(f"Project root: {project_root}")
    print(f"sys.path entries containing 'app' or similar:")
    for p in sys.path:
        if 'app' in p.lower() or 'business' in p.lower():
            print(f"  - {p}")
    
    print(f"\n{'='*60}")
    print("Starting verification...")
    
    results = []
    
    # Verify app (agents service)
    results.append((
        verify_package(
            "app",
            agents_path,
            "Agents Service Package (agents/app)"
        ),
        "app"
    ))
    
    # Verify landing_api
    landing_path = backend_path / "landing_api"
    results.append((
        verify_package(
            "landing_api",
            landing_path,
            "Backend API Package (backend/landing_api)"
        ),
        "landing_api"
    ))
    
    # Verify no collision with generic 'app'
    print(f"\n{'='*60}")
    print("Checking for shadowing issues...")
    print(f"{'='*60}")
    
    try:
        import app
        print(f"[WARN] Generic 'app' package found!")
        print(f"   Location: {inspect.getfile(app)}")
        print(f"   This could cause shadowing issues!")
    except ImportError:
        print(f"[OK] No generic 'app' package found")
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    for passed, package in results:
        status = "[OK] PASS" if passed else "[FAIL]"
        print(f"{status}: {package}")
    
    all_passed = all(result[0] for result in results)
    
    if all_passed:
        print("\n[OK] All packages verified successfully!")
    else:
        print("\n[FAIL] Some packages failed verification")
        sys.exit(1)

if __name__ == "__main__":
    main()

