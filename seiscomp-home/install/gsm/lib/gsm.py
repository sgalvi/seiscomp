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

from lib.cache import localcache, synccache

from lib import (
    package,
    log,
    installdeps,
    news,
    osutils,
)


from lib.const import (
    LICENSES,
    PT,
)

from lib.alias import Alias


class Gsm:
    def __init__(self, config):
        self.config = config
        self.package = package
        self.syncCache = synccache.SyncCache(config)
        self.localCache = localcache.LocalCache(config)
        self.localCache.setSyncCache(self.syncCache)
        self.news = news.News(self.config)
        self.alias = None

    def updateSyncIndex(self):
        self.config.fromUpdate = True
        if self.config.offline:
            return True

        return self.syncCache.updateIndex(self.localCache)

    def protectedPackages(self, names):
        result = []
        for name in names:
            pkg = self.getSyncPackage(name)
            if not pkg or not pkg.isPublic():
                result.append(name)

        return result

    def updateCheck(self):
        ret, retCode = self.package.updateCheck(
            self.localCache, self.syncCache, self.config
        )
        return ret, retCode

    def getPackagesUpdateInfo(self, fromUpOrDowngrade=False):
        ret, packages = package.getPackagesUpdateInfo(
            self.syncCache, self.localCache, self.config, fromUpOrDowngrade
        )
        return (ret, packages)

    def getSyncPackage(self, name):
        try:
            return self.syncCache.getPackages(name)[0]
        except IndexError:
            return None

    def showChangeLog(self, packages, show=False):
        if show:
            return package.showChangeLog(
                packages,
                self.config,
                self.localCache,
                self.syncCache,
                True,
            )

        pkgs = self.syncCache.getPackages(packages[0])
        if not pkgs:
            log.logError(
                f"Unable to locate {self.syncCache.notFoundMessage(packages[0])}"
            )
            return False

        del packages[1:]
        package.showChangeLog(
            [pkgs[0].name],
            self.config,
            self.localCache,
            self.syncCache,
            False,
        )

        return True

    def getDependencyInfo(self, packages):
        installationDeps = installdeps.InstallDeps(
            self.config, self.localCache, self.syncCache
        )
        installationDeps.getDependencyInfo(packages)

    def obsoletePackages(self, packages):
        obsolete = []
        known = []
        unknown = []
        for name in packages:
            if self.syncCache.contains([name], False):
                known.append(name)
            elif self.localCache.getPackage(name):
                obsolete.append(name)
            else:
                unknown.append(name)

        return obsolete, known + unknown

    def removeHoldPackages(self, packages):
        holdPackages = [
            name for name in packages if self.localCache.isHold(name)
        ]
        packagesWithoutHolds = [
            name for name in packages if name not in holdPackages
        ]

        if holdPackages:
            log.logInfo(
                f"The following package(s) set on hold: {', '.join(holdPackages)}"
            )

        return packagesWithoutHolds

    def createLicensesPackageList(self, packages):
        packages.remove(LICENSES)
        packagesLicenes = list(
            dict.fromkeys(packages + list(self.localCache.getIndex().keys()))
        )

        return packagesLicenes

    def filterPackages(self, excludePackages, packages):
        if not excludePackages:
            return packages

        filteredPackages = [
            package
            for package in packages
            if package not in excludePackages
        ]

        return filteredPackages

    def createAlias(self, name):
        self.alias = Alias(self.config, name)
        self.alias.createAlias()

    def licenseFailures(self, packages):
        failed = []
        for name in packages:
            pkg = self.getSyncPackage(name)

            if pkg.license != "None":
                if not self.config.offline:
                    if not package.downloadLicense(pkg, self.config):
                        failed.append(name)

            if not self.localCache.isInstallable(pkg):
                failed.append(name)

        return failed

    def checkDataInstallPaths(self, packages):
        for name in packages:
            pkg = self.getSyncPackage(name)
            if pkg.filePath and pkg.type == PT.DATA:
                tmpDir = self.config.dataPath(pkg.filePath)
                osutils.checkInstallPath(self.config.dataDir)

                currentPath = tmpDir
                while currentPath != self.config.dataDir:
                    osutils.checkInstallPath(currentPath)
                    currentPath = os.path.dirname(currentPath)

                osutils.createDirectory(tmpDir)

                if not os.listdir(tmpDir):
                    os.rmdir(tmpDir)

        return True
