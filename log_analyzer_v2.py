#!/usr/bin/env python3
from multiprocessing import Pool, Lock, Manager
from colorama import Fore, Style
from analyzer_lib import (
    universe_regex_patterns,
    universe_solutions,
    pg_regex_patterns,
    pg_solutions,
    solutions,
    htmlHeader,
    htmlFooter,
    barChart1,
    barChart2,
)
from log_lib import (
    getTimeFromLog,
    getFileMetadata,
    filterLogFilesByNode,
    filterLogFilesByTime,
    filterLogFilesByType,
)
from collections import OrderedDict
import logging
import datetime
import argparse
import re
import os
import tabulate
import tarfile
import gzip
import colorama
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
parser.add_argument("-l", "--log_files", nargs='+', help="List of log file[s] \n Examples:\n\t -l /path/to/logfile1 \n\t -l /path/to/logfile1 /path/to/logfile2 \n\t -l /path/to/log* \n\t -l /path/to/support_bundle.tar.gz")
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

# Define the lists to store the results
listOfErrorsInAllFiles = []
listOfErrorsInFile = []
listOfFilesWithNoErrors = []
listOfAllFilesWithNoErrors = []

# Define JSONs
histogramJSON = {}

barChartJSONLock = Lock()
hagenAIJSONLock = Lock()

# Define lock for writing to file
lock = Lock()

# Setup a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:- %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if args.directory:
    log_file = os.path.join(args.directory, 'analyzer.log')
else:
    log_file = 'analyzer.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Function to display the rotating spinner
def spinner():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if done:
            break
        sys.stdout.write('\r Building the one time log file metadata' + c)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\rDone!     \n')

# Function to write to file
def writeToFile(file, content):
    lock.acquire()
    with open(file, "a") as f:
        f.write(content)
    lock.release()

# Function to get all the tar files
def getArchiveFiles(logDirectory):
    archievedFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.endswith(".tar.gz") or file.endswith(".tgz"):
                archievedFiles.append(os.path.join(root,file))
    return archievedFiles

def extractTarFile(file):
    logger.info("Extracting file {}".format(file))
    with tarfile.open(file, "r:gz") as tar:
        # extract to filename directory
        tar.extractall(os.path.dirname(file))

def getTserverMasterList(logFilesMetadata):
    tserverList = []
    masterList = []
    for logFile in logFilesMetadata:
        if logFilesMetadata[logFile]["logType"] == "yb-tserver":
            tserverList.append(logFilesMetadata[logFile]["nodeName"])
        elif logFilesMetadata[logFile]["logType"] == "yb-master":
            masterList.append(logFilesMetadata[logFile]["nodeName"])
    return tserverList, masterList

def getNodeDirectory(logFilesMetadata, nodeName):
    for logFile in logFilesMetadata:
        if logFilesMetadata[logFile]["nodeName"] == nodeName:
            # Extract the directory path up to the node directory
            nodeDir = os.path.dirname(logFile)
            while nodeDir and not nodeDir.endswith(nodeName):
                nodeDir = os.path.dirname(nodeDir)
            if nodeDir.endswith(nodeName):
                return nodeDir
    return None

