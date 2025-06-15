from multiprocessing import Pool, Lock, Manager
from colorama import Fore, Style
from analyzer_lib import (
    universe_regex_patterns,
    universe_solutions,
    pg_regex_patterns,
    pg_solutions
)
from collections import deque
import logging
import datetime
import argparse
import re
import os
import tabulate
import tarfile
import gzip
import json
import sys
import itertools
import time
import threading

class ColoredHelpFormatter(argparse.RawTextHelpFormatter):
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

# Command line arguments
parser = argparse.ArgumentParser(description="Log Analyzer for YugabyteDB logs", formatter_class=ColoredHelpFormatter)
parser.add_argument("-d", "--directory", help="Directory containing log files")
parser.add_argument("-s","--support_bundle", help="Support bundle file name")
parser.add_argument("--types", metavar="LIST", help="List of log types to analyze \n Example: --types 'ms,ybc' \n Default: --types 'pg,ts,ms'")
parser.add_argument("-n", "--nodes", metavar="LIST", help="List of nodes to analyze \n Example: --nodes 'n1,n2'")
parser.add_argument("-o", "--output", metavar="FILE", dest="output_file", help="Output file name")
parser.add_argument("-p", "--parallel", metavar="N", dest='numThreads', default=5, type=int, help="Run in parallel mode with N threads")
parser.add_argument("--skip_tar", action="store_true", help="Skip tar file")
parser.add_argument("-t", "--from_time", metavar= "MMDD HH:MM", dest="start_time", help="Specify start time in quotes")
parser.add_argument("-T", "--to_time", metavar= "MMDD HH:MM", dest="end_time", help="Specify end time in quotes")
parser.add_argument("--histogram-mode", dest="histogram_mode", metavar="LIST", help="List of errors to generate histogram \n Example: --histogram-mode 'error1,error2,error3'")
args = parser.parse_args()

# Validated start and end time format
if args.start_time:
    try:
        datetime.datetime.strptime(args.start_time, "%m%d %H:%M")
    except ValueError as e:
        print("Incorrect start time format, should be MMDD HH:MM")
        exit(1)
if args.end_time:
    try:
        datetime.datetime.strptime(args.end_time, "%m%d %H:%M")
    except ValueError as e:
        print("Incorrect end time format, should be MMDD HH:MM")
        exit(1)

# 7 days ago from today
seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
seven_days_ago = seven_days_ago.strftime("%m%d %H:%M")
# If not start time then set it to today - 7 days in "MMDD HH:MM" format
start_time = datetime.datetime.strptime(args.start_time, "%m%d %H:%M") if args.start_time else datetime.datetime.strptime(seven_days_ago, "%m%d %H:%M")
end_time = datetime.datetime.strptime(args.end_time, "%m%d %H:%M") if args.end_time else datetime.datetime.now()

reportJSON = {}

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:- %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logFile = "analyzer.log"
file_handler = logging.FileHandler(logFile)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Function to get all the tar files
def getArchiveFiles(logDirectory):
    archievedFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.endswith(".tar.gz") or file.endswith(".tgz"):
                archievedFiles.append(os.path.join(root,file))
    return archievedFiles

def getStartAndEndTimes():
    # Calculate start and end times
    if args.start_time and args.end_time:
        startTime = datetime.datetime.strptime(args.start_time, '%m%d %H:%M')
        endTime = datetime.datetime.strptime(args.end_time, '%m%d %H:%M')
    elif args.start_time and not args.end_time:
        startTime = datetime.datetime.strptime(args.start_time, '%m%d %H:%M')
        endTime = datetime.datetime.strptime('1231 23:59', '%m%d %H:%M')
    elif not args.start_time and args.end_time:
        startTime = datetime.datetime.strptime('0101 00:00', '%m%d %H:%M')
        endTime = datetime.datetime.strptime(args.end_time, '%m%d %H:%M')
    else:
        startTime = datetime.datetime.strptime('0101 00:00', '%m%d %H:%M')
        endTime = datetime.datetime.strptime('1231 23:59', '%m%d %H:%M')
    startTimeLong = startTime.replace(year=datetime.datetime.now().year)
    endTimeLong = endTime.replace(year=datetime.datetime.now().year)
    startTimeShort = startTime.strftime('%m%d %H:%M')
    endTimeShort = endTime.strftime('%m%d %H:%M')
    return startTimeLong, endTimeLong, startTimeShort, endTimeShort

