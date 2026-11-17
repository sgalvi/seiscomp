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

from lib import package
from lib.cache import cacheutils
from lib.const import (
    SEISCOMP,
    REVERSED_REPLACEMENT,
    MSG_CONTINUE_QUESTION,
    EXIT_SUCCESS,
    EXIT_FAILURE,
)
from lib.utils import checkInput, getInput


class ReleaseDowngrade:
    def __init__(self, config, localCache):
        self.config = config
        self.localCache = localCache
        self.syncCache = None
        self.installedPackages = None
        self.newRelease = None
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
            REVERSED_REPLACEMENT,
        )

        if not self.config.downloadOnly and checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
            return False


        print("")
        return True

    def prepareRelease(self):
        releases = package.getLatestStableReleases(self.config, True)
        if self.config.upgradeTarget:
            if self.config.upgradeTarget not in releases:
                print("Release not found.")
                sys.exit(EXIT_FAILURE)
        else:
            if not releases:
                print("No older release found.")
                sys.exit(EXIT_SUCCESS)

            if not self.config.downloadOnly:  # a download changes nothing: no advice, no question
                print(
                    "\nPlease downgrade releases only if you know what you are doing\n"
                    "Depending on the release, additional steps may be required, e.g.:\n"
                    "\n"
                    "* Lower the database schema version\n"
                    "* Install additional modules which functionality is part of the newer"
                    " SeisComP release\n"
                    "* Install required dependencies\n"
                    "\n"
                    f"If your {SEISCOMP} installation is not under version control, we"
                    " recommend to make a backup before continuing.\n"
                )
                if checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
                    sys.exit(EXIT_SUCCESS)

        self.cacheUtils.storeBackup()

        if self.config.upgradeTarget:
            self.newRelease = self.config.upgradeTarget
        else:
            print("\nSelect a number from the list to choose the release:\n")

            for count, release in enumerate(releases, start=1):
                print(f"{count}: {release}")
            print("")

            try:
                value = int(getInput("Downgrade to Option"))
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

    def prepareDowngrade(self):
        self.prepareRelease()

        self.installedPackages = cacheutils.getInstalledPackages(self.localCache)

        if not self.findObsoletePackages():
            return False

        if not self.cacheUtils.downloadNewPackages(self.installedPackages):
            return False

        return cacheutils.allPackagesLicensed(
            self.localCache, self.installedPackages, "downgrade"
        )

    def run(self, app):
        prepared = False
        try:
            if not cacheutils.getInstalledPackages(self.localCache):
                self.prepareRelease()
                print(
                    "\nNo installed packages found! Only downgrade release configuration."
                )
                self.config.update({"release": self.newRelease}, [])
                self.config.updateInstallInfoFile("release", self.newRelease)
                sys.exit(EXIT_SUCCESS)

            self.config.updateOrDowngrade = True

            if not self.prepareDowngrade():
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
        return True