def getNodeDetails(logFilesMetadata):
    tserverUUID = masterUUID = placement  = numTablets = ''
    nodeDetails = {}
    tserverList, masterList = getTserverMasterList(logFilesMetadata)
    nodeList = set(tserverList + masterList)
    UUIDPattern = re.compile(r'^[a-f0-9]{32}$', re.IGNORECASE)
    for node in nodeList:
        nodeDir = getNodeDirectory(logFilesMetadata, node)
        if os.path.exists(nodeDir):
            # Get the number of tablets
            tabletMetaDir = os.path.join(nodeDir, "tserver", "tablet-meta")
            if os.path.exists(tabletMetaDir):
                # Get the number of files with regex UUID
                numTablets = len([f for f in os.listdir(tabletMetaDir) if UUIDPattern.match(f)])
            else:
                numTablets = 0
                
            # Get the tserver UUID
            tserverInstanceFile = os.path.join(nodeDir, "tserver", "instance")
            if os.path.exists(tserverInstanceFile):
                rawData = os.popen("yb-pbc-dump " + tserverInstanceFile).readlines()
                for line in rawData:
                    if line.startswith("uuid:"):
                        tserverUUID = line.split(":")[1].strip().replace('"','')
                        break
            else:
                tserverUUID = "-"
                
            # Get the master UUID
            masterInstanceFile = os.path.join(nodeDir, "master", "instance")
            if os.path.exists(masterInstanceFile):
                rawData = os.popen("yb-pbc-dump " + masterInstanceFile).readlines()
                for line in rawData:
                    if line.startswith("uuid:"):
                        masterUUID = line.split(":")[1].strip().replace('"','')
                        break
            else:
                masterUUID = "-"
            
            # Get the placement details
            gflagsFile = os.path.join(nodeDir, "tserver", "conf", "server.conf")
            cloud = region = zone = "-"
            if os.path.exists(gflagsFile):
                with open(gflagsFile, "r") as f:
                    for line in f:
                        if line.__contains__("placement_cloud"):
                            cloud = line.split("=")[1].strip()
                        if line.__contains__("placement_region"):
                            region = line.split("=")[1].strip()
                        if line.__contains__("placement_zone"):
                            zone = line.split("=")[1].strip()
                    placement = f"{cloud}.{region}.{zone}"
            else:
                placement = "-"
        else:
            nodeDir = "-"
            numTablets = 0
            tserverUUID = "-"
            masterUUID = "-"
            placement = "-"
        nodeDetails[node] = {}
        nodeDetails[node]["nodeDir"] = nodeDir
        nodeDetails[node]["tserverUUID"] = tserverUUID
        nodeDetails[node]["masterUUID"] = masterUUID
        nodeDetails[node]["placement"] = placement
        nodeDetails[node]["NumTablets"] = numTablets
    return nodeDetails

def getGFlags(logFilesMetadata):
    masterGFlags = {}
    tserverGFlags = {}
    masterNode = tserverNode = None
    # Get the master and tserver node
    for logFile in logFilesMetadata:
        if logFilesMetadata[logFile]["logType"] == "yb-master":
            masterNode = logFilesMetadata[logFile]["nodeName"]
        elif logFilesMetadata[logFile]["logType"] == "yb-tserver":
            tserverNode = logFilesMetadata[logFile]["nodeName"]
    # Get the gflags for master and tserver
    if masterNode:
        gFlagFile = getNodeDirectory(logFilesMetadata, masterNode) + "/master/conf/server.conf"
        if os.path.exists(gFlagFile):
            for line in open(gFlagFile, "r"):
                if line.startswith("--"):
                    key = line.split("=")[0].strip().replace("--", "")
                    value = line.split("=")[1].strip()
                    masterGFlags[key] = value
    if tserverNode:
        gFlagFile = getNodeDirectory(logFilesMetadata, tserverNode) + "/tserver/conf/server.conf"
        if os.path.exists(gFlagFile):
            for line in open(gFlagFile, "r"):
                if line.startswith("--"):
                    key = line.split("=")[0].strip().replace("--", "")
                    value = line.split("=")[1].strip()
                    tserverGFlags[key] = value
    
    allGFlags = {}
    allGFlags["master"] = masterGFlags 
    allGFlags["tserver"] = tserverGFlags
    # Remove the placement gflags from the gflags
    allGFlags = {k: v for k, v in allGFlags.items() if not k.startswith("placement_")}
    return allGFlags
                
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

def getLogFilesToAnalyze():
    logFiles = []
    if args.log_files:
        for logFile in args.log_files:
            if os.path.isfile(logFile):
                logFiles.append(logFile)
                return logFiles
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

def getTimeFromLog(line,previousTime):
    if line[0] in ['I','W','E','F']:
        try:
            timeFromLogStr = line.split(" ")[0][1:] + " " + line.split(" ")[1][:5]
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%m%d %H:%M")
        except Exception as e:
            timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
    else:
        try:
            timeFromLogStr = line.split(" ")[0] + " " + line.split(" ")[1]
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%Y-%m-%d %H:%M:%S.%f")
            timestamp = timestamp.strftime("%m%d %H:%M")
            timestamp = datetime.datetime.strptime(timestamp, "%m%d %H:%M")
        except Exception as e:
            timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
    return timestamp

def getLogFileType(logFilesMetadata, logFile):
    return logFilesMetadata[logFile]["logType"]

def openLogFile(logFile):
    try:
        if logFile.endswith(".gz"):
            with gzip.open(logFile, "rt") as f:
                lines = f.readlines()
            return lines
        else:
            with open(logFile, "r") as f:
                lines = f.readlines()
            return lines
    except Exception as e:
        logger.error("Error opening log file {}: {}".format(logFile, e))
        return []

