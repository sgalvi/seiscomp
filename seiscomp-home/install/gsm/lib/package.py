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
from pathlib import Path
import shutil
import tarfile
import textwrap

from collections import defaultdict

from datetime import datetime, timezone

from shutil import copy


from lib import osutils, pkgbuild, utils, log, versions
from lib.const import (
    DATE_REGEXP,
    DOC_URL,
    EXIT_GSM_UPDATE,
    NIGHTLY,
    SC,
    PT,
    urljoin,
    FILE_ENCODING,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UPDATE_DATE_FORMAT,
    CRT_EXTENSION,
    LICENSE_TXT_EXTENSION,
    CHANGELOG,
    INSTALL,
    SEISCOMP,
    LICENSES,
    EMAIL_GEMPA,
    GSM,
    DSC_EXTENSION,
    SIG_EXTENSION,
    NOTICE,
    URL_FILE,
    APP_DATA_PACKAGES,
    PUBLIC_MARKER,
    VISIBILITY_PUBLIC,
    EVENT_INSTALLED,
    EVENT_UPDATED,
    EVENT_DEINSTALLED,
    GREENSFUNCTIONS,
    CURRENT_RELEASE_MARK,
    blue,
    green,
    reset,
)

from lib.utils import checkInput, temporaryValue

FORMAT = "0.1"

INFO_LABEL_WIDTH = 17


INFO_MIN_VALUE_WIDTH = 20


def infoLine(label, value):
    indent = INFO_LABEL_WIDTH + 2
    value = str(value)
    try:
        width = os.get_terminal_size().columns - indent
    except OSError:
        width = 0

    if width >= INFO_MIN_VALUE_WIDTH and len(value) > width:
        lines = textwrap.wrap(value, width, break_long_words=True, break_on_hyphens=False)
        value = ("\n" + " " * indent).join(lines)

    return f"{blue}{label: <{INFO_LABEL_WIDTH}}{reset}  {value}"


def isOlderVersion(version, reference):
    return versions.isOlder(version, reference)


