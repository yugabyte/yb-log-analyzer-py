#!/usr/bin/env python3
from multiprocessing import Pool, Lock
from colorama import Fore, Style
from analyzer_dict import universe_regex_patterns, universe_solutions, pg_regex_patterns, pg_solutions
from analyzer_lib import *
from collections import OrderedDict
import logging
import datetime
import argparse
import re
import os
import tabulate
import tarfile
import gzip
import json

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
parser.add_argument("-o", "--output", metavar="FILE", dest="output_file", help="Output file name")
parser.add_argument("-p", "--parallel", metavar="N", dest='numThreads', default=1, type=int, help="Run in parallel mode with N threads")
parser.add_argument("--skip_tar", action="store_true", help="Skip tar file")
parser.add_argument("-t", "--from_time", metavar= "MMDD HH:MM", dest="start_time", help="Specify start time in quotes")
parser.add_argument("-T", "--to_time", metavar= "MMDD HH:MM", dest="end_time", help="Specify end time in quotes")
parser.add_argument("-s", "--sort-by", dest="sort_by", choices=['NO','LO','FO'], help="Sort by: \n\t NO = Number of occurrences, \n\t LO = Last Occurrence,\n\t FO = First Occurrence(Default)")
parser.add_argument("--histogram-mode", dest="histogram_mode", metavar="LIST", help="List of errors to generate histogram")
parser.add_argument("--html", action="store_true", default="true", help="Generate HTML report")
parser.add_argument("--markdown",action="store_true", help="Generate Markdown report")

args = parser.parse_args()

if args.markdown:
    args.html = False

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
end_time = datetime.datetime.strptime(args.end_time, "%m%d %H:%M") if args.end_time else None

# Define the lists to store the results
listOfErrorsInAllFiles = []
listOfErrorsInFile = []
listOfFilesWithNoErrors = []
listOfAllFilesWithNoErrors = []

# Define Barchart varz
histogramJSON = {}
barChartJSONLock = Lock()



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

# Log times

logger.info("Start Time: " + str(datetime.datetime.strftime(start_time, "%m%d %H:%M")))
if end_time:
    logger.info("End Time: " + str(datetime.datetime.strftime(end_time, "%m%d %H:%M")))

# Define lock for writing to file
lock = Lock()

# Function to write to file
def writeToFile(file, content):
    lock.acquire()
    with open(file, "a") as f:
        f.write(content)
    lock.release()

# Get the node list
def getTserversMastersList(dirPaths):
    tserverList = []
    masterList = []
    for dirPath in dirPaths:
        for root, dirs, files in os.walk(dirPath):
            if "instance" in files:
                instancePath = os.path.join(root, "instance")
                if instancePath.__contains__("tserver"):
                    tserverList.append(instancePath.split("/")[-3])
                elif instancePath.__contains__("master"):
                    masterList.append(instancePath.split("/")[-3])
    return tserverList, masterList

# Function to get the deployment type
def getDeploymentType(dirPaths):
    for dirPath in dirPaths:
        for root, dirs, files in os.walk(dirPath):
            if "server.conf" in files:
                return "vm"
            elif "gflags" in dirs:
                return "k8s"
    return "Unknown"

# Function to get the node directory
def getNodeDirectory(node):
    for dirPath in dirPaths:
        for root, dirs, files in os.walk(dirPath):
            if dirs.__contains__(node):
                nodeDir = os.path.join(root, node)
                return nodeDir
    return None

