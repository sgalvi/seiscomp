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


import copy
import glob
import os
import shutil
import sys
import tarfile
from time import gmtime, strftime
from datetime import datetime
from pathlib import Path


from lib import makelinks, osutils, package, utils, log, versions
from lib.cache import custominstall
from lib.const import (
    NIGHTLY,
    PRIVILEGE_COMMAND,
    PT,
    FILE_ENCODING,
    FORMAT,
    DEFAULT_TIME_FORMAT,
    INSTALL_DESC,
    INSTALL_FILES,
    DEFAULT_DATE_FORMAT,
    MAX_LEN_TABLE_COLUMN,
    HOLD_PACKAGE_FILE,
    HOLD_FILES_FILE,
    MBTILES_EXTENSION,
    NEW_EXTENSION,
    GRD_EXTENSION,
    ARCHIVE,
    SC,
    SEISCOMP,
    GSM,
    EMAIL_GEMPA,
    PKG_SUCCESS,
    PKG_FAILED,
    PKG_NOT_FOUND,
    PKG_INVALID_VERSION,
    INSTALL,
    UPDATE,
    REMOVE,
    MSG_CONTINUE_QUESTION,
    EVENT_INSTALLED,
    EVENT_UPDATED,
    EVENT_DEINSTALLED,
    blue,
    gray,
    reset,
    EXIT_SUCCESS,
    EXIT_FAILURE,
    HASH_PATTERN,
    DATE_REGEXP,
)
from lib.package import Package


def licenseOlderThanVersion(updatesUntil, version):
    if DATE_REGEXP.match(updatesUntil) and DATE_REGEXP.match(version):
        return tuple(map(int, updatesUntil.split("."))) < tuple(
            map(int, version.split("."))
        )
    return updatesUntil < version

def splitFileEntry(line):
    value, sep, member = line.partition("  ")
    if sep and HASH_PATTERN.match(value):
        return member, value

    return line, ""


class Summary:
    def __init__(
        self,
        name,
        fileCount,
        path,
        holdFiles,
        version,
        installSize,
        licenseCount=0,
        status=INSTALL,
        keptFiles=None,
    ):
        self.name = name
        self.fileCount = fileCount
        self.path = path
        self.holdFiles = holdFiles
        self.version = version
        self.installSize = installSize
        self.status = status
        self.licenseCount = licenseCount
        self.keptFiles = keptFiles or []

    def __repr__(self):
        return (
            f"<Summary {self.name}={self.version} {self.status}"
            f" files={self.fileCount}>"
        )


