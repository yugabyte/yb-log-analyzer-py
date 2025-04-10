# tests/test_zendesk_utils.py

import pytest
from typing import Optional
from utils.helper import extract_zendesk_ticket_id

# 2. If your project is structured as a package, you might use relative imports:
#    (e.g., if root is 'my_package' containing 'zendesk_utils.py' and 'tests/')
# from ..zendesk_utils import extract_zendesk_ticket_id # Adjust as per your structure

# Test cases using pytest parametrize for cleaner code
@pytest.mark.parametrize(
    "test_desc, input_path, expected_id",
    [
        # === Provided Examples ===
        ("Standard Unix path with timestamp", '/Users/vidigalp/work/cases/13318/2025-03-04T21_08_33', 13318),
        ("Simple Unix path, ID at end", '/home/support/cases/7306', 7306),
        ("Simple Unix path with trailing component", '/home/support/cases/7306/2025-03-04T21_08_33', 7306),

        # === Additional Valid Cases ===
        ("Standard Windows path", 'C:\\my_work\\cases\\98765\\attachments', 98765),
        ("Windows path with forward slashes", 'C:/my_work/cases/54321/data.zip', 54321),
        ("Single digit ID", '/long/path/prefix/cases/1/file.txt', 1),
        ("ID with leading zeros", '/cases/007/details', 7), # int() handles leading zeros
        ("Relative path", 'cases/123/more', 123),
        ("ID at very end of relative path", 'cases/456', 456),
        ("Mixed separators", '/unix/path/cases\\789\\file', 789), # Handles mixed / and \

        # === Negative Cases (Should return None) ===
        ("No 'cases' directory", '/data/no_ticket_here/12345', None),
        ("'cases' part of another word (prefix)", '/data/processed_cases/12345', None),
        ("'cases' part of another word (suffix)", '/data/cases_suffix/12345', None),
        ("'cases' directory exists, no ID follows", '/data/cases/', None),
        ("'cases' followed by non-digits", '/data/cases/not_a_number/file.txt', None),
        ("ID number mixed with text (not separate component)", '/data/cases/12345_with_text', None),
        ("Missing separator after 'cases'", 'cases-12345', None),
        ("Empty string input", '', None),
        ("None input", None, None),
        ("Path with digits, but not after 'cases/' or 'cases\\'", '/home/user123/files/456', None),
        ("Non-digit component after 'cases'", '/home/support/cases/abc', None),
        ("Path ends exactly at 'cases'", '/home/support/cases', None),
    ]
)
def test_extract_zendesk_ticket_id(test_desc: str, input_path: Optional[str], expected_id: Optional[int]):
    """
    Tests the extract_zendesk_ticket_id function with various inputs.
    Args:
        test_desc: A description of the test case (for clearer reporting).
        input_path: The input path string to pass to the function.
        expected_id: The expected integer ID or None.
    """
    assert extract_zendesk_ticket_id(input_path) == expected_id, f"Failed: {test_desc}"

def test_extract_zendesk_ticket_id_long_path_and_id():
    """Tests with a very long path and a large ID."""
    long_path_segment = '/a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/u/v/w/x/y/z/'
    long_path = long_path_segment * 5 + 'cases/98765432109876543210/more/stuff'
    expected_long_id = 98765432109876543210
    assert extract_zendesk_ticket_id(long_path) == expected_long_id