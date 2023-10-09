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
#   - Solution should be in markdown format
#   - Please do not use <variable> in the solution as it will be considered as html tags and will not be displayed rather use $variable
############################################################################################################

regex_patterns = {
    "Soft memory limit exceeded": r"Soft memory limit exceeded",
    "Number of aborted transactions not cleaned up on account of reaching size limits": r"Number of aborted transactions not cleaned up on account of reaching size limits",
    "Long wait for safe op id": r"Long wait for safe op id",
    "SST files limit exceeded": r"SST files limit exceeded",
    "Operation memory consumption has exceeded its limit": r"Operation failed.*operation memory consumption.*has exceeded",
    "Too big clock skew is detected":r"Too big clock skew is detected",
    "Stopping writes because we have immutable memtables":r"Stopping writes because we have \d+ immutable memtables",
    "UpdateConsensus requests dropped due to backpressure":r"UpdateConsensus request.*dropped due to backpressure",
    "Fail of leader detected":r"Fail of leader.*detected",
    "Can't advance the committed index across term boundaries until operations from the current term are replicated":r"Can't advance the committed index across term boundaries until operations from the current term are replicated"
    # Add more log messages here
}
solutions = {
    "Soft memory limit exceeded": """Memory utilization has reached `memory_limit_soft_percentage` (default 85%) and system has started throttling read/write operations.  
        **KB Article**: [How to optimize and resolve common memory errors in Yugabyte](https://support.yugabyte.com/hc/en-us/articles/360058731252-How-to-optimize-and-resolve-common-memory-errors-in-Yugabyte)
        """,
    "Number of aborted transactions not cleaned up on account of reaching size limits": """This typically means that we need to run compaction on offending tablets.  
        **Zendesk ticket**: 5416
        """,
    "Long wait for safe op id": """Write on disk is slow. This could be because of slow disk or load on the system.
        """,
    "SST files limit exceeded": """Tablet has too many SST files. This could be because of slow compaction or load on the system.  
        **KB Article**: [Writes failed with error "SST files limit exceeded"](https://support.yugabyte.com/hc/en-us/articles/4491328438413-Writes-failed-with-error-SST-files-limit-exceeded-)
        """,
    "Operation memory consumption has exceeded its limit": """We have an operation memory limit set to 1024 MB (Default) per tablet using `tablet_operation_memory_limit_mb`. We hit this issue if we have a hot shard and we keep hitting the same shard at a time at full throttle rather than spreading the workload.  
        **Useful Commands**:  
            - Get the list of tablets hitting this issue.  
            ```
            grep "operation memory consumption" logfile| awk '{print "T:", $6, "P:", $8}' | sort | uniq
            ```
        """,
    "Too big clock skew is detected": """This error indicates the nodes running tserver/master process are having clock skew outside of an acceptable range. Clock skew and clock drift can lead to significant consistency issues and should be fixed as soon as possible.  
        **KB Article**: [Too big clock skew leading to error messages or tserver crashes](https://support.yugabyte.com/hc/en-us/articles/4403707404173-Too-big-clock-skew-leading-to-error-messages-or-tserver-crashes)
        """,
    "Stopping writes because we have immutable memtables":"""This message is generally observed when a tablet has immutable memtables which need to flush to disk. It generally indicates that the application is writing at rate, and YB is not able to write the data to disk at the same speed, as the disk may be slow.  
        **KB Article**: [Stopping writes because we have immutable memtables (waiting for flush)](https://support.yugabyte.com/hc/en-us/articles/14950181387277-Stopping-writes-because-we-have-2-immutable-memtables-waiting-for-flush-)
    """,
    "UpdateConsensus requests dropped due to backpressure":"""This message is generally observed when a tablet server is overloaded with UpdateConsensus requests and is not able to process the requests at the same rate as they are coming. This could also happen when there are a huge number of tablets created on the tablet server.  
        **KB Article**: [Coordinator node overloaded rejecting connection](https://support.yugabyte.com/hc/en-us/articles/4404157217037-Coordinator-node-overloaded-rejecting-connection)
    """,
    "Fail of leader detected":"""This means that the failure of the leader is detected. More info to be added
    """,
    "Can't advance the committed index across term boundaries until operations from the current term are replicated":"""This means that the leader is not able to advance the committed index across term boundaries until operations from the current term are replicated.
        **KB Article**: [Can't advance the committed index across term boundaries until operations from the current term are replicated](https://support.yugabyte.com/hc/en-us/articles/15642214673293-Can-t-advance-the-committed-index-across-term-boundaries-until-operations-from-the-current-term-are-replicated)
        **Zendesk Tickets**: 
            - [7872](https://yugabyte.zendesk.com/agent/tickets/7872)
                - Customer observed high latency on YCQL API calls but latency on yb-tserver was normal.
                - Latency was high on YCQL API calls because as leadership was not stable and found that leader was unable to advance the committed index across term boundaries as it was not able to replicate the NoOp to followers.
            - [6137](https://yugabyte.zendesk.com/agent/tickets/6137)
                - Customers backup was failing with "Timed our waiting for snapshot" error.
                - Snapshot was failing because of the same reason as above.     
    """
    # Add more solutions here
}
