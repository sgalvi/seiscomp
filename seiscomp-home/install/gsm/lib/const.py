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
import signal
import sys
import re


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_GSM_UPDATE = 10
EXIT_INTERRUPT = 128 + signal.SIGINT


def urljoin(*args):
    return "/".join(map(lambda x: str(x).strip("/"), args))


LICENSES = "licenses"
BASE_URL = "https://data.gempa.de/"
BASE_PUBLIC_URL = urljoin(BASE_URL, "packages", "Public")

URL_FILE = "file://"

VISIBILITY_PUBLIC = "public"

PUBLIC_MARKER = "(public)"

RENAME_SEEDLINK_BUFFER = "gempa-rename-seedlink-buffer"
CHECK_SCCONFIG = "gempa-checkSCconfig"
SEISCOMP_TOOLS = "seiscomp-tools"

DOC_URL = "https://docs.gempa.de/"

NIGHTLY = "nightly"
SC = "seiscomp"
SC_DEBUG = f"{SC}-debug"

ETC_DIR = "etc"
GSM = "gsm"
GSM_CONF = "gsm.conf"


GSM_CONFIG_FILE = os.path.join(ETC_DIR, GSM_CONF)

GREENSFUNCTIONS = "greensfunctions"

FDSNWS_FRONTEND = "fdsnws-frontend"

OS_MAPPING = {
    "centos": "rhel",
    "rocky": "rhel",
    "almalinux": "rhel",
    "raspbian": "debian",
    "arch": "archlinux",
    "linuxmint": "ubuntu",
}

OS_VERSION_ID_MAPPING = {"archlinux": "BUILD_ID"}

OS_VERSION_OVERRIDES = {
    ("linuxmint", "21"): "22.04",
    ("linuxmint", "22"): "24.04",
    ("linuxmint", "23"): "26.04",
}

APP_DATA_PACKAGES = ["world-minimal"]

GEMPA = "Gempa"

EMAIL_GEMPA = "support@gempa.de"

SEISCOMP = "SeisComP"
DEFAULT_RELEASE = "7"
DEFAULT_ARCH = "x86_64"
DEFAULT_OS = "rhel"
DEFAULT_OS_VERSION = "9"

PRIVILEGE_COMMAND = "pkexec"

FILE_ENCODING = "utf-8"

DOT_CONFIG = ".config"

PACKAGES_REPLACEMENT = {
    "gaps-frontends-all": "gaps-frontends2-all",
    "gaps-frontends": "gaps-frontends2",
    }

NAGIOS_SERVICE_NAME = "gsm_updates"
NAGIOS_LICENSES_NAME = "gsm_licenses"
NAGIOS_OK, NAGIOS_WARNING, NAGIOS_CRITICAL, NAGIOS_UNKNOWN = 0, 1, 2, 3
NAGIOS_UPDATES_STATUS = ("warning", "critical")

REVERSED_REPLACEMENT = {v: k for k, v in PACKAGES_REPLACEMENT.items()}

ARCHIVE = "archive"
RESTORE_DIR = ".restore"

NO_ARCH = "noarch"
ANY = "any"
EXTEND_DIR = "extend"
ANY_NOARCH_DIR = os.path.join(ANY, NO_ARCH)

CUSTOM_INSTALL_PATH = os.path.join("lib", "cache", "custominstall")

VAR_DIR = "var"

DOWNLOAD_DIR = os.path.join(VAR_DIR, "packages")
SYNC_DIR = os.path.join(VAR_DIR, "sync")

HOME_LOCAL_BIN = os.path.join(os.path.expanduser("~"), ".local", "bin")

GPG_DIR = ".gnupg"

GSM_LOG_DIR = os.path.join(VAR_DIR, "log")
GSM_LOG_FILE_NAME = "gsm.log"
GSM_LOG_FILE = os.path.join(GSM_LOG_DIR, GSM_LOG_FILE_NAME)

ALIASES_DIR = "aliases"

SHARE_DIR = "share"
SHELL_COMPLETION = os.path.join(SHARE_DIR, "shell-completion")
SHELL_COMPLETION_FILE = os.path.join(SHELL_COMPLETION, f"{GSM}.bash")
MIGRATIONS = os.path.join(SHARE_DIR, "migrations")

FORMAT = {"0.2": "1.4.0"}

GSM_INFO_OBSOLETE_PACKAGES_URL = urljoin(BASE_URL, "gsminfo/")

GSM_NEWS_URL = urljoin(BASE_URL, "gsminfo/gsm.news")

LICENSE_INFO_DAYS = 30

LINE_WIDTH = 80

DEFAULT_TIMEOUT = 180

DEFAULT_INPUT_TIMEOUT = 30

DEFAULT_CMD_TIMEOUT = 30


class PT:
    def __init__(self):
        self.APP = None
        self.DATA = None
        self.CONFIG = None
        self.GSM = None


PT.APP = "app"
PT.DATA = "data"
PT.CONFIG = "config"
PT.GSM = "gsm"

CMD_CLEAN_ARGUMENTS = ["dbcache", "packages", "backup", "restore", "all"]

CMD_CHECK_ARGUMENTS = ["signature"]

