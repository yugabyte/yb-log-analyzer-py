# utils/helper.py
import os
import gzip
import shutil
import logging
from typing import List, Dict, Optional, Tuple, Iterable
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import LINES_TO_CHECK, REGEX_VERSION_PATTERN, DEFAULT_VERSION, TEMPLATE_DIR, ANALYSIS_DUMP_DIR

# Configure logging (assuming a logger might be passed or configured elsewhere)
logger = logging.getLogger(__name__)
# Basic configuration if run standalone or logger not configured externally
#if not logger.hasHandlers():
#    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---


# --- Jinja2 Environment Setup ---
try:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(['html', 'xml'])
    )
except Exception as e:
    logger.error(f"Failed to initialize Jinja2 environment. Check TEMPLATE_DIR: {TEMPLATE_DIR}. Error: {e}")
    env = None # Indicate failure

# --- Helper Functions ---

def get_hostname() -> str:
    """
    Gets the hostname of the current machine.

    Returns:
        str: The system's hostname.
    """
    return os.uname()[1] # platform.node() is another good option

def get_case_number_from_path(log_dir: str) -> Optional[str]:
    """
    Extracts the case number from a specific directory path structure.
    Assumes the case number is the third component (index 2) when split by '/'.

    Args:
        log_dir (str): The absolute path to the log directory.
                       Example: /basedir/casenumber/somedir

    Returns:
        Optional[str]: The extracted case number, or None if the path
                       structure is not as expected.
    """
    try:
        parts = log_dir.strip('/').split('/')
        if len(parts) > 2:
            return parts[1] # Index 1 if leading '/' is stripped, index 2 otherwise. Adjust if needed.
        else:
            logger.warning(f"Could not extract case number: Path '{log_dir}' does not have enough components.")
            return None
    except Exception as e:
        logger.error(f"Error extracting case number from path '{log_dir}': {e}")
        return None

def get_case_number_from_filename(filename: str) -> Optional[str]:
    """
    Extracts the case number from a filename assuming 'caseNumber-...' format.

    Args:
        filename (str): The filename string. Example: "12345-analysis.html"

    Returns:
        Optional[str]: The extracted case number (e.g., "12345"), or None if
                       the format is not matched or '-' is not present.
    """
    if '-' in filename:
        return filename.split('-', 1)[0]
    else:
        logger.warning(f"Could not extract case number: Filename '{filename}' does not contain '-'.")
        return None

def copy_analysis_file(source_file: str, case_number: str, dest_dir: str = ANALYSIS_DUMP_DIR) -> Optional[str]:
    """
    Copies the analysis file to the specified destination directory,
    prepending the case number to the filename.

    Args:
        source_file (str): The path to the source analysis file.
        case_number (str): The case number to prepend to the filename.
        dest_dir (str): The destination directory. Defaults to ANALYSIS_DUMP_DIR.

    Returns:
        Optional[str]: The full path to the copied file in the destination,
                       or None if the copy fails.
    """
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return None
    if not os.path.isdir(dest_dir):
        logger.error(f"Destination directory does not exist: {dest_dir}")
        # Optionally, try to create it:
        # try:
        #     os.makedirs(dest_dir, exist_ok=True)
        #     logger.info(f"Created destination directory: {dest_dir}")
        # except OSError as e:
        #     logger.error(f"Failed to create destination directory {dest_dir}: {e}")
        #     return None
        return None # Return None if directory doesn't exist and isn't created

    base_filename = os.path.basename(source_file)
    dest_filename = f"{case_number}-{base_filename}"
    dest_path = os.path.join(dest_dir, dest_filename)

    try:
        shutil.copy2(source_file, dest_path) # copy2 preserves metadata
        logger.info(f"Successfully copied '{source_file}' to '{dest_path}'")
        return dest_path
    except Exception as e:
        logger.error(f"Failed to copy '{source_file}' to '{dest_path}': {e}")
        return None

def get_analysis_items(directory: str = ANALYSIS_DUMP_DIR) -> List[Dict[str, str]]:
    """
    Scans a directory for HTML files and extracts case numbers from filenames.

    Args:
        directory (str): The directory to scan. Defaults to ANALYSIS_DUMP_DIR.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, where each dictionary
                               contains 'case_number' and 'filename'.
                               Returns an empty list if the directory doesn't exist
                               or no suitable files are found.
    """
    analysis_items = []
    if not os.path.isdir(directory):
        logger.warning(f"Analysis directory not found: {directory}")
        return []

    try:
        for filename in os.listdir(directory):
            if filename.endswith(".html") and filename != "index.html":
                case_num = get_case_number_from_filename(filename)
                if case_num:
                    analysis_items.append({
                        "case_number": case_num,
                        "filename": filename
                    })
                else:
                     logger.warning(f"Could not parse case number from file: {filename} in {directory}")
        # Sort items, e.g., by case number (optional)
        analysis_items.sort(key=lambda x: x.get('case_number', ''))
    except Exception as e:
        logger.error(f"Error listing or processing files in directory '{directory}': {e}")
        return [] # Return empty list on error

    return analysis_items


