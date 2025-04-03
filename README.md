# YugabyteDB log analyzer

## Objective
Parsing and analyzing logs can be a time-consuming process, particularly when troubleshooting issues. Often, we have to go through large volumes of logs to identify patterns, symptoms, and common error messages.

To streamline this process, this script automates the analysis of logs, allowing users to quickly uncover any known findings that would otherwise take significant amounts of time. By doing so, we can save valuable time and effort, and potentially resolve issues more quickly.

## What's New
**Configuration Update:**  
The log analyzer now uses a YAML configuration file (`log_conf.yml`) instead of the previous `analyzer_dict.py`. This change allows you to easily manage and extend log message patterns and their corresponding solutions without modifying the code.

## Configuration File: `log_conf.yml`
The `log_conf.yml` file is organized into two main sections:
- **universe:** Contains log messages related to the YugabyteDB universe.
- **pg:** Contains log messages related to PostgreSQL.

Each section has a list of log message entries. Each entry has:
- **name:** A unique identifier for the log message.
- **pattern:** A regular expression pattern that is used to match the log message.
- **solution:** The markdown-formatted solution or troubleshooting tip associated with the log message.

### Example Entry
```yaml
universe:
  log_messages:
    - name: "Soft memory limit exceeded"
      pattern: "Soft memory limit exceeded"
      solution: |
        Memory utilization has reached `memory_limit_soft_percentage` (default 85%) and system has started throttling read/write operations.
        
        **NOTE**
        - If the number of occurrences of this message is low or happens only occasionally, it may not be a problem.
        **KB Article**: [How to optimize and resolve common memory errors in Yugabyte](https://support.yugabyte.com/hc/en-us/articles/360058731252-How-to-optimize-and-resolve-common-memory-errors-in-Yugabyte)
```

## Adding New Patterns

To add a new log message pattern, follow these steps:
1. Open the log_conf.yml file in your favorite text editor.

2. Decide which section the new pattern belongs to:
    - universe for YugabyteDB related log messages. 
    - pg for PostgreSQL related log messages. 

3. Add a new list item under the respective section’s log_messages list with the following keys:
    - name: A unique name/identifier for the log message. 
    - pattern: The regex pattern that will match the desired log message. 
    - solution: A markdown-formatted explanation or troubleshooting tip that will be displayed when the log message is detected.

    ### New Pattern Example
    ```yaml
    universe:
      log_messages:
        - name: "Database connection timeout"
          pattern: "Database connection timeout"
          solution: |
            This error indicates that the connection to the database timed out. 
            - Verify network connectivity.
            - Check if the database server is running and accepting connections.
            - Refer to the [Database Timeout Troubleshooting Guide](https://example.com/db-timeout-guide) for more details.
    
    If you want to add a new log message for “Database connection timeout”, you might add the following under the universe section:
    ```
   
4. Save the file after adding the new entry.

When you run the analyzer (e.g., via ./analyzer.py), the script will automatically load the updated patterns and solutions from log_conf.yml without requiring any code changes.

## Help

```bash
usage: analyzer.py [-h] [-l LOG_FILES [LOG_FILES ...]] [-d DIRECTORY] [--support_bundle SUPPORT_BUNDLE] [-H] [-wc] [-A] [-t MMDD HH:MM] [-T MMDD HH:MM] [-s {NO,LO,FO}]

Log Analyzer for YugabyteDB logs

options:
  -h, --help            show this help message and exit
  -l LOG_FILES [LOG_FILES ...], --log_files LOG_FILES [LOG_FILES ...]
                        List of log file[s]
  -d DIRECTORY, --directory DIRECTORY
                        Directory containing log files
  --support_bundle SUPPORT_BUNDLE
                        Path to support bundle
  -H, --histogram       Generate histogram graph
  -wc, --word_count     List top 20 word count
  -A, --ALL             FULL Health Check
  -t MMDD HH:MM, --from_time MMDD HH:MM
                        Specify start time
  -T MMDD HH:MM, --to_time MMDD HH:MM
                        Specify end time
  -s {NO,LO,FO}, --sort-by {NO,LO,FO}
                        Sort by: NO = Number of occurrences, LO = Last Occurrence, FO = First Occurrence(Default)
```

## Example
```
bash-5.1$ ./analyzer.py --log_file_path sample.log -H
╒═══════════════╤══════════════════════════════════════════════════════════════════════════════════╤══════════════════════╤══════════════════════╤═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╕
│   Occurrences │ Message                                                                          │ First Occurrence     │ Last Occurrence      │ Troubleshooting Tips                                                                                                                                                │
╞═══════════════╪══════════════════════════════════════════════════════════════════════════════════╪══════════════════════╪══════════════════════╪═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╡
│             9 │ Rejecting Write request: Soft memory limit exceeded                              │ 0623 14:45:05.379797 │ 0623 16:45:05.725900 │ This typically means that we have overloaded system.                                                                                                                │
│               │                                                                                  │                      │                      │     Check this KB for more details: https://support.yugabyte.com/hc/en-us/articles/4403688844045-Throttling-mechanism-in-YugaByte-TServer-due-to-high-Memory-Usage- │
├───────────────┼──────────────────────────────────────────────────────────────────────────────────┼──────────────────────┼──────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│             4 │ Number of aborted transactions not cleaned up on account of reaching size limits │ 0623 14:44:05.725900 │ 0623 16:49:05.725900 │ This typically means that we need to run compaction on offending tablets                                                                                            │
│               │                                                                                  │                      │                      │     Check this case for more details                                                                                                                                │
│               │                                                                                  │                      │                      │     https://yugabyte.zendesk.com/agent/tickets/5416                                                                                                                 │
╘═══════════════╧══════════════════════════════════════════════════════════════════════════════════╧══════════════════════╧══════════════════════╧═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╛

Histogram of logs creating time period

The count of 0623 14:4 is 5
The count of 0623 16:4 is 4
The count of 0623 15:4 is 4
bash-5.1$
``` 

