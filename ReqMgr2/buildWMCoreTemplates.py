#!/usr/bin/env python
"""
Run it from vocms049 with your proxy in the environment
"""
from __future__ import print_function

import sys
import os
import random
import json
import httplib


def getRequestDict(workflow):
    url = "cmsweb.cern.ch"
    headers = {"Content-type": "application/json",
               "Accept": "application/json"}
    conn = httplib.HTTPSConnection(url, cert_file=os.getenv('X509_USER_PROXY'),
                                   key_file=os.getenv('X509_USER_PROXY'))
    urn = "/reqmgr2/data/request/%s" % workflow
    conn.request("GET", urn, headers=headers)
    r2 = conn.getresponse()
    request = json.loads(r2.read())["result"][0]
    return request[workflow]


def updateRequestDict(reqDict):
    """
    Remove some keys from the original dict and build the
    structure expected by the reqmgr client script.
    """
    paramBlacklist = ['AllowOpportunistic', 'AutoApproveSubscriptionSites', 'BlockCloseMaxEvents', 'BlockCloseMaxFiles', 'BlockCloseMaxSize',
                      'BlockCloseMaxWaitTime', 'CouchURL', 'CouchWorkloadDBName', 'CustodialGroup', 'CustodialSites', 'CustodialSubType',
                      'Dashboard', 'DeleteFromSource', 'GracePeriod', 'Group', 'HardTimeout', 'InitialPriority', 'InputDatasets',
                      'MaxMergeEvents', 'MaxMergeSize', 'MaxVSize', 'MergedLFNBase', 'MinMergeSize',
                      'NonCustodialGroup', 'NonCustodialSites', 'NonCustodialSubType', 'OutputDatasets', 'ReqMgr2Only', 'RequestDate',
                      'RequestName', 'RequestSizeFiles', 'RequestStatus', 'RequestTransition', 'RequestWorkflow',
                      'RequestorDN', 'SiteWhitelist', 'SoftTimeout', 'SoftwareVersions', 'SubscriptionPriority',
                      'Team', 'Teams', 'TotalEstimatedJobs', 'TotalInputEvents', 'TotalInputFiles', 'TotalInputLumis', 'TotalTime',
                      'TrustPUSitelists', 'TrustSitelists', 'UnmergedLFNBase', '_id', 'inputMode', 'timeStamp',
                      'DN', 'DQMHarvestUnit', 'DashboardHost', 'DashboardPort', 'EnableNewStageout', 'FirstEvent',
                      'FirstLumi', 'PeriodicHarvestInterval', 'RobustMerge', 'RunNumber', 'ValidStatus', 'VoGroup',
                      'VoRole', 'dashboardActivity', 'mergedLFNBase', 'unmergedLFNBase', 'MaxWaitTime']


    createDict = {}
    for key, value in reqDict.items():
        if key in paramBlacklist or value in ([], {}, None, ''):
            continue
        elif key == 'OpenRunningTimeout':
            continue
        elif key == 'Campaign':
            createDict[key] = "Campaign-OVERRIDE-ME"
        elif key == 'RequestString':
            createDict[key] = "RequestString-OVERRIDE-ME"
        elif key == 'DQMUploadUrl':
            createDict[key] = "https://cmsweb-testbed.cern.ch/dqm/dev"
        elif key == 'DbsUrl':
            createDict[key] = "https://cmsweb-testbed.cern.ch/dbs/int/global/DBSReader/"
        elif key == 'RequestPriority':
            createDict[key] = min(value + 100000, 999999)
        elif key == 'PrepID':
            createDict[key] = 'TEST-' + value
        elif key in ['ConfigCacheURL', 'ConfigCacheUrl']:
            createDict['ConfigCacheUrl'] = value
        else:
            createDict[key] = value

    createDict['Comments'] = ""
    createDict['Requestor'] = "amaltaro"
    newSchema = {'createRequest': createDict}
    if createDict['RequestType'] in ['TaskChain', 'StepChain']:
        handleTasksSteps(createDict)
    newSchema['assignRequest'] = handleAssignmentParams(createDict)

    return newSchema

def handleTasksSteps(reqDict):
    """
    Remove/overwrite some values
    """
    if 'TaskChain' in reqDict:
      name = 'Task'
      number = reqDict['TaskChain']
    else:
      name = 'Step'
      number = reqDict['StepChain']
    for i in range(1, number + 1):
        thisDict = name + str(i)
        for k in reqDict[thisDict].keys():
            # remove empty stuff
            if not reqDict[thisDict][k]:
                reqDict[thisDict].pop(k)
            elif k == 'ProcessingString':
                reqDict[thisDict][k] = "%s%s_WMCore_TEST" % (name, i)


def handleAssignmentParams(reqDict):
    """
    Add some predefined assignment parameters to the template
    """
    assignDict = {"SiteWhitelist": ["SiteWhitelist-OVERRIDE-ME"],
                  "Team": "Team-OVERRIDE-ME",
                  "AcquisitionEra": "AcquisitionEra-OVERRIDE-ME",
                  "ProcessingString": "ProcessingString-OVERRIDE-ME",
                  "Dashboard": "Dashboard-OVERRIDE-ME",
                  "ProcessingVersion": 19,
                  "MergedLFNBase": "/store/backfill/1",
                  "UnmergedLFNBase": "/store/unmerged",
                  "MaxRSS": reqDict.pop('MaxRSS'),
                  "MaxVSize": 40000000,
                  "SoftTimeout": 129600,
                  "GracePeriod": 300,
                  "SiteBlacklist": [],
                  #                                "TrustSitelists": False,
                  #                                "TrustPUSitelists": False,
                  #                                "MinMergeSize": 2147483648,
                  #                                "MaxMergeSize": 4294967296,
                  #                                "MaxMergeEvents": 50000,
                  #                                "CustodialSites": [],
                  #                                "NonCustodialSites": [],
                  #                                "AutoApproveSubscriptionSites": [],
                  #                                "SubscriptionPriority": "Low",
                  #                                "CustodialSubType": "Move",
                  #                                "BlockCloseMaxWaitTime": 14400,
                  #                                "BlockCloseMaxFiles": 500,
                  #                                "BlockCloseMaxEvents": 200000000,
                  #                                "BlockCloseMaxSize": 5000000000000
                 }

    for k in ['AcquisitionEra', 'ProcessingString']:
        if isinstance(reqDict[k], dict):
            assignDict[k] = {}
            for task, _ in reqDict[k].iteritems():
                assignDict[k][task] = k + "-OVERRIDE-ME"

    return assignDict


def createJsonTemplate(reqDict):
    """
    Create a json file based on the request type and a
    pseudo-random integer, just to avoid dups...
    """
    aNumber = str(random.randint(1, 1000))
    fileName = reqDict['createRequest']['RequestType'] + '_' + aNumber + '.json'
    with open(fileName, 'w') as outFile:
        json.dump(reqDict, outFile, indent=4, sort_keys=True)
    print("File %s successfully created." % fileName)


def main():
    if len(sys.argv) != 2:
        print("You must provide a request name")
        sys.exit(1)

    reqName = sys.argv[1]
    origDict = getRequestDict(reqName)
    newDict = updateRequestDict(origDict)
    createJsonTemplate(newDict)


if __name__ == "__main__":
    main()