class Package:
    def __init__(self, name, path):
        self.name = name
        self.directory = path

        self.desc = ""
        self.keywords = ""
        self.fileName = ""
        self.installSize = 0
        self.checksum = ""
        self.version = ""
        self.arch = ""
        self.buildDate = ""
        self.installPath = None
        self.dscFile = ""
        self.downloadSize = 0
        self.installDate = ""
        self.dataDir = None
        self.license = ""
        self.release = ""
        self.format = FORMAT
        self.type = PT.APP
        self.conflicts = None
        self.filePath = None
        self.changeLog = None
        self.os = ""
        self.osVersion = ""
        self.licenseFile = None
        self.installScript = None
        self.optional = None
        self.depends = None
        self.osInstallScripts = None
        self.sigFile = None
        self.localDir = ""
        self.visibility = None

    @classmethod
    def fromFile(cls, file, path):
        def getValue(key, default=None):
            v = symbols.get(key, default)
            if isinstance(v, list):
                return " ".join(v)

            return v

        def getOptValue(key):
            return getValue(key) if key in symbols else None

        symbols = pkgbuild.readPkgsDescFile(file)

        pkg = cls(getValue("pkgname"), path)
        pkg.dscFile = file

        pkg.desc = getValue("pkgdesc", pkg.desc)
        pkg.fileName = getValue("filename", pkg.fileName)
        pkg.downloadSize = getValue("pkgsize")

        if pkg.dscFile.endswith(DSC_EXTENSION):
            pkg.sigFile = pkg.dscFile[: -len(DSC_EXTENSION)] + SIG_EXTENSION
        else:
            pkg.sigFile = None

        pkg.checksum = getOptValue("sha256") or getValue("sha512sums", pkg.checksum)

        pkg.version = getValue("pkgver", pkg.version)

        pkg.os = getValue("pkgos", pkg.os)
        pkg.osVersion = getValue("pkgosversion", pkg.osVersion)
        pkg.arch = getValue("arch", pkg.arch)

        pkg.license = getValue("license", pkg.license)
        pkg.buildDate = getValue("builddate", pkg.buildDate)
        pkg.installSize = getValue("pkginstallsize")

        pkg.release = getOptValue("pkgrel") or pkg.release
        pkg.installPath = getOptValue("pkginstallpath")
        pkg.installDate = getOptValue("installdate") or pkg.installDate
        pkg.dataDir = getOptValue("installdatadir")
        pkg.format = getOptValue("pkgfileversion") or pkg.format
        pkg.keywords = getOptValue("pkgkeywords") or pkg.keywords
        pkg.changeLog = getOptValue("pkgchangelog") or pkg.changeLog
        pkg.conflicts = getOptValue("conflicts") or pkg.conflicts
        pkg.optional = getOptValue("optional") or pkg.optional
        pkg.depends = getOptValue("depends") or pkg.depends
        pkg.osInstallScripts = getOptValue("osinstallscripts") or pkg.osInstallScripts
        pkg.filePath = getOptValue("pkgfilepath") or pkg.filePath
        pkg.licenseFile = getOptValue("pkglicensefile") or pkg.licenseFile
        if pkg.licenseFile == "None":
            pkg.licenseFile = None
        pkg.installScript = getOptValue("pkginstallscript") or pkg.installScript
        pkg.visibility = getOptValue("pkgvisibility") or pkg.visibility

        pt = getOptValue("pkgtype")
        if pt:
            pkg.type = pt
        elif pkg.name == PT.GSM:
            pkg.type = PT.GSM

        return pkg

    def __lt__(self, other):
        return isOlderVersion(other.version, self.version)

    def isPublic(self):
        if self.visibility and self.visibility.strip().lower() == VISIBILITY_PUBLIC:
            return True

        return bool(self.desc) and self.desc.rstrip().endswith(PUBLIC_MARKER)

    def isGreensfunctions(self):
        return bool(self.filePath) and GREENSFUNCTIONS in self.filePath

    def fullName(self):
        return self.name + "=" + self.version

    def __repr__(self):
        return f"<Package {self.fullName()}>"

    def showInfo(self, updatesUntil, notValidAfter, showInstallDate):
        if self.release:
            print(infoLine("Release", self.release))

        print(infoLine("Version", self.version))

        if not self.filePath and self.type != PT.CONFIG:
            urlStr = urljoin(DOC_URL, f"{self.name}/current/")
            print(infoLine("Documentation", urlStr))

        print(infoLine("Architecture", self.arch))
        print(infoLine("Licenses", self.license))
        print(infoLine("Description", self.desc))
        print(infoLine("Filename", self.fileName))
        print(infoLine("Download size", utils.humanbytes(self.downloadSize)))
        print(infoLine("Installed size", utils.humanbytes(self.installSize)))
        print(infoLine("SHA256", self.checksum))
        print(
            infoLine(
                "Build date",
                f"{self.buildDate}{'' if self.buildDate == 'N/A' else ' UTC'}",
            )
        )
        print(infoLine("Package type", self.type))
        if self.dataDir:
            print(infoLine("Data path", self.dataDir))
        if self.optional:
            print(infoLine("Package optional", self.optional))
        if self.depends:
            print(infoLine("Package depends", self.depends))

        if showInstallDate:
            print(
                infoLine(
                    "Install date",
                    f"{self.installDate}"
                    f"{'' if self.installDate == 'N/A' else ' UTC'}",
                )
            )
        if not notValidAfter == "None":
            print(infoLine("Valid until", notValidAfter))

        if not updatesUntil == "None":
            print(infoLine("Updates until", updatesUntil))

    def installLicense(self, config, status=INSTALL):
        if not osutils.createDirectory(config.licenseDir):
            return False

        licenseFileName, members = getLicenseFiles(self, config.downloadLicenseDir)
        progress = utils.progressBar(members)

        licenseFileName = licenseFileName + " license"
        utils.setDesc(progress, status, licenseFileName)
        for member in progress:
            try:
                copy(member, config.licenseDir)
            except BaseException as e:
                log.log(status, f"{licenseFileName} ({e})", ok=False)
                return False

        log.logResult(progress, status, licenseFileName)
        log.history.info("license for %s was installed\n", self.name)

        return True


def getLicenseFiles(pkg, downloadLicenseDir):
    licenseFileName = getLicenseFileName(pkg)
    baseName = os.path.join(downloadLicenseDir, licenseFileName)

    return licenseFileName, glob.glob(rf"{baseName}*")


def getLicenseFileName(pkg):
    return pkg.licenseFile or pkg.name


