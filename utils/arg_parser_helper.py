from argparse import RawTextHelpFormatter, ArgumentParser, ArgumentTypeError
from colorama import Fore, Style
import datetime
from pathlib import Path

class ColoredHelpFormatter(RawTextHelpFormatter):
    def _get_help_string(self, action):
        return Fore.GREEN + super()._get_help_string(action) + Style.RESET_ALL

    def _format_usage(self, usage, actions, groups, prefix):
        return Fore.YELLOW + super()._format_usage(usage, actions, groups, prefix) + Style.RESET_ALL

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return Fore.CYAN + metavar + Style.RESET_ALL
        else:
            parts = []
            if action.nargs == 0:
                parts.extend(action.option_strings)
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                parts.extend(action.option_strings)
                parts[-1] += ' ' + args_string
            return Fore.CYAN + ', '.join(parts) + Style.RESET_ALL

    def _format_action(self, action):
        parts = super()._format_action(action)
        return Fore.CYAN + parts + Style.RESET_ALL

    def _format_text(self, text):
        return Fore.MAGENTA + super()._format_text(text) + Style.RESET_ALL

    def _format_args(self, action, default_metavar):
        return Fore.LIGHTCYAN_EX + super()._format_args(action, default_metavar) + Style.RESET_ALL

# --- Custom Type Functions ---

def parse_datetime(time_str: str) -> datetime.datetime:
    """
    Parses a string in 'MMDD HH:MM' format into a datetime object.
    Raises ArgumentTypeError if the format is incorrect.
    """
    try:
        # Assuming the current year for the datetime object
        current_year = datetime.datetime.now().year
        # Add year to the format string for strptime
        return datetime.datetime.strptime(f"{current_year}{time_str}", "%Y%m%d %H:%M")
    except ValueError:
        raise ArgumentTypeError(f"Invalid time format: '{time_str}'. Expected 'MMDD HH:MM'.")

def parse_comma_separated_list(list_str: str) -> list[str]:
    """
    Parses a comma-separated string into a list of stripped strings.
    Returns an empty list if the input is None or empty.
    """
    if not list_str:
        return []
    return [item.strip() for item in list_str.split(',')]

# --- Argument Parsing Function ---

def parse_arguments():
    """Parses command-line arguments for the Log Analyzer."""

    # Using the standard HelpFormatter here, replace with ColoredHelpFormatter if needed
    # from your_module import ColoredHelpFormatter
    # formatter_class=ColoredHelpFormatter
    parser = ArgumentParser(
        description="Log Analyzer for YugabyteDB logs",
        # formatter_class=ColoredHelpFormatter # Uncomment if you have this class
    )

    # --- Input Source (Mutually Exclusive) ---
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-d", "--directory",
        type=Path, # Use pathlib.Path for directory validation
        help="Directory containing log files to analyze."
    )
    input_group.add_argument(
        "-s", "--support_bundle",
        type=Path, # Use pathlib.Path for file validation
        help="Path to the support bundle archive (e.g., .tar.gz) to analyze."
    )

    # --- Filtering and Configuration ---
    parser.add_argument(
        "--types",
        type=parse_comma_separated_list,
        default="pg,ts,ms", # Set default directly
        help="Comma-separated list of log types to analyze (e.g., 'ms,ybc'). Default: 'pg,ts,ms'."
    )
    parser.add_argument(
        "-n", "--nodes",
        type=parse_comma_separated_list,
        metavar="NODE1,NODE2,...",
        help="Comma-separated list of specific node names or IPs to analyze (e.g., 'n1,n2'). Analyzes all found nodes if omitted."
    )
    parser.add_argument(
        "-t", "--from_time",
        type=parse_datetime,
        dest="start_time",
        metavar="'MMDD HH:MM'",
        help="Analyze logs starting from this time (inclusive). Format: 'MMDD HH:MM'."
    )
    parser.add_argument(
        "-T", "--to_time",
        type=parse_datetime,
        dest="end_time",
        metavar="'MMDD HH:MM'",
        help="Analyze logs up to this time (exclusive). Format: 'MMDD HH:MM'."
    )
    parser.add_argument(
        "--histogram-mode",
        type=parse_comma_separated_list,
        dest="histogram_errors", # Renamed for clarity
        metavar="ERROR1,ERROR2,...",
        help="Generate histograms for the specified comma-separated list of error messages or patterns."
    )

    # --- Output and Execution ---
    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        metavar="FILE",
        type=Path, # Use pathlib.Path for output file path
        help="Optional path to write analysis results to a file."
    )
    parser.add_argument(
        "-p", "--parallel",
        metavar="N",
        dest='num_threads', # Renamed for clarity
        type=int,
        default=5,
        help="Number of threads to use for parallel processing. Default: 5."
    )
    parser.add_argument(
        "--skip_tar",
        action="store_true",
        help="If using --support_bundle, assume it's already extracted and skip decompression (useful if -d points inside an extracted bundle)."
    )

    args = parser.parse_args()

    # --- Post-Parsing Validation (Optional but sometimes needed) ---
    # Example: Check if start_time is before end_time
    if args.start_time and args.end_time and args.start_time >= args.end_time:
        parser.error("--from_time must be earlier than --to_time.")  # Use parser.error for clean exit

    # Example: Validate directory/file existence if Path didn't suffice
    if args.directory and not args.directory.is_dir():
        parser.error(f"Input directory not found or not a directory: {args.directory}")
    if args.support_bundle and not args.support_bundle.is_file():
        parser.error(f"Support bundle file not found: {args.support_bundle}")

    # Convert default string for --types if it wasn't overridden by the user
    if isinstance(args.types, str):
        args.types = parse_comma_separated_list(args.types)

    return args