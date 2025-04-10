# utils/render.py

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Union, Optional
import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from config import DUMP_DIR

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




def get_analysis_date_from_path(relative_path: str) -> str | None:
  """
  Extracts the date and time from a specific filename pattern and formats it.

  The function expects a filename within the path that contains a date/time
  string in the format 'YYYY-MM-DD-HH-MM-SS' immediately followed by
  '_analysis.html'. It can handle optional prefixes before the date/time string.

  Args:
    relative_path: The string containing the filename (can be a full or relative path).
                     Examples: '13318-2025-04-10-15-27-48_analysis.html',
                               'results/2025-04-10-16-29-10_analysis.html'

  Returns:
    A formatted date and time string 'YYYY-MM-DD HH:MM:SS' if the
    pattern is found and represents a valid date/time.
    Returns None if the pattern is not found or the extracted string
    cannot be parsed into a valid date/time.
  """
  # Extract the filename from the path in case directories are included
  filename = os.path.basename(relative_path)

  # Regular expression to find the date/time pattern:
  # (\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}) : Captures the date/time string
  #   \d{4} : Year (4 digits)
  #   -       : Hyphen separator
  #   \d{2} : Month (2 digits)
  #   -       : Hyphen separator
  #   \d{2} : Day (2 digits)
  #   -       : Hyphen separator
  #   \d{2} : Hour (2 digits)
  #   -       : Hyphen separator
  #   \d{2} : Minute (2 digits)
  #   -       : Hyphen separator
  #   \d{2} : Second (2 digits)
  # _analysis\.html : Matches the literal string "_analysis.html" at the end
  #                   (the dot is escaped with \.)
  pattern = r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})_analysis\.html"

  match = re.search(pattern, filename)

  if match:
    datetime_str_hyphens = match.group(1) # Get the captured date/time string
    try:
      # Parse the string using its specific format with hyphens
      dt_object = datetime.datetime.strptime(datetime_str_hyphens, '%Y-%m-%d-%H-%M-%S')
      # Format the datetime object into the desired output string
      formatted_date = dt_object.strftime('%Y-%m-%d %H:%M:%S')
      return formatted_date
    except ValueError:
      # This might happen if the regex matches something that isn't a real date
      # (e.g., '2025-13-40-25-70-80'), although unlikely with this specific pattern.
      print(f"Warning: Matched string '{datetime_str_hyphens}' is not a valid date/time.")
      return None
  else:
    # The pattern was not found in the filename
    return None

def extract_zendesk_ticket_id(file_path_repr: str) -> str | None:
    """
    Extracts the Zendesk ticket ID from a file path string representation.

    The function expects the filename part of the path to start with a
    numeric Zendesk ticket ID followed by a hyphen.
    Example input format: "PosixPath('<any path>/13318-2025-04-10-15-27-48_analysis.html')"
    or just a path string like "/path/to/13318-..."

    Args:
        file_path_repr: A string representing the file path, potentially
                        like "PosixPath('/path/to/12345-....html')".

    Returns:
        The extracted Zendesk ticket ID (e.g., "13318") as a string,
        or None if the pattern is not found or the input is invalid.
    """
    if not isinstance(file_path_repr, str):
        return None # Input must be a string

    # Step 1: Handle potential PosixPath/WindowsPath string representation
    # Use regex to extract the actual path if it's wrapped.
    # This pattern looks for PosixPath('...') or WindowsPath('...')
    path_match = re.match(r"^(?:Posix|Windows)Path\('(.*)'\)$", file_path_repr)
    if path_match:
        actual_path = path_match.group(1)
    else:
        # Assume it's already a regular path string or just a filename
        actual_path = file_path_repr

    # Handle empty path edge case after potential extraction
    if not actual_path:
        return None

    # Step 2: Get the base filename from the path
    # os.path.basename correctly handles different path separators ('/' or '\')
    # and returns the input if it doesn't contain a separator.
    filename = os.path.basename(actual_path)

    # Step 3: Use regex to find the ticket ID at the start of the filename
    # ^      - matches the beginning of the string (filename)
    # (\d+)  - matches and captures one or more digits (the ticket ID)
    # -      - matches the literal hyphen immediately after the digits
    # .*     - matches any character (except newline) zero or more times (the rest of the filename)
    ticket_match = re.match(r"^(\d+)-.*", filename)

    if ticket_match:
        # If a match is found, group(1) contains the captured digits
        return ticket_match.group(1)
    else:
        # If the pattern doesn't match the start of the filename
        return None

def find_html_files(search_dir: Path) -> List[Path]:
    """
    Recursively finds all HTML files within a given directory.

    Args:
        search_dir: The Path object representing the directory to search.

    Returns:
        A list of Path objects, each pointing to an HTML file found.
        Returns an empty list if the directory doesn't exist or no HTML files are found.
    """
    if not search_dir.is_dir():
        logging.warning(f"Search directory does not exist or is not a directory: {search_dir}")
        return []

    html_files = list(search_dir.rglob('*.html'))
    logging.info(f"Found {len(html_files)} HTML file(s) in {search_dir}")
    return html_files