CMD_ALIAS_ARGUMENTS = ["create", "remove"]

CMD_PRINT_ARGUMENTS = ["nagios", "env"]
CMD_PRINT_NAGIOS_ARGUMENTS = ["crontab", "output", "licenses"]

DEFAULT_TIME_FORMAT = "%Y-%m-%d"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_UPDATE_DATE_FORMAT = "%Y.%j"
DEFAULT_NEWS_DATE_FORMAT = "%Y%m%d"
DEFAULT_NEWS_DELTA = 7

INSTALL_DESC = "desc"
INSTALL_FILES = "files"

HOLD_PACKAGE_FILE = ".hold"
HOLD_FILES_FILE = ".holdfiles"

NEW_EXTENSION = ".gsmnew"
MBTILES_EXTENSION = ".mbtiles"
GRD_EXTENSION = ".grd"
CRT_EXTENSION = ".crt"
DSC_EXTENSION = ".dsc"
ZIP_EXTENSION = ".zip"
TARGZ_EXTENSION = ".tar.gz"
TAR_EXTENSION = ".tar"
DB_EXTENSION = ".db"
SIG_EXTENSION = ".sig"
CORE_DB = f"core{DB_EXTENSION}"
CORE_DB_TIMESTAMP = f".{CORE_DB}.last_update"

LICENSE_TXT_EXTENSION = "-license.txt"
CHANGELOG = "CHANGELOG"


PKG_SUCCESS = 0
PKG_FAILED = 1
PKG_NOT_FOUND = 2
PKG_INVALID_VERSION = 3
PKG_IS_ALREADY_INSTALLED = 4

def _isTerminal():
    return sys.stdout.isatty() and sys.stderr.isatty()


def _encodable(text):
    try:
        text.encode(sys.stdout.encoding or "ascii")
    except (UnicodeEncodeError, LookupError, TypeError):
        return False

    return True


if _isTerminal() and not os.environ.get("NO_COLOR"):
    green = "\033[0;32m"
    red = "\033[0;31m"
    blue = "\033[0;94m"
    white = "\033[0;37m"
    gray = "\033[0;90m"
    percent = "\033[0;37;44m"
    reset = "\033[0m"
else:
    green = red = blue = white = gray = percent = reset = ""

eraseEOL = "\033[K" if _isTerminal() else ""

if _encodable("✓✗"):
    markOK, markFailed = "✓", "✗"
    CURRENT_RELEASE_MARK = f"({markOK})"
else:
    markOK, markFailed = "+", "x"
    CURRENT_RELEASE_MARK = "*"

OK = f"{gray}[{green}{markOK}{gray}]{reset}"
FAILED = f"{gray}[{red}{markFailed}{gray}]{reset}"

if _encodable("█░"):
    BAR_CHARS = [gray + "░", "█"]
else:
    BAR_CHARS = True

BAR_WIDTH = 30
MARK_WIDTH = 9

ACCESS = "ACCESS"

INFO = "INFO"
SKIP = "SKIP"
NOTICE = "NOTICE"
GET = "GET"
INSTALL = "INSTALL"
UPDATE = "UPDATE"
BACKUP = "BACKUP"
RESTORE = "RESTORE"
CHECKSUM = "CHECKSUM"
CHECKPGP = "CHECKGPG"
REMOVE = "REMOVE"
MIGRATE = "MIGRATE"

EVENT_INSTALLED = "was installed"
EVENT_UPDATED = "was updated"
EVENT_DEINSTALLED = "was deinstalled"

MAX_LEN_TABLE_COLUMN = 30

DEPS_GNUPG = [
    "gnupg",
]
DEPS_GNUPG_REDHAT = [
    "gnupg2",
]

PUBRING_KBX = "pubring.kbx"
TRUSTDB_GPG = "trustdb.gpg"

MIN_VERSIONS = {"ubuntu": (20, 4), "rhel": (8,), "debian": (11,)}

# The oldest version of an operating system a new gsm (1.8 and later) is installed on: it needs
# Python 3.9. The starter script 'gsm' has the same list. rhel is Rocky Linux, AlmaLinux, CentOS.
GSM_MIN_OS_VERSION = {"ubuntu": (22, 4), "debian": (12,), "rhel": (8,)}
GSM_OS_DISPLAY_NAME = {"ubuntu": "Ubuntu", "debian": "Debian", "rhel": "Rocky Linux / RHEL"}

INSTALL_COMMANDS_GNUPG = {
    "ubuntu": f"sudo apt install {' '.join(DEPS_GNUPG)}",
    "debian": f"As root: apt install {' '.join(DEPS_GNUPG)}",
    "rhel": f"As root: dnf install {' '.join(DEPS_GNUPG_REDHAT)}",
}

BINARY_SUFFIXES = (" KiB", " MiB", " GiB", " TiB", " PiB", " EiB", " ZiB", " YiB")

MSG_CONTINUE_QUESTION = "Do you want to continue?"

HASH_PATTERN = re.compile(r"[0-9a-f]{64}$")


DATE_REGEXP = re.compile(r"^\d{4}\.\d{1,3}$")
