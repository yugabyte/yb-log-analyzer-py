import os
import datetime
import re
import gzip
from collections import deque
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:- %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def getLogFilesFromCurrentDir():
    logFiles = []
    logDirectory = os.getcwd()
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.__contains__("log") or file.__contains__("postgres") or file.__contains__("controller") and file[0] != ".":
                logFiles.append(os.path.join(root, file))
    return logFiles

def getTimeFromLog(line):
    try:
        # Check for glog format (e.g., I0923 14:23:45.123456 12345 file.cc:123] log message)
        if line[0] in ['I', 'W', 'E', 'F']:
            timeFromLogLine = line.split(' ')[0][1:] + ' ' + line.split(' ')[1][:8]
            timestamp = datetime.datetime.strptime(timeFromLogLine, '%m%d %H:%M:%S')
            timestamp = timestamp.replace(year=datetime.datetime.now().year)
        # Check for PostgreSQL log format (e.g., 2023-09-23 14:23:45.123 UTC [12345] LOG:  log message)
        else:
            timeFromLogLine = ' '.join(line.split(' ')[:2])
            timeFromLogLine = timeFromLogLine.split('.')[0]
            timestamp = datetime.datetime.strptime(timeFromLogLine, '%Y-%m-%d %H:%M:%S')
        return timestamp
    except Exception as e:
        raise ValueError(f"Error parsing timestamp from log line: {line} - {e}")

def getFileMetadata(logFile):
    """
    Extracts metadata from a given log file, including start time, end time, log type, and node name.
    Args:
        logFile (str): The path to the log file.
    Returns:
        dict: A dictionary containing the following keys:
            - logStartsAt (datetime): The timestamp of the first log entry. Defaults to January 1st, 00:00 if not found.
            - logEndsAt (datetime): The timestamp of the last log entry. Defaults to December 31st, 23:59 if not found.
            - logType (str): The type of log file (e.g., "postgres", "yb-controller", "yb-tserver", "yb-master", or "unknown").
            - nodeName (str): The name of the node extracted from the file path. Defaults to "unknown" if not found.
    Raises:
        ValueError: If the log file contains invalid timestamps that cannot be parsed.
        Exception: For any unexpected errors during file processing.   
    """
    logStartsAt, logEndsAt = None, None
    if logFile.endswith('.gz'):
        try:
            logs = gzip.open(logFile, 'rt')
        except:
            print("Error opening file: " + logFile)
            return None
    else:
        try:
            logs = open(logFile, 'r')
        except:
            print("Error opening file: " + logFile)
            return None
    try:
        # Read first 10 lines to get the start time
        for i in range(10):
            line = logs.readline()
            try:
                logStartsAt = getTimeFromLog(line)
                break
            except ValueError:
                continue
        # Read last 10 lines to get the end time
        last_lines = deque(logs, maxlen=10)
        for line in reversed(last_lines):
            try:
                logEndsAt = getTimeFromLog(line)
                break
            except ValueError:
                continue
    except Exception as e:
        print(f"Error processing file: {logFile} - {e}")
        return None
    
    if not logStartsAt:
        logStartsAt = datetime.datetime.strptime('0101 00:00', '%m%d %H:%M')
    if not logEndsAt:
        logEndsAt = datetime.datetime.strptime('1231 23:59', '%m%d %H:%M')
    try:
        logStartsAt = logStartsAt.replace(year=datetime.datetime.now().year)
        logEndsAt = logEndsAt.replace(year=datetime.datetime.now().year)
    except Exception as e:
        print("Error getting metadata for file: " + logFile + " " + str(e))
    
    # Get the log type
    if "postgres" in logFile:
        logType = "postgres"
    elif "controller" in logFile:
        logType = "yb-controller"
    elif "tserver" in logFile:
        logType = "yb-tserver"
    elif "master" in logFile:
        logType = "yb-master"
    else:
        logType = "unknown"
        
        
    # Get the node name
    # /Users/pgyogesh/logs/log_analyzer_tests/yb-support-bundle-ybu-p01-bpay-20240412151237.872-logs/yb-prod-ybu-p01-bpay-n8/master/logs/yb-master.danpvvy00002.yugabyte.log.INFO.20230521-030902.3601
    nodeNameRegex = r"/(yb-[^/]*n\d+|yb-(master|tserver)-\d+_[^/]+)/"
    nodeName = re.search(nodeNameRegex, logFile)
    if nodeName:
        nodeName = nodeName.group().replace("/","")
    else:
        nodeName = "unknown"
    
    logger.debug(f"Metadata for file: {logFile} - {logStartsAt} - {logEndsAt} - {logType} - {nodeName}")
    return {"logStartsAt": logStartsAt, "logEndsAt": logEndsAt, "logType": logType, "nodeName": nodeName}

def filterLogFilesByTime(logFileList, logFileMetadata, start_time, end_time):
    filtered_files = []
    removed_files = []
    for logFile in logFileList:
        # Get the start and end time of the log file in datetime format
        log_start = datetime.datetime.strptime(logFileMetadata[logFile]["logStartsAt"], '%Y-%m-%d %H:%M:%S')
        log_end = datetime.datetime.strptime(logFileMetadata[logFile]["logEndsAt"], '%Y-%m-%d %H:%M:%S')
        if log_start >= end_time or log_end <= start_time:
            removed_files.append(logFile)
        else:
            filtered_files.append(logFile)
    logger.debug(f"Included files by time: {filtered_files}")
    logger.debug(f"Removed files by time: {removed_files}")
    return filtered_files, removed_files
    
def filterLogFilesByNode(logFileList, logFileMetadata, nodes):
    # Filter files containing the selected nodes
    filtered_files = []
    removed_files = []
    nodes = nodes.split(",")
    for logFile in logFileList:
        if any(node in logFileMetadata[logFile]["nodeName"] for node in nodes):
            filtered_files.append(logFile)
        else:
            removed_files.append(logFile)
    return filtered_files, removed_files

def filterLogFilesByType(logFileList, logFileMetadata, types):
    filteredLogFiles = []
    removedLogFiles = []
    type_map = {"pg": "postgres", "ts": "yb-tserver", "ms": "yb-master", "ybc": "yb-controller"}
    
    # Get the log types to include
    selectedTypes = [type_map[t] for t in types if t in type_map]
    for logFile in logFileList:
        if logFileMetadata[logFile]["logType"] in selectedTypes:
            filteredLogFiles.append(logFile)
        else:
            removedLogFiles.append(logFile)
    # Filter hidden files
    filteredLogFiles = [logFile for logFile in filteredLogFiles if not logFile.startswith('.')]
    logger.debug(f"Included files by type: {filteredLogFiles}")
    logger.debug(f"Removed files by type: {removedLogFiles}")
    return filteredLogFiles, removedLogFiles