def generate_index_html(analysis_items: List[Dict[str, str]],
                        output_dir: str = ANALYSIS_DUMP_DIR,
                        template_name: str = "index.html.j2",
                        title: str = "List of analyzed files") -> bool:
    """
    Generates an index.html file from a template and analysis data.

    Args:
        analysis_items (List[Dict[str, str]]): Data for the template.
        output_dir (str): Directory where index.html will be saved. Defaults to ANALYSIS_DUMP_DIR.
        template_name (str): The name of the Jinja2 template file.
        title (str): The title to be used in the generated HTML.

    Returns:
        bool: True if the index.html was generated successfully, False otherwise.
    """
    if env is None:
        logger.error("Jinja2 environment not initialized. Cannot generate HTML.")
        return False
    if not os.path.isdir(output_dir):
        logger.error(f"Output directory does not exist: {output_dir}")
        return False # Cannot write the file

    index_file_path = os.path.join(output_dir, "index.html")
    context = {
        "title": title,
        "analysis_items": analysis_items
    }

    try:
        template = env.get_template(template_name)
        html_content = template.render(context)
        with open(index_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Successfully generated index file: {index_file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate index file '{index_file_path}' using template '{template_name}': {e}")
        return False

def find_version_in_logs(file_paths: Iterable[str], logger: logging.Logger) -> str:
    """
    Searches for the first version string (format d.d.d.d) within the
    first few lines of a sequence of log files.

    It processes files sequentially based on the iterable order and stops
    scanning as soon as a version string matching the pattern is found in
    the first 'LINES_TO_CHECK' lines of any file. It handles both plain
    text and gzipped (.gz) files.

    Args:
        file_paths: An iterable (e.g., list, generator) of strings, where
                    each string is a path to a log file to be checked.
        logger: A configured logging.Logger instance used for logging
                warnings, errors, and informational messages during processing.

    Returns:
        The first version string found (e.g., "1.2.3.4").
        Returns "Unknown" if no version string is found in the initial
        lines of any of the processed files, if the iterable is empty,
        or if errors prevent checking the relevant lines.

    Raises:
        This function aims to handle common file-related exceptions internally
        (e.g., FileNotFoundError, PermissionError, IsADirectoryError,
        gzip errors, UnicodeDecodeError) by logging a warning/error and
        skipping the problematic file. Unexpected exceptions might still
        propagate.
    """
    logger.info(f"Attempting to find version in {LINES_TO_CHECK} lines of provided files...")

    for file_path in file_paths:
        logger.debug(f"Checking file: {file_path}")
        found_version: Optional[str] = None
        try:
            # Determine the correct opener and mode based on file extension
            is_gzipped = file_path.endswith('.gz')
            opener = gzip.open if is_gzipped else open
            # Always open in text mode ('rt') and specify encoding
            # Use 'errors=ignore' or 'errors=replace' to handle potential bad bytes,
            # otherwise UnicodeDecodeError might occur more often.
            mode = "rt"
            encoding = "utf-8" # Or latin-1, or another appropriate encoding
            errors = "ignore" # Be explicit about handling decoding errors

            with opener(file_path, mode=mode, encoding=encoding, errors=errors) as log_file:
                # Efficiently read and check the first LINES_TO_CHECK lines
                for i, line in enumerate(log_file):
                    if i >= LINES_TO_CHECK:
                        logger.debug(f"Checked {LINES_TO_CHECK} lines in {file_path}, version not found yet.")
                        break # Stop reading this file

                    match = REGEX_VERSION_PATTERN.search(line)
                    if match:
                        found_version = match.group(1)
                        logger.info(f"Found version '{found_version}' in file: {file_path} (line {i+1})")
                        return found_version # Exit function immediately upon finding the first version

        except FileNotFoundError:
            logger.warning(f"File not found: '{file_path}', skipping.")
            continue # Move to the next file path
        except IsADirectoryError:
            logger.warning(f"Path is a directory, not a file: '{file_path}', skipping.")
            continue
        except PermissionError:
            logger.warning(f"Permission denied for file: '{file_path}', skipping.")
            continue
        except (gzip.BadGzipFile, EOFError) as e: # Catch gzip specific errors
             logger.warning(f"Error reading gzip file '{file_path}': {e}, skipping.")
             continue
        except UnicodeDecodeError as e:
            # Should be less common with errors='ignore'/'replace', but good practice
            logger.warning(f"Unicode decode error in file '{file_path}' (even with error handling): {e}, skipping.")
            continue
        except Exception as e:
            # Catch any other unexpected errors during file processing
            logger.error(f"Unexpected error processing file '{file_path}': {e}", exc_info=True)
            continue # Skip to the next file

    # If the loop completes without returning a found version
    logger.info(f"Version pattern not found in the first {LINES_TO_CHECK} lines of any processed file.")
    return DEFAULT_VERSION