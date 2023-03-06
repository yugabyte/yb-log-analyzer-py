#!/usr/bin/env python
from analyzer_dict import regex_patterns, solutions
from collections import OrderedDict
import datetime
import argparse
import re
import os
import tabulate
import tarfile
import gzip
from histogram import *

# Command line arguments

parser = argparse.ArgumentParser(description="Log Analyzer for YugabyteDB logs")
parser.add_argument("-l", "--log_files", nargs='+', help="List of log file[s]")
parser.add_argument("-d", "--directory", help="Directory containing log files")
parser.add_argument("--support_bundle", help="Path to support bundle")
parser.add_argument("-H", "--histogram", action="store_true", help="Generate histogram graph")
parser.add_argument("-wc",'--word_count', action="store_true",help='List top 20 word count')
parser.add_argument('-A','--ALL', action="store_true", help='FULL Health Check')
parser.add_argument("-t", "--from_time", metavar= "MMDD HH:MM", dest="start_time", help="Specify start time")
parser.add_argument("-T", "--to_time", metavar= "MMDD HH:MM", dest="end_time", help="Specify end time")
parser.add_argument("-s", "--sort-by", dest="sort_by", help="Sort by: \n NO = Number of occurrences, \n LO = Last Occurrence,\n FO = First Occurrence(Default)")
args = parser.parse_args()

start_time = datetime.datetime.strptime(args.start_time, "%m%d %H:%M") if args.start_time else None
end_time = datetime.datetime.strptime(args.end_time, "%m%d %H:%M") if args.end_time else None
outputFile = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_analysis.txt"

def getLogFilesFromCommandLine():
    logFiles = []
    for file in args.log_files:
        # Check if this is file or directory
        if os.path.isfile(file):
            logFiles.append(file)
    return logFiles

def getLogFilesFromDirectory(logDirectory):
    print("Getting log files from directory: {}".format(logDirectory))
    logFiles = []
    for root, dirs, files in os.walk(logDirectory):
        for file in files:
            if file.__contains__("INFO"):
                logFiles.append(os.path.join(root, file))
    return logFiles

def getLogFilesFromSupportBundle(supportBundle):
    logFiles = []
    if supportBundle.endswith(".tar.gz"):
        tarFile=tarfile.open(supportBundle, "r:gz")
        support_bundle="support_bundle_{}".format(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        tarFile.extractall(support_bundle)
        tarFile.close()
        for root, dirs, files in os.walk(support_bundle):
            for file in files:
                if file.__contains__("INFO") and file[0] != ".":
                    logFiles.append(os.path.join(root, file))
        return logFiles
    else:
        logFiles = getLogFilesFromDirectory(supportBundle)
        return logFiles

def getTimeFromLog(line):
    timeFromLog = line.split(" ")[0][1:] + " " + line.split(" ")[1][:5]
    timestamp = datetime.datetime.strptime(timeFromLog, "%m%d %H:%M")
    return timestamp

def analyzeLogFiles(logFile, start_time=None, end_time=None):
    lines = logFile.readlines()                                                                                                             # Read all the lines in the log file
    results = {}                                                                                                                      # Dictionary to store the results
    for line in lines:                                                                                                                # For each line in the log file           
        for message, pattern in regex_patterns.items():                                                                                     # For each message and pattern
            match = re.search(pattern, line)                                                                                                # Search for the pattern in the line
            if match and (not start_time or getTimeFromLog(line) >= start_time) and (not end_time or getTimeFromLog(line) <= end_time):     # If the pattern is found in the line and the line is within the time range          
                if message not in results:                                                                                                     # If the message is not in the results dictionary, add it
                    results[message] = {                                                                                                           # Initialize the dictionary for the message
                        "numOccurrences": 0,                                                                                                          # Number of occurrences of the message
                        "firstOccurrenceTime": None,                                                                                                 # Time of the first occurrence of the message
                        "lastOccurrenceTime": None,                                                                                                  # Time of the last occurrence of the message
                        "solution": solutions[message],                                                                                                # Solution for the message
                    }                                                                                                                              # End of dictionary for the message            
                results[message]["numOccurrences"] += 1                                                                                       # Increment the number of occurrences of the message
                time = line.split()[0][1:] + " " + line.split()[1]                                                                             # Get the time from the log line
                if not results[message]["firstOccurrenceTime"]:                                                                              # If the first occurrence time is not set
                    results[message]["firstOccurrenceTime"] = time                                                                               # set it 
                results[message]["lastOccurrenceTime"] = time                                                                                # Set time as last occurrence time
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
                info["solution"],
            ]
        )
    return table
    
def get_histogram(logFile):
   print ("\nHistogram of logs creating time period\n")
   histogram(logFile)
   
def get_word_count(logFile):
   print ("\nMost widely used word in logs\n")
   word_count(logFile)

if __name__ == "__main__":
    if args.log_files:
        logFileList = getLogFilesFromCommandLine()
    elif args.directory:
        logFileList = getLogFilesFromDirectory(args.directory)
    elif args.support_bundle:
        logFileList = getLogFilesFromSupportBundle(args.support_bundle)
    else:
        print("Please specify a log file, directory or support bundle")
        exit(1)

    if type(logFileList) is not list:
        print("No log files found")
        exit(1)
    print("Log files to analyze: {}".format(logFileList))
    for logFile in logFileList:
        if logFile.endswith(".gz"):
            open(outputFile, "a").write("\n\n\nAnalysis of " + logFile + "\n\n")
            with gzip.open(logFile, "rt") as f:
                open(outputFile, "a").write(tabulate.tabulate(analyzeLogFiles(f, start_time, end_time), headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence", "Troubleshooting Tips"], tablefmt="simple_grid"))
        else:
            open(outputFile, "a").write("\n\n\nAnalysis of " + logFile + "\n\n")
            with open(logFile, "r") as f:
                open(outputFile, "a").write(tabulate.tabulate(analyzeLogFiles(f, start_time, end_time), headers=["Occurrences", "Message", "First Occurrence", "Last Occurrence", "Troubleshooting Tips"], tablefmt="simple_grid"))
        if args.histogram or args.ALL:
           get_histogram(logFile)
        if args.word_count or args.ALL:
           get_word_count(logFile)
    print("Analysis complete. Results are in " + outputFile)
    
    
    