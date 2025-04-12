import re

# Existing patterns...
LOG_PARSE_PATTERN = re.compile(
    r"(?P<log_level>[IWEF])(?P<month_day>\d{4}) (?P<time>\d{2}:\d{2}:\d{2}\.\d{6}) (?P<threadid>\d+) (?P<file_line>[\w\.]+:\d+)\] (?P<msg>.+)"
)
METRIC_PATTERN = re.compile(r"([\d\.]+)\s?(GB|MB|KB|ms|secs|blks|kb|bytes|MHz|GHz)")

# Patterns for the header...
HEADER_DATE_PATTERN = re.compile(r"Log file created at: (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
HEADER_MACHINE_PATTERN = re.compile(r"Running on machine: ([\w\.\-]+)")
HEADER_FINGERPRINT_PATTERN = re.compile(r"Application fingerprint: (.+)")
HEADER_YEAR_PATTERN = re.compile(r"Log file created at: (\d{4})")