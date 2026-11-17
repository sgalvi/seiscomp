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
import sys
import re
import shutil
import textwrap

from lib import package, utils, log, gpgutils, osutils
from lib.const import (
    LINE_WIDTH,
    PT,
    EXTEND_DIR,
    DSC_EXTENSION,
    SC,
    FDSNWS_FRONTEND,
    blue,
    gray,
    reset,
    EXIT_FAILURE,
)

from lib.package import Package


class SyncCache:
    def __init__(self, config):
        self.config = config
        self._index = {}
        self._publicPackages = []
        self._extendPackages = []
        self._backupDenyPackages = []
        self._loaded = False
        self._isValid = False
        self.gpgutils = None
        if self.config.gpgVerify:
            self.initGpgUtils()

    def initGpgUtils(self):
        if self.gpgutils is None:
            try:
                self.gpgutils = gpgutils.GPGUtils(self.config)
            except (ImportError, OSError) as e:
                osutils.printImportHelper(e, "gnupg")
                sys.exit(EXIT_FAILURE)

        return self.gpgutils

    def load(self, reload=False):
        if not self._loaded or reload:
            self._loaded = True
            self._isValid = self.read()

        return self._isValid

    @property
    def index(self):
        self.load()
        return self._index

    @index.setter
    def index(self, index):
        self._loaded = True
        self._index = index

    @property
    def publicPackages(self):
        self.load()
        return self._publicPackages

    @property
    def extendPackages(self):
        self.load()
        return self._extendPackages

    @property
    def backupDenyPackages(self):
        self.load()
        return self._backupDenyPackages

    def isValid(self):
        return self.load()

    def read(self):
        def getVersion(pkg):
            return pkg.version

        self._index = {}
        self._publicPackages = []
        self._extendPackages = []
        self._backupDenyPackages = []

        if not os.path.exists(self.config.syncDir):
            return False

        try:
            modules = sorted(
                filter(
                    lambda x: x != EXTEND_DIR
                    and os.path.isdir(self.config.syncPath(x)),
                    os.listdir(self.config.syncDir),
                )
            )
        except IOError as e:
            log.logError(f"Could not read sync directory: {e}")
            return False

        for module in modules:
            packages = []

            for relPath in (self.config.archDir, self.config.noArchDir):
                d = self.config.syncPath(module, relPath)
                if not os.path.isdir(d):
                    continue

                for fileName in os.listdir(d):
                    if not fileName.endswith(DSC_EXTENSION):
                        continue

                    descFile = os.path.join(d, fileName)
                    packages.append(Package.fromFile(descFile, relPath))
            if packages:
                packages = utils.naturalSorted(packages, key=getVersion, reverse=True)
                self._index[module] = packages

        if not os.path.isdir(self.config.extendDir):
            return True

        for relPath, _, files in os.walk(self.config.extendDir):
            packages = []
            module = os.path.basename(relPath)
            for fileName in files:
                if fileName.endswith(DSC_EXTENSION):
                    descFile = os.path.join(relPath, fileName)
                    pkg = Package.fromFile(descFile, relPath)
                    if pkg.type == PT.APP:
                        pkg.directory = ""
                    packages.append(pkg)

            packages = utils.naturalSorted(packages, key=getVersion, reverse=True)
            if packages:
                self._index[module] = packages
                self._backupDenyPackages.append(packages[0].name)

        for dirName in os.listdir(self.config.extendDir):
            self._extendPackages.append(dirName)

        for name, pkgs in self._index.items():
            if any(p.isPublic() for p in pkgs):
                self._publicPackages.append(name)

        return True

    def updateIndex(self, localCache):
        if not osutils.createDirectory(self.config.syncDir):
            return False

        url = f"{self.config.dbUrl}/{self.config.dbFileName}"
        dbFile = self.config.syncPath(self.config.dbFileName)

        if not utils.download(url, dbFile, self.config.dbFileName, self.config):
            return False

        try:
            for fileName in glob.glob(self.config.syncPath("*")):
                if fileName == dbFile:
                    continue
                if os.path.isdir(fileName) and not os.path.islink(fileName):
                    shutil.rmtree(fileName)
                else:
                    os.remove(fileName)
        except OSError as err:
            log.logFailed(f"{err}")
            return False

        # utils.install() returns a tuple (ok, file count, ...): a tuple is always true
        installed, *_ = utils.install(
            self.config,
            dbFile,
            self.config.syncDir,
            self.config.dbFileName,
            localCache,
        )
        if not installed:
            return False

        if not self.load(reload=True):
            return False

        self.makeFdsnwsFrontendReleaseLink()
        return True

    def makeFdsnwsFrontendReleaseLink(self):
        try:
            releases = os.listdir(self.config.syncPath(SC))
        except FileNotFoundError:
            return

        for release in releases:
            try:
                os.symlink(
                    "wa-angular-unused",
                    self.config.syncPath(FDSNWS_FRONTEND, release),
                )
            except (FileExistsError, FileNotFoundError):
                pass

    def setIndex(self, localIndex):
        self.index = localIndex

    def mergeIndex(self, packages):
        if self.index is None:
            self.index = {}

        self.index.update(packages)

    def getIndex(self):
        return self.index

    def contains(self, checkPackages, info=True):
        not_found = []
        for name in checkPackages:
            if not self.getPackages(name):
                not_found.append(name)

        if not_found:
            if info:
                log.logError(f"Unable to locate {self.notFoundMessage(not_found)}")
            return False

        return True

    def notFoundMessage(self, names, prefix=True):
        if isinstance(names, str):
            names = [names]
        names = ", ".join(f"{blue}{name}{reset}" for name in names)

        return (
            f"{'package ' if prefix else ''}{names} for"
            f" {self.config.os}/{self.config.os_version} ({self.config.arch})"
            f" (Release: {self.config.release})"
        )

    def getPackage(self, name):
        try:
            return self.getPackages(name)[0]
        except IndexError:
            return None

    @log.trace
    def getPackages(self, name):
        if isinstance(name, str) and "=" in name:
            key, version = name.split("=", 1)
            pkgs = self.index.get(key, [])
            matchingPkgs = [pkg for pkg in pkgs if pkg.version == version]
            return matchingPkgs if matchingPkgs else []

        return self.index.get(name, [])

    def infoPackages(self, url, packages=None, showAll=False, filterNames=None):
        if not packages:
            if len(url):
                print(f"Package URL: {url}\n")
            header = "Available packages"

            if not self.index:
                print(
                    f"No packages available. Please run {self.config.gsmCall} sync"
                )
                return True

            max_name_len = len(max(self.index.keys(), key=len))
            max_name_len = min(max(max_name_len, len(header)), 30)

            min_table_cols = max_name_len + 25

            try:
                cols = os.get_terminal_size().columns
            except OSError:
                cols = LINE_WIDTH

            if cols < min_table_cols:
                print(header)
                print(f"{gray}{''.ljust(len(header), '-')}{reset}")
                indent = "".ljust(min(cols, 4))
                for name in sorted(self.index):
                    if not self.getPackages(name):
                        continue
                    if filterNames:
                        if not name in filterNames:
                            continue

                    desc = (
                        self.index[name][0].desc.strip()
                        if self.index.get(name)
                        else None
                    )
                    print(f"{blue}{name}{reset}")
                    if desc:
                        print(
                            textwrap.fill(
                                desc,
                                width=cols,
                                initial_indent=indent,
                                subsequent_indent=indent,
                            )
                        )
            else:
                print(f"{header: <{max_name_len:}}  Description")
                print(f"{gray}{''.ljust(max_name_len, '-')}  -----------{reset}")
                indent = "".ljust(max_name_len + 2)
                for name in sorted(self.index):
                    if not self.getPackages(name):
                        continue
                    if filterNames:
                        if name not in filterNames:
                            continue
                    desc = (
                        self.index[name][0].desc.strip()
                        if self.index.get(name)
                        else None
                    )
                    nameField = f"{name: <{max_name_len:}}"
                    if desc:
                        try:
                            wrapped = textwrap.fill(
                                f"{nameField}  {desc}",
                                width=cols,
                                subsequent_indent=indent,
                            )
                            print(
                                f"{blue}{nameField}{reset}"
                                f"{wrapped[len(nameField):]}"
                            )
                        except UnicodeEncodeError:
                            print(f"{blue}{name}{reset}")
                    else:
                        print(f"{blue}{name}{reset}")

            return True

        first = True
        failed = []
        for name in packages:
            if name not in self.index:
                failed.append(name)
                continue

            pkgs = self.index.get(name, [])
            for i, pkg in enumerate(pkgs, start=1):
                first = not first and print("")
                header = name
                if showAll:
                    header += f" [{i}/{len(pkgs)}]"
                print(f"{blue}{header}{reset}")
                print(f"{gray}{''.ljust(max(len(header), 10), '-')}{reset}")
                pkg.showInfo("None", "None", False)
                if not showAll:
                    break
        if failed:
            log.logError(f"Package not found: {self.notFoundMessage(failed, False)}")

        return True

    def search(self, patterns):
        regexes = []
        for pattern in patterns:
            regexes.append(re.compile(pattern, re.IGNORECASE))

        matchedPkgs = {}
        for name in self.index:
            if all(regex.match(name) for regex in regexes):
                try:
                    pkg = self.index.get(name)[0]
                    matchedPkgs[name] = pkg
                except IndexError:
                    pass

        for name in sorted(self.index):
            try:
                pkgs = self.index.get(name, [])
                for pkg in pkgs:
                    for keyword in pkg.keywords.split():
                        if all(regex.search(keyword) for regex in regexes):
                            matchedPkgs[name] = pkg
            except IndexError:
                pass

        if not matchedPkgs:
            return False

        for name, pkg in matchedPkgs.items():
            print(f"{pkg.name} - {pkg.desc}")

        return True

    @log.trace
    def checksumCheck(self, name):
        if not osutils.createDirectory(self.config.downloadDir):
            return False

        pkg = self.getPackage(name)
        if not pkg:
            log.logError(f"Could not find package in index: {name}")
            return False

        fileName = self.config.packagePath(pkg)
        return utils.hashfile(fileName, pkg.checksum, pkg)

    def gpgCheck(self, name):
        if self.config.gpgVerify:
            if not osutils.createDirectory(self.config.downloadDir):
                return False

            pkg = self.getPackage(name)
            if not pkg:
                print(f"\n{self.notFoundMessage(name)}")
                return False

            fileName = self.config.packagePath(pkg)
            if pkg.sigFile:
                return self.initGpgUtils().verifyFile(fileName, pkg.sigFile, True)
            log.logWarning(f"No signature file for package: {name}")

        return True

    @log.trace
    def downloadPackages(self, packages):
        downloaded = []

        if not osutils.createDirectory(self.config.downloadDir):
            return downloaded

        for name in packages:
            pkg = self.getPackage(name)
            if not pkg:
                log.logError(f"Unable to locate {self.notFoundMessage(name)}")
                continue

            if pkg.localDir:
                downloaded.append(name)
                continue

            try:
                if package.download(pkg, self.config):
                    downloaded.append(name)
            except Exception as err:
                log.logError(f"{err}")

        return downloaded