# Function to get the node details
def getNodeDetails():
    nodeDetails = {}
    tserverList, masterList = getTserversMastersList(dirPaths)
    nodeList = set(tserverList + masterList)
    for node in nodeList:
        nodeDir= getNodeDirectory(node)
        if os.path.exists(nodeDir):
            # Get the number of tablets
            tabletMeta = os.path.join(nodeDir,"tserver", "tablet-meta")
            if os.path.exists(tabletMeta):
                numTablets = len(os.listdir(tabletMeta))
            else:
                numTablets = 0
            
            # Get the tserver UUID
            if os.path.exists(os.path.join(nodeDir, "tserver")):
                tserverInstanceFile = os.path.join(nodeDir, "tserver", "instance")
                if os.path.exists(tserverInstanceFile):
                    raw_data = os.popen("yb-pbc-dump " + tserverInstanceFile).readlines()
                    for line in raw_data:
                        if line.startswith("uuid"):
                            tserverUUID = line.split(":")[1].strip().replace('"','')
                        if line.startswith("format_stamp"):
                            tserverRunningOnMachine = line.split(" ")[-1].strip().replace('"','')
                else:
                    tserverUUID = "-"
                    tserverRunningOnMachine = "-"
            else:
                tserverUUID = "-"
                tserverRunningOnMachine = "-"
            
            # Get the master UUID
            if os.path.exists(os.path.join(nodeDir, "master")):
                masterInstanceFile = os.path.join(nodeDir, "master", "instance")
                if os.path.exists(masterInstanceFile):
                    raw_data = os.popen("yb-pbc-dump " + masterInstanceFile).readlines()
                    for line in raw_data:
                        if line.startswith("uuid"):
                            masterUUID = line.split(":")[1].strip().replace('"','')
                        if line.startswith("format_stamp"):
                            masterRunningOnMachine = line.split(" ")[-1].strip().replace('"','')
                else:
                    masterUUID = "-"
                    masterRunningOnMachine = "-"
            else:
                masterUUID = "-"
                masterRunningOnMachine = "-"
            
            # Get the running on machine
            if tserverRunningOnMachine != "-":
                runningOnMachine = tserverRunningOnMachine
            elif masterRunningOnMachine != "-":
                runningOnMachine = masterRunningOnMachine
            else:
                runningOnMachine = "-"
                
            # Get Placement Details
            gflagFile = os.path.join(nodeDir, "tserver", "conf", "server.conf")
            if os.path.exists(gflagFile):
                with open(gflagFile, "r") as f:
                    for line in f:
                        if line.__contains__("placement_cloud"):
                            cloud = line.split("=")[1].strip()
                        if line.__contains__("placement_region"):
                            region = line.split("=")[1].strip()
                        if line.__contains__("placement_zone"):
                            zone = line.split("=")[1].strip()
                    placement = cloud + "." + region + "." + zone
            else:
                placement = "-"
                
            # Populate the node details
            nodeDetails[node] = {}
            nodeDetails[node]["tserverUUID"] = tserverUUID
            nodeDetails[node]["masterUUID"] = masterUUID
            nodeDetails[node]["placement"] = placement
            nodeDetails[node]["runningOnMachine"] = runningOnMachine
            nodeDetails[node]["NumTablets"] = numTablets
    return nodeDetails

