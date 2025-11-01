"""
Test the fixed pre_write_validator with real-world HTML
"""
import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))

from app.core.pre_write_validator import validate_generator_output_structure


def test_javascript_code_not_flagged():
    """Test that correct JavaScript code is not flagged as inline handler"""
    
    # This is what the generator produces - CORRECT JavaScript!
    gen_out = {
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Test</title>
</head>
<body>
    <h1>Test Page</h1>
    <img src="test.jpg" alt="Test">
    
    <script>
    // This is CORRECT JavaScript - should NOT be flagged
    document.addEventListener('DOMContentLoaded', function() {
        const images = document.querySelectorAll('img');
        images.forEach((img) => {
            const imageLoader = new Image();
            imageLoader.onload = function() { console.log('loaded'); };
            imageLoader.onerror = function() { console.log('error'); };
            imageLoader.src = img.src;
        });
        
        window.onload = function() { console.log('window loaded'); };
    });
    </script>
</body>
</html>"""
    }
    
    is_valid, errors = validate_generator_output_structure(gen_out)
    
    print("Test: JavaScript property assignments should NOT be flagged")
    print("=" * 70)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    else:
        print("No errors (correct!)")
    print()
    
    assert is_valid, f"Should be valid! Errors: {errors}"
    print("[PASS] JavaScript code was correctly allowed!\n")


def test_html_inline_handlers_are_flagged():
    """Test that actual inline HTML handlers ARE flagged"""
    
    # This has INLINE HANDLERS in HTML - should be FLAGGED
    gen_out = {
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Test</title>
</head>
<body>
    <h1>Test Page</h1>
    <button onclick="alert('clicked')">Click Me</button>
    <img src="test.jpg" alt="Test" onload="console.log('loaded')">
</body>
</html>"""
    }
    
    is_valid, errors = validate_generator_output_structure(gen_out)
    
    print("Test: HTML inline handlers SHOULD be flagged")
    print("=" * 70)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    else:
        print("No errors")
    print()
    
    assert not is_valid, "Should be INVALID (has inline handlers)"
    assert any("SECURITY VIOLATION" in e for e in errors), "Should have security violation error"
    print("[PASS] Inline HTML handlers were correctly blocked!\n")


def test_mixed_case():
    """Test with both JavaScript (OK) and HTML inline handler (BAD)"""
    
    gen_out = {
        "html": """<!DOCTYPE html>
<html>
<body>
    <button onclick="bad()">Bad Button</button>
    <script>
    // This JavaScript is fine
    img.onload = function() { good(); };
    </script>
</body>
</html>"""
    }
    
    is_valid, errors = validate_generator_output_structure(gen_out)
    
    print("Test: Mixed case - JavaScript OK, HTML inline handler BAD")
    print("=" * 70)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    print()
    
    assert not is_valid, "Should be invalid due to HTML inline handler"
    assert any("onclick" in e.lower() for e in errors), "Should mention onclick"
    print("[PASS] Correctly detected HTML inline handler while allowing JavaScript!\n")


if __name__ == "__main__":
    print("=" * 70)
    print("TESTING FIXED PRE-WRITE VALIDATOR")
    print("=" * 70)
    print()
    
    try:
        test_javascript_code_not_flagged()
        test_html_inline_handlers_are_flagged()
        test_mixed_case()
        
        print("=" * 70)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("The validator now correctly:")
        print("  1. Allows JavaScript property assignments (imageLoader.onload)")
        print("  2. Blocks HTML inline handlers (<button onclick='...'>)")
        print("  3. Distinguishes between the two contexts")
        print()
        print("The build should now succeed!")
        
    except AssertionError as e:
        print("=" * 70)
        print(f"[FAIL] Test failed: {e}")
        print("=" * 70)
        sys.exit(1)

