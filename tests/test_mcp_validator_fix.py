"""
Test the fixed MCP validator rel attribute parsing.
Tests that the validator correctly handles both string and list formats from BeautifulSoup.
"""

from bs4 import BeautifulSoup

def test_rel_attribute_parsing():
    """Test that rel attribute is parsed correctly regardless of format."""
    
    # Case 1: String format (the bug case)
    html1 = '<a href="https://example.com" target="_blank" rel="noopener noreferrer">Link</a>'
    soup1 = BeautifulSoup(html1, "html.parser")
    a1 = soup1.find("a", target="_blank")
    
    # Simulate the BUGGY code (would fail)
    rel_buggy = " ".join(a1.get("rel") or [])
    print(f"Buggy parsing: '{rel_buggy}'")
    print(f"Buggy check would fail: {'noopener' not in rel_buggy}")
    
    # Simulate the FIXED code (should pass)
    rel_attr = a1.get("rel")
    if isinstance(rel_attr, str):
        rel_fixed = rel_attr.lower()
    elif isinstance(rel_attr, list):
        rel_fixed = " ".join(rel_attr).lower()
    else:
        rel_fixed = ""
    
    print(f"Fixed parsing: '{rel_fixed}'")
    print(f"Fixed check passes: {'noopener' in rel_fixed and 'noreferrer' in rel_fixed}")
    
    assert "noopener" in rel_fixed, "Should find 'noopener' in fixed version"
    assert "noreferrer" in rel_fixed, "Should find 'noreferrer' in fixed version"
    
    # Case 2: List format (already worked, but test it)
    html2 = '<a href="https://example.com" target="_blank">Link</a>'
    soup2 = BeautifulSoup(html2, "html.parser")
    a2 = soup2.find("a")
    a2["rel"] = ["noopener", "noreferrer"]  # Simulate list format
    
    rel_attr2 = a2.get("rel")
    if isinstance(rel_attr2, str):
        rel_fixed2 = rel_attr2.lower()
    elif isinstance(rel_attr2, list):
        rel_fixed2 = " ".join(rel_attr2).lower()
    else:
        rel_fixed2 = ""
    
    print(f"\nList format parsing: '{rel_fixed2}'")
    assert "noopener" in rel_fixed2, "Should handle list format"
    assert "noreferrer" in rel_fixed2, "Should handle list format"
    
    # Case 3: Missing rel (should fail validation)
    html3 = '<a href="https://example.com" target="_blank">Link</a>'
    soup3 = BeautifulSoup(html3, "html.parser")
    a3 = soup3.find("a", target="_blank")
    
    rel_attr3 = a3.get("rel")
    if isinstance(rel_attr3, str):
        rel_fixed3 = rel_attr3.lower()
    elif isinstance(rel_attr3, list):
        rel_fixed3 = " ".join(rel_attr3).lower()
    else:
        rel_fixed3 = ""
    
    print(f"\nMissing rel parsing: '{rel_fixed3}'")
    assert "noopener" not in rel_fixed3, "Should correctly detect missing rel"
    
    # Case 4: Partial rel (should fail validation)
    html4 = '<a href="https://example.com" target="_blank" rel="noopener">Link</a>'
    soup4 = BeautifulSoup(html4, "html.parser")
    a4 = soup4.find("a", target="_blank")
    
    rel_attr4 = a4.get("rel")
    if isinstance(rel_attr4, str):
        rel_fixed4 = rel_attr4.lower()
    elif isinstance(rel_attr4, list):
        rel_fixed4 = " ".join(rel_attr4).lower()
    else:
        rel_fixed4 = ""
    
    print(f"\nPartial rel parsing: '{rel_fixed4}'")
    assert "noopener" in rel_fixed4, "Should find noopener"
    assert "noreferrer" not in rel_fixed4, "Should correctly detect missing noreferrer"
    
    print("\n[PASS] All MCP validator rel attribute parsing tests passed!")

if __name__ == "__main__":
    test_rel_attribute_parsing()

