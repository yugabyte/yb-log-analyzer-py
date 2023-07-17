#!/usr/bin/env python3
from multiprocessing import Pool, Lock
from analyzer_dict import regex_patterns, solutions
from analyzer_lib import *
from histogram import *
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


# Command line arguments
parser = argparse.ArgumentParser(description="Log Analyzer for YugabyteDB logs")
parser.add_argument("-l", "--log_files", nargs='+', help="List of log file[s]")
parser.add_argument("-d", "--directory", help="Directory containing log files")
parser.add_argument("--support_bundle", help="Path to support bundle")
parser.add_argument("-p", "--parallel", metavar="N", dest='numThreads', default=1, type=int, help="Run in parallel mode with N threads")
parser.add_argument("-H", "--histogram", action="store_true", help="Generate histogram graph")
parser.add_argument("-wc",'--word_count', action="store_true",help='List top 20 word count')
parser.add_argument('-A','--ALL', action="store_true", help='FULL Health Check')
parser.add_argument("--skip_tar", action="store_true", help="Skip tar file")
parser.add_argument("-t", "--from_time", metavar= "MMDD HH:MM", dest="start_time", help="Specify start time")
parser.add_argument("-T", "--to_time", metavar= "MMDD HH:MM", dest="end_time", help="Specify end time")
parser.add_argument("-s", "--sort-by", dest="sort_by", choices=['NO','LO','FO'], help="Sort by: \n NO = Number of occurrences, \n LO = Last Occurrence,\n FO = First Occurrence(Default)")
parser.add_argument("--html", action="store_true", help="Generate HTML report")
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

# Define start and end time
start_time = datetime.datetime.strptime(args.start_time, "%m%d %H:%M") if args.start_time else None
end_time = datetime.datetime.strptime(args.end_time, "%m%d %H:%M") if args.end_time else None

# Define the lists to store the results
listOfErrorsInAllFiles = []
listOfErrorsInFile = []
listOfFilesWithNoErrors = []
listOfAllFilesWithNoErrors = []

# Define Barchart varz
histogramJSON = {}
barChartJSONLock = Lock()

# Define lock for writing to file
writeLock = Lock()

# Setup a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:- %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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
            if file.__contains__("INFO") and file[0] != ".":
                logFiles.append(os.path.join(root, file))
    return logFiles

