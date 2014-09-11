#!/usr/bin/env python -u
import os, sys, json
import subprocess
from pprint import pprint
from optparse import OptionParser
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from datetime import datetime
# Awesome, there is numpy in CMSSW env
from numpy import mean, std

### TODO: try to optimize it
### TODO: I'm cleaning up the write metrics because it looks like it's completely unreliable
### TODO: read metrics are also not very reliable, but ... let's keep them a bit longer

def buildStrucOfArrays(logCollects, metrics, writeOut = None):
    """
    It will create a dict of arrays where the key names are written only once, so
    taking much less memory to store the whole structure
    """
    dictRun, results = [{}, {}], [{}, {}]

    for i, _ in enumerate(dictRun):
        for m in metrics:
            dictRun[i][m] = []

    numLogCollects = 0
    for logCollect in logCollects:
        numLogCollects += 1
        print "%s: processing logCollect number: %d" % (datetime.now().time(), numLogCollects)
        # uncompress the big logCollect
        command = ["tar", "xvf", logCollect]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        logArchives = out.split()
        for logArchive in logArchives:
            print logArchive
            # then uncompress each tarball inside the big logCollect
            subcommand = ["tar", "-x", "cmsRun?/FrameworkJobReport.xml", "-zvf", logArchive]
            q = subprocess.Popen(subcommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = q.communicate()
            cmsRuns = sorted(out.split())
            for i, step in enumerate(cmsRuns):
                try:
                    xmldoc = minidom.parse(step)
                except ExpatError:
                    print "Ops, that's a very BAD file %s" % step
                    continue
                items = ( (item.getAttribute('Name'),item.getAttribute('Value')) for item in xmldoc.getElementsByTagName('Metric') )
                matched = [item for item in items if item[0] in metrics ]
                xmldoc.unlink()
                for ele in matched:
                    if ele[0] != 'CPUModels':
                        dictRun[i][ele[0]].append(float(ele[1]))
                    else:
                        dictRun[i][ele[0]].append(str(ele[1]))

    print "%s: calculating metrics now ..." % (datetime.now().time())
    for j, step in enumerate(dictRun):
        if not step:
            continue
        for k, v in step.iteritems():
            if not v:
                continue
            elif k == 'CPUModels':
                results[j][k] = list(set(v))
                continue
            results[j][k] = {}
            # Rounding in 3 digits to be nicely viewed
            results[j][k]['avg'] = "%.3f" % mean(v)
            results[j][k]['std'] = "%.3f" % std(v)
            results[j][k]['min'] = "%.3f" % min(v)
            results[j][k]['max'] = "%.3f" % max(v)

    # Printing outside the upper for, so we can kind of order it...
    for i, step in enumerate(results):
        if not step:
            continue
        print "\nResults for cmsRun%s:" % str(i+1)
        for metric in metrics: 
            print "%-47s : %s" % (metric, step[metric])

    # Debug
    #pprint(dictRun)
                   
    if writeOut:
        print ""   
        for i, step in enumerate(dictRun):
            if not step['TotalJobTime']:
                continue
            filename = 'cmsRun' + str(i+1) + '_' + writeOut
            print "Dumping whole cmsRun%d json into %s" % (i+1, filename)
            with open(filename, 'w') as outFile:
                json.dump(step, outFile)
                outFile.close()
    return

def main():
    """
    Provide a logCollect tarball as input (in your local machine) or a text file
    with their name.

    export SCRAM_ARCH=slc5_amd64_gcc462
    cd /build/relval/CMSSW_5_3_0/src/
    cmsenv
    """
    usage = "Usage: %prog -t tarball -i inputFile [-o outputFile] [--long] [--array] [--dic]"
    parser = OptionParser(usage = usage)
    parser.add_option('-t', '--tarball', help = 'Tarball for the logCollect jobs', dest = 'tar')
    parser.add_option('-i', '--inputFile', help = 'Input file containing the logCollect tarball names', dest = 'input')
    parser.add_option('-o', '--outputFile', help = 'Output file containing info in json format', dest = 'output')
    parser.add_option('-l', '--long', action = "store_true", 
                      help = 'Use it to make a long summary (27 metrics in total)', dest = 'long')
    parser.add_option('-a', '--array', action = "store_true", help = 'Produces a structure of arrays', dest = 'array')
    parser.add_option('-d', '--dic', action = "store_true", help = 'Produces an array of dictionaries', dest = 'dict')
    (options, args) = parser.parse_args()
    if not options.tar and not options.input:
        parser.error('You must either provide a logCollect tarball or a file with their names')
        sys.exit(1)
    if not options.array and not options.dict:
        parser.error('You must choose which data structure you want to build')
        sys.exit(1)

    if options.long:
        metrics = ["Timing-file-read-maxMsecs","Timing-tstoragefile-read-maxMsecs",
                   "Timing-tstoragefile-readActual-maxMsecs","Timing-file-read-numOperations",
                   "Timing-tstoragefile-read-numOperations","Timing-tstoragefile-readActual-numOperations",
                   "Timing-file-read-totalMegabytes","Timing-tstoragefile-read-totalMegabytes",
                   "Timing-tstoragefile-readActual-totalMegabytes","Timing-file-read-totalMsecs",
                   "Timing-tstoragefile-read-totalMsecs","Timing-tstoragefile-readActual-totalMsecs",
                   "Timing-file-write-maxMsecs","Timing-tstoragefile-write-maxMsecs",
                   "Timing-tstoragefile-writeActual-maxMsecs","Timing-file-write-numOperations",
                   "Timing-tstoragefile-write-numOperations","Timing-tstoragefile-writeActual-numOperations",
                   "Timing-file-write-totalMegabytes","Timing-tstoragefile-write-totalMegabytes",
                   "Timing-tstoragefile-writeActual-totalMegabytes","Timing-file-write-totalMsecs",
                   "Timing-tstoragefile-write-totalMsecs","Timing-tstoragefile-writeActual-totalMsecs",
                   "AvgEventTime", "TotalJobTime","CPUModels","averageCoreSpeed","totalCPUs"]
    else:
#        metrics = ["Timing-file-read-maxMsecs","Timing-file-read-numOperations",
#                   "Timing-file-read-totalMegabytes","Timing-file-read-totalMsecs",
#                   "Timing-file-write-totalMegabytes","AvgEventTime","TotalJobTime","TotalJobCPU"]
        metrics = ["Timing-tstoragefile-read-maxMsecs","Timing-tstoragefile-read-numOperations",
                   "Timing-tstoragefile-read-totalMegabytes","Timing-tstoragefile-read-totalMsecs",
                   "Timing-file-write-totalMegabytes","AvgEventTime","TotalJobTime","TotalJobCPU",
                   "CPUModels","averageCoreSpeed","totalCPUs"]

    if options.tar:
        logCollects = [options.tar]
    elif options.input:
        logCollects = []
        f = open(options.input, 'r')
        for tar in f:
            tar = tar.rstrip('\n')
            logCollects.append(tar)

    if options.array:
        # the array index defines a job (dict1 is cmsRun1, dict2 is cmsRun2) 
        # e.g. [{'AvgEventTime': [40.41, 37.4, 46.8], 'TotalJobCPU': [7772.4, 7764.5, 8349.0], etc}]
        buildStrucOfArrays(logCollects, metrics, options.output)
    elif options.dict:
        print "NOT_IMPLEMENTED_YET"
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
        main()
