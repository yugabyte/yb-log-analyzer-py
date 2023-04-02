############################################################################################################
# Description: This file contains the dictionary of log messages and their solutions                 
# regex_patterns is a dictionary of log messages and their regex patterns                            
# Where:                                                                                              
#   The key is the log message                                                                       
#   The value is the regex pattern for the log message                                                              
# solutions is a dictionary of log messages and their solutions                                      
# Where:                                                                                                
#   The key is the log message                                                                       
#   The value is the solution for the log message                                                     
# The keys in regex_patterns and solutions should be exactly the same
# Formatting:
#--------------------:------------------------------:--------------------------------------------------------
#   Block            : Description                  : Replaced with (Using python)
#--------------------:------------------------------:--------------------------------------------------------
#   $line-break$     : To insert line break         : <br>
#   $start-bold$     : Start bold characters        : <b>
#   $end-bold$       : End bold characters          : </b>
#   $start-italic$   : start italic characters      : <i>
#   $end-italic$     : end italic characters        : </i>
#   $start-code$     : start code characters        : <code>
#   $end-code$       : end code characters          : </code>
#   $tab$            : tab space                    : &nbsp;&nbsp;&nbsp;&nbsp;
#   $start-link$     : start link                   : <a href="
#   $end-link$       : end link                     : ' target='_blank'>
#   $end-link-text$  : end link text                : </a>
############################################################################################################

regex_patterns = {
    "Soft memory limit exceeded": r"Soft memory limit exceeded",
    "Number of aborted transactions not cleaned up on account of reaching size limits": r"Number of aborted transactions not cleaned up on account of reaching size limits",
    "Long wait for safe op id": r"Long wait for safe op id",
    "SST files limit exceeded": r"SST files limit exceeded",
    "Operation memory consumption has exceeded its limit": r"Operation failed.*operation memory consumption.*has exceeded"
    # Add more log messages here
}
solutions = {
    "Soft memory limit exceeded": """Memory utilization has reached $start-code$ `memory_limit_soft_percentage` $end-code$ (default 85%) and system has started throttling read/write operations.$line-break$
    $start-bold$ KB Article$end-bold$: $start-link$ https://support.yugabyte.com/hc/en-us/articles/360058731252-How-to-optimize-and-resolve-common-memory-errors-in-Yugabyte $end-link$ How to optimize and resolve common memory errors in Yugabyte $end-link-text$""",
    "Number of aborted transactions not cleaned up on account of reaching size limits": """This typically means that we need to run compaction on offending tablets $line-break$
    $start-bold$ Zendesk ticket:$end-bold$ 5416""",
    "Long wait for safe op id": """Write on disk is slow. This could be because of slow disk or load on the system.""",
    "SST files limit exceeded": """Tablet has too many SST files. This could be because of slow compaction or load on the system.$line-break$
    $start-bold$ KB Article$end-bold$: $start-link$ https://support.yugabyte.com/hc/en-us/articles/4491328438413-Writes-failed-with-error-SST-files-limit-exceeded-$end-link$ Writes failed with error "SST files limit exceeded"
 $end-link-text$""",
    "Operation memory consumption has exceeded its limit": """We have an operation memory limit set to 1024 MB (Default) per tablet using $start-code$ tablet_operation_memory_limit_mb $end-code$.
    We hit this issue if we have a hot shard and we keep hitting the same shard at a time at full throttle rather than spreading the workload.$line-break$
    $start-bold$ Useful Commands: $end-bold$ $line-break$
    $tab$ - Get the list of tablets hitting this issue.$line-break$
    $tab$ $tab$ $start-code$ grep "operation memory consumption" <logfile>| awk '{print "T:", $6, "P:", $8}' | sort | uniq$end-code$ """
    # Add more solutions here
}