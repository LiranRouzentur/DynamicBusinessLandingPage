"""
Test validation regex for false positives
"""
import re

def test_inline_handler_detection():
    """Test the inline handler regex from pre_write_validator.py"""
    
    # The actual regex from our validator
    pattern = r'\bon(click|load|submit|change|focus|blur|mouseover|mouseout|keydown|keyup)\s*='
    
    # Test cases
    test_cases = [
        # Should MATCH (these are inline handlers in HTML - BAD)
        ('<button onclick="alert()">Click</button>', True, "HTML onclick attribute"),
        ('<img onload="validate()">', True, "HTML onload attribute"),
        ('<div onmouseover="highlight()">', True, "HTML onmouseover attribute"),
        ('<body onload="init()">', True, "HTML body onload"),
        
        # Should NOT MATCH (these are JavaScript code - OK)
        ('imageLoader.onload = function() {};', False, "JavaScript property assignment"),
        ('img.onload = () => {};', False, "JavaScript arrow function"),
        ('window.onload = function() {};', False, "JavaScript window.onload"),
        ('element.onclick = handleClick;', False, "JavaScript property assignment to variable"),
        
        # Edge cases
        ('<img src="test" onload="x()">', True, "Inline handler with other attributes"),
        ('addEventListener("load", fn)', False, "addEventListener call"),
        ('document.addEventListener("click", fn)', False, "addEventListener on document"),
    ]
    
    print("Testing inline handler regex...")
    print("=" * 70)
    
    failures = []
    for html, should_match, description in test_cases:
        matches = re.findall(pattern, html, re.IGNORECASE)
        did_match = bool(matches)
        
        status = "[PASS]" if did_match == should_match else "[FAIL]"
        
        print(f"{status} | {description}")
        print(f"  Input: {html[:60]}...")
        print(f"  Expected match: {should_match}, Got match: {did_match}")
        if matches:
            print(f"  Matched: {matches}")
        print()
        
        if did_match != should_match:
            failures.append({
                'description': description,
                'html': html,
                'expected': should_match,
                'got': did_match,
                'matches': matches
            })
    
    print("=" * 70)
    if failures:
        print(f"\n[FAILED] {len(failures)} TEST(S) FAILED:\n")
        for f in failures:
            print(f"FAILED: {f['description']}")
            print(f"  Input: {f['html']}")
            print(f"  Expected: {f['expected']}, Got: {f['got']}")
            print(f"  Matches: {f['matches']}\n")
        return False
    else:
        print("[SUCCESS] ALL TESTS PASSED!\n")
        return True


def test_real_world_html():
    """Test with actual HTML from logs"""
    
    print("\nTesting real-world HTML snippet...")
    print("=" * 70)
    
    # From the logs - this is what generator created
    html_snippet = """
    <script>
        imageLoader.onload = function() { checkImages(); };
        imageLoader.onerror = function() { 
            img.src = 'data:image/svg+xml,...'; 
            checkImages(); 
        };
    </script>
    """
    
    pattern = r'\bon(click|load|submit|change|focus|blur|mouseover|mouseout|keydown|keyup)\s*='
    matches = re.findall(pattern, html_snippet, re.IGNORECASE)
    
    print(f"HTML snippet:\n{html_snippet}\n")
    print(f"Pattern: {pattern}")
    print(f"Matches found: {matches}")
    
    if matches:
        print(f"\n[WARNING] REGEX MATCHED in JavaScript code (FALSE POSITIVE!)")
        print(f"   This is the problem - regex is matching 'onload' in JavaScript")
        print(f"   Word boundary \\b is not preventing this match")
        return False
    else:
        print(f"\n[OK] No matches (correct - this is JavaScript, not HTML attribute)")
        return True


def test_improved_regex():
    """Test an improved regex that avoids false positives"""
    
    print("\nTesting improved regex...")
    print("=" * 70)
    
    # Improved regex that looks for HTML attribute context
    # Match only when on* is in an HTML tag context
    improved_pattern = r'<[^>]*\s(on(?:click|load|submit|change|focus|blur|mouseover|mouseout|keydown|keyup))\s*='
    
    test_cases = [
        # Should MATCH
        ('<button onclick="alert()">Click</button>', True),
        ('<img onload="validate()">', True),
        ('<div onmouseover="highlight()">', True),
        
        # Should NOT MATCH
        ('imageLoader.onload = function() {};', False),
        ('img.onload = () => {};', False),
        ('window.onload = function() {};', False),
    ]
    
    print(f"Improved pattern: {improved_pattern}\n")
    
    failures = []
    for html, should_match in test_cases:
        matches = re.findall(improved_pattern, html, re.IGNORECASE)
        did_match = bool(matches)
        
        status = "[OK]" if did_match == should_match else "[X]"
        print(f"{status} {html[:50]}... => Match: {did_match} (expected: {should_match})")
        
        if did_match != should_match:
            failures.append((html, should_match, did_match))
    
    if failures:
        print(f"\n[FAILED] Improved regex still has issues")
        return False
    else:
        print(f"\n[SUCCESS] Improved regex works correctly!")
        return True


if __name__ == "__main__":
    print("=" * 70)
    print("VALIDATION REGEX ANALYSIS")
    print("=" * 70)
    print()
    
    result1 = test_inline_handler_detection()
    result2 = test_real_world_html()
    result3 = test_improved_regex()
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    print("=" * 70)
    print(f"Basic regex test: {'[PASS]' if result1 else '[FAIL]'}")
    print(f"Real-world HTML test: {'[PASS]' if result2 else '[FAIL]'}")
    print(f"Improved regex test: {'[PASS]' if result3 else '[FAIL]'}")
    
    if not result2:
        print("\n[ROOT CAUSE FOUND]:")
        print("   The validation regex is matching JavaScript code, not just HTML attributes!")
        print("   This is a FALSE POSITIVE - the generator's JavaScript is correct.")
        print("\n[SOLUTION]:")
        print("   Update the regex in pre_write_validator.py to only match HTML attribute context")

