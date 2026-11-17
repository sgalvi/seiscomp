#!/usr/bin/env python3

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
import platform

import getopt
import difflib

gsmBaseDir, _ = os.path.split(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(gsmBaseDir)

from lib.const import EXIT_SUCCESS, EXIT_FAILURE  # noqa: E402

if sys.version_info < (3, 9):
    print(
        f"gsm requires at least Python 3.9. You have {str(platform.python_version())}."
    )
    sys.exit(EXIT_FAILURE)

osutils = None
try:
    from lib import osutils

    from lib import utils, log, nagios

    from lib import config, helpcli

    from lib import osupgrade, releasedowngrade, releaseupgrade

    from lib.gsm import Gsm

    from lib.cache import localcache

    from lib.app import AppCommands

    from lib.const import (
        BASE_PUBLIC_URL,
        DEFAULT_DATE_FORMAT,
        SEISCOMP,
        LICENSES,
        GSM,
        CMD_CLEAN_ARGUMENTS,
        GSM_CONFIG_FILE,
        ALIASES_DIR,
        GSM_CONF,
        ETC_DIR,
        EXIT_INTERRUPT,
    )

except ImportError as e:
    print(f"gsm: {e}", file=sys.stderr)
    sys.exit(EXIT_FAILURE)


def splitPackageList(value):
    return [name.strip() for name in value.split(",") if name.strip()]


class App(AppCommands):
    @staticmethod
    def resolveInvocation(argv):
        gsmAlias = GSM
        binary = None
        configFile = None

        args = argv[1:]
        index = 0
        while index < len(args):
            arg = args[index]
            if arg in ("-c", "--config", "-C"):
                value = args[index + 1] if index + 1 < len(args) else None
                index += 2
            elif arg.startswith("--config="):
                arg, value = "--config", arg[len("--config=") :]
                index += 1
            else:
                index += 1
                continue

            if value is None:
                continue

            if arg == "-C":
                binary = value
            else:
                configFile = value

        if binary:
            gsmAlias = os.path.basename(binary)

        return gsmAlias, configFile

    def __init__(self, argc, argv):
        self.argv = argv
        self.argc = argc

        if os.path.exists(GSM_CONFIG_FILE):
            gsmConfFile = GSM_CONFIG_FILE
        else:
            if  os.path.exists(GSM_CONF):
                gsmConfFile = GSM_CONF
            else:
                if not os.path.exists(ETC_DIR):
                    os.makedirs(ETC_DIR)
                gsmConfFile = GSM_CONFIG_FILE

        gsmAlias, configFile = self.resolveInvocation(argv)

        if configFile:
            gsmConfFile = configFile
            if not os.path.exists(gsmConfFile):
                print(f"Configuration file '{gsmConfFile}' not found.")
                sys.exit(EXIT_FAILURE)
        elif gsmAlias.startswith("gsm-"):
            gsmConfFile = os.path.join(ALIASES_DIR, gsmAlias[4:], GSM_CONFIG_FILE)

        baseDir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.config = config.Config(baseDir, gsmConfFile)

        self.config.gsmBinary = gsmAlias

        self.command = None
        self.args = None
        self.showHelp = False
        self.showVersion = False
        self.helpTopic = []
        self.installRequested = False
        self.helpcli = helpcli.HelpFunction()
        self.news = None
        self.fromReinstall = False
        self.gsm = None
        self.nagios = nagios.Nagios(self.config)

    def handleCommand(self, command):
        if command == "setup":
            return self.config.setup()

        if command == "print" and self.args[:1] == ["env"]:
            if len(self.args) != 1:
                print(f"Command '{self.config.gsmCall} print env' takes no further arguments")
                return False
            self.config.printShellCompletionHint()
            return True

        if command == "show" and self.args[:1] == ["history"]:
            if len(self.args) != 2:
                print(
                    f"Command '{self.config.gsmCall} {command} history' requires"
                    " exactly one package name"
                )
                return True

            return self.showHistory(self.args[1])

        if not self.checkCredentials(command):
            return False

        handled, result = self.checkPlatformSupport(command)
        if handled:
            return result

        if not self.args and command in ("remove", "hold", "unhold"):
            print(f"Command '{self.config.gsmCall} {command}' requires a package name")
            return False

        packages = self.collectPackages()

        if not packages and command in ("install", "remove", "hold", "unhold"):
            print(f"Command '{self.config.gsmCall} {command}' requires a package name")
            return False

        if command == "sync":
            if not utils.requireNoArgs(self.args, command):
                return False

            if self.config.offline:
                print("The command is not available in offline mode...")
                return False

            self.gsm.news.getNews(self.gsm.localCache)
            self.config.fromUpdate = True
            return self.gsm.updateSyncIndex()

        if command == "update":
            return self.update(command, packages)

        if command == "search":
            if not self.args:
                print(f"Command '{self.config.gsmCall} {command}' requires a search string")
                return False

            return self.gsm.syncCache.search(packages)

        if command == "clean":
            action = utils.requireOneSubArg(self.args, command, CMD_CLEAN_ARGUMENTS)
            if action is None:
                return False
            return osutils.clean(action, self.config)

        if command == "print":
            return self.print(command)

        if command == "show":
            return self.show(command, packages)

        if command == "info":
            return self.info(packages)

        if command == "localinstall":
            return self.localInstall(packages)

        if command == "install":
            handled, result = self.handleInstallLicenses(packages)
            if handled:
                return result

            if self.gsm.syncCache.getIndex():
                ret, _ = self.gsm.updateCheck()
                if ret and not self.selfUpdate():
                    return False

            return self.install(packages, False)

        if command == "reinstall":
            return self.reinstall(packages)

        if command == "remove":
            if any(pkg in [GSM] for pkg in packages):
                log.logInfo(f"The {GSM} package cannot be removed ... ")
                packages.remove(GSM)

            localPackages = [self.gsm.localCache.getPackage(name) for name in packages]
            if any(pkg and pkg.isGreensfunctions() for pkg in localPackages):
                print("The deinstallation of greensfunctions may take some time. " \
                      "Please do not cancel prematurely.")

            if packages:
                return self.remove(packages)

            return True

        if command == "hold":
            return self.applyHold(packages, self.gsm.localCache.addHold, False)

        if command == "unhold":
            return self.applyHold(packages, self.gsm.localCache.removeHold, True)

        if command in ("do-release-upgrade", "do-release-downgrade", "switch-os"):
            if self.upgradePrepare(command, packages):
                return True

        if command == "do-release-upgrade":
            return releaseupgrade.ReleaseUpgrade(self.config, self.gsm.localCache).run(self)

        if command == "do-release-downgrade":
            return releasedowngrade.ReleaseDowngrade(self.config, self.gsm.localCache).run(self)

        if command == "switch-os":
            return osupgrade.OSUpgrade(self.config, self.gsm.localCache).run(self)

        if command == "migrate":
            return self.config.makeMigration()

        if command == "check":
            return self.check(command, packages)

        if command == "alias":
            return self.alias(command)

        print(f"Unknown command {command}\n")
        suggestions = difflib.get_close_matches(
            command, self.helpcli.commandNames(), n=1
        )
        if suggestions:
            print(f"Did you mean {self.config.gsmCall} {suggestions[0]}?\n")
        print(f"Show available commands with {self.config.gsmCall} -h commands")
        return False

    def checkCredentials(self, command):
        if command == "clean":
            return True


        if not self.config.baseURL == BASE_PUBLIC_URL:
            if not self.config.user:
                print("No username specified")
                return False

            if not self.config.password:
                print("No password specified")
                return False

        if not self.config.release:
            print(f"No {SEISCOMP} release specified")
            return False
        return True

    def checkPlatformSupport(self, command):
        if not self.gsm.syncCache.getIndex():
            return False, None

        ret, info = self.config.checkOsSupport(self.config)
        if not ret and self.gsm.syncCache.isValid():
            print(info)
            if command == "switch-os":
                self.gsm.updateSyncIndex()
                return True, osupgrade.OSUpgrade(self.config, self.gsm.localCache).run(self, True)
            if command == "do-release-upgrade":
                sys.exit(EXIT_FAILURE)
            if command == "do-release-downgrade":
                sys.exit(EXIT_FAILURE)

        ret, info = self.config.checkReleaseSupport(self.config)
        if not ret and self.gsm.syncCache.isValid():
            print(info)

        return False, None

    def collectPackages(self):
        packages = []
        _ = [packages.append(x) for x in self.args if x not in packages]

        if not packages or len(packages) == 1 and packages[0].lower() == "all":
            packages = list(self.gsm.localCache.getIndex().keys())

        if packages and packages[0] == LICENSES and len(packages) == 1:
            packages.extend(list(self.gsm.localCache.getIndex().keys()))

        return packages

    def init(self):
        if not self.parseCommandLine(True):
            self.helpcli.printHelp(self.helpTopic)
            return False

        if self.showHelp:
            if not os.path.isfile(self.config.fileName) and self.helpcli.isSetupHelp(
                self.helpTopic
            ):
                print(
                    f"Configuration file '{self.config.fileName}' not found. Please run"
                    f" '{self.config.gsmCall} setup' to create an initial configuration\n"
                )
            return True

        if self.showVersion:
            return True

        if os.path.isfile(self.config.fileName):
            error = self.config.read()
            if error and self.command != "setup":
                print(error, file=sys.stderr)
                return False

            if self.command != "setup" and not self.config.checkInstallInfo():
                return False
        else:
            if self.command != "setup":
                print(
                    f"Configuration file '{self.config.fileName}' not found. Please run"
                    f" '{self.config.gsmCall} setup' to create an initial configuration"
                )
                return False

        if not self.parseCommandLine():
            self.helpcli.printHelp(self.helpTopic)
            return False

        if not osutils.createDirectory(self.config.logDir()):
            return False

        if self.config.makeBackup:
            if not osutils.createDirectory(self.config.packageBackupDir):
                return False

        log.setupLogFile(self.config.logPath(), DEFAULT_DATE_FORMAT)
        log.setupDebug(self.config)

        if self.command == "setup":
            return True

        self.gsm = Gsm(self.config)

        if (
            self.command in ("search", "install", "reinstall", "alias")
            or (self.command == "show" and self.args[:1] != ["history"])
        ) and not self.gsm.syncCache.isValid():
            print(
                f" Please run './{GSM} update' to create an initial package index"
            )
            return False

        retPackages, retFiles = self.gsm.localCache.initHoldPackagesAndFiles()
        if not retPackages:
            print("Could not read package hold list!", file=sys.stderr)
            return False
        if not retFiles:
            print("Could not read file hold list!", file=sys.stderr)
            return False

        if self.command not in ("migrate", "switch-os"):
            ret, info = osutils.checkOS(self.config)
            if not ret and self.command != "info":
                print(info, file=sys.stderr)

            return self.config.checkMigration()

        return True

    def parseCommandLine(self, initStage=False):
        options = (
            (("-u", "--user"),         True,     "config", "user",                   None),
            (("-p", "--password"),     True,     "config", "password",               None),
            (("-r", "--release"),      True,     "config", "release",                None),
            (("--arch",),              True,     "config", "arch",                   None),
            (("--os",),                True,     "config", "os",                     None),
            (("--osversion",),         True,     "config", "os_version",             None),
            (("--url",),               True,     "config", "baseURL",                None),
            (("--downloaddir",),       True,     "config", "downloadDir",            None),
            (("--installpath",),       True,     "config", "installPath",            None),
            (("--datadir",),           True,     "config", "dataDir",                None),
            (("--backupdir",),         True,     "config", "packageBackupDir",       None),
            (("--licenseinfodays",),   True,     "config", "licenseInfoDays",        None),
            (("--gpgverify",),         False,    "config", "gpgVerify",              True),
            (("--backup",),            False,    "config", "makeBackup",             True),
            (("--exclude",),           True,     "config", "excludePackages",        splitPackageList),
            (("--to",),                True,     "config", "upgradeTarget", None),
            (("-y", "--assumeyes"),    False,    "config", "assumeYes",              True),
            (("-d", "--downloadonly"), False,    "config", "downloadOnly",           True),
            (("-o", "--offline"),      False,    "config", "offline",                True),
            (("-f", "--force"),        False,    "config", "forceDownload",          True),
            (("--debug",),             False,    "config", "debug",                  True),
            (("--showurls",),          False,    "config", "showUrls",               True),
            (("--noverify",),          False,    "config", "verify",                 False),
            (("-c", "--config"),       True,     None,     None,                     None),
            (("-C",),                  True,     None,     None,                     None),
        )

        shortSpec = "hV"
        longSpec = ["help", "version"]
        dispatch = {}
        for spellings, takesArg, dest, attr, const in options:
            for name in spellings:
                if name.startswith("--"):
                    longSpec.append(name[2:] + ("=" if takesArg else ""))
                else:
                    shortSpec += name[1:] + (":" if takesArg else "")
                dispatch[name] = (takesArg, dest, attr, const)

        try:
            opts, args = getopt.gnu_getopt(self.argv[1:], shortSpec, longSpec)
        except getopt.GetoptError as err:
            print(str(err), file=sys.stderr)
            return False

        self.command = None
        for o, a in opts:
            if o in ("-h", "--help"):
                self.showHelp = True
                self.helpTopic = args
                return True

            if o in ("-V", "--version"):
                self.showVersion = True
                return True

            if initStage:
                continue

            entry = dispatch.get(o)
            if entry is None:
                print(f"unhandled option: {o}", file=sys.stderr)
                return False

            takesArg, dest, attr, const = entry
            if dest is None:
                continue

            if takesArg:
                value = const(a) if const else a
            else:
                value = const

            try:
                if dest == "config":
                    self.config.set(attr, value)
                else:
                    setattr(self, attr, value)
            except ValueError as err:
                print(f"{o}: {err}", file=sys.stderr)
                return False

        if not args:
            print("no arguments given", file=sys.stderr)
            return False

        self.command = args[0].lower()
        self.args = args[1:]

        if not initStage:
            self.config.setRelease(self.config.release)

        return True

    def run(self):
        if not self.init():
            return False

        if self.showHelp:
            return self.helpcli.printHelp(self.helpTopic)

        if self.showVersion:
            pkg = localcache.LocalCache(self.config).getPackage(GSM)
            print(pkg.version if pkg else "unknown")
            return True

        return self.handleCommand(self.command)


def main():
    app = App(len(sys.argv), sys.argv)
    return EXIT_SUCCESS if app.run() else EXIT_FAILURE


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted (Ctrl+C)")
        sys.exit(EXIT_INTERRUPT)
    finally:
        log.resetTerminal()

# vim: ts=4 noet