def extractTarFile(file):
    logger.info("Extracting file {}".format(file))
    with tarfile.open(file, "r:gz") as tar:
        # extract to filename directory
        tar.extractall(os.path.dirname(file))

# Function to extract all the tar files    
def extractAllTarFiles(logDirectory):
    extractedFiles = []
    extractedAll = False
    while not extractedAll:
        extractedAll = True
        for file in getArchiveFiles(logDirectory):
            extractedAll = False
            if file not in extractedFiles:
                logger.info("Extracting file {}".format(file))
                with tarfile.open(file, "r:gz") as tar:
                    try:
                        tar.extractall(os.path.dirname(file))
                    except EOFError:
                        logger.warning("Got EOF Exception while extracting file {}, File might have still extracted. Please check {} for more information ".format(file, log_file))
                        logger.error("EOF Exception while extracting file {}".format(file))
                extractedFiles.append(file)
        if len(extractedFiles) >= len(getArchiveFiles(logDirectory)):
            extractedAll = True
            
# Function to display the rotating spinner
def spinner():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if done:
            break
        sys.stdout.write('\r Building the one time log file metadata' + c)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\rDone!     \n')

def getLogFilesFromCurrentDir():
    logFiles = []
    logDirectory = os.getcwd()
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.__contains__("log") and file[0] != ".":
                logFiles.append(os.path.join(root, file))
    return logFiles

def getTimeFromLog(line,previousTime):
    if line[0] in ['I','W','E','F']:
        try:
            timeFromLogStr = line.split(" ")[0][1:] + " " + line.split(" ")[1][:5]
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%m%d %H:%M")
            timestamp = timestamp.replace(year=datetime.datetime.now().year)
        except Exception as e:
            timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
            timestamp = timestamp.replace(year=datetime.datetime.now().year)
    else:
        try:
            timeFromLogStr = line.split(" ")[0] + " " + line.split(" ")[1]
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%Y-%m-%d %H:%M:%S.%f")
            timestamp = timestamp.strftime("%m%d %H:%M")
            timestamp = datetime.datetime.strptime(timestamp, "%m%d %H:%M")
            timestamp = timestamp.replace(year=datetime.datetime.now().year)
        except Exception as e:
            timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
            timestamp = timestamp.replace(year=datetime.datetime.now().year)
    return timestamp

def openLogFile(logFile):
    if logFile.endswith('.gz'):
        try:
            logs = gzip.open(logFile, 'rt')
        except Exception as e:
            logger.error(f"Error opening file {logFile}: {e}")
            return None
    else:
        try:
            logs = open(logFile, 'r')
        except Exception as e:
            logger.error(f"Error opening file {logFile}: {e}")
            return None
    return logs

def getFileMetadata(logFile):
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
                logStartsAt = getTimeFromLog(line, '0101 00:00')
                break
            except ValueError:
                continue
        # Read last 10 lines to get the end time
        last_lines = deque(logs, maxlen=10)
        for line in reversed(last_lines):
            try:
                logEndsAt = getTimeFromLog(line, '1231 23:59')
                break
            except ValueError:
                continue
    except Exception as e:
        print(f"Error processing file: {logFile} - {e}")
        return None
    
    if logStartsAt is None:
        logStartsAt = datetime.datetime.strptime('0101 00:00', '%m%d %H:%M')
    if logEndsAt is None:
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
    elif "application" in logFile:
        logType = "YBA"
    else:
        logType = "unknown"
        
    # Get the subtype if available
    if "INFO" in logFile:
        subType = "INFO"
    elif "WARN" in logFile:
        subType = "WARN"
    elif "ERROR" in logFile:
        subType = "ERROR"
    elif "FATAL" in logFile:
        subType = "FATAL"
    elif "postgres" in logFile:
        subType = "INFO"
    elif "application" in logFile:
        subType = "INFO"
    else:
        subType = "unknown"
        
        
    # Get the node name
    # /Users/pgyogesh/logs/log_analyzer_tests/yb-support-bundle-ybu-p01-bpay-20240412151237.872-logs/yb-prod-ybu-p01-bpay-n8/master/logs/yb-master.danpvvy00002.yugabyte.log.INFO.20230521-030902.3601
    nodeNameRegex = r"/(yb-[^/]*n\d+|yb-(master|tserver)-\d+_[^/]+)/"
    nodeName = re.search(nodeNameRegex, logFile)
    if nodeName:
        nodeName = nodeName.group().replace("/","")
    else:
        nodeName = "unknown"
    
    logger.debug(f"Metadata for file: {logFile} - {logStartsAt} - {logEndsAt} - {logType} - {nodeName} - {subType}")
    return {"logStartsAt": logStartsAt, "logEndsAt": logEndsAt, "logType": logType, "nodeName": nodeName , "subType": subType}

