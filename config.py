import re
import os
from typing import Optional, Pattern
from multiprocessing import cpu_count
import platform # Use platform module for system info
from dotenv import load_dotenv

load_dotenv()
DUMP_DIR = os.getenv("ANALYZER_DUMP_DIR", "/home/support/logs_analyzer_dump/") # Default is lincoln's default location

# --- Constants ---
DEFAULT_LOG_TYPES = ["pg", "ts", "ms"]
METADATA_CACHE_FILE = 'log_files_metadata.json'
ANALYZER_LOG_FILE = 'analyzer.log'
HAGEN_AI_JSON_FILE = "hagen_ai.json"
DEFAULT_PARALLELISM = max(1, cpu_count() // 2) # Sensible default based on cores


## REGEX Patterns
_TICKET_ID_PATTERN: Pattern[str] = re.compile(pattern=r"cases[/\\](\d+)(?=[/\\]|$)")

