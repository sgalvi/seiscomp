############################################################################
# Copyright (C) 2026 gempa GmbH                                            #
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
import sys

from lib import gpgutils, log, utils

from lib.cache import synccache

from lib.const import (
    REMOVE,
    ANY_NOARCH_DIR,
    GSM,
    MSG_CONTINUE_QUESTION,
    PT,
    APP_DATA_PACKAGES,
    EMAIL_GEMPA,
    EXIT_SUCCESS,
    PKG_FAILED,
)

from lib.utils import checkInput

class CacheUtils:
    def __init__(self, config, localCache):
        self.config = config
        self.localCache = localCache
        self.syncCache = None
        self.backupStored = False

    def removePackages(self, installedPackages, newRelease):
        members = utils.sorting(installedPackages)
        count = 0
        failed = []
        progress = utils.progressBar(members, REMOVE)
        for member in progress:
            pkgName, _ = utils.getPackageName(
                self.localCache.getPackage(member)
            )
            utils.setDesc(progress, REMOVE, pkgName)
            status, _ = self.localCache.removePackage(member)
            if status == PKG_FAILED:
                failed.append(pkgName)
            else:
                count = count + 1

        log.logResult(progress, REMOVE, n=count, total=len(members))
        if failed:
            log.logError(f"Could not remove: {', '.join(failed)}")
            return False

        if newRelease:
            self.config.update({"release": newRelease}, [])
            self.config.updateInstallInfoFile("release", newRelease)

        return True

    def downloadNewPackages(self, installedPackages):
        downloadPackages = []

        self.config.setArchDir(
            os.path.join(
                self.config.release,
                self.config.os,
                self.config.os_version,
                self.config.arch,
            )
        )
        self.config.setNoArchDir(
            os.path.join(self.config.release, ANY_NOARCH_DIR)
        )

        syncCache = synccache.SyncCache(self.config)

        if not installedPackages:
            print("\nNo installed packages found.")

        for name in installedPackages:
            if syncCache.contains([name], False):
                downloadPackages.append(name)

        if not self.config.offline:
            utils.checkUrlAccessProgress(
                self.config, syncCache, downloadPackages
            )

            ret = syncCache.downloadPackages(downloadPackages)
        else:
            ret = True

        failed = []
        fileNotExist = []
        if ret:
            for name in downloadPackages:
                pkgSync = syncCache.getPackage(name)
                fileName = self.config.packagePath(pkgSync)
                if os.path.exists(fileName):
                    fail = utils.hashfile(fileName, pkgSync.checksum, pkgSync)
                    if not fail:
                        failed.append(pkgSync.name)
                        if os.path.isfile(fileName):
                            os.remove(fileName)
                else:
                    fileNotExist.append(pkgSync)

        if fileNotExist:
            for pkg in fileNotExist:
                log.logError(
                    f"The {pkg.fileName} file does not exist in the"
                    f" {self.config.downloadDir} directory."
                )
                return False

        if failed:
            print()
            log.logError(
                "Checksum validation for the following packages failed:"
                f" {', '.join(failed)}"
            )
            print(f"\nTry to run {self.config.gsmCall} update to refresh the package index.")

            return False

        return ret and self.checkSignatures(syncCache, downloadPackages)

    def checkSignatures(self, syncCache, names):
        """gpgverify: the signatures are checked with the download, before anything is removed.

        A package without a signature (the repository has none for the older releases) or with
        one that does not fit is asked about, with the default no. Without anybody to ask
        (-y, -d) the change stops here. Returns False if it is not to go on."""
        if not self.config.gpgVerify:
            return True

        failed = gpgutils.checkGPGProgress(
            self.config, syncCache, syncCache.gpgutils, names
        )
        if failed:
            if self.config.downloadOnly or self.config.assumeYes:
                return False
            if checkInput(
                "Do you want to install the packages with a failed signature check anyway?",
                "n",
                "yn",
            ):
                return False

        self.config.signaturesChecked = True
        return True

    def printDownloadOnly(self, noun):
        print(
            f"\nDownload only: the packages of the new {noun} are in {self.config.downloadDir}."
            " Nothing was changed."
        )

    def restoreBackup(self):
        ret, fileName = utils.backupRestore(self.config)
        if ret:
            log.logInfo(f"The {GSM} backup has been restored ...")
        else:
            log.logError(f"The backup could not be restored from {fileName}")

    def dropBackup(self):
        if self.backupStored:
            utils.backupDrop(self.config)
            self.backupStored = False

    def storeBackup(self):
        if self.config.downloadOnly:  # nothing is changed, nothing to go back to
            return
        self.backupStored = True
        ret, fileName = utils.backupStore(self.config)
        if ret:
            log.logInfo(f"The {GSM} backup has been saved under {fileName}")
        else:
            log.logError("The backup could not be created.")
            if checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
                sys.exit(EXIT_SUCCESS)

def getInstalledPackages(localCache):
    packages = list(localCache.getIndex().keys())
    installedPackages = []

    for name in packages:
        pkg = localCache.getPackage(name)
        if pkg.type == PT.APP and not pkg.name in APP_DATA_PACKAGES:
            installedPackages.append(pkg.name)

    return installedPackages

def buildSyncCache(config):
    syncCache = synccache.SyncCache(config)
    if not syncCache.getIndex():
        return None
    return syncCache


def reportObsoletePackages(installedPackages, syncCache, targetNoun,
                           targetDescription, replacements):
    obsolete = [
        name
        for name in installedPackages
        if not syncCache.contains([name], False)
    ]

    if obsolete:
        log.logInfo(
            "The following package(s) are no longer available in the new"
            f" {targetNoun} ({targetDescription}): {', '.join(obsolete)}"
        )
        print(
            "\nThese packages will be removed by the change and are not installed"
            " again. To stop, answer 'n' to the next question."
        )

        suggested = [name for name in obsolete if name in replacements]
        if suggested:
            print(
                "\nAfter the operation, you can install the following"
                " packages as replacements:"
            )
            for name in suggested:
                print(f"{name} --> {replacements[name]}")
            print("")

    return obsolete

def allPackagesLicensed(localCache, installedPackages, action):
    blocked = any(
        not localCache.isInstallable(localCache.getPackage(name))
        for name in installedPackages
    )
    if blocked:
        log.logError(
            f"Could not perform the {action} because at least one application"
            " is not covered by the license. Please get in touch with"
            f" {EMAIL_GEMPA}"
        )
        return False
    return True

def installTargetPackages(app, config, syncCache, installedPackages):
    app.init()
    config.assumeYes = True
    installable = [
        name
        for name in installedPackages
        if syncCache.contains([name], False)
    ]
    return app.install(installable, True)
