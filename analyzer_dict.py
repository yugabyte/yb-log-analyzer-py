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
#       - You can use http://demo.showdownjs.com/ for markdown preview
#   - Please do not use <variable> in the solution as it will be considered as html tags and will not be displayed rather use $variable
############################################################################################################

universe_regex_patterns = {
"Soft memory limit exceeded": r"Soft memory limit exceeded",
"Number of aborted transactions not cleaned up on account of reaching size limits": r"Number of aborted transactions not cleaned up on account of reaching size limits",
"Long wait for safe op id": r"Long wait for safe op id",
"SST files limit exceeded": r"SST files limit exceeded",
"Operation memory consumption has exceeded its limit": r"Operation failed.*operation memory consumption.*has exceeded",
"Too big clock skew is detected":r"Too big clock skew is detected",
"Stopping writes because we have immutable memtables":r"Stopping writes because we have \d+ immutable memtables",
"UpdateConsensus requests dropped due to backpressure":r"UpdateConsensus request.*dropped due to backpressure",
"Fail of leader detected":r"Fail of leader.*detected",
"Can't advance the committed index across term boundaries until operations from the current term are replicated":r"Can't advance the committed index across term boundaries until operations from the current term are replicated",
"Could not locate the leader master":r"Could not locate the leader master",
"The follower will never be able to catch up":r"The follower will never be able to catch up",
"RequestConsensusVote RPC timed out":r"RequestConsensusVote RPC.*timed out",
"RequestConsensusVote RPC Connection reset by peer":r"RequestConsensusVote RPC.*Connection reset by peer",
# Add more log messages here
}
universe_solutions = {
"Soft memory limit exceeded": """Memory utilization has reached `memory_limit_soft_percentage` (default 85%) and system has started throttling read/write operations.

**NOTE**
- If the number of occurrences of this message is low or happenings once in a while, then it is not a problem. We can ignore this message. It just indicates the busy system at that time.  
**KB Article**: [How to optimize and resolve common memory errors in Yugabyte](https://support.yugabyte.com/hc/en-us/articles/360058731252-How-to-optimize-and-resolve-common-memory-errors-in-Yugabyte)
""",
"Number of aborted transactions not cleaned up on account of reaching size limits": """This typically means that we need to run compaction on offending tablets.  
**Zendesk ticket**: 5416
""",
"Long wait for safe op id": """Write on disk is slow. This could be because of slow disk or load on the system. If number of occurrences of this message is high, then we need to check the disk performance.
""",
"SST files limit exceeded": """Tablet has too many SST files. This could be because of slow compaction or load on the system.  
**KB Article**: [Writes failed with error "SST files limit exceeded"](https://support.yugabyte.com/hc/en-us/articles/4491328438413-Writes-failed-with-error-SST-files-limit-exceeded-)
""",
"Operation memory consumption has exceeded its limit": """We have an operation memory limit set to 1024 MB (Default) per tablet using `tablet_operation_memory_limit_mb`. We hit this issue if we have a hot shard and we keep hitting the same shard at a time at full throttle rather than spreading the workload.  
**Useful Commands**:  

- Get the list of tablets hitting this issue. This sorts the tablet IDs and removes duplicates, providing you with a list of unique tablet IDs.

`zgrep -o -E 'tablet: [a-f0-9]+' <log file name> | awk '{print $2}' | sort -u`

- You can also just count the uniq tablets affected and show the count ob tablets. 

    `zgrep -o -E 'tablet: [a-f0-9]+' <log file name> | awk '{print $2}' | sort | uniq -c`

""",
"Too big clock skew is detected": """This error indicates the nodes running tserver/master process are having clock skew outside of an acceptable range. Clock skew and clock drift can lead to significant consistency issues and should be fixed as soon as possible.  
**KB Article**: [Too big clock skew leading to error messages or tserver crashes](https://support.yugabyte.com/hc/en-us/articles/4403707404173-Too-big-clock-skew-leading-to-error-messages-or-tserver-crashes)
""",
"Stopping writes because we have immutable memtables":"""This message is generally observed when a tablet has immutable memtables which need to flush to disk. It generally indicates that the application is writing at rate, and YB is not able to write the data to disk at the same speed, This could be because of slow disk or hot shard.

**NOTE**
- If the number of occurrences of this message is low or happenings once in a while, then it is not a problem. We can ignore this message. It just indicates the busy system at that time.

**KB Article**: [Stopping writes because we have immutable memtables (waiting for flush)](https://support.yugabyte.com/hc/en-us/articles/14950181387277-Stopping-writes-because-we-have-2-immutable-memtables-waiting-for-flush-)
""",
"UpdateConsensus requests dropped due to backpressure":"""This message is generally observed when a tablet server is overloaded with UpdateConsensus requests and is not able to process the requests at the same rate as they are coming. This could also happen when there are a huge number of tablets created on the tablet server.  
**KB Article**: [Coordinator node overloaded rejecting connection](https://support.yugabyte.com/hc/en-us/articles/4404157217037-Coordinator-node-overloaded-rejecting-connection)
""",
"Fail of leader detected":"""This means that the failure of the leader is detected. More info to be added
""",
"Can't advance the committed index across term boundaries until operations from the current term are replicated":"""This means that the leader is not able to advance the committed index across term boundaries until operations from the current term are replicated.

**NOTE**
- If this message is not observed frequently, then we can ignore this message. We should only be concerned if this message is observed continuously and when tablet replication is stuck.
   
**KB Article**: [Can't advance the committed index across term boundaries until operations from the current term are replicated](https://support.yugabyte.com/hc/en-us/articles/15642214673293-Can-t-advance-the-committed-index-across-term-boundaries-until-operations-from-the-current-term-are-replicated)   
**Zendesk Tickets**: 
- [7872](https://yugabyte.zendesk.com/agent/tickets/7872)
    - Customer observed high latency on YCQL API calls but latency on yb-tserver was normal.
    - Latency was high on YCQL API calls because as leadership was not stable and found that leader was unable to advance the committed index across term boundaries as it was not able to replicate the NoOp to followers.
- [6137](https://yugabyte.zendesk.com/agent/tickets/6137)
    - Customers backup was failing with "Timed our waiting for snapshot" error.
    - Snapshot was failing because of the same reason as above.
""",
"Could not locate the leader master":"""This means that the tablet server is not able to locate the leader master. This could be because of network issues or the master instances are unable to elect a leader.

**NOTE**
- If this message is not observed frequently, then we can ignore this message. We should only be concerned if this message is observed continuously by a perticular tablet server or while providing RCA of an issue happened at same time.
""",
"The follower will never be able to catch up":"""This means that the follower will never be able to catch up with the leader. This could be because of network issues or tablet server being down or overloaded. In case with tablets, they get removed and load balancer will take care of bootstrapping the new peers. But in case of master, We can follow below KB article.

**KB Article**: [[INTERNAL] YugabyteDB Anywhere Generates an Under-Replicated Master Alert](https://support.yugabyte.com/hc/en-us/articles/10700352325645--INTERNAL-YugabyteDB-Anywhere-Generates-an-Under-Replicated-Master-Alert)
""",
"RequestConsensusVote RPC timed out":"""This means that the RequestConsensusVote RPC timed out which means a candidate is requesting votes from the followers and the followers or one of the followers is not able to respond in time. This could be because of network issues or the tablet server being overloaded.
""",
"RequestConsensusVote RPC Connection reset by peer":"""This means that the RequestConsensusVote RPC call was reset by the peer which means a candidate is requesting votes from the followers and the followers or one of the followers is terminating the connection before responding. This could be because of network issues or the tablet server being overloaded.
"""
# Add more solutions here
}

