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


import difflib
import os
import sys

from collections import namedtuple

from lib import alias, gpgutils, log, makelinks, osutils, package, utils
from lib.cache import localcache
from lib.const import (
    urljoin,
    GSM_INFO_OBSOLETE_PACKAGES_URL,
    PT,
    ANY,
    NO_ARCH,
    CHANGELOG,
    DSC_EXTENSION,
    LICENSES,
    BASE_PUBLIC_URL,
    CRT_EXTENSION,
    DEFAULT_INPUT_TIMEOUT,
    EMAIL_GEMPA,
    FDSNWS_FRONTEND,
    GEMPA,
    GSM,
    LICENSE_TXT_EXTENSION,
    MSG_CONTINUE_QUESTION,
    NEW_EXTENSION,
    NIGHTLY,
    REMOVE,
    UPDATE,
    URL_FILE,
    CMD_ALIAS_ARGUMENTS,
    CMD_CHECK_ARGUMENTS,
    CMD_PRINT_ARGUMENTS,
    CMD_PRINT_NAGIOS_ARGUMENTS,
    blue,
    gray,
    reset,
    EXIT_GSM_UPDATE,
    EXIT_SUCCESS,
    EXIT_FAILURE,
)
from lib.package import Package, isOlderVersion
from lib.utils import checkInput, getInput, temporaryValue

def summaryHeadline(summaries, total):
    updated = sum(1 for summary in summaries if summary.status == UPDATE)
    fresh = len(summaries) - updated

    if not updated:
        return f"{len(summaries)}/{total} packages have been installed:"

    if not fresh:
        return f"{len(summaries)}/{total} packages have been updated:"

    return (
        f"{len(summaries)}/{total} packages have been processed:"
        f" {fresh} installed, {updated} updated:"
    )


Candidate = namedtuple("Candidate", "name remotePkg localPkg selectedPkg")


# the words 'gsm show' knows (all other names are packages)
SHOW_WORDS = (
    "public", "all", "releases", "hold", "history", "updates", "changelog", "own",
)


