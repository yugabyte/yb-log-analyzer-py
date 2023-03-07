# YugabyteDB log analyzer

## Objective:
Parsing and analyzing logs can be a time-consuming process, particularly when troubleshooting issues. Often, we have to go through large volumes of logs to identify patterns, symptoms, and common error messages.

To streamline this process, This script automates the analysis of logs, allowing users to quickly uncover any known findings that would otherwise take significant amounts of time. By doing so, we can save valuable time and effort, and potentially resolve issues more quickly.

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