def getPackagesUpdateInfo(syncCache, localCache, config, fromUpOrDowngrade=False):
    updatablePackages = []
    packages = []
    editedConfigs = set()
    for pkgName in sorted(syncCache.getIndex()):
        if pkgName == GSM or pkgName in config.excludePackages:
            continue

        pkg = localCache.getPackage(pkgName)

        if pkg is None:
            continue

        if pkg.type == PT.CONFIG and localCache.getModifiedFiles(pkg):
            editedConfigs.add(pkg.name)

        skipInstall = localCache.isHold(pkg.name) or pkg.name in editedConfigs

        if fromUpOrDowngrade and (
            pkg.type in (PT.DATA, PT.CONFIG)
            or (config.release == NIGHTLY and pkg.name == SC)
            or any(localCache.isInstallable(a) for a in syncCache.getPackages(pkg.name))
        ):
            continue

        installCandidate = syncCache.getPackages(pkg.name)

        if config.release == NIGHTLY:
            if pkg.type == PT.APP:
                if (
                    pkg.name in APP_DATA_PACKAGES
                    and pkg.version == installCandidate[0].version
                ):
                    continue

                updatablePackages.append((pkg.name, installCandidate[0]))
                if not skipInstall:
                    packages.append(pkg.name)
            if not pkg.type == PT.APP:
                if not pkg.version == installCandidate[0].version:
                    updatablePackages.append((pkg.name, installCandidate[0]))
                    if not skipInstall:
                        packages.append(pkg.name)

        elif installCandidate and (not pkg.version == installCandidate[0].version):
            updatablePackages.append((pkg.name, installCandidate[0]))
            if not skipInstall:
                packages.append(pkg.name)

        elif (
            installCandidate
            and (pkg.version == installCandidate[0].version)
            and not pkg.checksum == installCandidate[0].checksum
            and localCache.isInstalledToday(pkg.installDate)
        ):
            updatablePackages.append((pkg.name, installCandidate[0]))
            if not skipInstall:
                packages.append(pkg.name)

    if not updatablePackages:
        if not fromUpOrDowngrade:
            print("\nAll packages are up to date.")

        return False, None

    if config.release == NIGHTLY:
        print(
            "\nNightly release detected. It is strongly recommended to update all"
            " packages!\n"
        )
    else:
        print("\nThe following packages can be updated:\n")

    for name, pkgs in updatablePackages:
        cert = None
        pkg = localCache.getPackage(name)
        if pkg.license != "None":

            licenseFileName = getLicenseFileName(pkg)

            cert = utils.readCertificate(licenseFileName, config)
            # does the license cover the version that is offered (not the installed one)?
            if not config.offline:
                if cert and cert.updatesUntil and cert.updatesUntil < pkgs.version:
                    downloadLicense(pkg, config, pkgs.version)
                    cert = utils.readCertificate(licenseFileName, config)
                    print("\n")

            if cert and cert.updatesUntil and cert.updatesUntil < pkgs.version:
                print(
                    f"{pkg.name} ({pkg.version}) --> {pkgs.version} (Unsupported by"
                    f" license. Updates until: {cert.updatesUntil})"
                )
                if name in packages:
                    packages.remove(name)
                continue

        if utils.licenseInfoDays(config) and cert:
            lincensInfo = utils.prettyFormatLicenseInfo(cert, utils.licenseInfoDays(config))
        else:
            lincensInfo = ""

        if localCache.isHold(pkg.name):
            holdInfo = "(will not be updated, it's on hold)"
        elif name in editedConfigs:
            if localCache.hasNoChecksums(pkg):
                holdInfo = (
                    "(will not be updated, installed by an older gsm without"
                    " checksums: edited files cannot be told apart)"
                )
            else:
                holdInfo = "(will not be updated, configuration files were edited)"
        else:
            holdInfo = ""

        suffix = " (force update)" if pkg.version == pkgs.version else ""
        print(
            f"{pkg.name} ({pkg.version}) --> {pkgs.version}{suffix} {lincensInfo}{holdInfo}"
        )

    if not packages:
        return False, None

    return True, packages


def getDownloadURL(pkg, config):
    base = utils.publicOrBaseURL(pkg, config)

    if pkg.type == PT.CONFIG:
        return urljoin(base, pkg.name, pkg.fileName)

    if pkg.filePath:
        dir_part = os.path.dirname(pkg.filePath)
        return urljoin(base, os.path.join(dir_part, pkg.name), pkg.fileName)

    return urljoin(base, pkg.name, pkg.directory, pkg.fileName)


