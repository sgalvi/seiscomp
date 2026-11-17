############################################################################
# Copyright (C) 2024 gempa GmbH                                            #
#                                                                          #
# All Rights Reserved.                                                     #
#                                                                          #
# NOTICE: All information contained herein is, and remains                 #
# the property of gempa GmbH and its suppliers, if any. The intellectual   #
# and technical concepts contained herein are proprietary to gempa GmbH    #
# and its suppliers.                                                       #
# Dissemination of this information or reproduction of this material       #
# is strictly forbidden unless prior written permission is obtained        #
# from gempa GmbH.                                                         #
############################################################################


import glob
import os
import re
import sys

from lib import log, utils
from lib.const import EXIT_SUCCESS, EXIT_FAILURE


def getFilesList(path):
    try:
        return utils.naturalSorted(
            glob.glob(os.path.join(path, "*.so.*.*.*")), reverse=True
        )
    except OSError as err:
        print(err, file=sys.stderr)

    return None


def getLinkList(fileNames):
    linkMap = {}
    linkMap_so = {}

    for fileName in fileNames:
        match = re.search(r"(.+)\.so\.(\d+).(\d+).(\d+)", fileName)
        if not match:
            continue

        name = match.group(1)
        major = match.group(2)

        extendFileName = os.path.basename(name) + ".so." + major
        if not extendFileName in linkMap.values():
            linkMap.update(
                {os.path.basename(fileName): os.path.basename(extendFileName)}
            )

    for src, dst in linkMap.items():
        match = re.search(r"(.+)\.so\.(\d)", src)
        basename = match.group(1) + ".so"
        if not basename in linkMap_so.values():
            linkMap_so.update({dst: basename})

    for src, dst in linkMap_so.items():
        linkMap.update({src: dst})

    return linkMap


def removeDeadLinks(path):
    if not os.path.isdir(path):
        return True

    for fileName in glob.glob(os.path.join(path, "*.so*")):
        if not os.path.islink(fileName) or os.path.exists(fileName):
            continue
        try:
            os.remove(fileName)
        except OSError as err:
            log.logError(f"Can't remove dead library link: {err}")
            return False

    return True


def createSymLinks(linkMap, path):
    if not os.path.isdir(path):
        return True

    try:
        os.chdir(os.path.join(os.getcwd(), path))
    except OSError as err:
        log.logError(f"Can't create library links: {err}")
        return False

    for src, dst in linkMap.items():
        try:
            os.remove(dst)
        except OSError as err:
            if os.path.isfile(dst):
                log.logError(f"Can't create library links: {err}")
                return False
        try:
            os.symlink(src, dst)
        except OSError as err:
            log.logError(f"Can't create library links: {err}")
            return False
    return True


def main():
    if len(sys.argv) != 2:
        print("\nmakelinks.py - Repairs broken links\n")
        print(f"Usage: {sys.argv[0]} <directory>")
        return EXIT_FAILURE

    fileList = getFilesList(sys.argv[1])
    linkList = getLinkList(fileList)
    return EXIT_SUCCESS if createSymLinks(linkList, sys.argv[1]) else EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