pg_regex_patterns = {
"latch already owned by": r"latch already owned by",
"connection reset by peer": r"connection reset by peer",
"database system is ready to accept connections": r"database system is ready to accept connections"
# Add more log messages here
}
pg_solutions = {
"latch already owned by": """This message is observed when a process is trying to acquire a latch that is already owned by another process. This probably means unexpected backend process termination. The backend was likely terminated without fully cleaning up its resources. This could indicate that the shared memory state between the backends is messed up and so a larger issue may occur in the future. Keeping the cluster around for investigation is recommended. Useful steps to debug this issue are:
- Check the PostgreSQL logs for any errors or warnings.
- Check the system logs for any hardware or OS errors. Look for OOM killer, segmenation faults, etc.
- Contact engineering (specifically Sushant Mishra or Timothy Elgersma) for further assistance.
""",
"connection reset by peer": """This message indicates that the client gone away without closing the connection properly. This could be because of network issues or client application issues.
- Check the client application logs for any errors.
- Check if there idle timeout set on the client application or load balancer side.
- This is concerning if this message is observed frequently or if customer complaints about the connection termination.
""",
"database system is ready to accept connections": """This message indicates that the database was restarted and is ready to accept connections. This is an informational message and can be ignored if not observed frequently.
"""
# Add more solutions here
}