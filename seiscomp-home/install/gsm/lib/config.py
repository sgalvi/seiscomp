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


import configparser
import os
import re
import sys

from http import HTTPStatus

import subprocess

from typing import Callable, NamedTuple, Optional

from lib import utils, log, osutils

from lib.const import (
    BASE_URL,
    PRIVILEGE_COMMAND,
    EXIT_INTERRUPT,
    LICENSES,
    SC,
    urljoin,
    BASE_PUBLIC_URL,
    LICENSE_INFO_DAYS,
    FILE_ENCODING,
    EXTEND_DIR,
    ANY_NOARCH_DIR,
    CORE_DB,
    DEFAULT_RELEASE,
    SEISCOMP,
    GSM,
    MIGRATE,
    MIGRATIONS,
    GPG_DIR,
    GSM_CONFIG_FILE,
    MSG_CONTINUE_QUESTION,
    SHELL_COMPLETION_FILE,
    HOME_LOCAL_BIN,
    DOWNLOAD_DIR,
    SYNC_DIR,
    ALIASES_DIR,
    GSM_CONF,
    DOT_CONFIG,
    GSM_LOG_DIR,
    GSM_LOG_FILE,
    EXIT_SUCCESS,
    EXIT_FAILURE,
)
from lib.utils import checkInput, getInput

SECTION = "Settings"


class Option(NamedTuple):
    key: str
    attr: str
    getter: str = "get"
    setter: str = ""
    normalize: Optional[Callable] = None
    write: bool = True
    placeholder: str = ""
    help: str = ""


CONFIG_OPTIONS = (
    Option("os", "os", normalize=str.lower),
    Option("os_version", "os_version"),
    Option("arch", "arch", normalize=str.lower),
    Option("base_url", "baseURL"),
    Option("user", "user"),
    Option("password", "password"),
    Option("release", "release", normalize=str.lower),
    Option("download_dir", "downloadDir", setter="setDownloadDir"),
    Option("install_path", "installPath", setter="setInstallPath"),
    Option("data_dir", "dataDir", setter="setDataDir"),
    Option(
        "verify",
        "verify",
        getter="getboolean",
        placeholder="[True/False]",
        help="The server certificate is verified. (default = True)",
    ),
    Option(
        "gpgverify",
        "gpgVerify",
        getter="getboolean",
        placeholder="[True/False]",
        help="The signature for a package is checked. (default = False)",
    ),
    Option(
        "backup_package_enable",
        "makeBackup",
        getter="getboolean",
        placeholder="[True/False]",
        help="A backup of the package file to be installed is made before"
        " each installation. (default = False)",
    ),
    Option(
        "backup_package_path",
        "packageBackupDir",
        setter="setPackageBackupDir",
        placeholder="/home/data/gsm/backup",
        help="The directory in which the backups are created.",
    ),
    Option("sync_dir", "syncDir", setter="setSyncDir"),
    Option("local_dir", "localDir", setter="setLocalDir"),
    Option(
        "license_info_days",
        "licenseInfoDays",
        placeholder="[N]",
        help="Days before the license-expiry notice is shown."
        f" (default = {LICENSE_INFO_DAYS})",
    ),
    Option(
        "nagios_updates",
        "nagiosUpdates",
        normalize=str.lower,
        write=False,
        placeholder="[warning/critical]",
        help="Status of 'print nagios output' when updates are available."
        " (default = critical)",
    ),
    Option("db_url", "dbUrl", write=False),
    Option("db_filename", "dbFileName", write=False),
)


OPTIONS_BY_ATTR = {opt.attr: opt for opt in CONFIG_OPTIONS}


MIGRATION_VERSION = re.compile(r"^(\d+)\.(\d+)$")

DEFAULT_MIGRATION_VERSION = "0.0"


def parseMigrationVersion(value):
    match = MIGRATION_VERSION.match(value.strip())
    if not match:
        return None

    return int(match.group(1)), int(match.group(2))


def formatMigrationVersion(version):
    return f"{version[0]}.{version[1]}"


def getConfigParser():
    return configparser.RawConfigParser(allow_no_value=True)


