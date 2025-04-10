import re
import os
from typing import Optional, Pattern

if os.uname()[1] == "Pedros-MacBook-Pro.local":
    DUMP_DIR = "/Users/vidigalp/Code/tools/yb-log-analyzer-py/output_files"
else:
    DUMP_DIR = "/home/support/logs_analyzer_dump/"


## REGEX Patterns
_TICKET_ID_PATTERN: Pattern[str] = re.compile(r"cases[/\\](\d+)(?=[/\\]|$)")
