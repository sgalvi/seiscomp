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
import subprocess
import re
from datetime import date, datetime

from lib import package, utils
from lib.const import (
    DEFAULT_CMD_TIMEOUT,
    DEFAULT_TIME_FORMAT,
    GSM,
    NAGIOS_CRITICAL,
    NAGIOS_LICENSES_NAME,
    NAGIOS_OK,
    NAGIOS_SERVICE_NAME,
    NAGIOS_UNKNOWN,
    NAGIOS_UPDATES_STATUS,
    NAGIOS_WARNING,
    SC,
)

EXPIRED, ENDS, UPDATES_END, MISSING = "expired", "ends", "update period ends", "missing"

class Nagios:
    def __init__(self, config):
        self.config = config
        self.runCmd = os.path.join(self.config.baseDir, self.config.gsmBinary)

    def run(self,cmdArgs):
        try:
            proc = subprocess.run(cmdArgs, capture_output=True,
                                  text=True, timeout=DEFAULT_CMD_TIMEOUT, check=False)
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except Exception as e:
            return 1, "", str(e)

    def printNagios(self):
        status = self.config.nagiosUpdates
        if status not in NAGIOS_UPDATES_STATUS:
            print(f"{NAGIOS_SERVICE_NAME} ({self.config.gsmBinary}) "\
                  f"nagios_updates must be warning or critical, not '{status}'")
            return NAGIOS_UNKNOWN

        updatesStatus = NAGIOS_WARNING if status == "warning" else NAGIOS_CRITICAL
        rc, out, err = self.run([self.runCmd, "show", "updates"])
        if rc != 0:
            print(f"{NAGIOS_SERVICE_NAME} ({self.config.gsmBinary}) "\
                  f"show updates failed: rc={rc} err={err or out}")
            return 2

        text = out.strip()

        if "All packages are up to date" in text:
            print(f"{NAGIOS_SERVICE_NAME} ({self.config.gsmBinary}) "\
                  "All packages are up to date | updates=0;;;;")
            return 0

        pattern = re.compile(r"^\s*([A-Za-z0-9_.+-]+)\s*\([^)]+\)\s*-->\s*([^\s]+)", re.MULTILINE)
        matches = pattern.findall(text)
        if matches:
            pkgNames = [m[0] for m in matches]
            count = len(pkgNames)
            msg = f"{count} updates available: {', '.join(pkgNames)}"
            print(f"{NAGIOS_SERVICE_NAME} ({self.config.gsmBinary}) "\
                  f"{msg} | updates={count};;;;")
            return updatesStatus

        excerpt = text.splitlines()[:6]
        excerptText = " | ".join(line.strip() for line in excerpt if line.strip())
        if not excerptText:
            excerptText = "empty output"

        print(f"{NAGIOS_SERVICE_NAME} ({self.config.gsmBinary}) "\
              f"Unexpected output: {excerptText} | updates=UNKNOWN;;;;")
        return 2

    @staticmethod
    def licenseNotices(config, localPackages, today=None):
        today = today or date.today()
        days = utils.licenseInfoDays(config)
        notices = []
        for pkg in localPackages:
            if pkg.license == "None" or pkg.name in (SC, GSM):
                continue

            cert = utils.readCertificate(package.getLicenseFileName(pkg), config)
            if cert is None:
                notices.append((pkg.name, MISSING, None))
                continue

            validUntil = cert.not_valid_after.date() if hasattr(cert.not_valid_after, "date") else cert.not_valid_after
            if validUntil < today:
                notices.append((pkg.name, EXPIRED, validUntil))
                continue

            if days and (validUntil - today).days <= days:
                notices.append((pkg.name, ENDS, validUntil))

            updatesUntil = utils.findUpdatesUntil(cert.issuer)
            if days and updatesUntil:
                updatesUntil = datetime.strptime(updatesUntil, DEFAULT_TIME_FORMAT).date()
                if 0 <= (updatesUntil - today).days <= days:
                    notices.append((pkg.name, UPDATES_END, updatesUntil))

        return notices

    def printLicenses(self, localPackages):
        service = f"{NAGIOS_LICENSES_NAME} ({self.config.gsmBinary})"
        try:
            notices = self.licenseNotices(self.config, localPackages)
        except Exception as e:
            print(f"{service} license check failed: {e}")
            return NAGIOS_UNKNOWN

        expired = [n for n in notices if n[1] == EXPIRED]
        ahead = len(notices) - len(expired)
        perf = f"| expired={len(expired)};;;; ending={ahead};;;;"
        if not notices:
            print(f"{service} All licenses are valid {perf}")
            return NAGIOS_OK

        words = {EXPIRED: "license expired on", ENDS: "license ends on",
                 UPDATES_END: "update period ends on"}
        texts = [
            f"{name} has no license file" if kind == MISSING else f"{name} {words[kind]} {when}"
            for name, kind, when in sorted(notices, key=lambda n: (n[1] != EXPIRED, n[0]))
        ]
        print(f"{service} {len(notices)} license notice(s): {'; '.join(texts)} {perf}")
        return NAGIOS_CRITICAL if expired else NAGIOS_WARNING

    def printCrontab(self):
        print(f"20 5 * * * {self.runCmd} sync")
