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
import re
import shutil
import configparser

from lib.const import (
    ALIASES_DIR,
    GSM_CONFIG_FILE,
    GSM,
    GSM_LOG_DIR,
    DOT_CONFIG,
    ETC_DIR,
)

from lib import config, log

from lib.utils import checkInput

def checkAliasName(alias):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]+', alias))  # not match + '$': that accepts a line break at the end

class Alias:
    def __init__(self, config, name):
        self.name = name
        self.config = config
        self.configOriginal = config

    def writeInstallInfoFileAlias(self, aliasLocalDir):
        internalConfig = os.path.join(aliasLocalDir, DOT_CONFIG)
        try:
            parser = configparser.RawConfigParser(allow_no_value=True)
            parser.add_section("CONFIG")
            parser.set("CONFIG", "release", self.config.release)
            parser.set("CONFIG", "install_path", self.config.installPath)
            parser.set("CONFIG", "baseDir", self.configOriginal.baseDir)
            parser.set("CONFIG", "data_dir", self.config.dataDir)
            parser.set("CONFIG", "config", self.config.getLatestMigrationVersion())
            self.config.write(parser, internalConfig)
        except IOError as e:
            log.logError(f"Could not write {internalConfig} file: {e}")
            return False

        return True


    def createAlias(self):
        aliasDir = os.path.join(self.config.baseDir, ALIASES_DIR, self.name)
        aliasLocalDir = os.path.join(aliasDir, "local")
        aliasLogDir = os.path.join(aliasDir, GSM_LOG_DIR)
        aliasEtcDir = os.path.join(aliasDir, ETC_DIR)

        if os.path.exists(aliasDir):
            print(f"Could not create alias: '{self.name}' already exists")
            return False

        link = os.path.join(self.configOriginal.baseDir, f"{GSM}-{self.name}")
        linkExisted = os.path.lexists(link)
        try:
            return self.buildAlias(aliasDir, aliasLocalDir, aliasLogDir, aliasEtcDir)
        except BaseException:
            # an error or Ctrl+C: no half-made alias is left behind (it would be 'already exists')
            shutil.rmtree(aliasDir, ignore_errors=True)
            if not linkExisted and os.path.islink(link):
                os.remove(link)
            aliasesDir = os.path.join(self.configOriginal.baseDir, ALIASES_DIR)
            if os.path.isdir(aliasesDir) and not os.listdir(aliasesDir):
                os.rmdir(aliasesDir)
            raise

    def buildAlias(self, aliasDir, aliasLocalDir, aliasLogDir, aliasEtcDir):
        for directory in [aliasDir, aliasLocalDir, aliasLogDir, aliasEtcDir]:
            os.makedirs(directory, exist_ok=True)

        os.symlink(
            os.path.join("../../../local", GSM),
            os.path.join(aliasLocalDir, GSM),
        )

        self.config = config.Config(aliasDir, GSM_CONFIG_FILE)

        self.config.downloadDir = self.configOriginal.downloadDir
        self.config.syncDir = self.configOriginal.syncDir
        self.config.dataDir = self.configOriginal.dataDir
        self.config.installPath = self.configOriginal.installPath +"-" +self.name
        self.config.user = self.configOriginal.user
        self.config.password = self.configOriginal.password
        self.config.baseURL = self.configOriginal.baseURL
        self.config.verify = self.configOriginal.verify
        self.config.gpgVerify = self.configOriginal.gpgVerify
        self.config.licenseInfoDays = self.configOriginal.licenseInfoDays
        self.config.gsmBinary = os.path.join(self.configOriginal.baseDir,f"{GSM}-{self.name}")
        for attr in ("release", "os", "os_version", "arch", "offline",
                     "assumeYes", "makeBackup", "packageBackupDir"):
            setattr(self.config, attr, getattr(self.configOriginal, attr))

        if self.config.setup():
            self.writeInstallInfoFileAlias(aliasLocalDir)
            saveDir = os.getcwd()
            try:

                os.chdir(self.configOriginal.baseDir)
                os.symlink(GSM, os.path.basename(f"{GSM}-{self.name}"))
                print(f"The alias {self.name} ({GSM}-{self.name}) was created.")
            except FileExistsError:
                pass
            finally:
                os.chdir(saveDir)
        else:
            if os.path.exists(aliasDir):
                shutil.rmtree(aliasDir)

            aliasesDir = os.path.join(self.configOriginal.baseDir, ALIASES_DIR)
            if os.path.exists(aliasesDir) and not os.listdir(aliasesDir):
                shutil.rmtree(aliasesDir)

        return True

def removeAlias(config, name):
    aliasDir = os.path.join(config.baseDir, ALIASES_DIR, name)

    if not os.path.exists(aliasDir):
        print(f"The specified alias '{name} ({GSM}-{name})' does not exist.")
        return False

    if not config.assumeYes and checkInput(f"\nDo you really want to remove the alias {name} ({GSM}-{name})?", "N", "yn"):
        return False

    shutil.rmtree(aliasDir)

    for path in [
        os.path.join(config.baseDir, f"{GSM}-{name}"),
        os.path.join(os.path.expanduser("~"), ".local", "bin", f"{GSM}-{name}")
    ]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    aliasesDir = os.path.join(config.baseDir, ALIASES_DIR)
    if os.path.exists(aliasesDir) and not os.listdir(aliasesDir):
        shutil.rmtree(aliasesDir)

    return True
