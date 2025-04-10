import re
import os

# --- Constants ---
DUMP_DIR = "/home/support/logs_analyzer_dump/"
DUMP_DIR = "/Users/vidigalp/Code/tools/yb-log-analyzer-py/output_files"
INDEX_HTML_FILE = "index.html"
HOSTNAME_TRIGGER = "lincoln"

LINCOLN_HOSTNAME = "lincoln"
ANALYSIS_DUMP_DIR = "/home/support/logs_analyzer_dump/"
ANALYSIS_DUMP_DIR = "/Users/vidigalp/Code/tools/yb-log-analyzer-py/output_files"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates') # Assumes templates dir is one level up from utils

# Compile the regex pattern once for efficiency
REGEX_VERSION_PATTERN = re.compile(r'version\s+(\d+\.\d+\.\d+\.\d+)')
LINES_TO_CHECK = 10 # Number of lines to check at the beginning of each file
DEFAULT_VERSION = "Unknown"