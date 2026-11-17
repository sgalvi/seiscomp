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

from lib.const import (
    blue,
    reset,
)

class InstallDeps:
    def __init__(self, config, localCache, syncCache):
        self.config = config
        self.localCache = localCache
        self.syncCache = syncCache
        self.scriptDir = os.path.join(
            self.config.installPath,
            "share",
            "deps",
            self.config.os,
            self.config.os_version,
        )

    def getDependencyInfo(self, packages=None):
        if not packages:
            packages = list(self.localCache.getIndex().keys())

        deps = "Dependency name"
        pkgName = "Package name"
        scriptName = "Install script"

        failed = []
        allDeps = {}

        for name in packages:
            pkg = self.localCache.getPackage(name)
            if pkg and pkg.osInstallScripts:
                optionalPkgs = pkg.osInstallScripts.split(" ")
                allDeps[pkg.name] = optionalPkgs
            else:
                try:
                    pkgSync = self.syncCache.getPackage(pkg.fullName())
                except Exception:
                    pkgSync = None
                if pkgSync and pkgSync.osInstallScripts:
                    optionalPkgs = pkgSync.osInstallScripts.split(" ")
                    allDeps[pkg.name] = optionalPkgs
                else:
                    failed.append(name)

        if allDeps:
            try:
                maxlenPackageName = max(len(max(packages, key=len)), len(pkgName))
                maxlenScript = len(
                    max(
                        (string for value in allDeps.values() for string in value),
                        key=len,
                    )
                )
                maxlenPackage = maxlenScript - 11 if maxlenScript > 11 else len(deps)

                maxlenPackage = max(maxlenPackage, len(deps))
                maxlenPackageName = max(maxlenPackageName, len(pkgName))
                maxlenScript = max(maxlenScript, len(scriptName))

            except ValueError:
                maxlenPackageName = len(deps)
                maxlenScript = len(scriptName)
                maxlenPackage = len(pkgName)

            allDeps = {key: allDeps[key] for key in sorted(allDeps)}

            print(
                f"{deps: <{maxlenPackage:}}  {pkgName: <{maxlenPackageName}}  {scriptName}"
            )

            print(
                f"{''.ljust(maxlenPackage, '-')}  {''.ljust(maxlenPackageName, '-')}"
                f"  {''.ljust(maxlenScript, '-')}"
            )
            for pkg, value in allDeps.items():
                for script in value:
                    depName = (
                        script.split("/")[-1].split(".")[0].replace("install-", "")
                    )
                    print(
                        f"{depName: <{maxlenPackage:}}  {pkg: <{maxlenPackageName:}}  {script}"
                    )
                print("\n")

        if failed:
            print(
                f"No further dependencies need to be installed for: {blue}{', '.join(sorted(failed))}{reset}"
            )

        if allDeps:
            print(f"\nThe scripts are located under: {self.scriptDir}")