def analyzeLogFile(logFile, outputFile, logFilesMetadata):
    barChartJSON = {}
    results = {}
    nodeName = logFilesMetadata[logFile]["nodeName"]
    nodeDetails = {}
    nodeDetails[nodeName] = {}
    logFileName = os.path.basename(logFile)
    if logFileName.__contains__("postgresql"):
        regex_patterns = pg_regex_patterns
    elif logFileName.__contains__("tserver") or logFileName.__contains__("master"):
        regex_patterns = universe_regex_patterns
    else:
        logger.error("Invalid log file type for file {}".format(logFile))
        return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON

    logger.info("Analyzing log file: {}".format(logFile))
    previousTime = '0101 00:00'  # Default time

    # Open the log file and process it line by line
    try:
        if logFile.endswith(".gz"):
            logFileHandle = gzip.open(logFile, "rt")
        else:
            logFileHandle = open(logFile, "r")
    except Exception as e:
        logger.error("Error opening log file {}: {}".format(logFile, e))
        return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON

    with logFileHandle as f:
        for line in f:
            timeFromLog = getTimeFromLog(line, previousTime)
            previousTime = timeFromLog.strftime("%m%d %H:%M")

            # Skip lines before the start_time
            if timeFromLog < start_time:
                continue

            # Stop processing after the end_time
            if timeFromLog > end_time:
                break

            for message, regex in regex_patterns.items():
                match = re.search(regex, line, re.IGNORECASE)
                if match:
                    if message not in results:
                        results[message] = {
                            "count": 0,
                            "first_occurrence": None,
                            "last_occurrence": None,
                        }
                    results[message]["count"] += 1
                    time = timeFromLog.strftime("%m%d %H:%M")
                    if results[message]["first_occurrence"] is None:
                        results[message]["first_occurrence"] = time
                    results[message]["last_occurrence"] = time
                    listOfErrorsInFile.append(message)
                    hour = time[:-3]
                    barChartJSON.setdefault(message, {})
                    barChartJSON[message].setdefault(hour, 0)
                    barChartJSON[message][hour] += 1
                    nodeDetails[nodeName][message] = {}
                    nodeDetails[nodeName][message]["count"] = results[message]["count"]
                    nodeDetails[nodeName][message]["first_occurrence"] = results[message]["first_occurrence"]
                    nodeDetails[nodeName][message]["last_occurrence"] = results[message]["last_occurrence"]
                    nodeDetails[nodeName][message]["solution"] = getSolution(message)

    table = []
    for message, details in results.items():
        table.append([message, details["count"], details["first_occurrence"], details["last_occurrence"]])
    if table:
        formatLogFileHTMLId = logFile.replace("/", "_").replace(".", "_").replace(" ", "_").replace(":", "_")
        content = f"""
        <h4 id={formatLogFileHTMLId}> Log File: {logFile} </h4>
        """
        content += tabulate.tabulate(table, headers=["Error Message", "Count", "First Occurrence", "Last Occurrence"], tablefmt="html")
        content = content.replace("$line-break$", "<br>").replace("$tab$", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("$start-code$", "<code>").replace("$end-code$", "</code>").replace("$start-bold$", "<b>").replace("$end-bold$", "</b>").replace("$start-italic$", "<i>").replace("$end-italic$", "</i>").replace("<table>", "<table class='sortable' id='main-table'>")
        writeToFile(outputFile, content)
    else:
        listOfFilesWithNoErrors.append(logFile)
    logger.info("Finished analyzing log file: {}".format(logFile))
    return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON, nodeDetails

def getVersion(logFilesMetadata):
    version = None
    for logFile in logFilesMetadata:
        lines = openLogFile(logFile)[:10]
        for line in lines:
            match = re.search(r'version\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                logger.info("Found version: {} in log file {}".format(match.group(1), logFile))
                version = match.group(1)
                break
        if version:
            break
    if not version:
        logger.warning("Version not found in log files")
    return version

def getSolution(message):
    if args.histogram_mode:
        return "No solution available for custom pattern"
    else:
        return solutions[message]
    
if __name__ == "__main__":
    # Add Command line options and current directory to the htmlFooter
    cmdLineOptions = vars(args)
    logger.info("Command line options: {}".format(cmdLineOptions))
    currentDir = os.getcwd()
    cmdLineDetails = """<h2 id=command-line-options> Command Line Options </h2>
                        <table>
                        <tr>
                            <th>Command Line Options</th>
                            <th>Value</th>
                        </tr>"""
    for key, value in cmdLineOptions.items():
        cmdLineDetails += f"""
                        <tr>
                            <td>{key}</td>
                            <td>{str(value)}</td>
                        </tr>"""
    cmdLineDetails += f"""
                        <tr>
                            <td>Current Directory</td>
                            <td>{currentDir}</td>
                        </tr>
                    </table>"""
    htmlFooter = cmdLineDetails + htmlFooter
    dirPaths = []
    outputFilePrefix = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    choosenTypes = args.types.split(",") if args.types else ["pg", "ts", "ms"]
    # Create output file
    if not args.output_file:
        outputFile = outputFilePrefix + "_analysis.html"
    else:
        outputFile = args.output_file
    writeToFile(outputFile, htmlHeader)
    
    # Get Log files to analyze
    logFiles = getLogFilesToAnalyze()
    if not logFiles:
        logger.error("No log files found to analyze")
        # exit(1)
    if args.support_bundle or args.directory:
        # Build one time metadata for all the log files
        logFilesMetadataFile = 'log_files_metadata.json'
        if not os.path.exists(logFilesMetadataFile):
            done = False
            spinner_thread = threading.Thread(target=spinner)
            spinner_thread.start()
            logFilesMetadata = {}
            for logFile in logFiles:
                try:
                    metadata = getFileMetadata(logFile)
                    if metadata:
                        logFilesMetadata[logFile] = metadata
                except Exception as e:
                    logger.error(f"Error getting metadata for file {logFile}: {e}")
            done = True
            spinner_thread.join()
            with open(logFilesMetadataFile, "w") as f:
                json.dump(logFilesMetadata, f, default=str)
        with open(logFilesMetadataFile, "r") as f:
            logFilesMetadata = json.load(f)
        
        logFilesToProcess = list(logFilesMetadata.keys())
        
        # Filter log files by nodes
        if args.nodes:
            logger.debug(f"Filtering log files by nodes: {args.nodes}")
            includedLogFiles, removedFiles = filterLogFilesByNode(logFilesToProcess, logFilesMetadata, args.nodes)
            logFilesToProcess = [logFile for logFile in logFilesToProcess if logFile not in removedFiles]
            logger.debug(f"Filtered log files: {includedLogFiles}")
            logger.debug(f"Removed log files: {removedFiles}")
        
        # Filter log files by types
        if choosenTypes:
            logger.debug(f"Filtering log files by types: {choosenTypes}")
            includedLogFiles, removedFiles = filterLogFilesByType(logFilesToProcess, logFilesMetadata, choosenTypes)
            logFilesToProcess = [logFile for logFile in logFilesToProcess if logFile not in removedFiles]
            
            
        # Filter log files by time
        if start_time:
            start_time = start_time.replace(year=datetime.datetime.now().year)
            end_time = end_time.replace(year=datetime.datetime.now().year)  
            logger.info(f"Filtering log files by time: {start_time} - {end_time}")
            includedLogFiles, removedFiles = filterLogFilesByTime(logFilesToProcess, logFilesMetadata, start_time, end_time)
            logFilesToProcess = [logFile for logFile in logFilesToProcess if logFile not in removedFiles]
            logger.debug(f"Filtered log files: {includedLogFiles}")
            logger.debug(f"Removed log files: {removedFiles}")
        
        if len(logFilesToProcess) == 0:
            logger.error("No log files found to analyze after filtering")
            exit(1)
        table = []
        for file in logFilesToProcess:
            table.append([file[-100:], logFilesMetadata[file]["logStartsAt"], logFilesMetadata[file]["logEndsAt"], logFilesMetadata[file]["logType"], logFilesMetadata[file]["nodeName"]])
        table.sort(key=lambda x: (x[4], x[3], x[1]))  # Sort by Node Name, Type, then Start Time
        print(tabulate.tabulate(table, headers=["File", "Start Time", "End Time", "Type", "Node Name"], tablefmt="simple_grid"))
        
        # Get version
        version = getVersion(logFilesMetadata)
        if version:
            writeToFile(outputFile, f"<h2> YugabyteDB Version: {version} </h2>")
        
        # Writh version to localHagenAIJSON
        hagenAIJSON = {}
        hagenAIJSON["version"] = version
            
        # Get the node details
        logger.info("Getting node details")
        nodeDetails = getNodeDetails(logFilesMetadata)
        if nodeDetails is not None:
            totalTablets = sum([details["NumTablets"] for details in nodeDetails.values()])
            content = "<h2 id=node-details> Node Details </h2>"
            content += "<table class='sortable' id='node-details-table'>"
            content += "<tr><th>Node Name</th><th>Master UUID</th><th>TServer UUID</th><th>Placement</th><th>Num Tablets</th></tr>"
            for node, details in nodeDetails.items():
                # Calculate the percentage of tablets
                try:
                    percentage = round((int(details["NumTablets"]) / totalTablets) * 100)
                except ZeroDivisionError:
                    percentage = 0
                content += f"<tr><td>{node}</td><td>{details['masterUUID']}</td><td>{details['tserverUUID']}</td><td>{details['placement']}</td><td>{details['NumTablets']} ({percentage}%)</td></tr>"
            content += "</table>"
            writeToFile(outputFile, content)
            
            # Add the node details to localHagenAIJSON (default to empty with "")
            hagenAIJSON["nodeDetails"] = {}
            for node, details in nodeDetails.items():
                # Add the node details to localHagenAIJSON
                hagenAIJSON["nodeDetails"][node] = {}
                hagenAIJSON["nodeDetails"][node]["masterUUID"] = details["masterUUID"]
                hagenAIJSON["nodeDetails"][node]["tserverUUID"] = details["tserverUUID"]
                hagenAIJSON["nodeDetails"][node]["placement"] = details["placement"]
                hagenAIJSON["nodeDetails"][node]["NumTablets"] = details["NumTablets"]
                hagenAIJSON["nodeDetails"][node]["nodeDir"] = details["nodeDir"]

        # Get the gflags
        logger.info("Getting gflags")
        allGFlags = getGFlags(logFilesMetadata)
        # Add the gflags to localHagenAIJSON
        hagenAIJSON["gflags"] = {}
        hagenAIJSON["gflags"]["master"] = allGFlags["master"]
        hagenAIJSON["gflags"]["tserver"] = allGFlags["tserver"]

        # Get the list of all only the gflags for master and tserver, the keys are the gflags and the values are the values
        gFlagList = []
        for gFlag in allGFlags["master"]:
            gFlagList.append(gFlag)
        for gFlag in allGFlags["tserver"]:
            gFlagList.append(gFlag)
        uniqueGFlags = list(set(gFlagList))
        content = "<h2 id=gflags> GFlags </h2>"
        content += "<table class='sortable' id='gflags-table'>"
        content += "<tr><th>GFlag</th><th>Master Value</th><th>TServer Value</th></tr>"
        for gFlag in uniqueGFlags:
            masterValue = allGFlags["master"].get(gFlag, "-")
            tserverValue = allGFlags["tserver"].get(gFlag, "-")
            content += f"<tr><td>{gFlag}</td><td>{masterValue}</td><td>{tserverValue}</td></tr>"
        content += "</table>"
        writeToFile(outputFile, content)
        
        logger.info("Number of files to analyze: {}".format(len(logFilesToProcess)))
                
        # Create a pool of workers
        pool = Pool(processes=args.numThreads)
        for listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON, nodeDetails in pool.starmap(analyzeLogFile, [(logFile, outputFile, logFilesMetadata) for logFile in logFilesToProcess]):
            listOfErrorsInAllFiles = list(set(listOfErrorsInAllFiles + listOfErrorsInFile))
            listOfAllFilesWithNoErrors = list(set(listOfAllFilesWithNoErrors + listOfFilesWithNoErrors))
            for key, value in barChartJSON.items():
                if key in histogramJSON:
                    for subkey, subValue in value.items():
                        if subkey in histogramJSON[key]:
                            histogramJSON[key][subkey] += subValue
                        else:
                            histogramJSON[key][subkey] = subValue
                else:
                    histogramJSON[key] = value
            # Add the node details to hagenAIJSON
            if nodeDetails:
                for node, details in nodeDetails.items():
                    if node not in hagenAIJSON["nodeDetails"]:
                        hagenAIJSON["nodeDetails"][node] = {}
                    for message, messageDetails in details.items():
                        nodeMessages = hagenAIJSON["nodeDetails"][node]

                        if message not in nodeMessages:
                            nodeMessages[message] = {}

                        # Update count
                        nodeMessages[message]["count"] = nodeMessages[message].get("count", 0) + messageDetails.get("count", 0)

                        # Update first_occurrence
                        if (
                            "first_occurrence" not in nodeMessages[message]
                            or messageDetails["first_occurrence"] < nodeMessages[message]["first_occurrence"]
                        ):
                            nodeMessages[message]["first_occurrence"] = messageDetails["first_occurrence"]

                        # Update last_occurrence
                        if (
                            "last_occurrence" not in nodeMessages[message]
                            or messageDetails["last_occurrence"] > nodeMessages[message]["last_occurrence"]
                        ):
                            nodeMessages[message]["last_occurrence"] = messageDetails["last_occurrence"]

                        # Add or update solution
                        nodeMessages[message]["solution"] = getSolution(message)
        pool.close()
        pool.join()
        if listOfErrorsInAllFiles:
            # Create the histogram
            content = barChart1 + json.dumps(histogramJSON) + barChart2
            solutionMarkdown = "`"
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                solutionMarkdown += """###{}\n{} \n\n---\n\n""".format(error, solution).replace("`", "\`")
            solutionMarkdown += "`"
            content += """<script> htmlGenerateBar = new showdown.Converter();\n"""
            content += """solutionHtml = htmlGenerator.makeHtml({})\n""".format(solutionMarkdown)
            content += """document.write(solutionHtml); </script>"""
            writeToFile(outputFile, content)
        if listOfAllFilesWithNoErrors:
            content = "<h2> List of files with no errors </h2>"
            content += "<table>"
            for file in listOfAllFilesWithNoErrors:
                content += f"<tr><td>{file}</td></tr>"
            content += "</table>"
            writeToFile(outputFile, content)
        # Write the footer
        writeToFile(outputFile, htmlFooter)
        hagenAIJSONFile = "hagen_ai.json"
        with open(hagenAIJSONFile, "w") as f:
            json.dump(hagenAIJSON, f, indent=4)
            
        print("=============summary=================")
        print(f"Total log files: {len(logFiles)}, Included log files: {len(includedLogFiles)}")
        print(f"Start time: {start_time}, End time: {end_time}")
        logTypes =  sorted(list(set([logFilesMetadata[logFile]['logType'] for logFile in logFilesToProcess])))
        print(f"Log types: {logTypes}")
        nodes = sorted(list(set([logFilesMetadata[logFile]['nodeName'] for logFile in logFilesToProcess])))
        print(f"Nodes: {nodes}")
            # Log missing for the following nodes
        # Postgres logs
        colorama.init(autoreset=True)
        isLogMissing = False
        if "pg" in choosenTypes:
            missingNodes = [node for node in nodes if not any(node in file for file in logFilesToProcess if logFilesMetadata[file]["logType"] == "postgres")]
            if missingNodes:
                print(colorama.Fore.RED + f"Postgres logs missing for nodes: {', '.join(missingNodes)}")
                isLogMissing = True
        # TServer logs
        if "ts" in choosenTypes:
            missingNodes = [node for node in nodes if not any(node in file for file in logFilesToProcess if logFilesMetadata[file]["logType"] == "yb-tserver")]
            if missingNodes:
                print(colorama.Fore.RED + f"TServer logs missing for nodes: {', '.join(missingNodes)}")
                isLogMissing = True
        # Master logs
        if "ms" in choosenTypes:
            missingNodes = [node for node in nodes if not any(node in file for file in logFilesToProcess if logFilesMetadata[file]["logType"] == "yb-master")]
            if missingNodes:
                print(colorama.Fore.RED + f"Master logs missing for nodes: {', '.join(missingNodes)}")
                isLogMissing = True
        # Controller logs
        if "ybc" in choosenTypes:
            missingNodes = [node for node in nodes if not any(node in file for file in logFilesToProcess if logFilesMetadata[file]["logType"] == "yb-controller")]
            if missingNodes:
                print(colorama.Fore.RED + f"Controller logs missing for nodes: {', '.join(missingNodes)}")
                isLogMissing = True
        
        if isLogMissing:
            print(colorama.Fore.YELLOW + "WARNING: If missing logs are reported and if it is suspicious, please check the logs manually.")
        print("=====================================")
        print(f"Log analysis completed. Output file: {outputFile}")
