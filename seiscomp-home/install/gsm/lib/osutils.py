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

import grp
import hashlib
import os
import platform
import pwd
import shlex
import shutil
import subprocess
import sys

from lib.const import (
    PRIVILEGE_COMMAND,
    DEFAULT_ARCH,
    FILE_ENCODING,
    OS_MAPPING,
    OS_VERSION_ID_MAPPING,
    DEFAULT_OS,
    DEFAULT_OS_VERSION,
    MIN_VERSIONS,
    GSM_MIN_OS_VERSION,
    GSM_OS_DISPLAY_NAME,
    INSTALL_COMMANDS_GNUPG,
    OS_VERSION_OVERRIDES,
    EXIT_FAILURE,
    RESTORE_DIR,
)

from lib import log, utils


def checkOS(config):
    info = osMismatchInfo(config)
    return info is None, info


def osMismatchInfo(config):
    osName, version, arch = detectOS()
    if (osName, version, arch) == (config.os, config.os_version, config.arch):
        return None

    return (
        "WARNING: Operating-system mismatch\n\n"
        f"This installation targets {config.os}/{config.os_version} ({config.arch}), but the"
        " current system is\n"
        f"{osName}/{version} ({arch}). The software may not work as expected.\n\n"
        f"To switch the installation to {osName}, run:\n"
        f"  {config.gsmCall} switch-os\n"
    )


OS_RELEASE_FILES = ("/etc/os-release", "/usr/lib/os-release")


def readOsRelease():
    for path in OS_RELEASE_FILES:
        try:
            with open(path, "r", encoding=FILE_ENCODING) as f:
                osRelease = {}
                for line in f:
                    key, sep, value = line.partition("=")
                    if sep and not key.lstrip().startswith("#"):
                        osRelease[key.strip().upper()] = value.strip().strip("\"'")
                return osRelease
        except OSError:
            continue

    return None


def detectOS():
    arch = platform.machine() or DEFAULT_ARCH

    osRelease = readOsRelease()
    if not osRelease or not osRelease.get("ID"):
        return DEFAULT_OS, DEFAULT_OS_VERSION, arch

    osId = osRelease["ID"].lower()
    osName = OS_MAPPING.get(osId, osId)
    detectedVersion = osRelease.get(OS_VERSION_ID_MAPPING.get(osName, "VERSION_ID"), "")
    version = (
        OS_VERSION_OVERRIDES.get((osId, detectedVersion))
        or OS_VERSION_OVERRIDES.get((osName, detectedVersion))
        or detectedVersion
        or None
    )

    if osName == "rhel" and version:
        version = version.split(".")[0]

    return osName, version, arch


def unsupportedSystem(detected=None):
    """Why a new gsm does not run on this operating system, or None (it does, or it is not known).

    Only a system that is known and older than the oldest supported version is refused: another
    distribution (Arch, Fedora, ...) and a version that is no number (Debian testing) are not.
    """
    osName, version, _ = detected or detectOS()
    oldest = GSM_MIN_OS_VERSION.get(osName)
    try:
        have = tuple(int(part) for part in version.split("."))
    except (ValueError, AttributeError):
        return None
    if oldest is None or have >= oldest:
        return None

    supported = ", ".join(
        f"{GSM_OS_DISPLAY_NAME[name]} {'.'.join(str(part) for part in need)}"
        for name, need in GSM_MIN_OS_VERSION.items()
    )
    return (
        f"{GSM_OS_DISPLAY_NAME[osName]} {version} is no longer supported by gsm"
        f" (it needs Python 3.9 or newer). Supported are {supported} or newer."
        " Please upgrade the operating system."
    )


def printImportHelper(e, deps):
    os_, version, _ = detectOS()
    try:
        version_tuple = tuple(map(int, version.split(".")))
    except (ValueError, AttributeError):
        version_tuple = None

    print(
        f"""{e}\n\nYou may install all dependencies locally using the following command:\n"""
    )

    if os_ in MIN_VERSIONS and version_tuple and version_tuple >= MIN_VERSIONS[os_]:
        if deps == "gnupg":
            print(INSTALL_COMMANDS_GNUPG.get(os_))


def isPathInEnv(checkPath):
    pathVariable = os.environ["PATH"]
    paths = pathVariable.split(os.pathsep)
    return checkPath in paths


