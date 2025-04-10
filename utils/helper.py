import re
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Pattern

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from config import _TICKET_ID_PATTERN

def extract_zendesk_ticket_id(path_string: str) -> Optional[int]:
    """
    Extracts a Zendesk ticket ID (a sequence of digits) from a directory path string.

    The function looks for a pattern where a directory named 'cases' is
    followed by a directory consisting only of digits.

    Args:
        path_string: The directory path string potentially containing the ticket ID.

    Returns:
        The extracted ticket ID as an integer if found, otherwise None.
    """
    if not path_string:
        return None

    match = _TICKET_ID_PATTERN.search(path_string)

    if match:
        # group(1) returns the content of the first capturing group (the digits)
        ticket_id_str = match.group(1)
        try:
            return int(ticket_id_str)
        except ValueError:
            # Should not happen with \d+ pattern, but good practice
            return None  # Or raise an error, depending on desired strictness
    else:
        return None



