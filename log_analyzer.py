#!/usr/bin/env python3
from multiprocessing import Pool, Lock
from analyzer_dict import universe_regex_patterns, universe_solutions, pg_regex_patterns, pg_solutions
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
parser.add_argument("-o", "--output", metavar="FILE", dest="output_file", help="Output file name")
parser.add_argument("-p", "--parallel", metavar="N", dest='numThreads', default=1, type=int, help="Run in parallel mode with N threads")
parser.add_argument("--skip_tar", action="store_true", help="Skip tar file")
parser.add_argument("-t", "--from_time", metavar= "MMDD HH:MM", dest="start_time", help="Specify start time in quotes")
parser.add_argument("-T", "--to_time", metavar= "MMDD HH:MM", dest="end_time", help="Specify end time in quotes")
parser.add_argument("-s", "--sort-by", dest="sort_by", choices=['NO','LO','FO'], help="Sort by: \n NO = Number of occurrences, \n LO = Last Occurrence,\n FO = First Occurrence(Default)")
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

# If not start time then set it to today - 3 days in "MMDD HH:MM" format
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

# Define lock for writing to file
writeLock = Lock()

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
logger.addHandler(file_handler)


# Get the node list
def getTserversList():
    tserversDir = []
    tserverList = []
    for root, dirs, files in os.walk(args.directory):
        if "tserver" in dirs:
            tserversDir.append(os.path.join(root, "tserver"))
    for dir in tserversDir:
        tserver = dir.split("/")[-2]
        tserverList.append(tserver)
    return tserverList

def getMastersList():
    mastersDir = []
    masterList = []
    for root, dirs, files in os.walk(args.directory):
        if "master" in dirs:
            mastersDir.append(os.path.join(root, "master"))
    for dir in mastersDir:
        master = dir.split("/")[-2]
        masterList.append(master)
    return masterList
            