# Function to get the log files from the support bundle -- Will be deprecated
def getLogFilesFromSupportBundle(supportBundle):
    logFiles = []
    if supportBundle.endswith(".tar.gz"):
        tarFile=tarfile.open(supportBundle, "r:gz")
        support_bundle="support_bundle_{}".format(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        tarFile.extractall(support_bundle)
        tarFile.close()
        logFiles = getLogFilesFromDirectory(support_bundle)
    else:
        logFiles = getLogFilesFromDirectory(supportBundle)
    return logFiles

# Function to get the time from the log line
def getTimeFromLog(line,previousTime):
    try:
        timeFromLogStr = line.split(" ")[0][1:] + " " + line.split(" ")[1][:5]
        timestamp = datetime.datetime.strptime(timeFromLogStr, "%m%d %H:%M")
    except Exception as e:
        timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
    return timestamp

# Function to get all the tar files
def getArchiveFiles(logDirectory):
    archievedFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.endswith(".tar.gz"):
                archievedFiles.append(os.path.join(root,file))
    return archievedFiles
    
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
                    tar.extractall(os.path.dirname(file))
                extractedFiles.append(file)
        if len(extractedFiles) >= len(getArchiveFiles(logDirectory)):
            extractedAll = True

# Function to analyze the log files                
def analyzeLogFiles(logFile, outputFile, start_time=None, end_time=None):
    previousTime = '0101 00:00' # Default time
    logger.info("Analyzing file {}".format(logFile))
    global writeLock
    if logFile.endswith(".gz"):
        logs = gzip.open(logFile, "rt")
    else:
        logs = open(logFile, "r")
    try:
        lines = logs.readlines()
    except UnicodeDecodeError as e:
        logger.warning("Skipping file {} as it is not a text file".format(logFile))
        return listOfErrorsInFile, listOfFilesWithNoErrors
    results = {}
    barChartJSON = {}
    for line in lines:
        timeFromLog = getTimeFromLog(line,previousTime)
        for message, pattern in regex_patterns.items():
            match = re.search(pattern, line)
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
        with writeLock:
            if args.html:
                    formatLogFileForHTMLId = logFile.replace("/", "-").replace(".", "-").replace(" ", "-").replace(":", "-")
                    open(outputFile, "a").write("<h4 id=" + formatLogFileForHTMLId + ">" + logFile + "</h4>")
                    content = tabulate.tabulate(table, headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence"], tablefmt="html")
                    content = content.replace("$line-break$", "<br>").replace("$tab$", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("$start-code$", "<code>").replace("$end-code$", "</code>").replace("$start-bold$", "<b>").replace("$end-bold$", "</b>").replace("$start-italic$", "<i>").replace("$end-italic$", "</i>").replace("<table>", "<table class='sortable' id='main-table'>")
                    open(outputFile, "a").write(content)
            else:
                    open(outputFile, "a").write("\n\n\nAnalysis of " + logFile + "\n\n")
                    content = tabulate.tabulate(table, headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence"], tablefmt="simple_grid")
                    content = content.replace("$line-break$", "\n").replace("$tab$", "\t").replace("$start-code$", "`").replace("$end-code$", "`").replace("$start-bold$", "**").replace("$end-bold$", "**").replace("$start-italic$", "*").replace("$end-italic$", "*")
                    open(outputFile, "a").write(content)
    else:
        listOfFilesWithNoErrors.append(logFile)
    logs.close()
    logger.info("Finished analyzing file {}".format(logFile))
    return listOfErrorsInFile, listOfFilesWithNoErrors, barChartJSON
        

def get_histogram(logFile):
   print ("\nHistogram of logs creating time period\n")
   histogram(logFile)
   
def get_word_count(logFile):
   print ("\nMost widely used word in logs\n")
   word_count(logFile)

def getSolution(message):
    return solutions[message]
    
if __name__ == "__main__":
    # Create output file
    if args.html:
        outputFile = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_analysis.html"
        open(outputFile, "a").write(htmlHeader)
    else:
        outputFile = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_analysis.txt"
    
    # Get log files
    if args.log_files:
        logFileList = getLogFilesFromCommandLine()
    elif args.directory:
        if not args.skip_tar:
            extractAllTarFiles(args.directory)
        logFileList = getLogFilesFromDirectory(args.directory)
    elif args.support_bundle:
        logFileList = getLogFilesFromSupportBundle(args.support_bundle)
    else:
        logger.error("Please specify a log file, directory or support bundle")
        exit(1)

    # Check if log files were found
    if type(logFileList) is not list:
        logger.warning("No log files found")
        exit(1)
    
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
            open(outputFile, "a").write(barChart1 + json.dumps(histogramJSON) + barChart2)
            # Write troubleshooting tips
            open(outputFile, "a").write("<h2 id=troubleshooting-tips> Troubleshooting Tips </h2>")
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                formatErrorForHTMLId = error.replace(" ", "-").lower()
                open(outputFile, "a").write("<h3 id=" + formatErrorForHTMLId + ">" + error + " </h3>")
                content = solution.replace("$line-break$", "<br>").replace("$tab$", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("$start-code$", "<code>").replace("$end-code$", "</code>")
                content = content.replace("$start-bold$", "<b>").replace("$end-bold$", "</b>").replace("$start-italic$", "<i>").replace("$end-italic$", "</i>")
                content = content.replace("$start-link$", "<a href='").replace("$end-link$", "' target='_blank'>").replace("$end-link-text$", "</a>")
                open(outputFile, "a").write( "<p>" + content + " </p>")
                open(outputFile, "a").write("<hr>")
        else:
            # Write troubleshooting tips
            open(outputFile, "a").write("\n\n\nTroubleshooting Tips\n\n")
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                open(outputFile, "a").write("### " + error + "\n\n")
                content = solution.replace("$line-break$", "\n").replace("$tab$", "\t").replace("$start-code$", "`").replace("$end-code$", "`")
                content = content.replace("$start-bold$", "**").replace("$end-bold$", "**").replace("$start-italic$", "*").replace("$end-italic$", "*")
                content = content.replace("$start-link$", "").replace("$end-link$", "").replace("$end-link-text$", "")
                open(outputFile, "a").write(content + "\n\n")    
    # Write list of files with no errors
    if listOfAllFilesWithNoErrors:
        if args.html:
            open(outputFile, "a").write("<h2 id=files-with-no-issues> Files with no issues </h2>")
            askForHelpHtml = """<p> Below list of files are shinier than my keyboard ⌨️ - no issues to report! If you do find something out of the ordinary ☠️ in them, <a href="https://github.com/yugabyte/yb-log-analyzer-py/issues/new?assignees=pgyogesh&labels=%23newmessage&template=add-new-message.md&title=%5BNew+Message%5D" target="_blank"> create a Github issue </a> and I'll put on my superhero 🦹‍♀️ cape to come to the rescue in future:\n </p>"""
            open(outputFile, "a").write(askForHelpHtml)
            open(outputFile, "a").write("<ul>")
            for file in listOfAllFilesWithNoErrors:
                open(outputFile, "a").write("<li>" + file + "</li>")
            open(outputFile, "a").write("</ul>")

        else:
            askForHelp = """\n\n Below list of files do not have any issues to report! If you do find something out of the ordinary in them, create a Github issue at:
            https://github.com/yugabyte/yb-log-analyzer-py/issues/new?assignees=pgyogesh&labels=%23newmessage&template=add-new-message.md&title=%5BNew+Message%5D\n\n"""
            open(outputFile, "a").write(askForHelp)
            for file in listOfAllFilesWithNoErrors:
                open(outputFile, "a").write('- ' + file + "\n")
    if args.html:
        open(outputFile, "a").write(htmlFooter)
    logger.info("Analysis complete. Results are in " + outputFile)