def getLogFilesToBuildMetadata():
    logFiles = []
    if args.directory:
        if not args.skip_tar:
            extractAllTarFiles(args.directory)
        for root, dirs, files in os.walk(args.directory):
            for file in files:
                if file.__contains__("INFO") or file.__contains__("postgres") and file[0] != ".":
                    logFiles.append(os.path.join(root, file))
    if args.support_bundle:
        if args.support_bundle.endswith(".tar.gz") or args.support_bundle.endswith(".tgz"):
            if not args.skip_tar:
                extractTarFile(args.support_bundle)
                extractedDir = args.support_bundle.replace(".tar.gz", "").replace(".tgz", "")
                # Exctract the tar files in extracted directory
                extractAllTarFiles(extractedDir)
            for root, dirs, files in os.walk(extractedDir):
                for file in files:
                    if file.__contains__("INFO") or file.__contains__("postgres") and file[0] != ".":
                        full_path = os.path.abspath(os.path.join(root, file))
                        # Append the files with the absolute path
                        logFiles.append(full_path)
        else:
            logger.error("Invalid support bundle file format. Please provide a .tar.gz or .tgz file")
            exit(1)
    return logFiles

# Function to analyze the log files from the nodes
def analyzeNodeLogs(nodeName, logType, subType, startTimeLong, endTimeLong, logFilesMetadata):
    logger.info(f"Analyzing logs for node: {nodeName}, logType: {logType}, subType: {subType}")
    filteredLogs = []
    for logFile, metadata in logFilesMetadata[nodeName][logType][subType].items():
        logStartsAt = datetime.datetime.strptime(metadata["logStartsAt"], '%Y-%m-%d %H:%M:%S')
        logEndsAt = datetime.datetime.strptime(metadata["logEndsAt"], '%Y-%m-%d %H:%M:%S')
        if (logStartsAt >= startTimeLong and logStartsAt <= endTimeLong) or (logEndsAt >= startTimeLong and logEndsAt <= endTimeLong):
            filteredLogs.append(logFile)
    print(f"Filtered logs for node {nodeName}, logType {logType}, subType {subType}: {len(filteredLogs)} files")

    # Select patterns and names
    if logType == "postgres":
        patterns = list(pg_regex_patterns.values())
        pattern_names = list(pg_regex_patterns.keys())
    else:
        patterns = list(universe_regex_patterns.values())
        pattern_names = list(universe_regex_patterns.keys())

    # Track per-message stats
    message_stats = {}

    def to_iso(dt):
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    for logFile in filteredLogs:
        logger.info(f"Processing log file: {logFile}")
        try:
            with openLogFile(logFile) as logs:
                if logs is None:
                    continue
                previousTime = '0101 00:00'
                for line in logs:
                    try:
                        logTime = getTimeFromLog(line, previousTime)
                        previousTime = logTime.strftime("%m%d %H:%M")
                        if startTimeLong <= logTime <= endTimeLong:
                            for idx, pattern in enumerate(patterns):
                                if re.search(pattern, line):
                                    msg_type = pattern_names[idx]
                                    hour_bucket = logTime.replace(minute=0, second=0, microsecond=0)
                                    if msg_type not in message_stats:
                                        message_stats[msg_type] = {"StartTime": logTime, "EndTime": logTime, "count": 1, "histogram": {}}
                                    else:
                                        if logTime < message_stats[msg_type]["StartTime"]:
                                            message_stats[msg_type]["StartTime"] = logTime
                                        if logTime > message_stats[msg_type]["EndTime"]:
                                            message_stats[msg_type]["EndTime"] = logTime
                                        message_stats[msg_type]["count"] += 1
                                    # Update histogram
                                    hour_key = hour_bucket.strftime('%Y-%m-%dT%H:00:00Z')
                                    if hour_key not in message_stats[msg_type]["histogram"]:
                                        message_stats[msg_type]["histogram"][hour_key] = 0
                                    message_stats[msg_type]["histogram"][hour_key] += 1
                                    break
                    except ValueError:
                        logger.error(f"Invalid log time format in file {logFile}: {line.strip()}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing line in file {logFile}: {e}")
                        continue
                logs.close()
        except Exception as e:
            logger.error(f"Error reading log file {logFile}: {e}")

    # Format times for output
    logMessages = {}
    for msg_type, stats in message_stats.items():
        logMessages[msg_type] = {
            "StartTime": to_iso(stats["StartTime"]),
            "EndTime": to_iso(stats["EndTime"]),
            "count": stats["count"],
            "histogram": stats["histogram"]
        }

    result = {
        "node": nodeName,
        "logType": logType,
        "logMessages": logMessages
    }
    return result

