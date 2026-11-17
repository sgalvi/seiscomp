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
import importlib.util
import shutil

from lib.const import CUSTOM_INSTALL_PATH


def checkFilesExist(self, pkg):
    if pkg.format <= str(0.1):
        return checkFilesExistLegacy(self, pkg)
    else:
        modulePath = os.path.join(
            self.baseDir, CUSTOM_INSTALL_PATH, pkg.name + "." + "py"
        )

        if os.path.isfile(modulePath):
            spec = importlib.util.spec_from_file_location(pkg.name, modulePath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.checkFilesExist(self, pkg)

        return None


def install(self, installPath, pkg):
    if pkg.format <= str(0.1):
        installLegacy(self, installPath, pkg)
    else:
        modulePath = os.path.join(
            self.config.baseDir, CUSTOM_INSTALL_PATH, pkg.name + "." + "py"
        )

        if os.path.isfile(modulePath):
            spec = importlib.util.spec_from_file_location(pkg.name, modulePath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            module.install(self, installPath, pkg)


def remove(self, pkg):
    if pkg.format <= str(0.1):
        removeLegacy(self, pkg)
    else:
        customPath = os.path.join(self.config.baseDir, CUSTOM_INSTALL_PATH)
        modulePath = os.path.join(customPath, pkg.name + "." + "py")

        if os.path.isfile(modulePath):
            spec = importlib.util.spec_from_file_location(pkg.name, modulePath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            module.remove(self, pkg)
        if os.path.exists(modulePath):
            os.remove(modulePath)
            shutil.rmtree(os.path.join(customPath, "__pycache__"), ignore_errors=True)
        if not os.listdir(customPath):
            shutil.rmtree(customPath)


def checkFilesExistLegacy(pkg, installPath):
    if pkg.name in ("bom-addons-client", "templates-bom-toastd"):
        jsonFile = "oceans.geojson"
        dstJson = os.path.join(installPath, "share", "spatial", "vector", jsonFile)
        if os.path.isfile(dstJson):
            return dstJson

    if pkg.name == "scenarios-most":
        csvFile = "cregions_95percentile_20221004.csv"
        jsonFile = "t2_scenario_ruptures.json"
        mostSharePath = os.path.join(installPath, "share", "gds", "most")
        dstCsv = os.path.join(mostSharePath, csvFile)
        dstJson = os.path.join(mostSharePath, jsonFile)
        if os.path.isfile(dstJson):
            return dstJson
        if os.path.isfile(dstCsv):
            return dstCsv

    return None


def installLegacy(self, installPath, pkg):

    if pkg.name in ("bom-addons-client", "templates-bom-toastd"):

        dstPath = os.path.join(self.config.installPath, "share", "spatial", "vector")

        jsonFile = "oceans.geojson"

        if pkg.name == "bom-addons-client":
            srcPath = os.path.join(installPath, "spatial", "vector", jsonFile)
        else:
            srcPath = os.path.join(installPath, "extras", jsonFile)

        dstJson = os.path.join(dstPath, jsonFile)

        if not os.path.isdir(dstPath):
            os.makedirs(dstPath)

        if os.path.isfile(dstJson):
            os.remove(dstJson)

        os.symlink(srcPath, dstJson)

    if pkg.name == "scenarios-most":
        mostSharePath = os.path.join(self.config.installPath, "share", "gds", "most")

        csvFile = "cregions_95percentile_20221004.csv"
        srcCsv = os.path.join(installPath, csvFile)

        jsonFile = "t2_scenario_ruptures.json"
        srcJson = os.path.join(installPath, jsonFile)

        dstCsv = os.path.join(mostSharePath, csvFile)
        dstJson = os.path.join(mostSharePath, jsonFile)

        if not os.path.isdir(mostSharePath):
            os.makedirs(mostSharePath)
        os.symlink(srcCsv, dstCsv)
        os.symlink(srcJson, dstJson)

    if pkg.name == "oq-engine":
        src = os.path.join(installPath, "openquake")
        dst = os.path.join(self.config.installPath, "lib", "python")
        if os.path.exists(dst):
            dst = os.path.join(dst, "openquake")
            if not os.path.exists(dst):
                os.symlink(src, dst)

    if pkg.name in ("slabs-rum", "slabs-usgs"):
        folder = pkg.name.split("-")[1]
        src = os.path.join(installPath)
        dst = os.path.join(self.config.installPath, "share", "spatial", "vector")
        os.makedirs(dst, exist_ok=True)

        dst = os.path.join(dst, folder)
        if os.path.islink(dst) and not os.path.exists(dst):
            os.remove(dst)
        if not os.path.lexists(dst):
            os.symlink(src, dst)


def removeEmptyDir(path):
    if os.path.isdir(path) and not os.listdir(path):
        os.rmdir(path)


def removeLegacy(self, pkg):
    if pkg.name in ("bom-addons-client", "templates-bom-toastd"):
        dstPathSpatial = os.path.join(self.config.installPath, "share", "spatial")
        dstPath = os.path.join(self.config.installPath, "share", "spatial", "vector")

        jsonFile = "oceans.geojson"
        dstJson = os.path.join(dstPath, jsonFile)

        if os.path.islink(dstJson):
            os.remove(dstJson)

        removeEmptyDir(dstPath)
        removeEmptyDir(dstPathSpatial)

    if pkg.name == "scenarios-most":
        gdsSharePath = os.path.join(self.config.installPath, "share", "gds")
        mostSharePath = os.path.join(gdsSharePath, "most")
        csvFile = "cregions_95percentile_20221004.csv"
        jsonFile = "t2_scenario_ruptures.json"
        dstCsv = os.path.join(mostSharePath, csvFile)
        dstJson = os.path.join(mostSharePath, jsonFile)
        if os.path.islink(dstCsv):
            os.remove(dstCsv)
        if os.path.islink(dstJson):
            os.remove(dstJson)
        if os.path.exists(mostSharePath):
            if not os.listdir(mostSharePath):
                os.rmdir(mostSharePath)
        if os.path.exists(gdsSharePath):
            if not os.listdir(gdsSharePath):
                os.rmdir(gdsSharePath)

    if pkg.name == "oq-engine":
        dst = os.path.join(self.config.installPath, "lib", "python", "openquake")
        if os.path.islink(dst):
            os.remove(dst)

    elif pkg.name in ("slabs-rum", "slabs-usgs"):
        folder = pkg.name.split("-")[1]
        share = os.path.join(self.config.installPath, "share")
        # the link of gsm 1.7 (share/bna/<folder>) is taken away too
        for parts in (("spatial", "vector"), ("bna",)):
            dstDir = os.path.join(share, *parts)
            dst = os.path.join(dstDir, folder)
            if os.path.islink(dst):
                os.remove(dst)
            removeEmptyDir(dstDir)
