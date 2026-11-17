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


import sys

from lib import log, package, utils
from lib.cache import synccache, cacheutils
from lib.const import (
    BASE_PUBLIC_URL,
    NIGHTLY,
    SC,
    RENAME_SEEDLINK_BUFFER,
    CHECK_SCCONFIG,
    SEISCOMP_TOOLS,
    SEISCOMP,
    PACKAGES_REPLACEMENT,
    MSG_CONTINUE_QUESTION,
    EXIT_SUCCESS,
    EXIT_FAILURE,
)
from lib.utils import checkInput, getInput


class ReleaseUpgrade:
    def __init__(self, config, localCache):
        self.config = config
        self.localCache = localCache
        self.syncCache = None
        self.installedPackages = None
        self.newRelease = None
        self.oldSeiscompVersionPkg = None
        self.cacheUtils = cacheutils.CacheUtils(self.config, self.localCache)

    def findObsoletePackages(self):
        self.config.setRelease(self.newRelease)
        self.syncCache = cacheutils.buildSyncCache(self.config)
        if self.syncCache is None:
            return False

        cacheutils.reportObsoletePackages(
            self.installedPackages,
            self.syncCache,
            "release",
            self.newRelease,
            PACKAGES_REPLACEMENT,
        )

        if not self.config.downloadOnly and checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
            return False

        print("")
        return True

    def prepareRelease(self):
        releases = package.getLatestReleases(self.config, True)
        if self.config.upgradeTarget:
            if self.config.upgradeTarget not in releases:
                print("Release not found.")
                sys.exit(EXIT_FAILURE)
        else:
            if not releases:
                print("No new release found.")
                sys.exit(EXIT_SUCCESS)

            if not self.config.downloadOnly:  # a download changes nothing: no advice, no question
                print(
                    f"\nIf your {SEISCOMP} installation is not under version control, we"
                    " recommend to make a backup before continuing."
                )
                if checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
                    sys.exit(EXIT_SUCCESS)

        self.cacheUtils.storeBackup()

        if self.config.upgradeTarget:
            self.newRelease = self.config.upgradeTarget
        else:
            print("\nSelect a number from the list to choose the release:\n")

            first_element = releases.pop(0)
            releases.append(first_element)

            for count, release in enumerate(releases, start=1):
                print(f"{count}: {release}")
            print("")

            try:
                value = int(getInput("Upgrade to Option"))
                if value < 1:
                    raise IndexError
                self.newRelease = releases[value - 1]
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                print(
                    "Invalid entry. Select a number from the list to choose the release."
                )
                sys.exit(EXIT_FAILURE)

        return True

    def prepareUpgrade(self):
        self.prepareRelease()

        self.oldSeiscompVersionPkg = self.localCache.getPackage(SC)

        self.installedPackages = cacheutils.getInstalledPackages(self.localCache)

        if not self.findObsoletePackages():
            return False

        if not self.cacheUtils.downloadNewPackages(self.installedPackages):
            return False

        return cacheutils.allPackagesLicensed(
            self.localCache, self.installedPackages, "upgrade"
        )

    def printUpgradeNotes(self):
        if self.newRelease == NIGHTLY:
            print("")
            print(
                f"Please check your {SEISCOMP} environment settings in ~/.bashrc"
            )
            print("")
            print(
                "SeedLink in SeisComP3 prior to 2020 uses a simplified buffer. Migrate"
                f" the buffer using '{RENAME_SEEDLINK_BUFFER}' after upgrading."
            )
            print(
                "Download the script here:"
                f" {BASE_PUBLIC_URL}/tools/{RENAME_SEEDLINK_BUFFER}.py"
            )

        print("")
        print(
            f"Recommendation: Run the script '{CHECK_SCCONFIG}' after upgrading to check"
            f" the {SEISCOMP} configuration for deprecated parameters."
        )
        print(
            f"Install the script using gsm install {SEISCOMP_TOOLS} or"
            f" download from {BASE_PUBLIC_URL}/tools/{CHECK_SCCONFIG}.py"
        )
        print("")
        print(
            f"Please also check your {SEISCOMP} environment settings in ~/.bashrc"
        )
        print("")

    def installSeiscompTools(self, app):
        syncCache = synccache.SyncCache(self.config)
        pkg = syncCache.getPackage(SEISCOMP_TOOLS)
        if not pkg:
            return False

        url = utils.getDownloadDirectoryURL(pkg, self.config)
        ret, _ = utils.checkUrlAccess(self.config, url)

        if not self.config.offline and ret:
            if not self.localCache.isInstalled(pkg, False):
                if not self.config.upgradeTarget:
                    print("\n")
                    q = (
                        f"Do you want install {SEISCOMP_TOOLS}"
                        f" ({CHECK_SCCONFIG}) ?"
                    )
                    if not checkInput(
                        q,
                        "Y",
                        "yn",
                    ):
                        return False

                download = syncCache.downloadPackages([pkg.name])
                if not download:
                    print()
                    log.logError("The download of all packages failed.")
                if not syncCache.checksumCheck(pkg.name):
                    print(
                        f"\nTry to run {self.config.gsmCall} "\
                            "update to refresh the package index"
                        f" and run {self.config.gsmCall} install {SEISCOMP_TOOLS},"\
                            " after the upgrade..."
                    )
                else:
                    app.init()
                    app.install([SEISCOMP_TOOLS], True)
        return True

    def run(self, app):
        prepared = False
        try:
            if not cacheutils.getInstalledPackages(self.localCache):
                self.prepareRelease()
                print(
                    "\nNo installed packages found! Only upgrade release configuration."
                )
                self.config.update({"release": self.newRelease}, [])
                self.config.updateInstallInfoFile("release", self.newRelease)
                sys.exit(EXIT_SUCCESS)

            self.config.updateOrDowngrade = True

            if not self.prepareUpgrade():
                return False

            if self.config.downloadOnly:
                self.cacheUtils.printDownloadOnly("release")
                return True

            prepared = True
        finally:
            if not prepared:
                self.cacheUtils.dropBackup()

        try:
            if not self.cacheUtils.removePackages(
                self.installedPackages, self.newRelease
            ):
                self.cacheUtils.restoreBackup()
                return False

            self.printUpgradeNotes()

            if not cacheutils.installTargetPackages(
                app, self.config, self.syncCache, self.installedPackages
            ):
                self.cacheUtils.restoreBackup()
                return False
        except (KeyboardInterrupt, SystemExit):
            self.cacheUtils.restoreBackup()
            raise
        except Exception:
            self.cacheUtils.restoreBackup()
            return False

        self.cacheUtils.dropBackup()

        try:
            self.installSeiscompTools(app)
        except Exception:
            pass

        try:
            targetPkg = synccache.SyncCache(self.config).getPackage(SC)
            if self.config.offline:
                response = package.fetchChangeLogFromTar(targetPkg, self.config)
            else:
                response = package.fetchChangeLog(
                    self.oldSeiscompVersionPkg, self.config
                )
            if response:
                package.printImportantChanges(
                    response,
                    self.oldSeiscompVersionPkg.version,
                    SC,
                    targetPkg.version if targetPkg else None,
                )
        except Exception:
            pass

        return True
