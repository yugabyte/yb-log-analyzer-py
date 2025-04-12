import argparse
import datetime
import sys # For sys.exit
from typing import List, Optional, Any # For type hinting

# Assuming ColoredHelpFormatter exists elsewhere or replace with argparse.HelpFormatter
# from your_module import ColoredHelpFormatter
# For demonstration, using the standard formatter:
ColoredHelpFormatter = argparse.HelpFormatter

# --- Constants for Defaults ---
DEFAULT_LOG_TYPES = ['pg', 'ts', 'ms']
DEFAULT_PARALLEL_THREADS = 5
DATETIME_FORMAT = "%m%d %H:%M" # Define format string once

# --- Custom Type Validation Functions ---

def validate_datetime_format(time_str: str) -> datetime.datetime:
    """
    Validates if the input string matches the MMDD HH:MM format,
    assumes the current year, and returns a datetime object.

    Raises argparse.ArgumentTypeError if the format is incorrect.

    Note: This assumes the provided month/day belongs to the *current*
    calendar year. Be mindful of year boundaries if analyzing logs
    spanning New Year's Eve.
    """
    try:
        # Parse month, day, hour, minute (year defaults to 1900)
        parsed_dt = datetime.datetime.strptime(time_str, DATETIME_FORMAT)
        # Get the current year
        current_year = datetime.datetime.now().year
        # Create a new datetime object with the correct year
        final_dt = parsed_dt.replace(year=current_year)
        return final_dt
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid time format: '{time_str}'. Expected format: 'MMDD HH:MM'"
        )

def comma_separated_list(value: str) -> List[str]:
    """
    Splits a comma-separated string into a list of strings.
    Removes leading/trailing whitespace from each item.
    Filters out empty strings resulting from consecutive commas.
    """
    if not value:
        return []
    items = [item.strip() for item in value.split(',')]
    return [item for item in items if item] # Filter out empty strings

# --- Argument Parsing Function ---

def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for the YugabyteDB Log Analyzer.
    """
    parser = argparse.ArgumentParser(
        description="Log Analyzer for YugabyteDB logs",
        formatter_class=ColoredHelpFormatter # Use your custom formatter if available
    )

    # --- Input Source Arguments ---
    # Optional: If only one of directory or support_bundle should be allowed:
    # input_group = parser.add_mutually_exclusive_group(required=False) # Make required=True if one MUST be provided
    # input_group.add_argument(
    #     "-d", "--directory",
    #     help="Directory containing log files."
    # )
    # input_group.add_argument(
    #     "-s", "--support_bundle",
    #     help="Path to the support bundle file (e.g., .tar.gz)."
    # )
    # If both can be provided (or neither), use regular arguments:
    parser.add_argument(
        "-d", "--directory",
        help="Directory containing log files."
    )
    parser.add_argument(
        "-s", "--support_bundle",
        help="Path to the support bundle file (e.g., .tar.gz)."
    )
    parser.add_argument(
        "--skip_tar",
        action="store_true",
        help="Assume support bundle is already extracted (skip extraction)."
    )


    # --- Filtering Arguments ---
    parser.add_argument(
        "--types",
        metavar="TYPE1,TYPE2",
        type=comma_separated_list,
        default=DEFAULT_LOG_TYPES,
        help=(f"Comma-separated list of log types to analyze "
              f"(e.g., 'ms,ybc'). Default: {','.join(DEFAULT_LOG_TYPES)}")
    )
    parser.add_argument(
        "-n", "--nodes",
        metavar="NODE1,NODE2",
        type=comma_separated_list,
        default=None, # Default is to analyze all found nodes
        help="Comma-separated list of node names (or IP/IDs) to analyze (e.g., 'n1,n2')."
    )
    parser.add_argument(
        "-t", "--from_time",
        metavar="'MMDD HH:MM'",
        dest="start_time",
        type=validate_datetime_format, # Use custom type for validation
        help="Specify analysis start time (inclusive) in 'MMDD HH:MM' format (use quotes)."
    )
    parser.add_argument(
        "-T", "--to_time",
        metavar="'MMDD HH:MM'",
        dest="end_time",
        type=validate_datetime_format, # Use custom type for validation
        help="Specify analysis end time (exclusive) in 'MMDD HH:MM' format (use quotes)."
    )

    # --- Output Arguments ---
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        dest="output_file",
        help="Output file name to save analysis results."
    )

    # --- Performance Arguments ---
    parser.add_argument(
        "-p", "--parallel",
        metavar="N",
        dest='numThreads', # Keep original dest name if downstream code uses it
        type=int,
        default=DEFAULT_PARALLEL_THREADS,
        help=(f"Run analysis in parallel using N threads. "
              f"Default: {DEFAULT_PARALLEL_THREADS}")
    )

    # --- Analysis Mode Arguments ---
    parser.add_argument(
        "--histogram-mode",
        dest="histogram_errors", # Renamed for clarity, adjust if needed
        metavar="ERR1,ERR2",
        type=comma_separated_list,
        default=None,
        help=("Generate histograms for specific comma-separated errors "
              "(e.g., 'error1,error2,error3').")
    )

    args = parser.parse_args()

    # --- Post-Parsing Validation (Optional - if needed beyond type checks) ---
    # Example: Ensure at least one input source is provided if not using mutually exclusive group
    if not args.directory and not args.support_bundle:
         parser.error("Either --directory (-d) or --support_bundle (-s) must be specified.")

    # Example: Validate time range logic
    if args.start_time and args.end_time and args.start_time >= args.end_time:
        parser.error(f"--from_time ({args.start_time.strftime(DATETIME_FORMAT)}) must be before --to_time ({args.end_time.strftime(DATETIME_FORMAT)}).")

    return args