import os
import sys
import pytest
from site2md.logging import setup_logger

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def setup_logging():
    setup_logger(level="DEBUG")

@pytest.fixture
def sample_html():
    return """
    <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Test Title</h1>
            <p>Test content</p>
        </body>
    </html>
    """