# Function to get the gflags from the server.conf file    
def getGFlags(confFile):
    gflags = {}
    with open(confFile, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            key = line.split("=")[0].strip().replace("--", "")
            value = line.split("=")[1].strip()
            gflags[key] = value
    return gflags

# Function to get the log files from the command line
def getLogFilesFromCommandLine():
    logFiles = []
    for file in args.log_files:
        # Check if this is file or directory
        if os.path.isfile(file):
            logFiles.append(file)
    return logFiles

# Function to get the log files from the directory
def getLogFilesFromDirectory(logDirectory):
    logFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.__contains__("INFO") or file.__contains__("postgres") and file[0] != ".":
                logFiles.append(os.path.join(root, file))
    return logFiles

# Function to get the time from the log line
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

# Function to get all the tar files
def getArchiveFiles(logDirectory):
    archievedFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.endswith(".tar.gz") or file.endswith(".tgz"):
                archievedFiles.append(os.path.join(root,file))
    return archievedFiles

# Function to extract the tar file
def extractTarFile(file):
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

# Function to analyze the log files                
def analyzeLogFiles(logFile, outputFile, start_time=None, end_time=None):
    if logFile.__contains__("postgresql"):
        regex_patterns = pg_regex_patterns
    else:
        regex_patterns = universe_regex_patterns
    
    # Check if histogram mode is enabled and set the patterns to analyze
    if args.histogram_mode:
        regex_patterns = {}
        patternsToAnalyze = args.histogram_mode.split(",")
        for pattern in patternsToAnalyze:
            regex_patterns[pattern] = pattern

    previousTime = '0101 00:00' # Default time
    logger.info("Analyzing file {}".format(logFile))
    barChartJSON = {}
    if logFile.endswith(".gz"):
        logs = gzip.open(logFile, "rt")
    else:
        logs = open(logFile, "r")
    try:
        lines = logs.readlines()
    except UnicodeDecodeError as e:
        logger.warning("Skipping file {} as it is not a text file".format(logFile))
        return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON
    except Exception as e:
        logger.warning("Problem occured while reading the file: {}".format(logFile))
        logger.error(e)
        return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON
    results = {}
    for line in lines:
        timeFromLog = getTimeFromLog(line,previousTime)
        for message, pattern in regex_patterns.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match and (not start_time or timeFromLog >= start_time) and (not end_time or timeFromLog <= end_time):
                # Populate results
                if message not in results:
                    results[message] = {
                        "numOccurrences": 0,
                        "firstOccurrenceTime": None,
                        "lastOccurrenceTime": None,
                    }
                results[message]["numOccurrences"] += 1
                time = timeFromLog.strftime('%m%d %H:%M')
                if not results[message]["firstOccurrenceTime"]:
                    results[message]["firstOccurrenceTime"] = time
                results[message]["lastOccurrenceTime"] = time
                listOfErrorsInFile.append(message)
                
                # Create JSON for bar chart
                hour = time[:-3]
                barChartJSON.setdefault(message, {})
                barChartJSON[message].setdefault(hour, 0)
                barChartJSON[message][hour] += 1                              
    if args.sort_by == 'NO':
        sortedDict = OrderedDict(sorted(results.items(), key=lambda x: x[1]["numOccurrences"], reverse=True))
    elif args.sort_by == 'LO':
        sortedDict = OrderedDict(sorted(results.items(), key=lambda x: x[1]["lastOccurrenceTime"]))
    elif args.sort_by == 'FO' or True:
        sortedDict = OrderedDict(sorted(results.items(), key=lambda x: x[1]["firstOccurrenceTime"]))
    table = []
    for message, info in sortedDict.items():
        table.append(
            [
                info["numOccurrences"],
                message,
                info["firstOccurrenceTime"],
                info["lastOccurrenceTime"],
            ]
        )
    if table:
        if args.html:
            formatLogFileForHTMLId = logFile.replace("/", "-").replace(".", "-").replace(" ", "-").replace(":", "-")
            content = "<h4 id=" + formatLogFileForHTMLId + ">" + logFile + "</h4>"
            content += tabulate.tabulate(table, headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence"], tablefmt="html")
            content = content.replace("$line-break$", "<br>").replace("$tab$", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("$start-code$", "<code>").replace("$end-code$", "</code>").replace("$start-bold$", "<b>").replace("$end-bold$", "</b>").replace("$start-italic$", "<i>").replace("$end-italic$", "</i>").replace("<table>", "<table class='sortable' id='main-table'>")
            writeToFile(outputFile, content)
        else:
            formatLogFileForMarkdown = logFile.replace("/", "-").replace(".", "-").replace(" ", "-").replace(":", "-")
            content = "## " + formatLogFileForMarkdown + "\n\n"
            content += tabulate.tabulate(table, headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence"], tablefmt="simple_grid")
            content = content.replace("$line-break$", "\n").replace("$tab$", "\t").replace("$start-code$", "`").replace("$end-code$", "`").replace("$start-bold$", "**").replace("$end-bold$", "**").replace("$start-italic$", "*").replace("$end-italic$", "*")
            writeToFile(outputFile, content)
    else:
        listOfFilesWithNoErrors.append(logFile)
    logs.close()
    logger.info("Finished analyzing file {}".format(logFile))
    return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON

def getVersion():
    if args.log_files:
        files = getLogFilesFromCommandLine()
    elif args.directory:
        files = getLogFilesFromDirectory(args.directory)
    version = "Unknown"
    for file in files:
        if file.endswith('.gz'):
            logs = gzip.open(file, "rt")
        else:
            logs = open(file, "r")
        try:
            lines = logs.readlines()[:10]
        except UnicodeDecodeError as e:
            logger.warning("Skipping file {} as it is not a text file".format(file))
            continue
        for line in lines:
            match = re.search(r'version\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                version = match.group(1)
                break
        logs.close()
        if version != "Unknown":
            break
    return version
   
def getSolution(message):
    if args.histogram_mode:
        return "No solution available for custom patterns"
    return solutions[message]
    
if __name__ == "__main__":        
    dirPaths = []
    outputFilePrefix = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # Create output file
    if not args.output_file:
        if args.html:
            outputFile = outputFilePrefix + "_analysis.html"
            writeToFile(outputFile, htmlHeader)
        else:
            outputFile = outputFilePrefix + "_analysis.md"
    else:
        outputFile = args.output_file
        if args.html:
            writeToFile(outputFile, htmlHeader)
            
    # Get log files
    if args.log_files:
        logFileList = getLogFilesFromCommandLine()
        # if files are tar files, extract them
        if not args.skip_tar:
            for file in logFileList:
                if file.endswith(".tar.gz") or file.endswith(".tgz"):
                    logger.info("Extracting file {}".format(file))
                    extractTarFile(file)
                    extractedDir = file.replace(".tar.gz", "").replace(".tgz", "")
                    # Exctract the tar files in extracted directory
                    extractAllTarFiles(extractedDir)
                    dirPaths.append(extractedDir)
                    logFileList += getLogFilesFromDirectory(extractedDir)
    elif args.directory:
        if not args.skip_tar:
            extractAllTarFiles(args.directory)
        logFileList = getLogFilesFromDirectory(args.directory)
        dirPaths.append(args.directory)
    else:
        logger.info("Please specify a log file, or directory")
        exit(1)
    
    # Check if log files were found
    if type(logFileList) is not list:
        logger.warning("No log files found")
        exit(1)

    # Get the version of the software
    version= getVersion()
    if version != "Unknown":
        if args.html:
            content = "<h2> YugabyteDB Version: " + version + "</h2>"
            writeToFile(outputFile, content)
        else:
            content = "# YugabyteDB Version: " + version + "\n"
            writeToFile(outputFile, content)

    # Add node details to the output file in table format
    if len(getNodeDetails()) > 0:
        # Sum of all tablets
        totalTablets = 0
        for key, value in getNodeDetails().items():
            totalTablets += value["NumTablets"]
        
        if args.html:
            content = "<h2 id=node-details> Node Details </h2>"
            content += "<table class='sortable' id='node-table'>"
            content += "<tr><th>Node</th><th>Master UUID</th><th>TServer UUID</th><th>Placement Info</th><th>Running on Machine</th><th>Number of Tablets</th></tr>"
            for key, value in getNodeDetails().items():
                # Calculate the percentage of tablets
                try:
                    percentage = round((value["NumTablets"] / totalTablets) * 100, 2)
                except ZeroDivisionError:
                    percentage = str("N/A")
                content += "<tr><td>" + key + "</td><td>" + value["masterUUID"] + "</td><td>" + value["tserverUUID"] + "</td><td>" + value["placement"] + "</td><td>"  + value["runningOnMachine"] + "</td><td>" + str(value["NumTablets"]) + " (" + str(percentage) + "%) </td></tr>"
            content += "</table>"
            writeToFile(outputFile, content)
        else:
            content = "\n\n\n# Node Details\n\n"
            for key, value in getNodeDetails().items():
                content += "- " + key + "\n"
                content += "  - Master UUID: " + value["masterUUID"] + "\n"
                content += "  - TServer UUID: " + value["tserverUUID"] + "\n"
                content += "  - Placement Info: " + value["placement"] + "\n"
                content += "  - Running on Machine: " + value["runningOnMachine"] + "\n"
                content += "  - Number of Tablets: " + str(value["NumTablets"]) + "\n"
            writeToFile(outputFile, content)

    masterConfFile = None
    tserverConfFile = None
    for path in dirPaths:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file == "server.conf":
                    if root.__contains__("master"):
                        masterConfFile = os.path.join(root, file)
                    elif root.__contains__("tserver"):
                        tserverConfFile = os.path.join(root, file)

    gflags = {}
    if masterConfFile:
        gflags["master"] = getGFlags(masterConfFile)
    if tserverConfFile:
        gflags["tserver"] = getGFlags(tserverConfFile)
    
    allGFlags = {}
    if masterConfFile and tserverConfFile:
        allGFlags = set(list(gflags["master"].keys()) + list(gflags["tserver"].keys()))
    elif not masterConfFile and tserverConfFile:
        allGFlags = set(list(gflags["tserver"].keys()))
    elif not tserverConfFile and masterConfFile:
        allGFlags = set(list(gflags["master"].keys()))
        
    # Remove flags that are placement related
    allGFlags = [flag for flag in allGFlags if not flag.startswith("placement_")]

    if allGFlags:
        if args.html:
            content = "<h2 id=gflags> GFlags </h2>"
            content += "<table class='sortable' id='gflags-table'>"
            content += "<tr><th>Flag</th><th>Master</th><th>TServer</th></tr>"
            for flag in allGFlags:
                content += "<tr><td> <a href='https://github.com/search?q=repo%3Ayugabyte%2Fyugabyte-db+" + flag + "+language%3AXML++NOT+is%3Aarchived+path%3A%2F%5Emanaged%5C%2Fsrc%5C%2Fmain%5C%2Fresources%5C%2Fgflags_metadata%5C%2F%2F&type=code'>" + flag + "</a></td>"
                if masterConfFile and tserverConfFile:
                    content += "<td>" + gflags["master"].get(flag, "-") + "</td>"
                    content += "<td>" + gflags["tserver"].get(flag, "-") + "</td></tr>"
                elif masterConfFile:
                    content += "<td>" + gflags["master"].get(flag, "-") + "</td>"
                    content += "<td> - </td></tr>"
                elif tserverConfFile:
                    content += "<td> - </td>"
                    content += "<td>" + gflags["tserver"].get(flag, "-") + "</td></tr>"
            content += "</table>"
            content += "<p> Note: The GFlags listed above are from only one of the nodes. Also, This doesn't list the flags with default values and flags that are set runtime. </p>"
            writeToFile(outputFile, content)
        else:
            content = "\n\n\n# GFlags\n\n"
            for flag in allGFlags:
                content += "- " + flag + "\n"
                if masterConfFile and tserverConfFile:
                    content += "  - Master: " + gflags["master"].get(flag, "-") + "\n"
                    content += "  - TServer: " + gflags["tserver"].get(flag, "-") + "\n"
                elif masterConfFile:
                    content += "  - Master: " + gflags["master"].get(flag, "-") + "\n"
                elif tserverConfFile:
                    content += "  - TServer: " + gflags["tserver"].get(flag, "-") + "\n"
            writeToFile(outputFile, content)
    
    logger.info("Number of files to analyze:" + str(len(logFileList)))
    # Analyze log files
    pool = Pool(processes=args.numThreads)
    for listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON in pool.starmap(analyzeLogFiles, [(file, outputFile, start_time, end_time) for file in logFileList]):
        listOfErrorsInAllFiles = list(set(listOfErrorsInAllFiles + listOfErrorsInFile))
        listOfAllFilesWithNoErrors = list(set(listOfAllFilesWithNoErrors + listOfFilesWithNoErrors))
        for key, value in barChartJSON.items():
            if key in histogramJSON:
                for subkey, subvalue in value.items():
                    if subkey in histogramJSON[key]:
                        histogramJSON[key][subkey] += subvalue
                    else:
                        histogramJSON[key][subkey] = subvalue
            else:
                histogramJSON[key] = value
    
    if listOfErrorsInAllFiles:
        if args.html:
            # Write bar chart
            content = barChart1 + json.dumps(histogramJSON) + barChart2
            content += "<h2 id=troubleshooting-tips> Troubleshooting Tips </h2>\n"
            solutionMarkdown = "`"
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                solutionMarkdown += """### {}\n{}  \n\n---\n\n""".format(error, solution).replace('`','\`')
            solutionMarkdown += "`"
            content += """<script>htmlGenerator = new showdown.Converter();\n"""
            content += """solutionsHTML = htmlGenerator.makeHtml({})\n""".format(solutionMarkdown)
            content += """document.write(solutionsHTML);"""
            content += """</script>"""
            writeToFile(outputFile, content)
        else:
            # Write troubleshooting tips
            content = "\n\n\n# Troubleshooting Tips\n\n"
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                content += "### " + error + "\n\n"
                content += solution.replace("$line-break$", "\n").replace("$tab$", "\t").replace("$start-code$", "`").replace("$end-code$", "`")
                content += content.replace("$start-bold$", "**").replace("$end-bold$", "**").replace("$start-italic$", "*").replace("$end-italic$", "*")
                content += content.replace("$start-link$", "").replace("$end-link$", "").replace("$end-link-text$", "")
                writeToFile(outputFile, content)
    # Write list of files with no errors
    if listOfAllFilesWithNoErrors:
        if args.html:
            content = "<h2 id=files-with-no-issues> Files with no issues </h2>"
            content += """<p> Below list of files are shinier than my keyboard ⌨️ - no issues to report! If you do find something out of the ordinary ☠️ in them, <a href="https://github.com/yugabyte/yb-log-analyzer-py/issues/new?assignees=pgyogesh&labels=%23newmessage&template=add-new-message.md&title=%5BNew+Message%5D" target="_blank"> create a Github issue </a> and I'll put on my superhero 🦹‍♀️ cape to come to the rescue in future:\n </p>"""
            content += "<ul>"
            for file in listOfAllFilesWithNoErrors:
                content += "<li>" + file + "</li>"
            content += "</ul>"
            writeToFile(outputFile, content)

        else:
            content = "\n\n\n# Files with no issues\n\n"
            content += """\n\n Below list of files do not have any issues to report! If you do find something out of the ordinary in them, create a Github issue at:
            https://github.com/yugabyte/yb-log-analyzer-py/issues/new?assignees=pgyogesh&labels=%23newmessage&template=add-new-message.md&title=%5BNew+Message%5D\n\n"""
            content += "\n"
            for file in listOfAllFilesWithNoErrors:
                content += "- " + file + "\n"
            writeToFile(outputFile, content)
    if args.html:
        writeToFile(outputFile, htmlFooter)
    logger.info("Analysis complete. Results are in " + outputFile)

    # if hostname == "lincoln" then copy file to directory /tmp
    if os.uname()[1] == "lincoln":
        # Get obsolute path of the args.directory
        logDir = os.path.abspath(args.directory) if args.directory else os.path.abspath(args.log_files[0])
        caseNumber = logDir.split("/")[2]
        os.system("cp " + outputFile + " /home/support/logs_analyzer_dump/" + caseNumber + "-" + outputFile)
        logger.info("⌘+Click 👉👉 http://lincoln:7777/" + caseNumber + "-" + outputFile)
        listOfFiles = os.listdir("/home/support/logs_analyzer_dump/")
        content = "<table style='border-collapse: collapse; border: 1px solid black;'>"
        content += "<tr><td style='border: 1px solid black; padding: 5px;'> Ticket Number </td><td style='border: 1px solid black; padding: 5px;'> Analysis </td></tr>"
        open("/home/support/logs_analyzer_dump/index.html", "w").write("<h2> List of analyzed files </h2>")
        for file in listOfFiles:
            if file.endswith(".html"):
                caseNumber = file.split("-")[0]
                content += "<tr><td> " + caseNumber + " </td><td> <a href='" + file + "'>" + file + "</a> </td></tr>"
        content += "</table>"
        if os.path.exists("/home/support/logs_analyzer_dump/index.html"):
            os.remove("/home/support/logs_analyzer_dump/index.html")
        open("/home/support/logs_analyzer_dump/index.html", "a").write(content)
    else:
        logger.info("⌘+Click 👉👉 file://" + os.path.abspath(outputFile) + " to view the analysis")