def backupPackages(config, pkg, backupDenyPackages):
    if pkg.name in backupDenyPackages:
        log.logInfo(
            f"{pkg.name}: The package is not supported by the backup operation."
        )
        return None

    fileName = config.packagePath(pkg)
    creationTime = os.path.getctime(fileName)

    timeStr = int(creationTime)

    backupPath = os.path.join(config.packageBackupDir, pkg.name, pkg.version)

    backupFileOriginal = os.path.join(backupPath, os.path.basename(fileName))
    backupFile = backupFileOriginal + f".{timeStr}"

    os.makedirs(backupPath, exist_ok=True)

    if os.path.isfile(backupFile):
        log.logInfo(
            f"Backup file {backupFile} already exists. Skipping backup operation."
        )
        return None

    log.history.info(
        "Create backup from %s \n"
        "                      to backup: %s\n"
        "                      checksum: %s\n"
        "                      download_size: %s \n"
        "                      build_date: %s \n",
        fileName,
        backupFile,
        pkg.checksum,
        pkg.downloadSize,
        pkg.buildDate,
    )
    pkgName = f"{pkg.name} {pkg.version}"

    fileName_dsc = Path(f"{fileName}{DSC_EXTENSION}")
    backupFile_dsc = Path(f"{backupFileOriginal}{DSC_EXTENSION}.{timeStr}")
    if fileName_dsc.is_file():
        try:
            shutil.copy(fileName_dsc, backupFile_dsc)
            log.history.info(
                "Create backup from %s \n                      to backup: %s\n",
                fileName_dsc,
                backupFile_dsc,
            )
        except Exception:
            log.history.error(
                "Failed to create backup from %s \n"
                "                      to backup: %s\n",
                fileName_dsc,
                backupFile_dsc,
            )

    fileName_sig = Path(f"{fileName}{SIG_EXTENSION}")
    backupFile_sig = Path(f"{backupFileOriginal}{SIG_EXTENSION}.{timeStr}")
    if fileName_sig.is_file():
        try:
            shutil.copy(fileName_sig, backupFile_sig)
            log.history.info(
                "Create backup from %s \n                      to backup: %s\n",
                fileName_sig,
                backupFile_sig,
            )
        except Exception:
            log.history.error(
                "Failed to create backup from %s \n"
                "                      to backup: %s\n",
                fileName_sig,
                backupFile_sig,
            )

    return utils.copy(config, fileName, backupFile, pkgName, False)


def download(pkg, config):
    if not osutils.createDirectory(config.downloadDir):
        return False

    url = getDownloadURL(pkg, config)

    fileName = config.downloadPath(pkg.fileName)
    pkgName, _ = utils.getPackageName(pkg)

    try:
        if not utils.download(url, fileName, pkgName, config, pkg.dscFile):
            return False

    except Exception:
        log.logError(
            "The requested file can not be downloaded. "
            f"{urljoin(url, pkg.fileName)}"
        )
        return False
    return True


def licenseNeedsRefresh(pkg, config, version=None):
    """Is the local license missing, expired, or not valid for 'version' (default: the version of
    pkg)? Then it is fetched whatever the time of the file on the server is."""
    cert = utils.readCertificate(getLicenseFileName(pkg), config)
    if cert is None:
        return True

    notValidAfter = getattr(cert, "not_valid_after", None)
    if notValidAfter is not None:
        if notValidAfter.tzinfo is None:
            notValidAfter = notValidAfter.replace(tzinfo=timezone.utc)
        if notValidAfter < datetime.now(timezone.utc):
            return True

    version = version or pkg.version
    updatesUntil = cert.updatesUntil
    if updatesUntil and version:
        if DATE_REGEXP.match(updatesUntil) and DATE_REGEXP.match(version):
            return tuple(map(int, updatesUntil.split("."))) < tuple(
                map(int, version.split("."))
            )
        return updatesUntil < version

    return False