def checksum(fileName):
    hasher = hashlib.sha256()
    try:
        with open(fileName, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                hasher.update(chunk)
    except OSError:
        return ""

    return hasher.hexdigest()


def relativeTo(path, base):
    prefix = base + os.sep
    return path[len(prefix):] if path.startswith(prefix) else path


def du(path):
    totalSize = 0
    if os.path.exists(path):
        for dirPath, _, fileNames in os.walk(path):
            for fileName in fileNames:
                filePath = os.path.join(dirPath, fileName)
                try:
                    totalSize += os.path.getsize(filePath)
                except OSError:
                    pass
        return utils.humanbytes(totalSize)

    return None


def cleanDirectory(directory, directoryName):
    if os.path.isdir(directory):
        try:
            usedDiskSpace = du(directory)
            print(f"{log.getLogPrefix('CLEAN')}{directoryName} ... ", end="")
            shutil.rmtree(directory)
            print(f"OK: disk space saved: ({directory}, {usedDiskSpace})")
        except OSError as ex:
            log.logError(str(ex))
            return False
    else:
        log.logError(f"{directoryName} does not exist ({directory})")
    return True


def clean(patterns, config):
    if "packages" in patterns:
        cleanDirectory(config.downloadDir, "packages")

    if "dbcache" in patterns:
        cleanDirectory(config.syncDir, "dbcache")

    if "backup" in patterns:
        cleanDirectory(config.packageBackupDir, "backup")

    if "restore" in patterns:
        restoreDir = os.path.join(os.path.dirname(config.localDir), RESTORE_DIR)
        cleanDirectory(restoreDir, "restore")

    if "all" in patterns:
        cleanDirectory(config.syncDir, "dbcache")
        cleanDirectory(config.downloadDir, "packages")

    return True


def checkInstallPath(path):
    if os.path.exists(path):
        if not os.access(path, os.W_OK):
            log.logError(f"Permission denied on directory {path}")
            sys.exit(EXIT_FAILURE)
    return True


def checkCanCreateDirectory(path):
    existing = os.path.abspath(path)
    while not os.path.exists(existing):
        existing = os.path.dirname(existing)

    if os.path.isdir(existing) and os.access(existing, os.W_OK | os.X_OK):
        return True, None

    return False, existing


def currentOwner():
    try:
        return f"{pwd.getpwuid(os.getuid()).pw_name}:{grp.getgrgid(os.getgid()).gr_name}"
    except (KeyError, OSError):
        return f"{os.getuid()}:{os.getgid()}"


def createDirectoryHint(path):
    path = shlex.quote(os.path.abspath(path))
    return (
        "Create the directory once as root, afterwards no special rights are needed:\n"
        f"  mkdir -p {path} && chown {currentOwner()} {path}"
    )


def privilegeAvailable():
    return os.geteuid() != 0 and shutil.which(PRIVILEGE_COMMAND) is not None


def createDirectoryPrivileged(path):
    path = os.path.abspath(path)
    owner = currentOwner()
    print(f"  {PRIVILEGE_COMMAND} mkdir -p {shlex.quote(path)} && chown {owner} {shlex.quote(path)}")
    # the path and the owner are arguments of the script, they are never part of its text
    script = 'mkdir -p -- "$1" && chown -- "$2" "$1"'
    return subprocess.run([PRIVILEGE_COMMAND, "sh", "-c", script, "sh", path, owner]).returncode == 0


def missingDirectories(path):
    missing = []
    current = os.path.abspath(path)
    while current and not os.path.exists(current):
        missing.append(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return missing[::-1]


def removeEmptyDirectory(path):
    try:
        os.rmdir(path)
        return True
    except FileNotFoundError:
        return True
    except PermissionError:
        pass
    except OSError:
        return False  # not empty

    if not privilegeAvailable():
        return False

    print(f"  {PRIVILEGE_COMMAND} rmdir {shlex.quote(path)}")
    return subprocess.run([PRIVILEGE_COMMAND, "rmdir", "--", path]).returncode == 0


def createDirectory(path):
    checkInstallPath(path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            log.logError(f"Failed to create directory '{path}': {e}")
            sys.exit(EXIT_FAILURE)

    return True
