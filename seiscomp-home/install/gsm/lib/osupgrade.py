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
import sys

from lib.cache import cacheutils

from lib.utils import checkInput, getInput
from lib.osutils import detectOS

from lib.const import (
    SEISCOMP,
    MSG_CONTINUE_QUESTION,
    EXIT_FAILURE,
)


class OSUpgrade:
    def __init__(self, config, localCache):
        self.config = config
        self.localCache = localCache
        self.syncCache = None
        self.installedPackages = None
        self.new_os = None
        self.new_os_version = None
        self.new_arch = None

        self.old_os = config.os
        self.old_os_version = config.os_version
        self.old_arch = config.arch

        self.OS = "operating systems"
        self.VERSION = "versions"
        self.ARCH = "architectures"

        self.detect_os_name, self.detect_os_version, self.detect_os_arch = (
            detectOS()
        )
        self.cacheUtils = cacheutils.CacheUtils(self.config, self.localCache)
        self.failedOS = False

    def displayAvailableItems(self, items, itemType):

        print(f"\nSelect a number from the list to choose the {itemType}:\n")
        for count, item in enumerate(items, start=1):
            print(f"{count}: {item}")
        print("")

    def prepareItemType(self, itemType):
        base_path = self.config.scPath(self.config.release)
        path = []

        if itemType == self.OS:
            path = sorted(os.listdir(base_path))
            if len(path) == 1:
                self.new_os = path[0]
        elif itemType == self.VERSION:
            path = sorted(os.listdir(os.path.join(base_path, self.new_os)))
            if len(path) == 1:
                self.new_os_version = path[0]
        elif itemType == self.ARCH:
            path = os.listdir(
                os.path.join(base_path, self.new_os, self.new_os_version)
            )
            if len(path) == 1:
                self.new_arch = path[0]

        return path, len(path) == 1

    def prepareItems(self, itemType):
        items, ret = self.prepareItemType(itemType)

        if ret:
            return ret

        self.displayAvailableItems(items, itemType)

        try:
            if itemType == self.OS:
                if self.detect_os_name in items:
                    idx = getInput(
                        f"Upgrade to Option ({items.index(self.detect_os_name) + 1})"
                    )
                    if not idx:
                        idx = items.index(self.detect_os_name) + 1
                else:
                    idx = getInput("Upgrade to Option")
                value = int(idx)
                self.new_os = items[value - 1]

            if itemType == self.VERSION:
                if (
                    self.new_os == self.detect_os_name
                    and self.detect_os_version in items
                ):
                    idx = getInput(
                        f"Upgrade to Option ({ items.index(self.detect_os_version) + 1})"
                    )
                else:
                    if not self.detect_os_version in items:
                        if not self.failedOS:
                            print(
                                f"NOTICE: The selected {SEISCOMP} release is not available for the "
                                f"selected operating system.\n        Try a"
                                f" {self.config.gsmCall} do-release-upgrade followed by a"
                                f" {self.config.gsmCall} switch-os to resolve the issue."
                                " To cancel press CTRL+C.\n"
                            )
                    idx = getInput("Upgrade to Option")

                if not idx and self.new_os == self.detect_os_name:
                    idx = items.index(self.detect_os_version) + 1
                value = int(idx)
                self.new_os_version = items[value - 1]

            if itemType == self.ARCH:
                if self.detect_os_arch in items:
                    idx = getInput(
                        f"Upgrade to Option ({items.index(self.detect_os_arch) + 1})"
                    )
                    if not idx:
                        idx = items.index(self.detect_os_arch) + 1
                else:
                    idx = getInput("Upgrade to Option")
                value = int(idx)
                self.new_arch = items[value - 1]

        except KeyboardInterrupt as e:
            raise e

        except Exception:
            print("Invalid entry. Please select an entry from the list.")
            return False

        return True

    def parseTarget(self):
        parts = self.config.upgradeTarget.split("/")
        if len(parts) not in (2, 3):
            print(
                f"Invalid --to value '{self.config.upgradeTarget}'."
                " Expected format os/version[/arch]."
            )
            sys.exit(EXIT_FAILURE)

        new_os, new_os_version = parts[0], parts[1]
        new_arch = parts[2] if len(parts) == 3 else None

        base_path = self.config.scPath(self.config.release)

        if new_os not in os.listdir(base_path):
            print(f"Operating system '{new_os}' not found.")
            sys.exit(EXIT_FAILURE)

        if new_os_version not in os.listdir(os.path.join(base_path, new_os)):
            print(f"Version '{new_os_version}' not found for {new_os}.")
            sys.exit(EXIT_FAILURE)

        if new_arch and new_arch not in os.listdir(
            os.path.join(base_path, new_os, new_os_version)
        ):
            print(
                f"Architecture '{new_arch}' not found for "
                f"{new_os}/{new_os_version}."
            )
            sys.exit(EXIT_FAILURE)

        self.new_os, self.new_os_version, self.new_arch = (
            new_os,
            new_os_version,
            new_arch,
        )

    def prepareUpgrade(self):
        if not self.config.downloadOnly:  # a download changes nothing: no advice, no question
            print(
                f"\nIf your {SEISCOMP} installation is not under version control, we"
                " recommend making a backup before continuing."
            )

            if checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
                return False

        self.cacheUtils.storeBackup()

        if self.config.upgradeTarget:
            self.parseTarget()
            if not self.new_arch:
                while not self.prepareItems(self.ARCH):
                    pass
        else:
            for item in (self.OS, self.VERSION, self.ARCH):
                while not self.prepareItems(item):
                    pass

        if (
            self.config.os == self.new_os
            and self.config.os_version == self.new_os_version
            and self.config.arch == self.new_arch
        ):
            print("\nNothing to do ...")
            return False

        if self.new_os and self.new_os_version and self.new_arch:
            self.config.os = self.new_os
            self.config.os_version = self.new_os_version
            self.config.arch = self.new_arch

            self.installedPackages = cacheutils.getInstalledPackages(self.localCache)

            if (
                not self.findObsoletePackages()
                or not self.cacheUtils.downloadNewPackages(self.installedPackages)
            ):
                return False

            if not cacheutils.allPackagesLicensed(
                self.localCache, self.installedPackages, "switch"
            ):
                return False

            if not self.config.downloadOnly:
                self.config.update(
                    {
                        "os": self.new_os,
                        "os_version": self.new_os_version,
                        "arch": self.new_arch,
                    },
                    [],
                )

        return True

    def findObsoletePackages(self):
        config = self.config
        config.setRelease(config.release)

        self.syncCache = cacheutils.buildSyncCache(config)
        if self.syncCache is None:
            return False

        cacheutils.reportObsoletePackages(
            self.installedPackages,
            self.syncCache,
            "os",
            f"{self.new_os} {self.new_os_version} ({self.new_arch})",
            {},
        )

        if not self.config.downloadOnly and checkInput(
            f"Do you want to continue with the switch to OS: {self.new_os}/"
            f"{self.new_os_version} ({self.new_arch}) ?",
            "n",
            "yn",
        ):
            return False
        print("")
        return True

    def run(self, app, failedOS=False):
        self.failedOS = failedOS
        prepared = False
        try:
            self.config.updateOrDowngrade = True

            if not self.prepareUpgrade():
                return False

            if self.config.downloadOnly:
                self.cacheUtils.printDownloadOnly("operating system")
                return True

            prepared = True
        finally:
            if not prepared:
                self.cacheUtils.dropBackup()

        try:
            if not self.cacheUtils.removePackages(self.installedPackages, None):
                self.cacheUtils.restoreBackup()
                return False

            if not cacheutils.installTargetPackages(
                app, self.config, self.syncCache, self.installedPackages
            ):
                self.cacheUtils.restoreBackup()
                return False

            self.cacheUtils.dropBackup()
            return True

        except (KeyboardInterrupt, SystemExit):
            self.cacheUtils.restoreBackup()
            raise
        except Exception:
            self.cacheUtils.restoreBackup()
            return False