def downloadLicense(pkg, config, version=None):
    if not osutils.createDirectory(config.downloadLicenseDir):
        return False

    url = urljoin(config.baseURL, LICENSES)

    licenseFileName = getLicenseFileName(pkg)

    fn = licenseFileName + CRT_EXTENSION

    try:
        # The file on the server is compared by its time ('-f' fetches it in any case). That is not
        # enough if the license is missing, expired or too old for the version: a copy of the gsm
        # directory gives the license the time of the copy, so a renewed license on the server
        # would look older. In these cases the license is fetched in any case.
        refresh = licenseNeedsRefresh(pkg, config, version)
        with temporaryValue(config, "forceDownload", bool(config.forceDownload or refresh)):
            if not utils.download(
                urljoin(url, fn), os.path.join(config.downloadLicenseDir, fn), fn, config
            ):
                log.logError(
                    f"Missing {licenseFileName} license. Please get in touch with"
                    f" {EMAIL_GEMPA}"
                )
                return False

            fn = licenseFileName + LICENSE_TXT_EXTENSION
            utils.download(
                urljoin(url, fn), os.path.join(config.downloadLicenseDir, fn), fn, config
            )
    except Exception:
        log.logError(
            f"The requested file can not be downloaded. {urljoin(url, fn)}"
        )
        return False

    return True


def getLatestRelease(config):
    try:
        releases = [r for _, r in comparableReleases(getReleases(config)) if r != NIGHTLY]
        return releases[0] if releases else None
    except Exception:
        return None

def isNewReleaseAvailable(config):
    if config.release == NIGHTLY:
        return False, None

    latest = getLatestRelease(config)

    if not latest:
        return False, None

    try:
        if int(latest) <= int(config.release):
            return False, None

        info = (
            f"New {SEISCOMP} release {latest} is available. "
            f"Run {config.gsmCall} do-release-upgrade to upgrade."
        )
        return True, info
    except Exception:
        return False, None


def updateInfoGsm(localCache, syncCache):
    localPackageInfo = localCache.getPackage(GSM)
    if not localPackageInfo or localPackageInfo.version == "VERSION":
        return False

    try:
        remotePackageInfo = syncCache.getPackage(GSM)
        if not syncCache.getPackage(GSM):
            return False

        if versions.isOlder(localPackageInfo.version, remotePackageInfo.version):
            print(
                f"\nNew {GSM} release '{remotePackageInfo.version}' available.\n\n"
                f"{NOTICE}: Updates for {GSM} are currently being held back."
                f" Use {localCache.config.gsmCall} unhold {GSM} to reactivate updates."
            )
    except IndexError:
        pass

    return True


def isGsmDownloaded(pkg, config):
    """Is the file of the new gsm in the download directory, with the right checksum?"""
    fileName = config.packagePath(pkg)
    return os.path.isfile(fileName) and osutils.checksum(fileName) == pkg.checksum


def updateCheck(localCache, syncCache, config):
    retCode = 0
    localPackageInfo = localCache.getPackage(GSM)

    if not localPackageInfo or localPackageInfo.version == "VERSION":
        return (False, retCode)

    try:
        remotePackageInfo = syncCache.getPackage(GSM)
        if not remotePackageInfo:
            return (False, retCode)

        if versions.isOlder(localPackageInfo.version, remotePackageInfo.version):
            reason = osutils.unsupportedSystem()
            if reason:
                print(
                    f"\nNew {GSM} release '{remotePackageInfo.version}' available, but it"
                    f" cannot be installed on this system: {reason}\n"
                    f"This {GSM} stays as it is.\n"
                )
                return (False, retCode)

            if config.offline and not isGsmDownloaded(remotePackageInfo, config):
                print(
                    f"\nNew {GSM} release '{remotePackageInfo.version}' available, but not"
                    " downloaded (offline mode).\n"
                )
                return (False, retCode)

            print(
                f"\nNew {GSM} release '{remotePackageInfo.version}' available. To upgrade"
                f" run: {config.gsmCall} install {GSM}\n"
            )
            if not config.assumeYes:
                ret = checkInput(f"Do you want to update {GSM} first?", "y", "yn")
                if ret:
                    retCode = EXIT_GSM_UPDATE
                return (ret, retCode)

            return (False, retCode)
    except IndexError:
        pass

    return (False, retCode)


def fetchChangeLog(pkg, config):
    relPath = pkg.name
    if pkg.filePath:
        relPath = os.path.join(os.path.dirname(pkg.filePath), pkg.name)

    try:
        if config.baseURL.startswith(URL_FILE):
            path = os.path.join(config.baseURL.replace(URL_FILE, ""), relPath, CHANGELOG)
            with open(path, "r", encoding=FILE_ENCODING) as file:
                return file.read()

        url = urljoin(utils.publicOrBaseURL(pkg, config), relPath, CHANGELOG)
        return utils.getDataFromUrl(url, config)
    except Exception:
        return None