if __name__ == "__main__":
    logFilesMetadata = {}
    logFilesMetadataFile = 'log_files_metadata.json'
    logFileList = getLogFilesToBuildMetadata()
    if not logFileList:
        logger.error("No log files found in the specified directory or support bundle.")
        exit(1)
    done = False
    # Start the spinner in a separate thread
    spinner_thread = threading.Thread(target=spinner)
    spinner_thread.start()
    # Build the metadata for the log files
    for logFile in logFileList:
        metadata = getFileMetadata(logFile)
        if metadata:
            node = metadata["nodeName"]
            logType = metadata["logType"]
            subType = metadata["subType"]
            if node not in logFilesMetadata:
                logFilesMetadata[node] = {}
            if logType not in logFilesMetadata[node]:
                logFilesMetadata[node][logType] = {}
            if subType not in logFilesMetadata[node][logType]:
                logFilesMetadata[node][logType][subType] = {}
            logFilesMetadata[node][logType][subType][logFile] = {
                "logStartsAt": str(metadata["logStartsAt"]),
                "logEndsAt": str(metadata["logEndsAt"])
            }
    # Save the metadata to a file
    with open(logFilesMetadataFile, 'w') as f:
        json.dump(logFilesMetadata, f, indent=4)
    done = True
    spinner_thread.join()
    logger.info(f"Log files metadata saved to {logFilesMetadataFile}")
    # Get long start and end times
    startTimeLong, endTimeLong, startTimeShort, endTimeShort = getStartAndEndTimes()
    logger.info(f"Analyzing logs from {startTimeShort} to {endTimeShort}")
    summary_results = []
    # Build nested result: node -> logType -> logMessages
    nested_results = {}
    for nodeName, nodeData in logFilesMetadata.items():
        if nodeName not in nested_results:
            nested_results[nodeName] = {}
        for logType, logTypeData in nodeData.items():
            for subType, subTypeData in logTypeData.items():
                result = analyzeNodeLogs(nodeName, logType, subType, startTimeLong, endTimeLong, logFilesMetadata)
                # Only add logType if not present
                if logType not in nested_results[nodeName]:
                    nested_results[nodeName][logType] = {"logMessages": {}}
                # Merge logMessages for this logType
                for msg, stats in result["logMessages"].items():
                    nested_results[nodeName][logType]["logMessages"][msg] = stats
    # Write nested results to a JSON file
    with open("node_log_summary.json", "w") as f:
        json.dump(nested_results, f, indent=2)
    logger.info("Wrote node log summary to node_log_summary.json")
    logger.info("Log analysis completed.")