class AppCommands:

    def handleInstallLicenses(self, packages):
        if packages[0] == LICENSES:
            packages.remove(LICENSES)
            return True, self.installLicenses(packages)

        if LICENSES in packages:
            self.installLicenses(self.gsm.createLicensesPackageList(packages))

        return False, None

    def applyHold(self, packages, holdFunc, abortIfMissing):
        if packages[0] == "files":
            for name in packages[1:]:
                holdFunc(name, True)
            return True

        for name in packages:
            if not self.gsm.localCache.getPackage(name):
                log.logInfo(f"{name} is not installed ... ")
                if abortIfMissing:
                    return False
                continue
            holdFunc(name)

        return True

    @log.trace
    def update(self, command, packages):
        if not utils.requireNoArgs(self.args, command):
            return False

        if not self.config.offline:
            self.gsm.news.getNews(self.gsm.localCache)

        self.config.fromUpdate = True

        self.gsm.updateSyncIndex()

        if self.gsm.syncCache.getIndex():
            ret, info = package.isNewReleaseAvailable(self.config)
            if ret:
                print("")
                print(info)
            if not self.gsm.localCache.isHold(GSM):
                ret, retCode = self.gsm.updateCheck()
                if ret:
                    if not self.config.offline:
                        try:
                            pkg = self.gsm.localCache.getPackage(GSM)
                            os.remove(self.config.packagePath(pkg))
                        except Exception:
                            pass
                    if not self.selfUpdate():
                        return False

                if retCode == EXIT_GSM_UPDATE:
                    sys.exit(EXIT_GSM_UPDATE)
            else:
                package.updateInfoGsm(self.gsm.localCache, self.gsm.syncCache)

            ret, updatePackages = self.gsm.getPackagesUpdateInfo()
            if ret:
                if not self.config.assumeYes:
                    if checkInput(
                        "\nDo you want to install packages which"
                        " can be updated?",
                        "n",
                        "yN",
                    ):
                        return False

                    self.installRequested = True
                else:
                    print("Skip GSM update")

                if updatePackages:
                    return self.install(updatePackages, False)

                return self.install(packages, False)
            return True

        return False

    def confirmLicenses(self, packages):
        failed = self.gsm.licenseFailures(packages)
        if not failed:
            return packages

        print()
        log.logWarning(
            f"The {LICENSES} of the following packages are expired or are missing:"
            f" {', '.join(failed)}"
        )
        q = (
            f"Do you want to (s)kip those packages, (i)gnore the missing {LICENSES} or"
            " (c)ancel the installation entirely?"
        )
        answer = utils.getInput(q, "s", "sic")
        if answer == "s":
            packages = [name for name in packages if name not in failed]
        elif answer == "c":
            sys.exit(EXIT_SUCCESS)
        print("")

        if not packages:
            print("No package with a valid licence file remain to be installed.")
            return None

        return packages

    @log.trace
    def confirmObsoletePackages(self, packages):
        obsolete, remaining = self.gsm.obsoletePackages(packages)
        if not obsolete:
            return remaining

        print(
            "The following package(s) are no longer available:\n"
            f" {', '.join(obsolete)}"
        )

        for name in obsolete:
            response = utils.getDataFromUrl(
                urljoin(GSM_INFO_OBSOLETE_PACKAGES_URL, name),
                self.config,
                True,
            )
            if response:
                print(response)

        if checkInput(f"\n{MSG_CONTINUE_QUESTION}", "n", "yn"):
            return None

        return remaining

    @log.trace
    def narrowInstallCandidates(self, packages, excludePackages):
        packages = self.gsm.filterPackages(excludePackages, packages)[:]
        if not packages:
            print("\nNo matching packages found.")
            return None

        packages.sort()

        packages = self.confirmObsoletePackages(packages)
        if packages is None:
            return None

        if not packages:
            print("\nAll selected packages became obsolete.")
            return None

        packages = self.gsm.removeHoldPackages(packages)[:]
        if not packages:
            print("\nAll selected packages are marked as hold.")
            return None

        if not self.gsm.syncCache.contains(packages):
            return None

        return packages

    def showHistory(self, pkgName):
        text = package.packageHistory(self.config.logPath(), pkgName)
        if not text:
            print(f"No history found for '{pkgName}'")
            return True

        utils.displayTextSideBySide(text)
        return True

    def print(self, command):
        action = utils.requireOneSubArg(
            self.args, command, CMD_PRINT_ARGUMENTS, oneArg=False
        )
        if action is None:
            return False
        if action == "nagios":
            subaction = utils.requireOneSubArg(
                self.args[1:], f"{command} nagios", CMD_PRINT_NAGIOS_ARGUMENTS
            )
            if subaction is None:
                return False
            if subaction == "crontab":
                self.nagios.printCrontab()
            elif subaction == "output":
                sys.exit(self.nagios.printNagios())
            elif subaction == "licenses":
                sys.exit(
                    self.nagios.printLicenses(self.gsm.localCache.index.values())
                )
        elif action == "env":
            self.config.printShellCompletionHint()
        return True

    def show(self, command, packages):
        if not packages:
            return self.gsm.syncCache.infoPackages(
                self.config.baseURL, packages if self.args else None, True
            )

        action = packages[0]

        if action == "updates":
            return self.gsm.getPackagesUpdateInfo()
        if action == "releases":
            if len(packages) >= 2:
                return package.showReleasesFull(self.config, packages[1])
            return package.showReleases(self.config)
        if action == "hold":
            return self.gsm.localCache.showHold()
        if action == "public":
            packages.remove("public")
            return self.gsm.syncCache.infoPackages(
                BASE_PUBLIC_URL, packages if self.args else None, True,
                filterNames=self.gsm.syncCache.publicPackages,
            )
        if action == "changelog":
            if (len(packages) > 2 or (len(packages) == 1 and packages[0])):
                print(f"Command '{GSM} {command} {action}' requires only one package name")
                return True
            if len(packages) == 2 and packages[0] == "changelog":
                packages.remove("changelog")
                if not self.gsm.syncCache.contains(packages):
                    return False
                return self.gsm.showChangeLog(packages)
        if action == "own":
            if self.config.offline:
                print("The option is not available in offline mode...")
                return True
            packages.remove("own")
            ret, ownPackages = utils.showOwnPackages(
                self.config,
                self.gsm.syncCache.publicPackages,
                self.gsm.syncCache.extendPackages,
            )
            if ret:
                return self.gsm.syncCache.infoPackages(
                    self.config.baseURL, packages if self.args else None, True,
                    filterNames=ownPackages,
                )
        if action == "all" and len(packages) >= 2:
            packages.remove("all")
            return self.gsm.syncCache.infoPackages(
                self.config.baseURL, packages, True
            )

        result = self.gsm.syncCache.infoPackages(
            "", packages if self.args else None, True
        )
        # a name that is no package, but looks like a word of 'show': 'show update'
        if action not in self.gsm.syncCache.index:
            similar = difflib.get_close_matches(action, SHOW_WORDS, n=1, cutoff=0.8)
            if similar:
                print(f"\nDid you mean {self.config.gsmCall} show {similar[0]}?")
        return result

    def info(self, packages):
        if not packages:
            return self.gsm.localCache.infoPackages(packages if self.args else None)

        action = packages[0]

        if action == "short":
            return self.gsm.localCache.infoPackagesShort()

        if action == "deps":
            self.gsm.getDependencyInfo(packages[1:])
            return True

        return self.gsm.localCache.infoPackages(packages if self.args else None)

    @log.trace
    def reinstall(self, packages):
        self.fromReinstall = True
        handled, result = self.handleInstallLicenses(packages)
        if handled:
            return result

        installedPackages = []
        staticPackages = []
        packages = self.gsm.filterPackages(self.config.excludePackages, packages)

        localPackages = {}

        for name in packages:
            pkg = self.gsm.localCache.getPackage(name)
            if not pkg:
                log.logWarning(f"{name} is not installed ... ")
                continue

            if pkg.type == PT.DATA:
                staticPackages.append(name)
                continue

            installedPackages.append(pkg.fullName())
            localPackages[pkg.fullName()] = pkg

        if staticPackages:
            log.logInfo(
                f"{', '.join(staticPackages)} cannot be reinstalled. This operation is not"
                f" supported for {PT.DATA} packages."
            )
            log.logInfo(
                f"Please use {self.config.gsmCall} remove"\
                    f" [module] and {self.config.gsmCall} install [module].\n"
            )

        return self.install(installedPackages, True, localPackages)

    def upgradePrepare(self, command, packages):
        target = self.config.upgradeTarget

        if command == "do-release-upgrade" and self.config.release == NIGHTLY:
            print(f"You're already on release: {NIGHTLY}...")
            return True

        if command == "do-release-downgrade" and not package.getLatestStableReleases(self.config, True):
            print(f"You're already using the oldest available release "\
                  f"({self.config.release})...")
            return True

        if target and command != "switch-os":
            if self.config.release == target:
                print(f"You're already on release: {target}...")
                return True
            if command == "do-release-upgrade" and isOlderVersion(target, self.config.release):
                print(f"Please use {GSM} do-release-downgrade to downgrade a release")
                return True
            if command == "do-release-downgrade" and isOlderVersion(
                    self.config.release, target):
                print(f"Please use {GSM} do-release-upgrade to upgrade a release")
                return True

            if not package.isUpgradeReleaseAvailable(self.config, command):
                print(f"Release: {target} not found.")
                sys.exit(EXIT_FAILURE)

        if not self.runUpdateBeforeUpgradeOrDowngrade(packages):
            sys.exit(EXIT_FAILURE)

        return False

    def check(self, command, packages):
        action = utils.requireOneSubArg(self.args, command, CMD_CHECK_ARGUMENTS, False)
        if action is None:
            return False

        if action == "signature":
            packages = packages[1:]
            if not packages:
                print(f"Command '{GSM} {command} {action}' requires a package name")
                return False

            self.config.gpgVerify = True
            for name in packages:
                self.gsm.syncCache.gpgCheck(name)

        return True

    def alias(self, command):
        action = utils.requireOneSubArg(self.args, command, CMD_ALIAS_ARGUMENTS, False)
        if action is None:
            return False

        if action == "create":
            if utils.requireOneArg(self.args, f"{command} {action}"):
                aliasName = self.args[1]
                if alias.checkAliasName(aliasName):
                    self.gsm.createAlias(aliasName)
                else:
                    print(f'Error: Invalid alias name "{aliasName}"')
                    print("Please use a valid alias name consisting only of uppercase " \
                          "and lowercase letters, and optionally include numbers. " \
                          'Special characters such as "?" are not allowed.')

        if action == "remove":
            if utils.requireOneArg(self.args, f"{command} {action}"):
                alias.removeAlias(self.config, self.args[1])

        return True

    def matchesTarget(self, pkg):
        if pkg.type in (PT.DATA, PT.CONFIG):
            return True

        if pkg.arch == NO_ARCH and pkg.os == ANY and pkg.osVersion in ("", ANY):
            return True

        return (
            pkg.os == self.config.os
            and pkg.osVersion == self.config.os_version
            and pkg.release == self.config.release
            and pkg.arch == self.config.arch
        )

    @log.trace
    def localInstall(self, packagesFiles):
        packages = []
        localPackages = {}

        for localpkg in packagesFiles:
            descFile = localpkg + DSC_EXTENSION

            missing = [f for f in (descFile, localpkg) if not os.path.isfile(f)]
            if missing:
                for f in missing:
                    log.logInfo(f"The file {f} does not exist.")
                continue

            pkg = Package.fromFile(os.path.abspath(descFile), ".")
            pkg.localDir = os.path.dirname(os.path.abspath(localpkg))

            if not self.matchesTarget(pkg):
                log.logSkip(
                    f"The {localpkg} has been built"
                    " for a different target system."
                )
                continue

            localPackages[pkg.name] = [pkg]
            packages.append(pkg.name)

        if not packages:
            return True

        self.gsm.syncCache.mergeIndex(localPackages)

        return self.install(packages, self.config.forceDownload)

    def selfUpdate(self) -> bool:
        with temporaryValue(self.config, "assumeYes", True):
            if not self.install([GSM], False):
                return False

        print(
            f"\nPlease read the {CHANGELOG} in case there are still steps to"
            " be taken to complete the update!\n"
        )
        return True

    @log.trace
    def installLicenses(self, packages):
        ret = True
        for name in packages:
            pkg = self.gsm.localCache.getPackage(name)
            if not pkg and self.config.forceDownload:
                pkgs = self.gsm.getSyncPackage(name)
                if not pkgs:
                    log.logError(
                        f"Unable to locate package {blue}{name}{reset} for"
                        f" {self.config.os}/{self.config.os_version} ({self.config.arch}) (Release:"
                        f" {self.config.release})"
                    )
                    continue

                pkg = self.gsm.getSyncPackage(name)
            if not pkg:
                pkgs = self.gsm.getSyncPackage(name)
                if not pkgs:
                    log.logError(
                        f"Unable to locate package {blue}{name}{reset} for"
                        f" {self.config.os}/{self.config.os_version} ({self.config.arch}) (Release:"
                        f" {self.config.release})"
                    )
                    continue
                pkg = self.gsm.getSyncPackage(name)
                if pkg.license == "None":
                    log.logInfo(f"{name} does not need a license ...")
                else:
                    log.logInfo(
                        f"{name} is not installed ... (You can use the parameter "
                        "'-f' to install the license anyway)"
                    )
                continue

            if pkg.license == "None":
                log.logInfo(f"{name} does not need a license ...")
                continue

            if self.config.downloadOnly:
                if not package.downloadLicense(pkg, self.config):
                    ret = False
            elif not package.downloadLicense(
                pkg, self.config
            ) or not pkg.installLicense(self.config):
                ret = False

        return ret

    @log.trace
    def runUpdateBeforeUpgradeOrDowngrade(self, packages):
        if self.gsm.localCache.getIndex():
            packages = list(self.gsm.localCache.getIndex().keys())
            if GSM in packages:
                packages.remove(GSM)
            if not packages:
                return True

            self.gsm.updateSyncIndex()
            if self.gsm.syncCache.getIndex():
                ret, _ = self.gsm.updateCheck()
                if ret and not self.selfUpdate():
                    return False

                ret, updatePackages = self.gsm.getPackagesUpdateInfo(True)
                if ret:
                    if not self.config.assumeYes:
                        if checkInput(
                            "\nDo you want to install packages which can be updated? "
                            "This is necessary before we can continue?",
                            "y",
                            "Yn",
                        ):
                            self.installRequested = True
                        else:
                            sys.exit(EXIT_SUCCESS)
                    if updatePackages:
                        return self.install(updatePackages, False)
        return True


    @log.trace
    def resolveCandidates(self, packages, localPackages=None):
        localPackages = localPackages or {}
        preferLocal = self.config.offline and self.fromReinstall
        candidates = {}

        for name in packages:
            remotePkg = self.gsm.getSyncPackage(name)
            localPkg = localPackages.get(name) or self.gsm.localCache.getPackage(name)
            candidates[name] = Candidate(
                name,
                remotePkg,
                localPkg,
                (localPkg or remotePkg) if preferLocal else remotePkg,
            )

        return candidates

    def dropUnsupportedGsm(self, packages):
        """gsm is not installed on an operating system it does not support: asked for alone that
        is an error (None), in a longer list it is left out."""
        reason = osutils.unsupportedSystem() if GSM in packages else None
        if not reason:
            return packages

        if packages == [GSM]:
            log.logError(f"{GSM} cannot be installed on this system: {reason}")
            return None

        print(f"\n{GSM} is left out: {reason}")
        return [name for name in packages if name != GSM]

    @log.trace
    def install(self, packages, force, localPackages=None):
        packages = self.narrowInstallCandidates(packages, self.config.excludePackages)
        if packages is None:
            return False

        packages = self.dropUnsupportedGsm(packages)
        if packages is None:
            return False

        if not (len(packages) == 1 and packages[0] == GSM):
            ret, retCode = self.gsm.updateCheck()

            if ret and not self.selfUpdate():
                return False

            if retCode == EXIT_GSM_UPDATE:
                sys.exit(EXIT_GSM_UPDATE)

        if not self.config.assumeYes:
            packages = self.gsm.localCache.checkOptionalInstall(packages)

        packages = self.gsm.localCache.addDependencies(packages)

        if not self.gsm.checkDataInstallPaths(packages):
            return False

        remote = utils.remoteMembers(self.gsm.syncCache, packages)

        if (
            remote
            and not self.config.offline
            and not self.config.baseURL.startswith(URL_FILE)
        ):
            if self.gsm.protectedPackages(remote):
                ret, retCode = utils.checkUrlAccess(self.config)

                if not ret:
                    if retCode == 401:
                        log.logError("Could not login: Invalid login credentials.")
                    elif retCode == 404:
                        log.logError("Could not login: Invalid repository URL.")
                    sys.exit(EXIT_FAILURE)

            failed = utils.checkUrlAccessProgress(self.config, self.gsm.syncCache, packages)

            if failed:
                print(
                    "\nThe following packages are not activated in your repository:"
                    f" {', '.join(failed)}"
                )
                print(f"Please get in touch with {EMAIL_GEMPA}")
                q = "Do you want to (s)kip those packages, (c)ancel the installation entirely?"
                answer = utils.getInput(q, "c", "sc", DEFAULT_INPUT_TIMEOUT)
                if answer == "s":
                    packages = [
                        package
                        for package in packages
                        if package not in failed
                    ]
                elif answer == "c":
                    sys.exit(EXIT_SUCCESS)
                print("")

                if not packages:
                    print("No package remain to be installed.")
                    return False

        packages = self.confirmLicenses(packages)
        if packages is None:
            return False

        candidates = self.resolveCandidates(packages, localPackages)

        installed = []

        skipInstalledCheck = force or self.config.fromUpdate

        if not skipInstalledCheck:
            downgrade = []
            for name in packages:
                pkg = candidates[name].selectedPkg
                show = True

                if self.gsm.localCache.isInstalled(pkg, show):
                    installed.append(name)
                    continue

                local = candidates[name].localPkg
                if pkg and not local:
                    local = self.gsm.localCache.getPackage(pkg.name)
                if (
                    pkg
                    and local
                    and isOlderVersion(pkg.version, local.version)
                    and not self.config.forceDownload  # -f: the older version anyway
                ):
                    log.logSkip(
                        f"The package {pkg.name} is already installed"
                        f" in a newer version {local.version}. Use '-f' to"
                        " install the older version anyway or remove the"
                        " installed version and restart the installation."
                    )
                    downgrade.append(name)

            packages = [
                package for package in packages if package not in downgrade
            ]

            if downgrade and not packages:
                return True

        packages = [
            package for package in packages if package not in installed
        ]

        if not packages:
            print(
                "\nAll packages are already up to date. Use 'reinstall' to force"
                " re-installation."
            )
            return True

        firstInstall = [
            name for name in packages if name not in self.gsm.localCache.getIndex()
        ]

        if installed and not self.config.fromUpdate:
            print(
                "\nThe following packages are installed in their latest version:"
                f" {', '.join(installed)}\nUse 'reinstall' to force re-installation.\n"
            )

        runCheckSum = []
        fileNotExist = []
        fileNotExistCrt = []
        fileNotExistLicenseTxt = []
        runCheckSumFailedDownloadAgain = []

        for name in packages:
            candidate = candidates[name]
            pkgSync = candidate.selectedPkg
            pkg = candidate.localPkg

            if not pkgSync:
                continue

            if (
                not pkg
                or pkgSync.localDir
                or isOlderVersion(pkg.version, pkgSync.version)
            ):
                pkg = pkgSync
            if (pkg and pkg.checksum == pkgSync.checksum) or (
                pkg and not pkg.checksum == pkgSync.checksum
            ):

                fileName = self.config.packagePath(pkg)
                if (
                    not self.config.updateOrDowngrade and not force
                ) or self.config.offline:
                    if os.path.exists(fileName):
                        if not utils.hashfile(fileName, pkgSync.checksum, pkg):

                            if os.path.isfile(fileName):
                                runCheckSumFailedDownloadAgain.append(name)
                                if not self.config.offline:
                                    os.remove(fileName)
                        else:
                            if self.config.offline and self.fromReinstall:
                                runCheckSum.append(pkg.fullName())
                            else:
                                runCheckSum.append(pkg.name)
                    else:
                        fileNotExist.append(pkg)

                if pkg.license == GEMPA:
                    if pkg.licenseFile:
                        licenseFile = pkg.licenseFile
                    else:
                        licenseFile = pkg.name

                    fileNameCrt = os.path.join(
                        self.config.downloadLicenseDir,
                        licenseFile + CRT_EXTENSION,
                    )
                    if not os.path.exists(fileNameCrt):
                        fileNotExistCrt.append(fileNameCrt)

                    fileNameLicenseTxt = os.path.join(
                        self.config.downloadLicenseDir,
                        licenseFile + LICENSE_TXT_EXTENSION,
                    )
                    if not os.path.exists(fileNameLicenseTxt):
                        fileNotExistLicenseTxt.append(fileNameLicenseTxt)

        if self.config.forceDownload and self.config.offline:
            for name in packages:
                if name in runCheckSumFailedDownloadAgain:
                    runCheckSumFailedDownloadAgain.remove(name)
                if name not in runCheckSum:
                    runCheckSum.append(name)

        if self.config.downloadOnly or len(self.args) == 0:
            if not self.installRequested and not self.config.assumeYes:
                downloadArray = []
                for element in packages:
                    if element not in runCheckSum:
                        downloadArray.append(element)
                if downloadArray:
                    if self.config.downloadOnly:
                        onlyText = "only"
                    else:
                        onlyText = ""
                    print(
                        "The following packages are selected for"
                        f" download {onlyText}: {', '.join(downloadArray)}\n"
                    )
                else:
                    if self.config.downloadOnly:
                        if not self.config.offline:
                            runCheckSumFailedDownloadAgain = []
                            for name in packages:
                                checkPkg = candidates[name].selectedPkg
                                url = package.getDownloadURL(
                                    checkPkg, self.config
                                )
                                fileName = self.config.packagePath(checkPkg)
                                ret, _ = utils.isDirty(
                                    fileName, url, self.config
                                )
                                if ret:
                                    runCheckSumFailedDownloadAgain.append(name)

                        if not runCheckSumFailedDownloadAgain:
                            print("\nAll packages are already downloaded.")
                        else:
                            print()
                            log.logWarning(
                                "The checksum check for the following packages has failed:"
                                f" {', '.join(runCheckSumFailedDownloadAgain)}."
                                " The download is forced for these packages."
                            )
                            print()

        if self.config.offline:
            downloaded = packages
            failed = [name for name in downloaded if name not in runCheckSum]

            if fileNotExist:
                for pkg in fileNotExist:
                    log.logError(
                        f"The {pkg.fileName} file does not exist in the"
                        f" {self.config.downloadDir} directory."
                    )
                    if pkg.name in failed:
                        failed.remove(pkg.name)

            if failed:
                print()
                log.logError(
                    "Checksum validation for the following packages failed:"
                    f" {', '.join(failed)}"
                )

            if fileNotExistCrt:
                for name in fileNotExistCrt:
                    log.logError(
                        f"The {name} file does not exist in the"
                        f" {self.config.downloadLicenseDir} directory."
                    )
            if fileNotExistLicenseTxt:
                for name in fileNotExistLicenseTxt:
                    log.logError(
                        f"The {name} file does not exist in the"
                        f" {self.config.downloadLicenseDir} directory."
                    )
            if (
                fileNotExist
                or failed
                or fileNotExistCrt
                or fileNotExistLicenseTxt
            ):
                return True

        else:
            downloaded = self.gsm.syncCache.downloadPackages(packages)
            failed = [name for name in packages if name not in downloaded]

            if failed:
                packages = [name for name in packages if name not in failed]

                if not packages:
                    print()
                    log.logError("The download of all packages failed.")
                    print(f"\nTry to run {GSM} update to refresh the package index.")
                    return False

                print()
                log.logError(
                    f"The download of the following packages failed: {', '.join(failed)}"
                )
                if not checkInput(f"{MSG_CONTINUE_QUESTION}", "y", "yn"):
                    return False

        failed = []
        for name in downloaded:
            if name not in runCheckSum and not self.gsm.syncCache.checksumCheck(name):
                failed.append(name)

        if failed:
            print()
            log.logError(
                "Checksum validation for the following packages failed:"
                f" {', '.join(failed)}"
            )
            print(f"\nTry to run {GSM} update to refresh the package index.")

            if self.config.downloadOnly:
                return False

            q = (
                "\nDo you want to (s)kip those packages, (i)gnore the checksum errors or"
                " (c)ancel the installation entirely?"
            )
            answer = getInput(q, "s", "sic")
            if answer == "s":
                packages = [
                    package for package in packages if package not in failed
                ]
            elif answer == "c":
                sys.exit(EXIT_SUCCESS)

            if not packages:
                print(
                    "No package with a valid checksum remain to be installed."
                )
                return False

            print("")

        if self.config.downloadOnly:
            return not (self.config.gpgVerify and self.checkSignaturesDownloadOnly(packages))

        ret, showChangeLog = self.gsm.showChangeLog(packages, True)

        if ret and showChangeLog and not self.config.assumeYes:
            if not checkInput(
                "NOTE: Some packages may require additional steps after the update. "
                "Please read the instructions carefully before proceeding."
                f" {MSG_CONTINUE_QUESTION}",
                "Y",
                "yn",
            ):
                return False
        if self.config.gpgVerify and not self.config.signaturesChecked:
            ret = gpgutils.checkGPGProgress(
                self.config,
                self.gsm.syncCache,
                self.gsm.syncCache.gpgutils,
                packages)
            if ret:
                if not checkInput(f"{MSG_CONTINUE_QUESTION}", "Y", "yn"):
                    return False
        if FDSNWS_FRONTEND in packages:
            packages.remove(FDSNWS_FRONTEND)
            pkgTemp = candidates[FDSNWS_FRONTEND].remotePkg
            log.logInfo(
                f"The package {pkgTemp.name} {pkgTemp.version} is only available for download."
                f" The file is located here: {self.config.downloadDir}/{pkgTemp.fileName}"
            )
            if not packages:
                return True
        if not showChangeLog:
            if not self.config.assumeYes:
                if not self.installRequested:
                    print(
                        f"{log.getLogPrefix('INSTALL')}{blue}{', '.join(packages)}{reset}\n"
                    )
                    if any(
                        candidates[name].selectedPkg
                        and candidates[name].selectedPkg.isGreensfunctions()
                        for name in packages
                    ):
                        print("The installation of greensfunctions may take some time. " \
                              "Please do not cancel prematurely.")
                    if not checkInput(f"{MSG_CONTINUE_QUESTION}", "Y", "yn"):
                        return False
        return self.performInstall(packages, firstInstall, candidates)

    def checkSignaturesDownloadOnly(self, packages):
        """Download only: nothing is installed, so nobody is asked about a signature that is
        missing or does not fit; the command ends with an error. The files stay downloaded.
        Returns the packages with a problem."""
        failed = gpgutils.checkGPGProgress(
            self.config, self.gsm.syncCache, self.gsm.syncCache.gpgutils, packages
        )
        if failed:
            log.logError("The signature check failed, the downloaded packages were not installed.")
        return failed

    @log.trace
    def performInstall(self, packages, firstInstall, candidates):
        installed = []
        success = True

        for name in packages:
            pkg = candidates[name].selectedPkg
            if not pkg:
                log.logError(f"Unable to locate package {blue}{name}{reset}")
                success = False
                continue

            if self.config.makeBackup:
                package.backupPackages(
                    self.config, pkg, self.gsm.syncCache.backupDenyPackages
                )

            ret, summary = self.gsm.localCache.installPackage(pkg)
            if ret == 0:
                installed.append(summary)
            else:
                success = False

        print(f"\n{summaryHeadline(installed, len(packages))}\n")

        for summary in installed:
            pkg = self.gsm.localCache.getPackage(summary.name)
            licenses = (
                f" (+{summary.licenseCount} License files)"
                if summary.licenseCount
                else ""
            )
            print(
                f"{blue}{pkg.name} ({pkg.version}){reset} to {summary.path}:"
                f" {gray}{summary.fileCount} file(s){licenses},"
                f" {utils.humanbytes(pkg.installSize)}{reset} "
            )
            if summary.holdFiles:
                print(
                    "\nThe following files have not been updated as"
                    f" they are set on hold by configuration ({pkg.name}):"
                )
                for name in summary.holdFiles:
                    print(f"  {name}")
                print("\n")
            if summary.keptFiles:
                print(
                    "\nThe following configuration files have been modified and"
                    f" were kept ({pkg.name}). The shipped version is available"
                    f" as *{NEW_EXTENSION}:"
                )
                for name in summary.keptFiles:
                    print(f"  {name}")
                print("\n")

        if firstInstall:
            print("\n")
            self.gsm.getDependencyInfo(firstInstall)

        if os.path.isdir(self.config.libDir):
            fileList = makelinks.getFilesList(self.config.libDir)
            linkList = makelinks.getLinkList(fileList)
            ret = makelinks.createSymLinks(linkList, self.config.libDir)
            return success and ret

        return success

    @log.trace
    def remove(self, packages):
        packages = self.gsm.filterPackages(self.config.excludePackages, packages)
        packages = self.gsm.removeHoldPackages(packages)
        if not packages:
            print("\nAll selected packages are marked as hold.")
            return False

        packages.sort()
        failed = []
        for name in packages:
            pkg = self.gsm.localCache.getPackage(name)
            if not pkg:
                log.logInfo(f"{name} is not installed ... ")
                failed.append(name)

        packages = [package for package in packages if package not in failed]

        if not packages:
            print("")
            print("Nothing todo ...")
            return True

        if not self.config.assumeYes:
            packages = self.gsm.localCache.checkOptionalRemove(packages)

        packages = self.gsm.localCache.checkDependsRemove(packages)

        if not self.config.assumeYes:
            print(f"{log.getLogPrefix('REMOVE')}{blue}{', '.join(packages)}{reset}\n")
            if checkInput(f"{MSG_CONTINUE_QUESTION}", "n", "yn"):
                return False

        ret = True
        removedPackages = []

        members = utils.sorting(packages)
        count = 0
        progress = utils.progressBar(members, REMOVE)

        for member in progress:
            pkg = self.gsm.localCache.getPackage(member)
            pkgName, _ = utils.getPackageName(pkg)
            utils.setDesc(progress, REMOVE, pkgName)
            count = count + 1

            status, summary = self.gsm.localCache.removePackage(member)
            if status == localcache.PKG_SUCCESS:
                removedPackages.append(summary)
            else:
                ret = False

        log.logResult(
            progress,
            REMOVE,
            n=len(removedPackages),
            total=len(members),
            ok=ret,
        )
        if removedPackages:
            self.gsm.localCache.removeEmptyInstallPath()
            print(
                f"\n{len(removedPackages)}/{len(packages)} packages have been"
                " removed:\n"
            )
        else:
            print(f"\nNone of {len(packages)} package(s) has been removed.")

        for summary in removedPackages:
            print(
                f"{blue}{summary.name} ({summary.version}){reset} from {summary.path}:"
                f" {gray}{summary.fileCount} file(s),"
                f" {utils.humanbytes(summary.installSize)}{reset} "
            )
            if summary.holdFiles:
                print(
                    "\nThe following files have not been removed as they are set"
                    f" on hold by configuration ({summary.name}):"
                )
                for name in summary.holdFiles:
                    print(f"  {name}")
                print("\n")
            if summary.keptFiles:
                print(
                    "\nThe following configuration files have not been removed"
                    f" as they have been modified or their checksum is unknown ({summary.name}):"
                )
                for name in summary.keptFiles:
                    print(f"  {name}")
                print("\n")
        fileList = makelinks.getFilesList(self.config.libDir)
        linkList = makelinks.getLinkList(fileList)

        return ret and makelinks.createSymLinks(linkList, self.config.libDir)