def fetchChangeLogFromTar(pkg, config):
    fileName = config.packagePath(pkg)
    if not os.path.exists(fileName):
        log.logError(f"File not found: {fileName}")
        return None
    try:
        with tarfile.open(fileName, "r", encoding=FILE_ENCODING) as pkgTar:
            names = set(pkgTar.getnames())
            member = next(
                m for m in (os.path.join(SC, pkg.changeLog), pkg.changeLog)
                if m in names
            )
            file = pkgTar.extractfile(member)
            response = ""
            for line in file.readlines():
                response += line.decode(FILE_ENCODING)
    except Exception:
        return None

    return response


CHANGELOG_HEADING = "## "
CHANGELOG_IMPORTANT_SECTION = "### Important"
CHANGELOG_IMPORTANT_BLOCK = "**Important**"


def changeLogEntryKey(token):
    for dateFormat in (DEFAULT_UPDATE_DATE_FORMAT, DEFAULT_TIME_FORMAT):
        try:
            return "date", datetime.strptime(token, dateFormat)
        except ValueError:
            continue

    parts = token.split(".")
    if len(parts) > 1 and all(part.isdigit() for part in parts):
        return "version", utils.splitVersionString(token)

    return None


def parseChangeLog(changeLogText):
    entries = []
    for line in changeLogText.splitlines():
        keys = {}
        if line.startswith(CHANGELOG_HEADING):
            for token in line[len(CHANGELOG_HEADING):].split():
                key = changeLogEntryKey(token)
                if key and key[0] not in keys:
                    keys[key[0]] = key[1]

        if keys:
            entries.append(
                {
                    "title": line[len(CHANGELOG_HEADING):].strip(),
                    "keys": keys,
                    "lines": [],
                }
            )
        elif entries:
            entries[-1]["lines"].append(line)

    return entries


def newerChangeLogEntries(changeLogText, version, target=None):
    key = changeLogEntryKey(str(version))
    if not key:
        return []

    kind, current = key
    targetKey = changeLogEntryKey(str(target)) if target else None
    upper = targetKey[1] if targetKey and targetKey[0] == kind else None

    return [
        entry
        for entry in parseChangeLog(changeLogText)
        if kind in entry["keys"]
        and entry["keys"][kind] > current
        and (upper is None or entry["keys"][kind] <= upper)
    ]


def importantChangeLogLines(lines):
    important = []
    mode = None
    for line in lines:
        if line.startswith(CHANGELOG_IMPORTANT_SECTION):
            mode = "section"
        elif line.startswith(CHANGELOG_IMPORTANT_BLOCK):
            mode = "block"
        elif mode == "section" and line.startswith("#"):
            mode = None
        elif mode == "block" and not line.strip():
            mode = None

        if mode:
            important.append(line)

    return important


def printImportantChanges(changeLogText, version, pkgName, target=None):
    first = True
    for entry in newerChangeLogEntries(changeLogText, version, target):
        important = importantChangeLogLines(entry["lines"])
        if not important:
            continue

        if first:
            print(f"\nImportant changes for {pkgName}\n")
            first = False

        print(entry["title"])
        print("\n".join(important))

    return not first


def showChangeLog(packages, config, localCache, syncCache, version=False):
    responses = []
    isShowChangeLog = False
    if not version:
        if len(packages) == 1:
            pkg = localCache.getPackage(packages[0])
            if not pkg:
                print(f"Package not installed: {packages[0]}")
                return True, False
            if config.offline:
                response = fetchChangeLogFromTar(pkg, config)
                if not response:
                    return True, False
            else:
                response = fetchChangeLog(pkg, config)
            if response:
                utils.displayTextSideBySide(response)

                return True, False

    else:
        packages = utils.sorting(packages)
        progress = utils.progressBar(packages, CHANGELOG)
        for member in progress:
            targetPkg = syncCache.getPackage(member)
            pkg = localCache.getPackage(member.partition("=")[0]) or targetPkg
            pkgName = f"{CHANGELOG} {pkg.name}"
            utils.setDesc(progress, CHANGELOG, pkgName)
            if config.offline:
                response = fetchChangeLogFromTar(targetPkg or pkg, config)
            else:
                response = fetchChangeLog(pkg, config)
            if response:
                target = targetPkg.version if targetPkg else None
                responses.append([response, pkg.version, pkg.name, target])

        log.logResult(
            progress, CHANGELOG, n=len(responses), total=len(packages)
        )

        for changeLog, pkgVersion, pkgName, target in responses:
            if printImportantChanges(changeLog, pkgVersion, pkgName, target):
                isShowChangeLog = True

    return True, isShowChangeLog