def prepare_template_data(
    html_files: List[Path],
    output_dir: Path
) -> List[Dict[str, Union[str, int, None]]]:
    """
    Prepares data for the Jinja2 template from a list of HTML file paths.

    Extracts ticket IDs and calculates relative paths for linking.

    Args:
        html_files: A list of Path objects for the HTML files.
        output_dir: The Path object representing the directory where the final
                    rendered HTML index file will be saved. This is used to
                    calculate correct relative paths for the links.

    Returns:
        A list of dictionaries, where each dictionary represents an analysis
        item with 'case_number' and 'filename' (relative path).
    """
    analysis_items = []
    for file_path in html_files:
        try:
            # Extract ticket ID using the helper function
            ticket_id = extract_zendesk_ticket_id(str(file_path))

            # Calculate the relative path from the output directory to the HTML file
            # This ensures links in the index.html work correctly.
            relative_path = os.path.relpath(file_path.resolve(), output_dir.resolve())

            analysis_date = get_analysis_date_from_path(relative_path)

            analysis_items.append({
                "case_number": ticket_id if ticket_id is not None else "N/A",
                "filename": relative_path,
                "analysis_date": analysis_date
            })
            logging.debug(f"Processed {file_path}: Ticket ID={ticket_id}, Relative Path={relative_path}")

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}", exc_info=True)
            # Optionally skip the file or add an error entry
            analysis_items.append({
                "case_number": "Error",
                "filename": str(file_path.name) # Fallback filename
            })

    # Sort items, e.g., by case number (treating 'N/A' appropriately if needed)
    analysis_items.sort(key=lambda item: str(item.get("case_number", "")))

    return analysis_items

def generate_index_html(
    source_dir_path: Union[str, Path] = DUMP_DIR,
    output_dir_path: Union[str, Path] = DUMP_DIR,
    output_filename: str = "index.html",
    template_path: Union[str, Path] = "templates/index.html.j2",
    title: str = "Log Analyser Index"
) -> bool:
    """
    Collects HTML files, renders them into a Jinja2 template, and saves the result.

    Args:
        source_dir_path: Path to the directory containing the HTML files to index.
        output_dir_path: Path to the directory where the rendered index HTML
                         file should be saved.
        output_filename: The name for the rendered HTML file (e.g., "index.html").
        template_path: Path to the Jinja2 template file relative to the project root.
                       Defaults to "templates/index.html.j2".
        title: The title to be used within the HTML template.

    Returns:
        True if the index HTML was generated successfully, False otherwise.
    """
    try:
        source_dir = Path(source_dir_path).resolve()
        output_dir = Path(output_dir_path).resolve()
        template_file = Path(template_path) # Keep relative for loader

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Ensured output directory exists: {output_dir}")

        # 1. Find HTML files
        html_files = find_html_files(source_dir)
        if not html_files:
            logging.warning(f"No HTML files found in {source_dir}. Index file will be empty.")
            # Decide if you still want to generate an empty index or return False
            # For now, we proceed to generate an index showing "No analysis files found."

        # 2. Prepare data for the template
        analysis_data = prepare_template_data(html_files, output_dir)

        # 3. Set up Jinja2 environment
        # Assume the script/caller is run from the project root
        # The loader path should be the directory *containing* the 'templates' folder
        # If template_path is "templates/index.html.j2", the loader needs the project root.
        project_root = Path(__file__).parent.parent # Assumes utils is one level down from root
        template_dir_abs = project_root / template_file.parent
        template_filename = template_file.name

        if not template_dir_abs.is_dir():
             logging.error(f"Template directory not found: {template_dir_abs}")
             # Try searching relative to current working directory as a fallback
             template_dir_abs = Path(template_file.parent).resolve()
             if not template_dir_abs.is_dir():
                 logging.error(f"Template directory also not found relative to CWD: {template_dir_abs}")
                 return False

        logging.info(f"Using template directory: {template_dir_abs}")
        logging.info(f"Looking for template file: {template_filename}")

        env = Environment(
            loader=FileSystemLoader(searchpath=template_dir_abs),
            autoescape=select_autoescape(['html', 'xml']) # Enable autoescaping
        )

        # 4. Load the template
        try:
            template = env.get_template(template_filename)
            logging.info(f"Successfully loaded template: {template_filename}")
        except TemplateNotFound:
            logging.error(f"Template not found: {template_filename} in {template_dir_abs}")
            return False
        except Exception as e:
            logging.error(f"Error loading template {template_filename}: {e}", exc_info=True)
            return False

        current_year = datetime.date.today().year

        # 5. Render the template
        rendered_html = template.render(
            title=title,
            analysis_items=analysis_data,
            current_year=current_year
        )
        logging.info("Template rendered successfully.")

        # 6. Save the rendered document
        output_file_path = output_dir / output_filename
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            logging.info(f"Successfully saved rendered HTML to: {output_file_path}")
            return True
        except IOError as e:
            logging.error(f"Failed to write output file {output_file_path}: {e}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during file writing: {e}", exc_info=True)
            return False

    except Exception as e:
        logging.error(f"An unexpected error occurred in generate_index_html: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    generate_index_html()
