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

import os
import shutil
import subprocess
import sys


from lib import log, utils

from lib.const import (
    PKG_SUCCESS,
    PKG_FAILED,
    PKG_NOT_FOUND,
    PUBRING_KBX,
    TRUSTDB_GPG,
    EXIT_FAILURE,
    PT,
    CHECKPGP,
    SIG_EXTENSION,
)

PKG_SIG_NOT_FOUND = 3

# gsm starts the gpg program of the system itself (gpg --verify with --status-fd); no Python
# package is needed. A signature counts only if gpg says GOODSIG and VALIDSIG and exits with 0.
# An expired key ends gpg with 0 and EXPKEYSIG: the exit code alone is not enough.
GPG_PROGRAMS = ("gpg", "gpg2")
STATUS_PREFIX = "[GNUPG:] "
GOOD_STATUS = ("GOODSIG", "VALIDSIG")  # both are needed
BAD_STATUS = ("BADSIG", "ERRSIG", "NO_PUBKEY", "EXPSIG", "EXPKEYSIG", "REVKEYSIG")  # any of them is enough
VERIFY_TIMEOUT = 3600  # seconds; a hanging gpg must not hang gsm


def findGpg():
    """The gpg program of the system, or None."""
    for name in GPG_PROGRAMS:
        path = shutil.which(name)
        if path:
            return path
    return None


def statusWords(output):
    """The keywords of the status lines gpg wrote, e.g. {'NEWSIG', 'GOODSIG', 'VALIDSIG'}."""
    words = set()
    for line in output.splitlines():
        if line.startswith(STATUS_PREFIX):
            fields = line[len(STATUS_PREFIX):].split()
            if fields:
                words.add(fields[0])
    return words


def isValid(returnCode, output):
    """Do the exit code and the status output of gpg --verify say that the signature is good?"""
    words = statusWords(output)
    return (
        returnCode == 0
        and all(word in words for word in GOOD_STATUS)
        and not any(word in words for word in BAD_STATUS)
    )


class GPGUtils:
    def __init__(self, config):
        self.gpgDir = config.gpgDir
        self.program = findGpg()
        if self.program is None and config.gpgVerify:
            raise OSError("The gpg program is missing. Verifying signatures needs it.")

        if config.gpgVerify:
            for path in (os.path.join(config.gpgDir, PUBRING_KBX),
                 os.path.join(config.gpgDir, TRUSTDB_GPG)):
                if not os.path.exists(path):
                    log.logError(f"The {path} does not exist.")
                    sys.exit(EXIT_FAILURE)

    def check(self, filePath, signaturePath):
        """Run gpg --verify <signature> <file>: is the signature good?"""
        command = [self.program, "--homedir", self.gpgDir, "--batch", "--no-tty",
                   "--status-fd", "1", "--verify", signaturePath, filePath]
        env = dict(os.environ, LC_ALL="C", LANGUAGE="C")
        try:
            done = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                  env=env, check=False, timeout=VERIFY_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as err:
            log.logError(f"Could not run gpg: {err}")
            return False
        return isValid(done.returncode, done.stdout)

    def verifyFile(self, filePath, signaturePath, info=False):

        if not os.path.isfile(filePath):
            if info:
                log.logError(f"The '{filePath}' does not exist.")
            return PKG_NOT_FOUND

        if not os.path.isfile(signaturePath):
            if info:
                log.logWarning(f"The signature file '{signaturePath}' does not exist.")
            return PKG_SIG_NOT_FOUND

        if self.check(filePath, signaturePath):
            if info:
                log.logInfo(f"Verification successfully for file '{filePath}'.")
            return PKG_SUCCESS

        if info:
            log.logError(f"Verification failed for file '{filePath}'.")

        return PKG_FAILED


def checkGPGProgress(config, syncCache, gpgutils, members):
    members = utils.sorting(members)
    failed = []

    failedNoSignatureFile = []
    failedSignatureCheck = []
    noSignatureType = []
    skip_count = 0
    failed_count = 0

    progress = utils.progressBar(members, CHECKPGP)

    for member in progress:
        pkg = syncCache.getPackage(member)
        fileName = config.packagePath(pkg)

        if pkg.type in (PT.CONFIG, PT.DATA) and not (
            pkg.sigFile and os.path.isfile(pkg.sigFile)
        ):
            noSignatureType.append(pkg.name)
            skip_count += 1
            ret = 0
        else:
            sigFile = pkg.sigFile if pkg.sigFile else fileName + SIG_EXTENSION
            ret = gpgutils.verifyFile(fileName, sigFile)

            if ret == 1:
                failedSignatureCheck.append(pkg.name)

            if ret == 3:
                failedNoSignatureFile.append(pkg.name)
                failed_count += 1

            if ret != 0:
                failed.append(pkg.name)

    log.logResult(
        progress,
        CHECKPGP,
        n=len(members) - failed_count - skip_count,
        total=len(members),
        ok=not failed,
    )

    if noSignatureType:
        print(
            "The signature file for the following packages "
            f"was skipped: {', '.join(noSignatureType)}"
        )
    if failedNoSignatureFile:
        log.logError(
            "The signature file for the following packages "
            f"has not found: {', '.join(failedNoSignatureFile)}"
        )
        if not failedSignatureCheck:
            print("\n")

    if failedSignatureCheck:
        log.logError(
            "The signature check for the following packages"
            f" has failed: {', '.join(failedSignatureCheck)}"
        )
        print()

    return failed