def getReleases(config):
    try:
        return os.listdir(config.scPath())
    except OSError:
        return []


def prepareOnlyOS(config, result):
    removables = []
    for release in result:
        if not os.path.exists(
            config.scPath(release, config.os, config.os_version)
        ):
            removables.append(release)
    for release in removables:
        result.remove(release)

    return result

def comparableReleases(releases):
    result = []
    for release in releases:
        try:
            result.append((releaseKey(release), release))
        except ValueError:
            pass
    return sorted(result, reverse=True)


def getLatestStableReleases(config, onlyOS=False):
    try:
        current = releaseKey(config.release)
    except ValueError:
        current = releaseKey(NIGHTLY)

    result = [r for k, r in comparableReleases(getReleases(config)) if k < current]

    if onlyOS:
        return prepareOnlyOS(config, result)

    return result

def getLatestReleases(config, onlyOS=False):
    if config.release == NIGHTLY:
        return []

    releases = getReleases(config)
    try:
        current = releaseKey(config.release)
    except ValueError:
        result = releases
    else:
        result = [r for k, r in comparableReleases(releases) if k > current]

    if onlyOS:
        return prepareOnlyOS(config, result)

    return result


def versionKey(version):
    return tuple(int(part) for part in version.split("."))


def releaseKey(release):
    if release == NIGHTLY:
        return (float("inf"),)
    return (int(release),)


def showReleasesFull(config, optOs=""):
    versions = defaultdict(lambda: defaultdict(list))
    for sc in getReleases(config):
        scPath = config.scPath(sc)
        if os.path.isdir(scPath):
            for distro in os.listdir(scPath):
                distroPath = os.path.join(scPath, distro)
                if os.path.isdir(distroPath):
                    for version in os.listdir(distroPath):
                        version_path = os.path.join(distroPath, version)
                        if os.path.isdir(version_path):
                            versions[distro][version].append(sc)

    if optOs and optOs not in versions and optOs != "all":
        available_distros = ", ".join(versions.keys())
        print(
            f"\nThe selected OS '{optOs}' is not supported! \nPlease use: {available_distros}"
        )

        return True

    for distro, versionDict in versions.items():
        if optOs and distro != optOs and optOs != "all":
            continue
        print(f"{distro}:")
        for version, releases in sorted(
            versionDict.items(), key=lambda x: versionKey(x[0])
        ):
            sortedReleases = sorted(releases, key=releaseKey)

            if distro == config.os and version == config.os_version:
                versionDisplay = f"{version}*"
            else:
                versionDisplay = version

            releasesStr = " / ".join(sortedReleases)
            if distro == config.os and version == config.os_version:
                releasesStr = releasesStr.replace(config.release, f"{config.release}*")
            print(f"\t{versionDisplay} ( {releasesStr} )")

    return True

def showReleases(config):
    releases = sorted(getReleases(config), reverse=True)

    if releases:
        print(f"{SEISCOMP} releases:")
        for release in releases:
            if release == config.release:
                print(f"  {green}{release}{CURRENT_RELEASE_MARK}{reset}")
            else:
                print(f"  {release}")

    return True


def isUpgradeReleaseAvailable(config, mode):
    if mode == "do-release-upgrade":
        releases = getLatestReleases(config, True)
        if config.upgradeTarget in releases:
            return True
    if mode == "do-release-downgrade":
        releases = getLatestStableReleases(config, True)
        if config.upgradeTarget in releases:
            return True

    return False


def packageHistory(logPath, package):
    if not os.path.isfile(logPath):
        return None

    events = (
        f"{package} {EVENT_INSTALLED}",
        f"{package} {EVENT_UPDATED}",
        f"{package} {EVENT_DEINSTALLED}",
    )
    lines = []
    keep = False
    with open(logPath, "r", encoding=FILE_ENCODING, errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line[:1] in (" ", "\t"):
                if keep:
                    lines.append(line)
                continue
            message = line.split(" - ", 1)[-1]
            keep = message.startswith(events)
            if keep:
                lines.append(line)

    return "\n".join(lines)