class LocalCache:
    def __init__(self, config):
        self.config = config
        self.index = self.read()
        self.syncCache = None
        self.holdPackageFile = self.config.localPath(HOLD_PACKAGE_FILE)
        self.holdFilesFile = self.config.localPath(HOLD_FILES_FILE)
        self.holdPackageList = {}
        self.holdFilesList = []
        self.protectedFiles = set()

    def initHoldPackagesAndFiles(self):
        retFiles = True
        retPackages = True
        if os.path.isfile(self.holdPackageFile):
            try:
                with open(self.holdPackageFile, "r", encoding=FILE_ENCODING) as f:
                    for line in f:
                        name, _, date = line.strip().partition("\t")
                        if name:
                            self.holdPackageList[name] = date or "N/A"
            except IOError as e:
                log.logError(f"Could not read package hold list: {e}")
                retPackages = False

        if os.path.isfile(self.holdFilesFile):
            try:
                with open(self.holdFilesFile, "r", encoding=FILE_ENCODING) as f:
                    self.holdFilesList = [l.strip() for l in f.readlines()]
            except IOError as e:
                log.logError(f"Could not read files hold list: {e}")
                retFiles = False

        return retPackages, retFiles

    def setSyncCache(self, cache):
        self.syncCache = cache

    def pkgDataPath(self, pkg, *parts):
        return os.path.join(pkg.dataDir or self.config.dataDir, *parts)

    def pkgLocalPath(self, pkg, *parts):
        return self.config.localPath(pkg.name, *parts)

    def read(self):
        index = {}
        if not os.path.isdir(self.config.localDir):
            return index

        for name in os.listdir(self.config.localDir):
            modulePath = self.config.localPath(name)
            if not os.path.isdir(modulePath) or name.startswith("."):
                continue

            descFile = os.path.join(modulePath, INSTALL_DESC)
            try:
                pkg = Package.fromFile(descFile, self.config.localDir)
                index[pkg.name] = pkg
            except Exception as e:
                log.logError(f"Could not read package description '{descFile}': {e}")

        return index

    def getFileInfo(self):
        fileInfo = {}
        allFiles = glob.glob(self.config.localPath("*"))
        for fileName in allFiles:
            filePath = os.path.join(fileName, INSTALL_FILES)
            pkg = self.index.get(os.path.basename(fileName))
            dirOnly = (
                pkg is not None
                and pkg.type == PT.DATA
                and not pkg.isGreensfunctions()
            )
            try:
                with open(filePath, "r", encoding=FILE_ENCODING) as f:
                    for line in f:
                        member, _ = splitFileEntry(line.rstrip())
                        fileInfo[member] = fileInfo.get(member, 0) + 1
                        if dirOnly:
                            break
            except IOError as e:
                log.logError(f"Could not read file list '{filePath}': {e}")

        return fileInfo

    def getRemovableFiles(self, pkg):
        fileInfo = {}
        fileList = []
        holdList = []
        fileCount = 0

        fileInfo = self.getFileInfo()

        if pkg.type == PT.DATA and not pkg.filePath == ARCHIVE:
            removeDir = self.pkgDataPath(pkg)
            pkg.path = self.getSummaryPath(pkg)
        elif pkg.filePath == ARCHIVE:
            removeDir = self.pkgDataPath(pkg)
            pkg.path = removeDir
        elif pkg.type == PT.CONFIG:
            removeDir = self.config.installPath
            pkg.path = removeDir
        elif pkg.type == PT.GSM:
            removeDir = self.getInstallPath(pkg)
        else:
            removeDir = self.config.installPath
            pkg.path = os.path.join(self.getInstallPath(pkg), self.config.rootDir)

        lines = self.getFileList(pkg)
        hasContent = self.hasContentList(pkg, lines)
        modified = self.getModifiedFiles(pkg)
        keptList = []

        for line in lines:
            if not hasContent and fileInfo.get(line) != 1:
                continue

            fileName = os.path.join(removeDir, line)
            if not os.path.lexists(fileName):
                log.history.debug(
                    "%s: %s does not exist anymore", pkg.name, fileName
                )

            if pkg.type == PT.CONFIG:
                candidate = fileName + NEW_EXTENSION
                if os.path.isfile(candidate):
                    fileList.append(candidate)
                if fileName in modified:
                    keptList.append(fileName)
                    continue

            if not self.isHold(fileName, True):
                fileList.append(fileName)
                if os.path.isfile(fileName) and not os.path.islink(fileName):
                    fileCount += 1
            else:
                holdList.append(fileName)

        if pkg.license != "None":
            licenseFileName = package.getLicenseFileName(pkg)
            shared = any(
                other.name != pkg.name
                and other.license != "None"
                and package.getLicenseFileName(other) == licenseFileName
                for other in self.index.values()
            )
            if not shared:
                pattern = os.path.join(
                    self.config.licenseDir, glob.escape(licenseFileName) + "*"
                )
                for filePath in sorted(glob.glob(pattern)):
                    if os.path.isfile(filePath):
                        fileList.append(filePath)
                        fileCount += 1

        if pkg.type == PT.DATA and not hasContent:
            if pkg.fileName.endswith(GRD_EXTENSION) or pkg.fileName.endswith(
                MBTILES_EXTENSION
            ):
                fileCount = 1
            else:
                fileCount = 0
                for _, _, files in os.walk(pkg.path):
                    fileCount += len(files)
        return fileList, fileCount, holdList, hasContent, keptList

    def getIndex(self):
        return self.index

    def isInstalledToday(self, installdate):
        try:
            installDate = datetime.strptime(installdate, DEFAULT_DATE_FORMAT).strftime(
                DEFAULT_TIME_FORMAT
            )
        except ValueError:
            return False

        return installDate == datetime.now().strftime(DEFAULT_TIME_FORMAT)

    def isInstalled(self, pkg, show=False):
        if not pkg:
            return False

        item = self.index.get(pkg.name)
        if item is None:
            return False

        if item.version == "VERSION":
            return True

        if self.config.release == NIGHTLY:
            same = item.version == pkg.version
        else:
            same = versions.sameVersion(item.version, pkg.version)

        if same:
            if self.config.release == NIGHTLY and pkg.type != PT.APP:
                return True

            if show:
                if item.checksum != pkg.checksum and self.isInstalledToday(
                    item.installDate
                ):
                    log.logInfo(
                        f"Force reinstall of {pkg.name} {item.version} (invalid checksum)"
                    )
                    return False

                log.logSkip(
                    f"Latest version of {pkg.name} is already installed: {item.version}"
                )
            return True

        return False

    def writeHoldList(self, holdFile, holdList, files=False):
        try:
            with open(holdFile, "w", encoding=FILE_ENCODING) as f:
                if files:
                    f.write("\n".join(holdList))
                else:
                    f.write(
                        "\n".join(f"{name}\t{date}" for name, date in holdList.items())
                    )
        except IOError as e:
            if files:
                log.logError(f"Could not write file hold list: {e}")
            else:
                log.logError(f"Could not write package hold list: {e}")
            return False
        if os.stat(holdFile).st_size == 0:
            os.remove(holdFile)
        return True

    def addHold(self, name, files=False):
        if files:
            if not os.path.isfile(name):
                log.logInfo(f"{name} does not exist ... ")
                return False

            if not name.startswith(self.config.installPath):
                log.logInfo(
                    f"The file {name} is not below the normal installation path:"
                    f" {self.config.installPath}"
                )
                return False

            if name in self.holdFilesList:
                log.logError(f"The file {name} is already on hold")
                return False

            self.holdFilesList.append(name)
            if not self.writeHoldList(self.holdFilesFile, self.holdFilesList, True):
                return False

            log.logInfo(f"Set file {name} on hold")

        else:
            if name in self.holdPackageList:
                log.logError(f"The package {name} is already on hold")
                return False

            self.holdPackageList[name] = strftime(DEFAULT_DATE_FORMAT, gmtime())

            if not self.writeHoldList(self.holdPackageFile, self.holdPackageList):
                return False

            log.logInfo(f"Set package {name} on hold")

        return True

    def removeHold(self, name, files=False):
        if files:
            if name not in self.holdFilesList:
                log.logError(f"The file {name} is not on hold")
                return False
            self.holdFilesList.remove(name)
            if not self.writeHoldList(self.holdFilesFile, self.holdFilesList, True):
                return False

            log.logInfo(f"The file {name} was removed from hold")
        else:
            if name not in self.holdPackageList:
                log.logError(f"The package {name} is not on hold")
                return False

            del self.holdPackageList[name]
            if not self.writeHoldList(self.holdPackageFile, self.holdPackageList):
                return False

            log.logInfo(f"The package {name} was removed from hold")
        return True

    def showHold(self):
        if not os.path.exists(self.holdPackageFile) and not os.path.exists(
            self.holdFilesFile
        ):
            log.logInfo("No packages/files on hold")
            return True

        if os.path.exists(self.holdPackageFile):
            pkgs = [pkg for pkg in map(self.getPackage, self.holdPackageList) if pkg]
            headerPackages, maxlenPackage = self.getMaxLen(
                "Packages", [pkg.name for pkg in pkgs]
            )
            headerVersion, maxlenVersion = self.getMaxLen(
                "Version", [pkg.version for pkg in pkgs]
            )
            headerDate, maxlenDate = self.getMaxLen(
                "Date", [self.holdPackageList[pkg.name] for pkg in pkgs]
            )
            print("")
            print(
                f"{headerPackages: <{maxlenPackage:}}  "
                f"{headerVersion: <{maxlenVersion:}}  {headerDate}"
            )
            print(
                f"{gray}{''.ljust(maxlenPackage, '-')}  "
                f"{''.ljust(maxlenVersion, '-')}  "
                f"{''.ljust(maxlenDate, '-')}{reset}"
            )
            for pkg in pkgs:
                if not self.syncCache.contains([pkg.name], False):
                    errorText = " (No longer available)"
                else:
                    errorText = ""
                print(
                    f"{blue}{pkg.name: <{maxlenPackage:}}{reset}  "
                    f"{pkg.version: <{maxlenVersion:}}  "
                    f"{self.holdPackageList[pkg.name]}{errorText}"
                )

        if os.path.exists(self.holdFilesFile):
            print("Files on hold:")
            for name in self.holdFilesList:
                if not os.path.exists(name):
                    errorText = " (No longer available)"
                else:
                    errorText = ""
                print(f"  {name}{errorText}")

        return True

    def isHold(self, name, files=False):
        if files:
            return name in self.holdFilesList or name in self.protectedFiles

        return name in self.holdPackageList

    def getPackage(self, fullname):
        name, sep, version = fullname.partition("=")
        pkg = self.index.get(name)
        if pkg is None:
            return None

        if sep and version != pkg.version:
            return None
        return pkg

    def getLicenseInfo(self, config, pkg):
        cert = utils.readCertificate(package.getLicenseFileName(pkg), config)
        if cert:
            _, _, updatesUntil, notValidAfter = utils.getLicenseTimeDelta(cert)
            return updatesUntil, notValidAfter

        return "None", "None"

    def getMaxLen(self, headerValue, value):
        maxlenValue = len(max(value, key=len)) if value else 0
        maxlenValue = min(max(maxlenValue, len(headerValue)), MAX_LEN_TABLE_COLUMN)

        return headerValue, maxlenValue

    def printInstallInfo(self):
        mismatch = osutils.osMismatchInfo(self.config)
        print(f"\n{mismatch}" if mismatch else "")

        print(
            "Installation details\n"
            f"  Configured OS:   {self.config.os}/{self.config.os_version} ({self.config.arch})\n"
            f"  Install path:    {self.config.installPath}\n"
            f"  Data path:       {self.config.dataDir}\n"
            f"  Package DB:      {self.config.localDir}"
        )
        if self.config.makeBackup:
            usedDiskSpace = osutils.du(self.config.packageBackupDir)
            print(
                f"  Package backup:  {self.config.packageBackupDir} ({usedDiskSpace})\n"
            )
        else:
            print("")

    def infoPackagesShort(self):
        installed_packages = [pkg for pkg in self.index if pkg != GSM]
        installed_packages.sort()
        self.printInstallInfo()
        print(
            f"Installed packages: {blue}{' '.join(installed_packages)}{reset}"
        )

        return True

    def infoPackages(self, packages=None):
        pkgs = list(self.index.keys())

        if not packages:
            headerPackages, maxlenPackage = self.getMaxLen("Installed packages", pkgs)

            versions = []
            datesValid = []
            datesUpdate = []
            datesInstall = []

            for name in self.index:
                pkg = self.getPackage(name)
                versions.append(pkg.version)
                dateUpdate, dateValid = self.getLicenseInfo(self.config, pkg)
                datesValid.append(dateValid)
                datesUpdate.append(dateUpdate)
                datesInstall.append(pkg.installDate)

            headerVersion, maxlenVersion = self.getMaxLen("Version", versions)
            headerDates, maxlenDates = self.getMaxLen("Valid until", datesValid)
            headerUntil, maxlenUntil = self.getMaxLen("Updates until", datesUpdate)
            headerInstall, maxlenInstall = self.getMaxLen(
                "Install date", datesInstall
            )
            self.printInstallInfo()
            print(
                f"{headerPackages: <{maxlenPackage:}}  {headerVersion: <{maxlenVersion:}}  "
                f"{headerDates: <{maxlenDates:}}  {headerUntil: <{maxlenUntil:}}  "
                f"{headerInstall}"
            )
            print(
                f"{gray}{''.ljust(maxlenPackage, '-')}  {''.ljust(maxlenVersion, '-')}  "
                f"{''.ljust(maxlenDates, '-')}  {''.ljust(maxlenUntil, '-')}  "
                f"{''.ljust(maxlenInstall, '-')}{reset}"
            )
            for name in sorted(self.index):
                pkg = self.getPackage(name)
                updatesUntil, notValidAfter = self.getLicenseInfo(self.config, pkg)

                if len(self.syncCache.getIndex()) == 0:
                    errorText = ""
                else:
                    errorText = (
                        ""
                        if self.syncCache.contains([name], False)
                        else " (no longer available)"
                    )
                if pkg.dataDir and pkg.dataDir != self.config.dataDir:
                    errorText += f" (data path: {pkg.dataDir})"

                print(
                    f"{blue}{pkg.name: <{maxlenPackage:}}{reset}  "
                    f"{pkg.version: <{maxlenVersion:}}"
                    f"  {notValidAfter: <{maxlenDates:}}  {updatesUntil: <{maxlenUntil}}"
                    f"  {pkg.installDate: <{maxlenInstall}}  {errorText:}"
                )
            return True

        first = True
        for name in packages:
            first = not first and print("")
            pkg = self.getPackage(name)
            if not pkg:
                print(f"Package not installed: {name}")
                continue
            updatesUntil, notValidAfter = self.getLicenseInfo(self.config, pkg)

            print(f"{blue}{name}{reset}")
            print(f"{gray}{''.ljust(max(len(name), 10), '-')}{reset}")
            pkg.showInfo(updatesUntil, notValidAfter, True)
            if not self.syncCache.contains([name], False):
                print(package.infoLine("Info", "No longer available"))
        return True

    def createDesc(self, pkg):
        dscFile = pkg.dscFile

        if not os.path.isfile(dscFile):
            syncPkgs = self.syncCache.getPackages(f"{pkg.name}={pkg.version}")
            if syncPkgs:
                dscFile = syncPkgs[0].dscFile

        if not os.path.isfile(dscFile):
            log.logError(
                f"Failed to create package description: {dscFile} not found"
            )
            return False

        pkgLocalDir = self.pkgLocalPath(pkg)
        installDesc = self.pkgLocalPath(pkg, INSTALL_DESC)

        if not osutils.createDirectory(pkgLocalDir):
            return False

        try:
            shutil.copyfile(dscFile, installDesc)
            with open(installDesc, "a+", encoding=FILE_ENCODING) as f:
                f.write(
                    f"\ninstalldate=('{strftime(DEFAULT_DATE_FORMAT, gmtime())}')\n"
                )
                if pkg.type == PT.DATA:
                    f.write(f"installdatadir=('{self.config.dataDir}')\n")
        except IOError as err:
            log.logError(f"Failed to create package description: {err}")
            return False

        return True

    def createFiles(self, pkg, fileList):
        fileList = fileList or []
        pkgLocalDir = self.pkgLocalPath(pkg)
        installFiles = self.pkgLocalPath(pkg, INSTALL_FILES)
        if not osutils.createDirectory(pkgLocalDir):
            return False

        try:
            with open(installFiles, "w", encoding=FILE_ENCODING) as f:
                if pkg.type == PT.DATA and not pkg.filePath == ARCHIVE:
                    if pkg.isGreensfunctions():
                        f.write(pkg.filePath + "\n")
                        f.write(pkg.filePath + ".desc\n")
                        return True

                    base = pkg.installPath or pkg.filePath
                    f.write(base + "\n")

                    rootDir = self.config.rootDir
                    for member in fileList:
                        if rootDir != SC and (
                            member == SC or member.startswith(SC + os.sep)
                        ):
                            member = rootDir + member[len(SC) :]
                        f.write(f"{os.path.join(base, member)}\n")

                    return True

                for member in fileList:
                    if pkg.type == PT.CONFIG:
                        f.write(f"{self.fileEntry(member)}\n")
                    elif pkg.filePath == ARCHIVE:
                        f.write(f"{os.path.join(ARCHIVE, Path(member))}\n")
                    else:
                        prefix = SC + os.sep
                        if member.startswith(prefix):
                            f.write(f"{member[len(prefix):]}\n")

        except OSError as err:
            log.logError(f"Failed to create package file list: {err}")
            return False

        return True

    def fileEntry(self, member):
        fileName = os.path.join(self.config.installPath, member)
        if fileName in self.protectedFiles:
            return member

        if os.path.islink(fileName) or not os.path.isfile(fileName):
            return member

        return f"{osutils.checksum(fileName)}  {member}"

    def readEntries(self, pkg):
        try:
            with open(
                self.pkgLocalPath(pkg, INSTALL_FILES), "r", encoding=FILE_ENCODING
            ) as f:
                return [splitFileEntry(line.rstrip()) for line in f if line.strip()]
        except IOError as e:
            log.logError(f"Could not read file list of '{pkg.name}': {e}")

        return []

    def getFileList(self, pkg):
        return [member for member, _ in self.readEntries(pkg)]

    def getHashes(self, pkg):
        return {
            member: value for member, value in self.readEntries(pkg) if value
        }

    def hasNoChecksums(self, pkg):
        """File list written by an older gsm: no checksums, so edits cannot be told apart."""
        if pkg.type != PT.CONFIG or pkg.name not in self.index:
            return False

        return bool(self.getFileList(pkg)) and not self.getHashes(pkg)

    def getModifiedFiles(self, pkg):
        if pkg.type != PT.CONFIG or pkg.name not in self.index:
            return set()

        hashes = self.getHashes(pkg)
        modified = set()
        for member in self.getFileList(pkg):
            fileName = os.path.join(self.config.installPath, member)
            if os.path.islink(fileName) or not os.path.isfile(fileName):
                continue
            if hashes.get(member) != osutils.checksum(fileName):
                modified.add(fileName)

        return modified

    def dropStaleHolds(self, holdFiles):
        stale = {name for name in holdFiles if not os.path.lexists(name)}
        if not stale:
            return

        self.holdFilesList = [
            name for name in self.holdFilesList if name not in stale
        ]
        self.writeHoldList(self.holdFilesFile, self.holdFilesList, True)

    def pruneEmptyDirs(self, dirNames, baseDir=None):
        base = os.path.normpath(baseDir or self.config.installPath)
        prefix = base + os.sep
        candidates = {os.path.normpath(name) for name in dirNames}
        for path in sorted(candidates, key=lambda p: p.count(os.sep), reverse=True):
            while path.startswith(prefix):
                if os.path.isdir(path):
                    try:
                        os.rmdir(path)
                    except OSError:
                        break
                path = os.path.dirname(path)

    def removeObsoleteFiles(self, pkg, oldFiles, fileList, hashes):
        if pkg.type != PT.CONFIG or not oldFiles:
            return [], []

        shipped = set(fileList or [])
        removed = []
        kept = []
        for member in oldFiles:
            # a list recorded with './' in front ('./etc/a.cfg') names the same file
            if member in shipped or os.path.normpath(member) in shipped:
                continue

            fileName = os.path.join(self.config.installPath, member)
            if os.path.islink(fileName) or not os.path.isfile(fileName):
                continue

            if hashes.get(member) != osutils.checksum(fileName):
                kept.append(fileName)
                continue

            try:
                os.remove(fileName)
                removed.append(fileName)
            except OSError as ex:
                log.logError(
                    f"{pkg.name}: could not remove {fileName}: {ex.strerror}"
                )

        self.pruneEmptyDirs({os.path.dirname(name) for name in removed})

        return removed, kept

    def writeNewCandidates(self, pkg, fileName, protected):
        written = []
        try:
            with tarfile.open(fileName, utils.tarMode(fileName)) as tar:
                for member in tar.getmembers():
                    target = os.path.join(self.config.installPath, member.name)
                    if not member.isfile() or target not in protected:
                        continue

                    source = tar.extractfile(member)
                    if source is None:
                        continue

                    with source, open(target + NEW_EXTENSION, "wb") as f:
                        shutil.copyfileobj(source, f)
                    written.append(target + NEW_EXTENSION)
        except (OSError, tarfile.TarError) as err:
            log.logError(f"{pkg.name}: could not write new configuration: {err}")

        return written

    def hasContentList(self, pkg, fileList):
        return (
            pkg.type == PT.DATA
            and not pkg.filePath == ARCHIVE
            and not pkg.isGreensfunctions()
            and len(fileList) > 1
        )

    def getInstallPath(self, pkg):
        if pkg.type == PT.GSM:
            return os.path.dirname(os.getcwd())
        if pkg.type == PT.DATA:
            if pkg.installPath:
                return self.pkgDataPath(pkg, pkg.installPath)

            return self.pkgDataPath(pkg, pkg.filePath)

        if pkg.type == PT.CONFIG:
            return self.config.installPath

        return os.path.dirname(self.config.installPath)

    def getSummaryPath(self, pkg):
        if pkg.type == PT.DATA:
            if pkg.installPath and not pkg.isGreensfunctions():
                return self.pkgDataPath(pkg, pkg.installPath)

            return self.pkgDataPath(pkg, pkg.filePath)

        installPath = self.getInstallPath(pkg)

        if pkg.type == PT.GSM:
            return installPath

        if pkg.type == PT.CONFIG:
            return self.config.installPath

        return os.path.join(installPath, self.config.rootDir)

    def checkInstallable(self, pkg, fileName, installPath):
        if not os.path.isfile(fileName):
            log.logError(f"{pkg.name}: {fileName} does not exist")
            return False

        target = wanted = installPath
        if pkg.type not in (PT.DATA, PT.CONFIG, PT.GSM):
            rootPath = wanted = os.path.join(installPath, self.config.rootDir)
            if os.path.isdir(rootPath):
                target = rootPath

        while target and not os.path.isdir(target):
            target = os.path.dirname(target)

        if target and not os.access(target, os.W_OK):
            log.logError(f"{pkg.name}: no write permission for {target}")
            print(osutils.createDirectoryHint(wanted))
            return False

        return True

    @log.trace
    def installPackage(self, pkg):
        if not pkg:
            return PKG_NOT_FOUND, None

        if pkg.format != package.FORMAT:
            required = FORMAT.get(pkg.format)
            if required is None or utils.splitVersionString(
                self.getPackage(GSM).version
            ) < utils.splitVersionString(required):
                hint = (
                    f"Please use gsm version >= {required}"
                    if required
                    else "Please use a newer gsm version"
                )
                log.logError(
                    f"{pkg.dscFile} is not compatible ({pkg.format} != {package.FORMAT})\n"
                    f"{hint}"
                )
                return PKG_INVALID_VERSION, None

        if pkg.dataDir:
            pkg = copy.copy(pkg)
            pkg.dataDir = None

        installPath = self.getInstallPath(pkg)

        holdFiles = []
        fileCount = 0

        oldPkg = self.index.get(pkg.name)
        status = UPDATE if oldPkg and oldPkg.version != pkg.version else INSTALL

        fileName = self.config.packagePath(pkg)

        if not self.checkInstallable(pkg, fileName, installPath):
            return PKG_FAILED, None

        if pkg.type not in (PT.CONFIG, PT.GSM):
            self.removePackage(pkg.name)

        currentDir = os.getcwd()

        if not osutils.checkInstallPath(self.config.installPath):
            if not osutils.createDirectory(installPath):
                return PKG_FAILED, None

        self.protectedFiles = self.getModifiedFiles(pkg)

        replacesConfig = oldPkg is not None and pkg.type == PT.CONFIG
        obsoleteFiles = self.getFileList(pkg) if replacesConfig else []
        obsoleteHashes = self.getHashes(pkg) if replacesConfig else {}
        obsoleteKept = []

        if pkg.installScript:
            ret, existFileName = utils.runCustomInstallScript(self, fileName, pkg)
            if not ret:
                log.logError(f"{pkg.installScript}' not found in {fileName}")
                return PKG_FAILED, None

            if existFileName:
                log.logError(
                    f"{os.path.basename(existFileName)} from package {pkg.name} exist"
                    f" in {os.path.join(installPath, os.path.dirname(existFileName))}"
                )
                return PKG_FAILED, None

        if pkg.filePath:
            if pkg.name == GSM:
                ret, fileCount, fileList, holdFiles = utils.untarGsm(
                    self.config, fileName, pkg, status
                )
                if not fileCount:
                    return PKG_FAILED, None

            extension = fileName[fileName.rfind(".") :]
            if (GRD_EXTENSION in extension) or (MBTILES_EXTENSION in extension):
                targetDir = installPath
                installPath = os.path.join(installPath, pkg.fileName)
                if MBTILES_EXTENSION in extension:
                    if not osutils.createDirectory(targetDir):
                        return PKG_FAILED, None

                    workingDir = os.getcwd()
                    os.chdir(targetDir)

                    try:
                        os.symlink(pkg.fileName, pkg.name + MBTILES_EXTENSION)
                    except FileExistsError as err:
                        log.logError(f"Package link exists: {err}")
                        return PKG_FAILED, None

                    os.chdir(workingDir)
        if not pkg.name == GSM:
            ret, fileCount, fileList, holdFiles = utils.install(
                self.config, fileName, installPath, pkg, self, status
            )
            if not ret or (fileCount == 0 and not holdFiles):
                return PKG_FAILED, None

            self.createFiles(pkg, fileList)
            _, obsoleteKept = self.removeObsoleteFiles(
                pkg, obsoleteFiles, fileList, obsoleteHashes
            )

        keptFiles = sorted(self.protectedFiles | set(obsoleteKept))
        if self.protectedFiles:
            holdFiles = [f for f in holdFiles or [] if f not in self.protectedFiles]
            self.writeNewCandidates(pkg, fileName, self.protectedFiles)

        if not self.createDesc(pkg):
            return PKG_FAILED, None

        if status == UPDATE:
            versionInfo = (
                f"{EVENT_UPDATED} from version {oldPkg.version} to {pkg.version}"
            )
        else:
            versionInfo = f"{EVENT_INSTALLED} in version {pkg.version}"
        log.history.info(
            "%s %s \n"
            "                      checksum: %s\n"
            "                      download_size: %s \n"
            "                      build_date: %s \n"
            "                      file_name: %s\n",
            pkg.name,
            versionInfo,
            pkg.checksum,
            pkg.downloadSize,
            pkg.buildDate,
            pkg.fileName,
        )
        custominstall.install(self, installPath, pkg)

        os.chdir(currentDir)
        licenseCount = 0
        if not pkg.license == "None":
            pkg.installLicense(self.config, status)
            _, licenseFiles = package.getLicenseFiles(
                pkg, self.config.downloadLicenseDir
            )
            licenseCount = len(licenseFiles)

        self.index[pkg.name] = pkg

        summary = Summary(
            pkg.name,
            fileCount,
            self.getSummaryPath(pkg),
            holdFiles,
            pkg.version,
            pkg.installSize,
            licenseCount,
            status,
            keptFiles,
        )

        return PKG_SUCCESS, summary

    @log.trace
    def removePackage(self, name):
        pkg = self.getPackage(name)
        if not pkg:
            return PKG_NOT_FOUND, None

        pkgPath = self.pkgLocalPath(pkg)
        if not os.path.isdir(pkgPath):
            return PKG_NOT_FOUND, None

        summary = None

        try:
            dirInfo = {}
            failed = False
            (
                removables,
                fileCount,
                holdFiles,
                hasContent,
                keptFiles,
            ) = self.getRemovableFiles(pkg)
            summary = Summary(
                pkg.name,
                fileCount,
                self.getSummaryPath(pkg),
                holdFiles,
                pkg.version,
                pkg.installSize,
                status=REMOVE,
                keptFiles=keptFiles,
            )

            baseDir = (
                self.pkgDataPath(pkg)
                if pkg.type == PT.DATA
                else os.path.dirname(self.config.installPath)
            )
            wholeDir = (
                pkg.type == PT.DATA
                and not pkg.filePath == ARCHIVE
                and not hasContent
            )

            for filename in removables:
                try:
                    if wholeDir:
                        try:
                            if os.path.isfile(filename):
                                os.remove(filename)
                            elif os.path.lexists(filename):
                                shutil.rmtree(filename)
                        except OSError as ex:
                            log.logError(
                                f"{pkg.name}: could not remove {filename}:"
                                f" {ex.strerror}"
                            )
                            failed = True
                            continue
                        dirInfo[
                            os.path.dirname(osutils.relativeTo(filename, baseDir))
                        ] = 0

                    else:
                        if os.path.isdir(filename) and not os.path.islink(filename):
                            dirInfo[osutils.relativeTo(filename, baseDir)] = 0
                            continue
                        try:
                            if os.path.lexists(filename):
                                os.remove(filename)
                        except OSError as ex:
                            log.logError(
                                f"{pkg.name}: could not remove {filename}:"
                                f" {ex.strerror}"
                            )
                            failed = True
                            continue
                        dirInfo[
                            os.path.dirname(osutils.relativeTo(filename, baseDir))
                        ] = 0

                except OSError:
                    pass

            if (
                not failed
                and pkg.type == PT.DATA
                and not pkg.filePath == ARCHIVE
            ):
                custominstall.remove(self, pkg)

            if pkg.type not in (PT.CONFIG, PT.DATA):
                try:
                    if not os.listdir(self.config.licenseDir):
                        shutil.rmtree(self.config.licenseDir)
                except Exception:
                    pass
            if not failed:
                try:
                    shutil.rmtree(pkgPath)
                except OSError as ex:
                    log.logError(
                        f"{pkg.name}: could not remove {pkgPath}: {ex.strerror}"
                    )
                    failed = True

            if pkg.type not in (PT.CONFIG, PT.DATA) and makelinks.removeDeadLinks(
                self.config.libDir
            ):
                dirInfo[
                    osutils.relativeTo(
                        self.config.libDir, os.path.dirname(self.config.installPath)
                    )
                ] = 0

            for filename in holdFiles:
                dirInfo[
                    os.path.dirname(osutils.relativeTo(filename, baseDir))
                ] = 0

            self.dropStaleHolds(holdFiles)

            self.pruneEmptyDirs(
                (os.path.join(baseDir, key) for key in dirInfo if key), baseDir
            )
        except Exception as ex:
            log.logError(f"{pkg.name}: could not remove package: {str(ex)}")
            return PKG_FAILED, summary

        if failed:
            return PKG_FAILED, summary

        del self.index[pkg.name]

        log.history.info(
            f"%s {EVENT_DEINSTALLED} in version %s \n"
            "                      checksum: %s\n"
            "                      download_size: %s \n"
            "                      build_date: %s \n"
            "                      file_name: %s\n",
            pkg.name,
            pkg.version,
            pkg.checksum,
            pkg.downloadSize,
            pkg.buildDate,
            pkg.fileName,
        )
        return PKG_SUCCESS, summary

    def removeEmptyInstallPath(self):
        installPath = self.config.installPath
        try:
            if os.path.isdir(installPath) and not os.listdir(installPath):
                os.rmdir(installPath)
        except PermissionError as ex:
            if (
                not self.config.assumeYes
                and osutils.privilegeAvailable()
                and utils.getInput(
                    f"The directory {installPath} is empty now. Do you want to remove it"
                    f" with {PRIVILEGE_COMMAND}?",
                    "N",
                    "yn",
                )
                == "y"
                and osutils.removeEmptyDirectory(installPath)
            ):
                return
            log.logInfo(f"The empty directory {installPath} was kept: {ex.strerror}")
        except OSError as ex:
            log.logInfo(f"The empty directory {installPath} was kept: {ex.strerror}")

    def isInstallable(self, pkg):
        if pkg.conflicts:
            for name in pkg.conflicts.split(" "):
                other = self.getPackage(name)
                if other:
                    log.logError(f"{pkg.name} is in conflict with {other.name} ... ")
                    sys.exit(EXIT_FAILURE)
        if pkg.license == "None":
            return True

        version = 0
        if pkg.name == SC:
            return True
        cert = utils.readCertificate(pkg.name, self.config)
        if cert:
            if cert.updatesUntil and licenseOlderThanVersion(
                cert.updatesUntil, pkg.version
            ):
                log.logError(
                    f"The {pkg.name} license no longer allows updates. Updates until:"
                    f" {cert.updatesUntil} "
                )
                return False

            if not cert.updatesUntil:
                try:
                    version = int(self.config.release)

                except ValueError:
                    pass

                if version >= 4:
                    print(
                        f"No update until date found in {pkg.name} license. The update"
                        f" information is required by gempa modules build for {SEISCOMP}"
                        f" 4 and newer. Please contact {EMAIL_GEMPA}."
                    )
                    return False
        return True

    @log.trace
    def addDependencies(self, packages):
        missingPkgs = []
        for name in packages:
            pkg = self.syncCache.getPackage(name)

            if pkg and pkg.depends:
                pkgDeps = pkg.depends.split(" ")
                pkgDeps = [pkgName for pkgName in pkgDeps if pkgName not in packages]

                for pkgName in pkgDeps:
                    other = self.syncCache.getPackage(pkgName)
                    if not other:
                        if self.getPackage(pkgName):
                            continue

                        missingPkgs.append(pkgName)
                        continue
                    if self.isInstallable(other) and not self.isInstalled(
                        other, False
                    ):
                        if pkgName not in packages:
                            packages.append(pkgName)

        if missingPkgs:
            if self.syncCache.isValid():
                reason = "do not exist in the repository"
            else:
                reason = (
                    "cannot be resolved without a package index, run"
                    f" '{self.config.gsmCall} update'"
                )

            print(
                f"\nThe following packages are defined as depend but {reason}:",
                f"{', '.join(missingPkgs)}\n",
            )
            if not self.config.assumeYes and utils.checkInput(
                f"{MSG_CONTINUE_QUESTION}", "N", "yn"
            ):
                sys.exit(EXIT_SUCCESS)

        return packages

    def collectOptional(self, packages):
        optional = []
        missing = []

        pending = list(dict.fromkeys(packages))
        seen = set(pending)

        while pending:
            pkg = self.syncCache.getPackage(pending.pop(0))
            if not pkg:
                continue

            for name in (pkg.optional or "").split():
                if name in seen:
                    continue
                seen.add(name)

                other = self.syncCache.getPackage(name)
                if not other:
                    missing.append(name)
                    continue
                if not self.isInstallable(other) or self.isInstalled(other, False):
                    continue

                optional.append(name)
                pending.append(name)

            for name in (pkg.depends or "").split():
                if name in seen:
                    continue
                seen.add(name)

                other = self.syncCache.getPackage(name)
                if other and not self.isInstalled(other, False):
                    pending.append(name)

        return optional, missing

    @log.trace
    def checkOptionalInstall(self, packages, ask=None):
        optional, missingPkgs = self.collectOptional(packages)

        if missingPkgs:
            print()
            log.logWarning(
                "The following packages are defined as optional but do"
                f" not exist in the repository: {', '.join(missingPkgs)}"
            )
            print()
            if utils.checkInput(f"{MSG_CONTINUE_QUESTION}", "N", "yn"):
                sys.exit(EXIT_SUCCESS)

        if optional:
            if not ask:
                sizes = [
                    f"{name}"
                    f" ({utils.humanbytes(self.syncCache.getPackage(name).downloadSize)})"
                    for name in optional
                ]
                print(
                    "\nThe following packages are optional:",
                    f"{', '.join(sizes)}\n",
                )

                if utils.checkInput("Do you want to add these packages?", "Y", "yn"):
                    packages.extend(optional)
            else:
                packages.extend(optional)

        return packages

    def optionalSources(self):
        sources = {}
        for name in sorted(self.getIndex()):
            pkg = self.getPackage(name)
            if pkg and pkg.optional:
                for optional in pkg.optional.split():
                    sources.setdefault(optional, set()).add(name)

        return sources

    def dependsSources(self):
        sources = {}
        for name in sorted(self.getIndex()):
            pkg = self.getPackage(name)
            if pkg and pkg.depends:
                for depends in pkg.depends.split():
                    sources.setdefault(depends, set()).add(name)

        return sources

    @log.trace
    def checkOptionalRemove(self, packages):
        optionalSources = self.optionalSources()
        dependsSources = self.dependsSources()

        offered = []
        leaving = set(dict.fromkeys(packages))

        def follows(name, sources):
            if name in leaving:
                return False
            if not self.isInstalled(self.getPackage(name), False):
                return False

            return not sources.get(name, set()) - leaving

        changed = True
        while changed:
            changed = False
            for name in sorted(leaving):
                pkg = self.getPackage(name)
                if not pkg:
                    continue

                for optional in (pkg.optional or "").split():
                    if follows(optional, optionalSources):
                        offered.append(optional)
                        leaving.add(optional)
                        changed = True

                for depends in (pkg.depends or "").split():
                    if follows(depends, dependsSources):
                        leaving.add(depends)
                        changed = True

        if not offered:
            return packages

        print(
            "\nThe following packages were optionally/dependency installed:",
            f"{', '.join(offered)}\n",
        )

        if utils.checkInput("Do you want to remove these packages?", "Y", "yn"):
            packages.extend(offered)

        return list(dict.fromkeys(packages))

    @log.trace
    def checkDependsRemove(self, packages):
        toRemove = set(packages)
        toRemoveOriginal = set(packages)
        allDependsMap = {}
        reverseDependsMap = {}

        for name in sorted(self.getIndex()):
            pkg = self.getPackage(name)
            if pkg.depends:
                dependsPkgs = pkg.depends.split()
                allDependsMap[pkg.name] = dependsPkgs
                for dep in dependsPkgs:
                    if dep not in reverseDependsMap:
                        reverseDependsMap[dep] = set()
                    reverseDependsMap[dep].add(pkg.name)

        if not toRemove:
            return []

        def canRemove(pkgName):
            if pkgName not in reverseDependsMap:
                return True
            return all(dep in toRemove for dep in reverseDependsMap[pkgName])

        for pkgName in packages:
            dependencies = allDependsMap.get(pkgName, [])
            for dep in dependencies:
                if dep in self.getIndex() and dep not in toRemove:
                    if canRemove(dep):
                        toRemove.add(dep)

        def removeUnneededPackages():
            changed = True
            while changed:
                changed = False
                for pkg in list(toRemove):
                    for dep in allDependsMap.get(pkg, []):
                        if dep not in toRemove and canRemove(dep):
                            toRemove.add(dep)
                            changed = True

        removeUnneededPackages()

        for pkgName in list(toRemove):
            for dep in reverseDependsMap.get(pkgName, []):
                if dep not in toRemove and canRemove(dep):
                    toRemove.add(dep)

        result = toRemove - toRemoveOriginal
        if result:
            print(
                "\nThe following packages are removed as dependencies:",
                ", ".join(sorted(result)),
                "\n",
            )

        return list(toRemove)
