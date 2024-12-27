import json
import trafilatura
from typing import Dict, Any, Union
from site2md.logging import logger

def extract_content(html: str, wants_json: bool = False) -> Union[str, Dict[str, Any]]:
    """Extract and convert HTML content to markdown or JSON

    Uses trafilatura to extract main content and metadata from HTML.
    Supports both markdown and structured JSON output.

    Args:
        html: Source HTML content
        wants_json: True for JSON output with metadata

    Returns:
        Union[str, Dict[str, Any]]: Markdown text or JSON dict
    """
    try:
        config = {
            'include_comments': False,
            'include_tables': True,
            'include_formatting': True,
            'include_links': True,
            'include_images': True,
            'with_metadata': True,
            'output_format': 'json' if wants_json else 'markdown',
            'favor_precision': True
        }

        if not (extracted := trafilatura.extract(html, **config)):
            logger.warning("No content extracted")
            return {} if wants_json else ""

        if wants_json and isinstance(extracted, str):
            try:
                return json.loads(extracted)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                return {}

        return extracted

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {} if wants_json else ""
