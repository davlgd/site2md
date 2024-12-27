import pytest
from site2md.converter import extract_content

@pytest.mark.parametrize("html,expected", [
    ("""
    <html><body><h1>Test</h1></body></html>
    """, "Test"),
    ("""
    <html><body><p>Hello World</p></body></html>
    """, "Hello World"),
    ("""
    <html><body><article><h1>Title</h1><p>Content</p></article></body></html>
    """, "Title Content"),
])
def test_extract_markdown(html, expected):
    """Test markdown extraction with various HTML inputs"""
    result = extract_content(html)
    assert expected in result.replace('\n', ' ').replace('  ', ' ')

@pytest.mark.parametrize("html,expected_keys", [
    ("""
    <html>
        <head><title>Page</title><meta name="author" content="Test"/></head>
        <body><h1>Title</h1><p>Content</p></body>
    </html>
    """, ["title", "author"]),
    ("""
    <html><body><article><h1>Simple</h1><p>Text</p></article></body></html>
    """, ["text"]),
])
def test_extract_json(html, expected_keys):
    """Test JSON extraction with metadata"""
    result = extract_content(html, wants_json=True)
    assert isinstance(result, dict)
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"

def test_invalid_inputs():
    """Test handling of invalid inputs"""
    assert extract_content("") == ""
    assert extract_content("<invalid>") == ""
    assert extract_content(None, wants_json=True) == {}
    assert extract_content("<script>alert(1)</script>") == ""