# Get number of tablets per node
def getNumTabletsPerNode():
    tserversList = getTserversList()
    numTabletsPerNode = {}
    # Get tserver directories for each node
    dirList = os.listdir(args.directory)
    for node in tserversList:
        if node in dirList:
            tabletMetaDir = os.path.join(args.directory, node, "tserver", "tablet-meta")
            print("Tablet Meta Dir: ", tabletMetaDir)
            numTablets = len(os.listdir(tabletMetaDir))
            numTabletsPerNode[node] = numTablets
    return numTabletsPerNode

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
    # If line starts I,W,E,F then it is yugabyte log and time is in format I0319 14:50:44.286835
    # Else it is postgres log and time is in format 2024-03-19 13:58:21.588 IST
    # Convert the time to MMDD HH:MM format
    if line[0] in ['I','W','E','F']:
        try:
            timeFromLogStr = line.split(" ")[0][1:] + " " + line.split(" ")[1][:5]
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%m%d %H:%M")
        except Exception as e:
            timestamp = datetime.datetime.strptime(previousTime, "%m%d %H:%M")
    else:
        try:
            timeFromLogStr = line.split(" ")[0] + " " + line.split(" ")[1]
            # Change the format of the time to MMDD HH:MM
            timestamp = datetime.datetime.strptime(timeFromLogStr, "%Y-%m-%d %H:%M:%S.%f")
            # Convert the time to UTC based on the timezone
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
    previousTime = '0101 00:00' # Default time
    logger.info("Analyzing file {}".format(logFile))
    barChartJSON = {}
    global writeLock
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
    outputFilePrefix = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # Create output file
    if not args.output_file:
        if args.html:
            outputFile = outputFilePrefix + "_analysis.html"
            open(outputFile, "a").write(htmlHeader)
        else:
            outputFile = outputFilePrefix + "_analysis.md"
    else:
        outputFile = args.output_file
        if args.html:
            open(outputFile, "a").write(htmlHeader)
            
    # Get log files
    if args.log_files:
        logFileList = getLogFilesFromCommandLine()
    elif args.directory:
        if not args.skip_tar:
            extractAllTarFiles(args.directory)
        logFileList = getLogFilesFromDirectory(args.directory)
    else:
        logger.info("Please specify a log file, or directory")
        exit(1)

    # Check if log files were found
    if type(logFileList) is not list:
        logger.warning("No log files found")
        exit(1)

    # Add number of tablets per node to the output file in table format
    if args.html:
        open(outputFile, "a").write("<h2 id=tablets-per-node> Number of tablets per node </h2>")
        open(outputFile, "a").write("<table class='sortable' id='tablets-table'>")
        open(outputFile, "a").write("<tr><th>Node</th><th>Number of Tablets</th></tr>")
        for key, value in getNumTabletsPerNode().items():
            open(outputFile, "a").write("<tr><td>" + key + "</td><td>" + str(value) + "</td></tr>")
        open(outputFile, "a").write("</table>")
    else:
        open(outputFile, "a").write("\n\n\n# Number of tablets per node\n\n")
        for key, value in getNumTabletsPerNode().items():
            open(outputFile, "a").write("- " + key + ": " + str(value) + "\n")

    masterConfFile = None
    tserverConfFile = None
    for root, dirs, files in os.walk(args.directory):
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

    if allGFlags:
        if args.html:
            open(outputFile, "a").write("<h2 id=gflags> GFlags </h2>")
            open(outputFile, "a").write("<table class='sortable' id='gflags-table'>")
            open(outputFile, "a").write("<tr><th>Flag</th><th>Master</th><th>TServer</th></tr>")
            for flag in allGFlags:
                open(outputFile, "a").write("<tr><td> <a href='https://github.com/search?q=repo%3Ayugabyte%2Fyugabyte-db+" + flag + "+language%3AXML++NOT+is%3Aarchived+path%3A%2F%5Emanaged%5C%2Fsrc%5C%2Fmain%5C%2Fresources%5C%2Fgflags_metadata%5C%2F%2F&type=code'>" + flag + "</a></td>")
                if masterConfFile and tserverConfFile:
                    open(outputFile, "a").write("<td>" + gflags["master"].get(flag, "-") + "</td>")
                    open(outputFile, "a").write("<td>" + gflags["tserver"].get(flag, "-") + "</td></tr>")
                elif masterConfFile:
                    open(outputFile, "a").write("<td>" + gflags["master"].get(flag, "-") + "</td>")
                    open(outputFile, "a").write("<td> - </td></tr>")
                elif tserverConfFile:
                    open(outputFile, "a").write("<td> - </td>")
                    open(outputFile, "a").write("<td>" + gflags["tserver"].get(flag, "-") + "</td></tr>")
            open(outputFile, "a").write("</table>")
            open(outputFile, "a").write("<p> Note: The GFlags listed above are from only one of the nodes. So, placement related flags might be different on other nodes. Also, The list does not include the default values and the values set at runtime. </p>")
        else:
            open(outputFile, "a").write("\n\n\n# GFlags\n\n")
            for flag in allGFlags:
                open(outputFile, "a").write("- " + flag + "\n")
                if masterConfFile and tserverConfFile:
                    open(outputFile, "a").write("  - Master: " + gflags["master"].get(flag, "-") + "\n")
                    open(outputFile, "a").write("  - TServer: " + gflags["tserver"].get(flag, "-") + "\n")
                elif masterConfFile:
                    open(outputFile, "a").write("  - Master: " + gflags["master"].get(flag, "-") + "\n")
                elif tserverConfFile:
                    open(outputFile, "a").write("  - TServer: " + gflags["tserver"].get(flag, "-") + "\n")
    
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
            open(outputFile, "a").write("<h2 id=troubleshooting-tips> Troubleshooting Tips </h2>\n")
            solutionMarkdown = "`"
            for error in listOfErrorsInAllFiles:
                solution = getSolution(error)
                solutionMarkdown += """### {}\n{}  \n\n---\n\n""".format(error, solution).replace('`','\`')
            solutionMarkdown += "`"
            open(outputFile, "a").write("""<script>htmlGenerator = new showdown.Converter();\n""")
            open(outputFile, "a").write("""solutionsHTML = htmlGenerator.makeHtml({})\n""".format(solutionMarkdown))
            open(outputFile, "a").write("""document.write(solutionsHTML);""")
            open(outputFile, "a").write("""</script>""")
        else:
            # Write troubleshooting tips
            open(outputFile, "a").write("\n\n\n# Troubleshooting Tips\n\n")
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

    # if hostname == "lincoln" then copy file to directory /tmp
    if os.uname()[1] == "lincoln":
        os.system("cp " + outputFile + " /home/support/logs_analyzer_dump")
        logger.info("open http://lincoln:7777/" + outputFile + " to view the analysis")

    print("tserver list: ", getTserversList())
    print("master list: ", getMastersList())
    print("Number of tablets per node: ", getNumTabletsPerNode())