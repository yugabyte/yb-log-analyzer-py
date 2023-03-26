############################################################################################################
# Description: This file contains the dictionary of log messages and their solutions                       #
# regex_patterns is a dictionary of log messages and their regex patterns                                  #
# Where:                                                                                                    #
#   The key is the log message                                                                             #
#   The value is the regex pattern for the log message                                                     #               
# solutions is a dictionary of log messages and their solutions                                            #
# Where:                                                                                                    #  
#   The key is the log message                                                                             #
#   The value is the solution for the log message                                                          # 
# The keys in regex_patterns and solutions should be exactly the same                                      #
############################################################################################################

regex_patterns = {
    "Soft memory limit exceeded": r"Soft memory limit exceeded",
    "Number of aborted transactions not cleaned up on account of reaching size limits": r"Number of aborted transactions not cleaned up on account of reaching size limits",
    "Long wait for safe op id": r"Long wait for safe op id",
    "SST files limit exceeded": r"SST files limit exceeded",
    # Add more log messages here
}
solutions = {
    "Soft memory limit exceeded": """Memory utilization has reached `memory_limit_soft_percentage` (default 85%) and system has started throttling read/write operations.\n
    KB Article: https://support.yugabyte.com/hc/en-us/articles/360058731252-How-to-optimize-and-resolve-common-memory-errors-in-Yugabyte""",
    "Number of aborted transactions not cleaned up on account of reaching size limits": """This typically means that we need to run compaction on offending tablets \n
    Similar Zendesk ticket: https://yugabyte.zendesk.com/agent/tickets/5416""",
    "Long wait for safe op id": """Write on disk is slow. This could be because of slow disk or load on the system.""",
    "SST files limit exceeded": """Tablet has too many SST files. This could be because of slow compaction or load on the system.\n
    KB Article:https://support.yugabyte.com/hc/en-us/articles/4491328438413-Writes-failed-with-error-SST-files-limit-exceeded-"""
    # Add more solutions here
}