class Config:
    @staticmethod
    def expandAbsPath(path):
        return os.path.abspath(os.path.expanduser(path))

    @property
    def gsmCall(self):
        return utils.gsmCallName(self.gsmBinary, self.baseDir)

    def readInstallInfoFile(self):
        parser = getConfigParser()
        if not parser.read(os.path.join(self.localDir, self.internalConfig)):
            log.logError(f"Could not parse config file: {self.internalConfig}")
            return None

        return parser

    def writeInstallInfoFile(self, release, installPath, gsmBaseDir, dataDir):
        if not os.path.isdir(self.localDir):
            log.logError(
                f"The local_dir {(self.localDir)} defined in {GSM_CONFIG_FILE} does not exist."
            )
            return False
        try:
            parser = getConfigParser()
            parser.add_section("CONFIG")
            parser.set("CONFIG", "release", release)
            parser.set("CONFIG", "install_path", installPath)
            parser.set("CONFIG", "baseDir", gsmBaseDir)
            parser.set("CONFIG", "data_dir", dataDir)
            parser.set("CONFIG", "config", "0.0")
            self.write(parser, self.internalConfig)
        except IOError as e:
            log.logError(f"Could not write {self.internalConfig} file: {e}")
            return False

        return True

    def updateInstallInfoFile(self, section, value):
        try:
            parser = getConfigParser()
            parser.read(self.internalConfig)
            parser.set("CONFIG", section, value)
            self.write(parser, self.internalConfig)
        except IOError as e:
            log.logError(f"Could not write {self.internalConfig} file: {e}")
            return False

        return True

    def writeInitialConfigFile(
        self, release, installPath, gsmBaseDir, dataDir
    ):
        try:
            if not os.path.isfile(self.internalConfig):
                self.writeInstallInfoFile(
                    release, installPath, gsmBaseDir, dataDir
                )
                self.updateInstallInfoFile(
                    "config", self.getLatestMigrationVersion()
                )
        except IOError as e:
            log.logError(f"Could not write {self.internalConfig} file: {e}")
            return False

        return True

    def getMigrationSteps(self):
        migrationDir = self.getMigrationDir()
        try:
            fileNames = os.listdir(migrationDir)
        except OSError as err:
            log.logError(f"Cannot read {migrationDir}: {err}")
            return None

        steps = []
        for fileName in fileNames:
            toks = fileName.split("_to_")
            if len(toks) != 2:
                continue

            begin = parseMigrationVersion(toks[0])
            end = parseMigrationVersion(toks[1])
            if begin is None or end is None or end <= begin:
                continue

            if not os.path.isfile(os.path.join(migrationDir, fileName)):
                continue

            steps.append((begin, end, fileName))

        return sorted(steps)

    def getLatestMigrationVersion(self):
        steps = self.getMigrationSteps()
        if not steps:
            return DEFAULT_MIGRATION_VERSION

        return formatMigrationVersion(steps[-1][1])

    def getCurrentVersion(self):
        value = "0.0"
        if os.path.isfile(self.internalConfig):
            parser = self.readInstallInfoFile()
            try:
                value = parser.get("CONFIG", "config")

            except Exception:
                value = "0.0"

        return value

    def getMigrationDir(self):
        if self.gsmBinary != GSM:
            return os.path.join(self.baseDir.split(ALIASES_DIR)[0], MIGRATIONS)

        return os.path.join(self.baseDir, MIGRATIONS)

    def getMigrationFiles(self):
        steps = self.getMigrationSteps()
        if steps is None:
            return ["failed"]

        current = parseMigrationVersion(self.getCurrentVersion())
        if current is None:
            current = (0, 0)

        return [
            [fileName, formatMigrationVersion(end)]
            for begin, end, fileName in steps
            if begin >= current
        ]

    def runMigrationStep(self, fileName):
        with subprocess.Popen(
            [sys.executable, os.path.join(self.getMigrationDir(), fileName)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as proc:
            for line in proc.stdout:
                line = line.strip().lstrip("*").strip()
                if line:
                    log.log(MIGRATE, line)

        return proc.returncode == 0

    def makeMigration(self, show=True):
        files = self.getMigrationFiles()
        if files and files[0] == "failed":
            return False

        if not files:
            if show:
                log.logSkip("Configuration is up to date")
            return True

        absEnd = None
        progress = utils.progressBar(files, MIGRATE)
        for fileName, end in progress:
            step = fileName.replace("_to_", " -> ")
            utils.setDesc(progress, MIGRATE, step)
            if not self.runMigrationStep(fileName):
                log.logResult(progress, MIGRATE, step, ok=False)
                progress.close()
                return False

            absEnd = end

        log.logResult(progress, MIGRATE, f"config {absEnd}")

        return self.updateInstallInfoFile("config", absEnd)

    def checkMigration(self, show=True):
        migrationCount = len(self.getMigrationFiles())
        if migrationCount:
            if show:
                binary = self.gsmCall if self.gsmBinary else GSM
                log.logWarning(
                    f"{migrationCount} outstanding migration(s), "
                    f"run: {binary} migrate"
                )
            return False
        return True

    def checkInstallInfoWithExistConfig(self):
        if not os.path.isfile(self.internalConfig):
            return False
        parser = self.readInstallInfoFile()
        if not parser or not parser.has_section("CONFIG"):
            if not self.writeInstallInfoFile(
                self.release, self.installPath, self.baseDir, self.dataDir
            ):
                return False

            parser = self.readInstallInfoFile()
            if not parser or not parser.has_section("CONFIG"):
                return False

        cfgRelease = parser.get("CONFIG", "release").lower()
        cfgInstallPath = parser.get("CONFIG", "install_path")
        try:
            cfgBaseDir = parser.get("CONFIG", "baseDir")
        except configparser.NoOptionError:
            self.updateInstallInfoFile("baseDir", self.baseDir)
            cfgBaseDir = self.baseDir
        try:
            cfgDataPath = parser.get("CONFIG", "data_dir")
        except configparser.NoOptionError:
            self.updateInstallInfoFile("data_dir", self.dataDir)
            cfgDataPath = self.dataDir

        failed = True
        os.chdir(self.baseDir)
        if not os.getcwd() == cfgBaseDir:
            q = (
                f"Note: {GSM} directory has been copied/moved to a new "
                f"location({os.getcwd()} / {cfgBaseDir}) "
                "This may lead to undefined behavior!\n\n"
                "Adjust configuration to the new directory?"
            )
            if not checkInput(q, "Y", "Yn"):
                sys.exit(EXIT_SUCCESS)

            try:
                print("")
                self.setDownloadDir(
                    getInput(
                        "Download dir", os.path.join(self.baseDir, DOWNLOAD_DIR)
                    )
                )
                self.setSyncDir(
                    getInput("Sync dir", os.path.join(self.baseDir, SYNC_DIR))
                )
                self.setLocalDir(
                    getInput("Local dir", os.path.join(self.baseDir, "local"))
                )
                self.internalConfig = os.path.join(self.localDir, DOT_CONFIG)
                print("")

                self.writeInstallInfoFile(
                    self.release, self.installPath, self.baseDir, self.dataDir
                )

                self.update({"download_dir": self.downloadDir}, [])
                self.update({"local_dir": self.localDir}, [])
                self.update({"sync_dir": self.syncDir}, [])

            except KeyboardInterrupt:
                print("\n\nSetup aborted by user.")
                sys.exit(EXIT_INTERRUPT)
            sys.exit(EXIT_SUCCESS)

        if not cfgRelease == self.release:
            log.logWarning(
                f"The {SEISCOMP} release was manually changed from {cfgRelease} to"
                f" {self.release} in the {GSM_CONFIG_FILE} leading to problems."
                " Take the following steps to resolve the issue:\n\n"
                f"1. Correct {GSM_CONFIG_FILE}: Revert the release back to {cfgRelease}\n"
                f"2. Synchronize the package index: {self.gsmCall} update\n"
                f"3. Upgrade release with '{self.gsmCall} do-release-upgrade' or downgrade with"
                f" '{self.gsmCall} do-release-downgrade'. "\
                f"This will also adjust {GSM_CONFIG_FILE}\n\n"
                f"Information: Do not modify {GSM_CONF} manually."
            )

            sys.exit(EXIT_FAILURE)

        if not cfgInstallPath == self.installPath:
            q = (
                f"The {SEISCOMP} installation path was manually changed from"
                f" {cfgInstallPath} to {self.installPath}.\n"
                "Do you want to reset your manual changes?"
            )

            if not checkInput(q, "Y", "Yn"):
                sys.exit(EXIT_SUCCESS)
            self.updateInstallInfoFile("install_path", self.installPath)

        if not cfgDataPath == self.dataDir:
            log.logWarning(
                "The data dir installation path was manually changed from"
                f" {cfgDataPath} to {self.dataDir}."
            )
            failed = False

        return failed

    def checkInstallInfo(self):
        if os.path.isfile(self.internalConfig):
            failed = self.checkInstallInfoWithExistConfig()

            if not failed:
                if not checkInput(f"\n{MSG_CONTINUE_QUESTION}", "y", "yn"):
                    return False

        else:
            return self.writeInstallInfoFile(
                self.release, self.installPath, self.baseDir, self.dataDir
            )

        return True

    def __init__(self, baseDir, gsmConfigFile=GSM_CONFIG_FILE):
        self.baseDir = self.expandAbsPath(baseDir)

        self.fileName = os.path.join(self.baseDir, gsmConfigFile)

        self.localDir = os.path.join(self.baseDir, "local")

        self.os = ""
        self.os_version = ""
        _, _, self.arch = osutils.detectOS()
        self.baseURL = ""
        self.user = ""
        self.password = ""
        self.release = DEFAULT_RELEASE

        self.downloadDir = None
        self.installPath = None
        self.rootDir = None
        self.licenseDir = None
        self.libDir = None
        self.userConfigDir = None

        self.homeDir = self.expandAbsPath("~")

        self.setDownloadDir(os.path.join(self.baseDir, DOWNLOAD_DIR))
        self.setInstallPath(os.path.join(self.homeDir, SC))

        self.verify = True
        self.debug = False
        self.dataDir = os.path.join(os.sep, "home", "data")

        self.dbUrl = urljoin(BASE_URL, "coredb")
        self.dbFileName = CORE_DB

        self.syncDir = os.path.join(self.baseDir, SYNC_DIR)
        self.internalConfig = os.path.join(self.localDir, DOT_CONFIG)

        self.gpgVerify = False
        self.gpgDir = os.path.join(self.localDir, GPG_DIR)

        self.showAll = False
        self.downloadOnly = False
        self.showUrls = False
        self.assumeYes = False
        self.offline = False

        self.licenseInfoDays = None
        self.nagiosUpdates = "critical"

        self.forceDownload = False

        self.archDir = None
        self.noArchDir = None
        self.extendDir = None

        self.updateOrDowngrade = False
        self.signaturesChecked = False  # a release change checked the signatures with the download
        self.fromUpdate = False

        self.packageBackupDir = os.path.join(self.dataDir, "gsm", "backup")
        self.makeBackup = False

        self.runAgain = False

        self.gsmBinary = f"{GSM}"
        self.upgradeTarget = None

        self.excludePackages = []


    def set(self, attr, value):
        opt = OPTIONS_BY_ATTR.get(attr)
        if opt and opt.normalize and isinstance(value, str):
            value = opt.normalize(value)

        if opt and opt.setter:
            getattr(self, opt.setter)(value)
        else:
            setattr(self, attr, value)

    def write(self, parser, fileName):
        tmpFile = f"{fileName}.tmp"
        fd = os.open(tmpFile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding=FILE_ENCODING) as f:
            parser.write(f)
        os.replace(tmpFile, fileName)

    def update(self, updates, removals, parser=None):
        if not parser:
            parser = getConfigParser()
            parser.read(self.fileName)

        if updates and not parser.has_section(SECTION):
            parser.add_section(SECTION)

        for key, value in updates.items():
            parser.set(SECTION, key, value)

        for key in removals:
            parser.remove_option(SECTION, key)

        self.write(parser, self.fileName)

    def read(self):
        parser = getConfigParser()
        updates = {}
        removals = []

        try:
            if not parser.read(self.fileName):
                return (
                    f"{log.getLogPrefix('ERROR')}Could not parse config file:"
                    f" {self.fileName}"
                )
        except configparser.DuplicateOptionError as err:
            print(err)
            sys.exit(EXIT_FAILURE)

        try:
            if os.stat(self.fileName).st_mode & 0o077:
                os.chmod(self.fileName, 0o600)
        except OSError:
            pass

        missing = set()
        for opt in CONFIG_OPTIONS:
            try:
                value = getattr(parser, opt.getter)(SECTION, opt.key)
            except configparser.NoOptionError:
                missing.add(opt.key)
                continue

            if opt.normalize:
                value = opt.normalize(value)

            if opt.setter:
                getattr(self, opt.setter)(value)
            else:
                setattr(self, opt.attr, value)

        if "centos" in self.os:
            self.os = "rhel"
            updates["os"] = self.os

        if "install_path" in missing:
            error = self.readLegacyInstallDir(parser, updates, removals)
            if error:
                return error

        self.setRelease(self.release)

        self.extendDir = os.path.join(self.syncDir, EXTEND_DIR)

        if updates or removals:
            self.update(updates, removals, parser)

        return None

    def readLegacyInstallDir(self, parser, updates, removals):
        try:
            installDir = parser.get(SECTION, "install_dir")
        except configparser.NoOptionError:
            return (
                f"{log.getLogPrefix('ERROR')}Could not find mandatory config"
                " option: install_path"
            )

        self.setInstallPath(os.path.join(self.expandAbsPath(installDir), SC))
        print(
            "Found deprecated option 'install_dir' which was replaced by"
            " 'install_path'. While the 'install_dir' named the base path"
            " without the seiscomp root folder, the 'install_path' will"
            " include it. Based on your current settings we suggest to set\n "
            f" 'install_path = {self.installPath}"
        )
        if checkInput("Replace install_dir with install_path?", "y", "yn"):
            updates["install_path"] = self.installPath
            removals.append("install_dir")

        return None

    def setRelease(self, release):
        self.release = release
        self.archDir = os.path.join(
            self.release, self.os, self.os_version, self.arch
        )

        self.noArchDir = os.path.join(self.release, ANY_NOARCH_DIR)

    def setNoArchDir(self, noArchDir):
        self.noArchDir = noArchDir

    def setArchDir(self, archDir):
        self.archDir = archDir

    def createdDirectories(self):
        if not hasattr(self, "createdDirs"):
            self.createdDirs = {}
        return self.createdDirs

    def cleanupCreatedDirectories(self, currentDirAttr=None, keep=None):
        created = self.createdDirectories()
        for attr in [currentDirAttr] if currentDirAttr else list(created):
            directories = created.get(attr, [])
            if keep and directories and directories[-1] == keep:
                continue
            for directory in reversed(directories):
                if osutils.removeEmptyDirectory(directory):
                    print(f"Removed the directory {directory}, created for the setup.")
                else:
                    print(f"The directory {directory} was kept.")
            created.pop(attr, None)

    def setDirectory(self, prompt, currentDirAttr):
        while True:
            path = self.expandAbsPath(
                getInput(prompt, getattr(self, currentDirAttr))
            )

            ret, msg = osutils.checkCanCreateDirectory(path)

            if ret:
                self.cleanupCreatedDirectories(currentDirAttr, keep=path)
                setattr(self, currentDirAttr, path)
                break

            print(
                f"Failed to create directory '{path}', permission denied on: '{msg}'"
            )
            print(osutils.createDirectoryHint(path))
            if osutils.privilegeAvailable() and getInput(
                f"Do you want to create the directory now with {PRIVILEGE_COMMAND}?", "N", "yn"
            ) == "y":
                missing = osutils.missingDirectories(path)
                if osutils.createDirectoryPrivileged(path):
                    self.cleanupCreatedDirectories(currentDirAttr)
                    self.createdDirectories()[currentDirAttr] = missing
                    setattr(self, currentDirAttr, path)
                    break
                print(f"The directory could not be created with {PRIVILEGE_COMMAND}.")
            q = "Would you like to proceed? Please keep in mind that this may lead to " \
                 "potential issues during the installation."
            answer = getInput(q, "N", "yn")
            if answer == "n":
                setattr(self, currentDirAttr, getattr(self, currentDirAttr))
            else:
                setattr(self, currentDirAttr, path)
                return True

        return True

    def setDataDirSetup(self):
        self.setDirectory("Data path", "dataDir")

    def setDataDir(self, dataDir):
        self.dataDir = self.expandAbsPath(dataDir)

    def setPackageBackupDirSetup(self):
        self.setDirectory("Package backup path", "packageBackupDir")

    def setPackageBackupDir(self, packageBackupDir):
        self.packageBackupDir = self.expandAbsPath(packageBackupDir)

    def setLicenseInfoDaysSetup(self):
        while True:
            licenseInfoDaysInput = getInput(
                "Number of days before "
                "the license expires message "
                "is displayed: ",
                self.licenseInfoDays,
            )
            try:
                licenseInfoDays = int(licenseInfoDaysInput)

                if licenseInfoDays >= 0:
                    self.licenseInfoDays = licenseInfoDays
                    break
                print("Please enter a positive integer or 0.")

            except ValueError:
                print("Invalid input. Please enter an integer.")

    def setDownloadDirSetup(self):
        self.setDirectory("Download dir", "downloadDir")

    def setDownloadDir(self, downloadDir):
        self.downloadDir = self.expandAbsPath(downloadDir)
        self.downloadLicenseDir = os.path.join(self.downloadDir, LICENSES)

    def setSyncDir(self, syncDir):
        self.syncDir = self.expandAbsPath(syncDir)

    def setLocalDir(self, localDir):
        self.localDir = self.expandAbsPath(localDir)
        self.internalConfig = os.path.join(self.localDir, DOT_CONFIG)

    def syncPath(self, *parts):
        return os.path.join(self.syncDir, *parts)

    def downloadPath(self, *parts):
        return os.path.join(self.downloadDir, *parts)

    def packagePath(self, pkg):
        return os.path.join(pkg.localDir or self.downloadDir, pkg.fileName)

    def localPath(self, *parts):
        return os.path.join(self.localDir, *parts)

    def scPath(self, *parts):
        return self.syncPath(SC, *parts)

    def dataPath(self, *parts):
        return os.path.join(self.dataDir, *parts)

    def gsmPath(self, *parts):
        return os.path.join(os.path.dirname(self.localDir), *parts)

    def logDir(self):
        return self.gsmPath(GSM_LOG_DIR)

    def logPath(self):
        return self.gsmPath(GSM_LOG_FILE)

    def setInstallPathSetup(self):
        self.setDirectory("Install path", "installPath")
        self.setInstallPath(self.installPath)
        self.updatePaths()

    def setInstallPath(self, installPath):
        self.installPath = self.expandAbsPath(installPath)
        self.rootDir = os.path.basename(self.installPath)
        if not self.rootDir:
            raise ValueError("Root directory not supported as install path")

        self.updatePaths()

    def updatePaths(self):
        self.licenseDir = os.path.join(self.installPath, "share", LICENSES)
        self.libDir = os.path.join(self.installPath, "lib")
        self.userConfigDir = os.path.join(self.homeDir, f".{SC}")

    def setLoginCredentials(self):
        self.user = getInput("Username", self.user)
        self.password = utils.getInputPW("Password", self.password)

        if not self.baseURL:
            self.baseURL = urljoin(BASE_URL, "packages", self.user.upper())

        url = getInput("Repository URL", self.baseURL)

        self.baseURL = (
            url if "/" in url else f"{self.baseURL.rpartition('/')[0]}/{url}"
        )

    def checkOsSupport(self, config):
        checkOsPath = config.scPath(config.archDir)

        ret = os.path.exists(checkOsPath)
        info = (
            f"\nThe selected OS ({config.os} {config.os_version}"
            f" ({config.arch})) is no longer supported!\n"
        )
        return ret, info

    def checkReleaseSupport(self, config):
        ret = os.path.exists(config.scPath(config.release))
        info = (
            f"\nThe selected {SEISCOMP} release ({config.release}) is "
            "no longer supported!\n"
            f"You can switch to a new release with {config.gsmCall} do-release-upgrade.\n"
        )

        return ret, info

    @staticmethod
    def askNonEmpty(prompt, default):
        while True:
            answer = (getInput(prompt, default) or "").strip()
            if answer:
                return answer
            print(f"{prompt} must not be empty.")

    def setupOS(self):
        os_ = version = arch = None
        if not all((self.os, self.os_version, self.arch)):
            os_, version, arch = osutils.detectOS()
        if not self.os:
            self.os = os_
        if not self.os_version:
            self.os_version = version
        if not self.arch:
            self.arch = arch

        while True:
            os_Save = self.os
            self.os = self.askNonEmpty("Operating system", self.os)
            ret, availableOses = utils.isOsAvailable(
                self.release, self.os, self.verify
            )
            if ret:
                break
            print(
                f"The specified OS [{self.os}] is not supported. "
                f"Available operating systems for {SEISCOMP} release"
                f" ({self.release}): [{', '.join(availableOses or [])}]"
            )
            self.os = os_Save

        while True:
            try:
                if self.os != os_:
                    ret, availableOsVersions = utils.isOsVersionAvailable(
                        self.release, self.os, self.os_version, self.verify
                    )
                    if not ret and availableOsVersions:
                        self.os_version = max(availableOsVersions)
                    elif not ret:
                        self.os_version = None
            except UnboundLocalError:
                pass
            os_version_save = self.os_version
            self.os_version = self.askNonEmpty(
                "Operating system version", self.os_version
            )
            ret, availableOsVersions = utils.isOsVersionAvailable(
                self.release, self.os, self.os_version, self.verify
            )
            if ret:
                break
            print(
                f"The specified OS version [{self.os_version}] is not supported. "
                f"Available operating systems version for {self.os}:"
                f" [{', '.join(availableOsVersions or [])}]"
            )
            self.os_version = os_version_save

        while True:
            arch_saved = self.arch
            self.arch = self.askNonEmpty("System architecture", self.arch)
            ret, availableArch = utils.isArchAvailable(
                self.release, self.os, self.os_version, self.arch, self.verify
            )
            if ret:
                break
            print(
                f"The specified architecture [{self.arch}] is not supported. "
                f"Available operating systems architectures for"
                f" {self.os}/{self.os_version}: [{', '.join(availableArch or [])}]"
            )
            self.arch = arch_saved

        if os_ is None:
            os_, version, arch = osutils.detectOS()
        return bool(
            os_ == self.os
            and version == self.os_version
            and arch == self.arch
        )

    def setupURL(self):
        if self.baseURL == BASE_PUBLIC_URL:
            default = "n"
        else:
            default = "y"
        q = (
            f"Do you want to use your private repository with"
            f" gempa modules? Otherwise use the public {SEISCOMP} without gempa modules."
        )
        answer = getInput(q, f"{default}", "yn")
        if answer == "y":
            self.setLoginCredentials()

            ret, retCode = utils.checkUrlAccess(self)

            while not ret:
                if retCode == 401:
                    print("Invalid login credentials.")
                elif retCode == 404:
                    print("Invalid repository URL.")
                else:
                    print(f"HTTP Error: {HTTPStatus(retCode).phrase} ")

                self.setLoginCredentials()
                ret, retCode = utils.checkUrlAccess(self)
        else:
            self.baseURL = BASE_PUBLIC_URL
            self.user = ""
            self.password = ""

    def setupRelease(self):
        self.release = utils.getLatestRelease(self.verify) or self.release
        while True:
            self.release = getInput(
                f"{SEISCOMP} release", self.release
            ).strip()
            ret, availableReleases = utils.isReleaseAvailable(
                self.release, self.verify
            )
            if ret:
                break
            print(
                f"Unknown {SEISCOMP} release: [{self.release}], "
                f"available {SEISCOMP} releases: [{', '.join(availableReleases)}]"
            )
            self.release = DEFAULT_RELEASE

    def setupGPG(self):
        if not self.gpgVerify:
            default = "n"
        else:
            default = "y"

        q = "Do you want to validate the downloaded packages using gnupg?:"
        answer = getInput(q, f"{default}", "yn")
        if answer == "y":
            self.gpgVerify = True

    def setupPackageBackup(self):
        if not self.makeBackup:
            default = "n"
        else:
            default = "y"

        q = "Do you want to backup the downloaded packages:"
        answer = getInput(q, f"{default}", "yn")
        if answer == "y":
            self.makeBackup = True
        if self.makeBackup:
            self.setPackageBackupDirSetup()

    def setupLocalBin(self):
        if os.path.exists(HOME_LOCAL_BIN) and osutils.isPathInEnv(
            HOME_LOCAL_BIN
        ):
            if not os.path.exists(os.path.join(HOME_LOCAL_BIN, self.gsmBinary)):
                q = f"Would you like to create a link to {HOME_LOCAL_BIN}:"
                answer = getInput(q, "n", "yn")
                if answer == "y":
                    try:
                        if os.path.basename(self.gsmBinary).startswith("gsm-"):
                            source = os.path.join(self.baseDir, self.gsmBinary)
                            target = os.path.join(HOME_LOCAL_BIN, os.path.basename(self.gsmBinary))
                            print("Please run: source ~/.bashrc")
                        else:
                            source = os.path.join(self.baseDir, GSM)
                            target = os.path.join(HOME_LOCAL_BIN, GSM)
                            print("Please add to your .bashrc: "\
                                  f'source "{self.shellCompletionScript()}"')

                        if not os.path.isfile(target):
                            os.symlink(source, target)

                    except Exception as e:
                        print(e)

    def shellCompletionScript(self):
        baseDir = self.baseDir
        if self.gsmBinary != GSM:
            baseDir = self.baseDir.split(ALIASES_DIR)[0].rstrip(os.sep)
        return os.path.join(baseDir, SHELL_COMPLETION_FILE)

    def printShellCompletionHint(self):
        script = self.shellCompletionScript()
        if not os.path.isfile(script):
            return
        print(
            f"""
To enable tab completion for '{self.gsmBinary}', add this line to your \
~/.bashrc:

    source "{script}"

Then reload it once with:

    source ~/.bashrc
"""
        )

    def setup(self):
        self.createdDirs = {}
        done = False
        try:
            done = self.runSetup()
            return done
        finally:
            if not done:
                self.cleanupCreatedDirectories()

    def runSetup(self):
        self.runAgain = os.path.exists(self.fileName)
        if self.assumeYes:
            return self.setupNonInteractive()
        if self.runAgain:
            print(
                f"""
The setup file exists already. Your current settings will be suggested as
default values and may be confirmed simply by pressing enter.

NOTE: You cannot change the {SEISCOMP} release or operating system by calling \
{self.gsmCall} setup.
* to change the {SEISCOMP} release, explicitly use {self.gsmCall} do-release-upgrade
  or {self.gsmCall} do-release-downgrade.
* to change the operating system, explicitly use {self.gsmCall} switch-os.
"""
            )
            if checkInput(f"{MSG_CONTINUE_QUESTION}", "N", "yn"):
                return False
        else:
            print(
                """====================================================================
Package manager setup
====================================================================

This initializes the configuration of your package manager.
If you already made adjustments to the configuration file then your
current settings will be suggested as default values and may be
confirmed simply by pressing enter.
The configuration file is only written after the setup is completed
entirely.
"""
            )

        try:
            if not self.runAgain:
                self.setupRelease()
                if not self.setupOS():
                    if not checkInput(
                        "\nThe operating system selection does not match the system you are "
                        "currently using.\n"
                        "Do you want to restart the setup for the operating system?",
                        "n",
                        "yN",
                    ):
                        self.os = None
                        self.os_version = None
                        self.arch = None

                        self.setupOS()

            self.setupURL()

            self.setDownloadDirSetup()
            if not self.runAgain:
                self.setInstallPathSetup()
                self.setDataDirSetup()
            if self.licenseInfoDays in (None, ""):
                self.licenseInfoDays = LICENSE_INFO_DAYS
            self.setLicenseInfoDaysSetup()
            self.setupGPG()
            self.setupPackageBackup()
            self.setupLocalBin()

        except KeyboardInterrupt:
            print("\n\nSetup aborted by user.")
            return False

        return self.writeSetup()

    def writeSetup(self):
        parser = getConfigParser()

        parser.add_section(SECTION)
        for opt in CONFIG_OPTIONS:
            if opt.write:
                parser.set(SECTION, opt.key, getattr(self, opt.attr))

        self.write(parser, self.fileName)

        self.writeInitialConfigFile(
            self.release,
            self.installPath,
            self.baseDir,
            self.dataDir,
        )

        self.printShellCompletionHint()

        return True

    def setupNonInteractive(self):
        detOs, detVersion, detArch = osutils.detectOS()
        self.os = self.os or detOs
        self.os_version = self.os_version or detVersion
        self.arch = self.arch or detArch

        if not self.offline:
            ret, available = utils.isReleaseAvailable(self.release, self.verify)
            if not ret:
                log.logError(
                    f"Unknown {SEISCOMP} release '{self.release}'. "
                    f"Available: [{', '.join(available)}]"
                )
                return False

            ret, available = utils.isOsAvailable(
                self.release, self.os, self.verify
            )
            if not ret:
                log.logError(
                    f"Unsupported operating system '{self.os}' for {SEISCOMP} "
                    f"release {self.release}. Available: [{', '.join(available)}]"
                )
                return False

            ret, available = utils.isOsVersionAvailable(
                self.release, self.os, self.os_version, self.verify
            )
            if not ret:
                log.logError(
                    f"Unsupported version '{self.os_version}' for {self.os}. "
                    f"Available: [{', '.join(available)}]"
                )
                return False

            ret, available = utils.isArchAvailable(
                self.release, self.os, self.os_version, self.arch, self.verify
            )
            if not ret:
                log.logError(
                    f"Unsupported architecture '{self.arch}' for "
                    f"{self.os}/{self.os_version}. Available: [{', '.join(available)}]"
                )
                return False

        self.setRelease(self.release)

        if not self.user and not self.password:
            self.baseURL = BASE_PUBLIC_URL
            self.user = ""
            self.password = ""
        else:
            if not self.baseURL:
                log.logError(
                    "A repository URL is required when a user or password is "
                    "given. Provide it with --url."
                )
                return False
            if not self.offline:
                ret, retCode = utils.checkUrlAccess(self)
                if not ret:
                    log.logError(
                        f"Cannot access repository '{self.baseURL}' "
                        f"(HTTP {retCode})."
                    )
                    return False

        try:
            self.setDownloadDir(self.downloadDir)
            self.setInstallPath(self.installPath)
            self.setDataDir(self.dataDir)
        except ValueError as e:
            log.logError(str(e))
            return False

        if self.licenseInfoDays in (None, ""):
            self.licenseInfoDays = LICENSE_INFO_DAYS
        try:
            if int(self.licenseInfoDays) < 0:
                raise ValueError
        except (TypeError, ValueError):
            log.logError("license-info-days must be a non-negative integer.")
            return False

        if self.makeBackup:
            self.setPackageBackupDir(self.packageBackupDir)

        return self.writeSetup()
