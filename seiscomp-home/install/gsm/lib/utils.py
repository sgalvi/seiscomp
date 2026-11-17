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


import hashlib
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import time
import math
import re
import textwrap

import tty
import termios
import signal

from contextlib import contextmanager

from base64 import b64encode

from datetime import datetime, date, timezone
from email.utils import parsedate_to_datetime

from zipfile import ZipFile

import warnings

from html.parser import HTMLParser

import requests

from tqdm import tqdm

from lib.const import (
    LICENSE_INFO_DAYS,
    LICENSES,
    SC,
    urljoin,
    DEFAULT_TIMEOUT,
    BASE_PUBLIC_URL,
    DEFAULT_RELEASE,
    PT,
    CUSTOM_INSTALL_PATH,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UPDATE_DATE_FORMAT,
    MBTILES_EXTENSION,
    GRD_EXTENSION,
    ZIP_EXTENSION,
    TARGZ_EXTENSION,
    TAR_EXTENSION,
    DB_EXTENSION,
    CRT_EXTENSION,
    BAR_CHARS,
    INSTALL,
    GET,
    CHECKSUM,
    ACCESS,
    GSM_NEWS_URL,
    GSM,
    INFO,
    BACKUP,
    RESTORE,
    SIG_EXTENSION,
    FILE_ENCODING,
    URL_FILE,
    CORE_DB_TIMESTAMP,
    RESTORE_DIR,
    GSM_CONFIG_FILE,
    BINARY_SUFFIXES,
    EXIT_FAILURE,
)

from lib import certificate, log
from lib.cache import custominstall


class TimeoutOccurred(Exception):
    pass


def timeoutHandler(signum, frame):
    raise TimeoutOccurred


def timedinput(prompt="", timeout=0, default=None):
    oldHandler = signal.signal(signal.SIGALRM, timeoutHandler)
    try:
        signal.setitimer(signal.ITIMER_REAL, timeout or 0)
        return input(prompt)
    except TimeoutOccurred:
        print()
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except (termios.error, OSError, ValueError):
            pass
        if default is not None:
            return default
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, oldHandler)

try:
    real_raw_input = raw_input
except NameError:
    real_raw_input = input


def noInputAvailable():
    print()
    log.logError(
        "No input available to answer the question (stdin is closed)."
        " Use -y to run non-interactively."
    )
    sys.exit(EXIT_FAILURE)


def getInput(question, default=None, options=None, timeout=None):
    if timeout is not None:
        print(f"This prompt has a timeout of {timeout}s:")
    else:
        timeout = 0

    def _default(text):
        if default:
            print(f"\x1b[F\x1b[{len(text) + 1}G{default}")
        return default

    if not options:
        defaultStr = "" if default is None else f" [{default}]"
        question = f"{question}{defaultStr}: "
        if timeout in (None, 0):
            try:
                return real_raw_input(question) or _default(question)
            except EOFError:
                noInputAvailable()
        try:
            user_input = timedinput(
                question, timeout=timeout, default=None
            )
        except TimeoutOccurred:
            sys.exit(EXIT_FAILURE)
        except EOFError:
            noInputAvailable()

        if not user_input:
            return _default(question)
        return user_input

    if default is not None:
        default = str(default).lower()

    opts = [str(o).lower() for o in options]
    optStr = "/".join(o.upper() if o == default else o for o in opts)
    question = f"{question} [{optStr}]: "
    while True:
        try:
            res = timedinput(question, timeout=timeout, default=None)
        except TimeoutOccurred:
            sys.exit(EXIT_FAILURE)
        except EOFError:
            noInputAvailable()
        if not res and default:
            return _default(question)

        if res.lower() in opts:
            return res.lower()


def gsmCallName(binary, baseDir):
    name = os.path.basename(binary)
    found = shutil.which(name)
    local = os.path.join(baseDir, name)
    if found and os.path.exists(local) and os.path.samefile(found, local):
        return name

    return binary if os.sep in binary else os.path.join(".", name)


def sorting(lst):
    return sorted(lst, key=len)


def naturalSortKey(value):
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", str(value))
    ]


def naturalSorted(iterable, key=None, reverse=False):
    if key is None:
        keyFunc = naturalSortKey
    else:
        def keyFunc(item):
            return naturalSortKey(key(item))

    return sorted(iterable, key=keyFunc, reverse=reverse)


def remoteMembers(syncCache, members):
    result = []
    for member in members:
        pkg = syncCache.getPackage(member)
        if pkg and pkg.localDir:
            continue
        result.append(member)

    return result


def checkUrlAccessProgress(config, syncCache, members):
    members = sorting(remoteMembers(syncCache, members))
    failed = []
    progress = progressBar(members, ACCESS)
    for member in progress:
        pkg = syncCache.getPackage(member)
        pkgName, _ = getPackageName(pkg)
        setDesc(progress, ACCESS, pkgName)
        url = getDownloadDirectoryURL(pkg, config)
        ret, _ = checkUrlAccess(config, url)

        if not ret:
            failed.append(pkg.name)

    log.logResult(
        progress,
        ACCESS,
        n=len(members) - len(failed),
        total=len(members),
        ok=not failed,
    )

    return failed


def basicAuthHeaders(user, password):
    headers = {}
    if user and password:
        credentials = b64encode(
            f"{user}:{password}".encode(FILE_ENCODING)
        ).decode(FILE_ENCODING)
        headers["Authorization"] = f"Basic {credentials}"
    return headers


def authHeadersFor(url, config):
    """The login for 'url': only the repository (base_url) and the package index (db_url) get it.

    The public repository, the news and the notes on obsolete packages do not need it, and
    must not see the password of the user.
    """
    if not (config.user and config.password):
        return {}

    for own in (config.baseURL, config.dbUrl):
        own = own.rstrip("/") if own else own
        if own and (url == own or url.startswith(own + "/")):
            return basicAuthHeaders(config.user, config.password)
    return {}


def publicOrBaseURL(pkg, config):
    if config.baseURL.startswith(URL_FILE):
        return config.baseURL

    return BASE_PUBLIC_URL if pkg.isPublic() else config.baseURL


def checkUrlAccess(config, url=None):
    if not url:
        url = config.baseURL
    disableHTTPSWarnings(config.verify)

    headers = basicAuthHeaders(config.user, config.password)

    showUrl(config, url)
    try:
        with requests.get(
            url,
            stream=True,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
            verify=config.verify,
        ) as r:
            return r.status_code == 200, r.status_code
    except Exception:
        return (False, None)


def createNewSession(user=None, password=None, verify=True):
    session = requests.Session()
    session.verify = verify
    headers = basicAuthHeaders(user, password)
    if headers:
        session.headers.update(headers)

    return session

class AnchorHrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value is not None:
                self.hrefs.append(value)


def fetchDirectories(url, session):
    directories = []
    try:
        response = session.request("GET", url, timeout=DEFAULT_TIMEOUT)
        parser = AnchorHrefParser()
        parser.feed(response.text)

        for href in parser.hrefs:
            if href.endswith("/") and href != "../":
                directories.append(href.rstrip("/"))
    except requests.RequestException:
        log.logError(f"HTTP error while retrieving {url}")

    return directories

def setupWarnings(verify):
    disableHTTPSWarnings(verify)
    if not verify:
        warnings.filterwarnings(
            action="ignore", message="unclosed", category=ResourceWarning
        )


def listDirFromPublicURL(url, verify, value):
    setupWarnings(verify)

    try:
        with createNewSession(verify=verify) as session:
            directories = fetchDirectories(url, session)

        if directories:
            return True, directories

    except Exception:
        return True, [value]

    return False, None


def listDirFromURL(config, url=None):
    if not url:
        url = config.baseURL

    setupWarnings(config.verify)

    try:
        with createNewSession(
            config.user, config.password, config.verify
        ) as session:
            directories = fetchDirectories(url, session)

        if directories:
            return True, directories

    except Exception:
        return True, [config.arch]

    return False, None

def compareResult(ret, result, value):
    return bool(ret and value in result), result


def isAvailable(verify, value, *parts):
    url = urljoin(BASE_PUBLIC_URL, *parts)
    ret, result = listDirFromPublicURL(url, verify, value)
    return compareResult(ret, result, value)


def isArchAvailable(release, os_, version, arch, verify):
    return isAvailable(verify, arch, SC, release, os_, version)


def isOsVersionAvailable(release, os_, version, verify):
    return isAvailable(verify, version, SC, release, os_)


def isOsAvailable(release, os_, verify):
    return isAvailable(verify, os_, SC, release)


def isReleaseAvailable(release, verify):
    return isAvailable(verify, release, SC)


def getLatestRelease(verify):
    _, releases = isReleaseAvailable(DEFAULT_RELEASE, verify)
    numeric = [r for r in releases or [] if r.isdigit()]
    return max(numeric, key=int) if numeric else None


def showOwnPackages(config, publicPackages, extendPackages):
    ret, result = listDirFromURL(config)

    if not ret or not result:
        log.logWarning(
            "Invalid login credentials. Only the public packages are shown."
        )
        print()
        return True, publicPackages

    result.extend(publicPackages)

    for pkg in extendPackages:
        if pkg in result:
            retExtend, resultExtend = listDirFromURL(
                config, urljoin(config.baseURL, pkg)
            )

            if retExtend and resultExtend:
                result.extend(resultExtend)

    return True, result


def checkInput(question, default, options):
    default = str(default).lower()
    return getInput(question, default, options) == default


def humanbytes(B):
    try:
        bytes_ = float(B)
    except (ValueError, TypeError):
        return "N/A"

    absBytes = abs(bytes_)
    if absBytes == 1:
        return f"{int(bytes_)} Byte"
    if absBytes < 1024:
        return f"{int(bytes_)} Bytes"

    exp = int(min(math.log(absBytes, 1024), len(BINARY_SUFFIXES)))
    return f"{bytes_ / (1024**exp):.1f}{BINARY_SUFFIXES[exp - 1]}"


def readCertificate(name, config):
    fileName = f"{name}{CRT_EXTENSION}"
    licenseFiles = [
        os.path.join(config.downloadLicenseDir, fileName),
        os.path.join(config.licenseDir, fileName),
        os.path.join(config.userConfigDir, LICENSES, fileName),
    ]

    cert = None

    for licenseFile in licenseFiles:
        if os.path.isfile(licenseFile):
            res = readCertificateFile(licenseFile)
            if res and (
                cert is None
                or (
                    res.updatesUntil
                    and (
                        not cert.updatesUntil
                        or cert.updatesUntil < res.updatesUntil
                    )
                )
            ):
                cert = res
                break

    return cert


class CertLocal:
    def __init__(self, issuer, not_valid_after):
        self.issuer = issuer
        self.not_valid_after = not_valid_after
        self.updatesUntil = None


UPDATES_UNTIL_PATTERN = re.compile(r"updatesUntil=(\d{4}-\d{2}-\d{2})")


def findUpdatesUntil(issuer):
    """The date ('YYYY-MM-DD') of the first 'updatesUntil=' in the text of the issuer, or None."""
    match = UPDATES_UNTIL_PATTERN.search(str(issuer))
    return match.group(1) if match else None


def readCertificateFile(licenseFile):
    try:
        with open(licenseFile, "rb") as certFile:
            cert = certificate.readCertificate(certFile.read())

        cert = CertLocal(cert.issuer, cert.notAfter)
        timeStr = findUpdatesUntil(cert.issuer)
        if timeStr:
            cert.updatesUntil = datetime.strptime(
                timeStr, DEFAULT_TIME_FORMAT
            ).strftime(DEFAULT_UPDATE_DATE_FORMAT)
    except Exception:
        return None

    return cert


def getTerminalLines():
    return shutil.get_terminal_size().lines


def getTerminalColumns():
    return shutil.get_terminal_size().columns


WRAP_INDENT = re.compile(r"^(\s*(?:[-*]\s+|[\w.-]+: )?)")


def wrapForTerminal(text, columns):
    lines = []
    for line in text.split("\n"):
        if len(line) <= columns:
            lines.append(line)
            continue

        indent = " " * len(WRAP_INDENT.match(line).group(1))
        if len(indent) > columns // 2:
            indent = " " * (len(line) - len(line.lstrip()))
        prefix = WRAP_INDENT.match(line).group(1)
        value = line[len(prefix):]
        if prefix and len(value.split()) == 1:
            room = max(columns - len(prefix), 1)
            lines.append(prefix + value[:room])
            lines += [indent + value[i : i + room] for i in range(room, len(value), room)]
            continue

        lines += textwrap.wrap(
            line,
            columns,
            subsequent_indent=indent,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [line]

    return "\n".join(lines)


def displayTextSideBySide(text):
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        try:
            print(text)
            sys.stdout.flush()
        except BrokenPipeError:
            # the reader ended first (gsm show history x | head): not an error. stdout is pointed to
            # /dev/null so that Python does not report the same error again when it exits.
            try:
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
            except (OSError, ValueError):
                pass
        return

    maxLines = getTerminalLines()

    lines = wrapForTerminal(text, getTerminalColumns()).split("\n")

    for i in range(0, len(lines), maxLines):
        chunk = "\n".join(lines[i : i + maxLines])
        print(chunk)
        if i + maxLines < len(lines):
            input("\nPress any button to continue or (Ctrl+C) to cancel...")


def hashfile(fileName, checksum, pkg):
    pkgName, _ = getPackageName(pkg)
    blockSize = 2**16
    hasher = hashlib.sha256()
    if not os.path.isfile(fileName):
        log.logError(f"No such file or directory: {fileName}")
        return False
    fileSize = os.path.getsize(fileName)
    try:
        with open(fileName, "rb") as f:
            with tqdm(
                total=fileSize,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=log.label(pkgName),
                ascii=BAR_CHARS,
                bar_format=log.barFormat(CHECKSUM),
                leave=False,
            ) as pbar:
                for buf in iter(lambda: f.read(blockSize), b""):
                    hasher.update(buf)
                    pbar.update(len(buf))

                ok = hasher.hexdigest() == checksum
    except IOError as e:
        log.logError(f"Error reading file: {e}")
        return False

    log.logResult(pbar, CHECKSUM, pkgName, ok=ok)

    return ok


def disableHTTPSWarnings(value):
    if not value:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def showUrl(config, url):
    if config.showUrls:
        tqdm.write(f"{log.getLogPrefix(INFO)}{url}", file=sys.stderr)


def isDirty(fileName, url, config):
    disableHTTPSWarnings(config.verify)
    lastModified = None
    showUrl(config, url)
    try:
        response = requests.head(
            url,
            headers=authHeadersFor(url, config),
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True,
            verify=config.verify,
        )
        if response.status_code != 200:
            raise ValueError(
                f"{url}: {response.status_code} {response.reason}"
            )
        try:
            lastModified = parsedate_to_datetime(response.headers["last-modified"])

            dbFilePath = config.syncPath(config.dbFileName)
            timestampDbFilePath = config.syncPath(CORE_DB_TIMESTAMP)

            if os.path.basename(fileName) == config.dbFileName:
                if os.path.exists(dbFilePath):
                    if os.path.exists(timestampDbFilePath):
                        with open(timestampDbFilePath, 'r', encoding=FILE_ENCODING) as file:
                            timestamp = float(file.read().strip())
                    else:
                        timestamp = os.path.getmtime(dbFilePath)
                else:
                    timestamp = 0
                    if os.path.exists(timestampDbFilePath):
                        os.remove(timestampDbFilePath)
            else:
                timestamp = os.path.getmtime(os.path.abspath(fileName))

            lastUpdate = datetime.fromtimestamp(timestamp, timezone.utc)

            if lastUpdate >= lastModified:
                return False, lastModified
        except (KeyError, TypeError):
            pass
    except (OSError, ValueError):
        pass

    return True, lastModified


def getNewsFromUrl(verify):
    disableHTTPSWarnings(verify)

    try:
        r = requests.get(
            GSM_NEWS_URL,
            timeout=DEFAULT_TIMEOUT,
            verify=verify,
        )
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError:
        pass
    except requests.exceptions.RequestException as err:
        log.logError(f"{err}")

    return None


def getDataFromUrl(url, config, update=False):
    disableHTTPSWarnings(config.verify)
    showUrl(config, url)
    try:
        r = requests.get(
            url,
            headers=authHeadersFor(url, config),
            timeout=DEFAULT_TIMEOUT,
            verify=config.verify,
        )
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError as err:
        if update is False:
            log.logError(f"{url}: ({err})")
    except requests.exceptions.RequestException as err:
        log.logError(f"{err}")

    return None


def statusName(config, installInfo):
    if config.baseURL.startswith("file:///"):
        return GET
    return INSTALL if installInfo else BACKUP


def isStaleCopy(source, fileName):
    try:
        dst = os.stat(fileName)
    except FileNotFoundError:
        return True

    try:
        src = os.stat(source)
    except FileNotFoundError:
        return True

    return src.st_size != dst.st_size or src.st_mtime > dst.st_mtime


def copy(config, fileName, path, pkgName, installInfo=True):
    if not os.path.isfile(fileName):
        log.logError(f"No such file or directory: {fileName}")
        return False
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            log.logError(f"Failed to create directory '{path}': {e}")
            return False

    fileSize = os.path.getsize(fileName)
    bufSize = 2**20 * 10
    numChunks = math.ceil(fileSize / bufSize)

    # written under another name and renamed when it is complete: an interrupted copy (disk full,
    # Ctrl+C) leaves no half file under the name of the target that a later run takes for a copy
    tmpPath = f"{path}.tmp"
    try:
        with open(fileName, "rb") as src_f, open(tmpPath, "wb") as dest_f:
            status = statusName(config, installInfo)
            progress = progressBar(range(numChunks), status, pkgName)

            for _ in progress:
                chunk = src_f.read(bufSize)
                if not chunk:
                    break
                dest_f.write(chunk)
        os.replace(tmpPath, path)

    except (IOError, KeyboardInterrupt) as err:
        try:
            os.remove(tmpPath)
        except OSError:
            pass
        if isinstance(err, KeyboardInterrupt):
            raise
        log.log(statusName(config, installInfo), f"{pkgName} ({err})", ok=False)
        log.logError(f"{pkgName} ({err})")
        return False

    log.logResult(progress, status, pkgName)

    return True


def download(url, fileName, desc, config, dscFile=None):
    if url.startswith(URL_FILE):
        source = url.replace(URL_FILE, "")
        if isStaleCopy(source, fileName):
            return copy(config, source, fileName, desc)

        return True
    disableHTTPSWarnings(config.verify)

    try:
        dirty, mtime = isDirty(fileName, url, config)
    except Exception as err:
        log.logError(f"{err}")
        return False

    if not config.forceDownload and not dirty:
        return True

    if not mtime:
        log.logError(
            "http request did not provide 'last-modified'. Please try again."
        )
        return False

    authHeaders = authHeadersFor(url, config)

    def get(firstByte):
        header = {"Accept-Encoding": "", **authHeaders}
        if firstByte:
            header["Range"] = f"bytes={firstByte}-"
        return requests.get(
            url,
            headers=header,
            stream=True,
            timeout=DEFAULT_TIMEOUT,
            verify=config.verify,
        )

    tmpFile = fileName + ".tmp"
    firstByte = os.path.getsize(tmpFile) if os.path.isfile(tmpFile) else 0
    try:
        r = get(firstByte)
        if firstByte and r.status_code == 416:
            r.close()
            firstByte = 0
            r = get(firstByte)
        if r.status_code >= 300:
            log.logError(f"{url}: {r.status_code} {r.reason}")
            r.close()
            return False
    except requests.exceptions.RequestException as err:
        log.logError(f"{str(err)}")
        return False

    if r.status_code != 206:
        firstByte = 0
    contentLength = r.headers.get("content-length")
    fileSize = firstByte + int(contentLength) if contentLength else None

    try:
        with r, open(tmpFile, "ab" if firstByte else "wb") as f:
            with tqdm(
                total=fileSize,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=log.label(desc),
                initial=firstByte,
                ascii=BAR_CHARS,
                bar_format=log.barFormat(GET),
                leave=False,
            ) as pbar:
                for chunk in r.iter_content(32 * 1024):
                    f.write(chunk)
                    pbar.update(len(chunk))
    except (requests.exceptions.RequestException, OSError) as err:
        log.logError(f"{err}: {desc}, try to run install again")
        return False

    log.logResult(pbar, GET, desc)
    try:
        size = os.path.getsize(tmpFile)
        if fileSize is not None and size != fileSize:
            if size > fileSize:
                os.remove(tmpFile)
            raise ValueError("incomplete download")
    except (OSError, ValueError) as err:
        log.logError(f"{err}: {desc}, try to run install again")
        return False

    os.replace(tmpFile, fileName)
    os.utime(fileName, (time.time(), mtime.timestamp()))

    if dscFile:
        sigFile = os.path.splitext(dscFile)[0] + SIG_EXTENSION
        if os.path.isfile(dscFile):
            shutil.copy2(dscFile, config.downloadDir)
        if os.path.isfile(sigFile):
            shutil.copy2(sigFile, config.downloadDir)

    if os.path.basename(fileName) == config.dbFileName:
        lastUpdate = os.path.getmtime(config.syncPath(config.dbFileName))
        timestamp_dbFileName = config.syncPath(CORE_DB_TIMESTAMP)
        with open(timestamp_dbFileName, 'w', encoding=FILE_ENCODING) as file:
            file.write(f"{lastUpdate}")

    return True


def tarMode(fileName):
    if fileName.endswith((TARGZ_EXTENSION, DB_EXTENSION)):
        return "r:gz"
    if fileName.endswith(TAR_EXTENSION):
        return "r:"
    return "r"


def setExtractionFilter(tar):
    tar.extraction_filter = getattr(
        tar, "data_filter", (lambda member, path: member)
    )


def progressBar(items, status="", text="", total=None):
    return tqdm(
        items,
        total=total,
        ascii=BAR_CHARS,
        bar_format=log.barFormat(status),
        desc=log.label(text),
        leave=False,
    )


def setDesc(progress, status, text):
    progress.bar_format = log.barFormat(status)
    progress.set_description_str(log.label(text))


def extractFailed(pkgName, err, status=INSTALL):
    log.log(status, f"{pkgName} ({err})", ok=False)
    log.logError(f"{pkgName} ({err})")


def unlinkIfRegularFile(dst):
    if not os.path.islink(dst) and os.path.isfile(dst):
        os.unlink(dst)


def unzip(fileName, path, pkg, status=INSTALL):
    pkgName, installScript = getPackageName(pkg)

    fileCount = 0
    if not os.path.isfile(fileName):
        log.logError(f"No such file or directory: {fileName}")
        return fileCount
    try:
        with ZipFile(fileName, "r") as zipper:
            members = zipper.infolist()
            fileTotal = sum(1 for m in members if not m.is_dir())
            progress = progressBar(None, status, pkgName, total=fileTotal)
            for member in members:
                if not member.is_dir():
                    unlinkIfRegularFile(os.path.join(path, member.filename))
                    fileCount += 1
                    progress.update(1)
                if installScript and member.filename == installScript:
                    continue
                zipper.extract(member, path=path)

            log.logResult(progress, status, pkgName)
    except IOError as err:
        extractFailed(pkgName, err, status)

    return fileCount


def getPackageName(pkg):
    installScript = None
    if hasattr(pkg, "name"):
        pkgName = pkg.name + " " + pkg.version
        installScript = pkg.installScript
    else:
        pkgName = pkg

    return (pkgName, installScript)


def runCustomInstallScript(self, fileName, pkg):
    _, installScript = getPackageName(pkg)

    if not os.path.isfile(fileName):
        log.logError(f"No such file or directory: {fileName}")

        return False, None

    mode = tarMode(fileName)

    extractPath = os.path.join(self.config.baseDir, CUSTOM_INSTALL_PATH)
    try:
        with tarfile.open(fileName, mode) as tf:
            setExtractionFilter(tf)
            scriptMember = tf.getmember(installScript)
            checkMember(scriptMember, extractPath)
            tf.extract(member=scriptMember, path=extractPath)
    except KeyError:
        return False, "installScript"

    existFileName = custominstall.checkFilesExist(self.config, pkg)

    if existFileName:
        os.remove(os.path.join(extractPath, installScript))
        shutil.rmtree(os.path.join(extractPath, "__pycache__"), ignore_errors=True)

    if not os.listdir(extractPath):
        shutil.rmtree(extractPath)

    return True, existFileName


def checkMember(member, targetDir):
    """A member of a package archive stays inside targetDir and gets no setuid, setgid or
    sticky bit. tarfile.extract() writes to os.path.join(targetDir, name), so an absolute
    name or one with '..' would leave targetDir (for a hard link: its target)."""
    base = os.path.abspath(targetDir)
    names = [member.name] + ([member.linkname] if member.islnk() else [])
    for name in names:
        finalPath = os.path.abspath(os.path.join(targetDir, name))
        if finalPath != base and not finalPath.startswith(base + os.sep):
            raise IOError(f"refusing to extract outside target dir: {name}")
    member.mode &= 0o777


def extractMemberAtomic(tar, member, targetDir):
    base = os.path.abspath(targetDir)
    finalPath = os.path.abspath(os.path.join(targetDir, member.name))

    if finalPath != base and not finalPath.startswith(base + os.sep):
        raise IOError(f"refusing to extract outside target dir: {member.name}")

    checkMember(member, targetDir)

    if member.isdir():
        os.makedirs(finalPath, exist_ok=True)
        try:
            os.chmod(finalPath, member.mode)
        except OSError:
            pass
        return

    parent = os.path.dirname(finalPath)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    if member.issym():
        tmp = finalPath + ".gsm_new"
        if os.path.lexists(tmp):
            os.remove(tmp)
        os.symlink(member.linkname, tmp)
        os.replace(tmp, finalPath)
        return

    if member.islnk():
        source = os.path.abspath(os.path.join(targetDir, member.linkname))
        tmp = finalPath + ".gsm_new"
        if os.path.lexists(tmp):
            os.remove(tmp)
        os.link(source, tmp)
        os.replace(tmp, finalPath)
        return

    if not member.isfile():
        return

    src = tar.extractfile(member)
    if src is None:
        return

    fd, tmp = tempfile.mkstemp(
        prefix=os.path.basename(finalPath) + ".",
        suffix=".gsm_new",
        dir=parent or ".",
    )
    try:
        with os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(tmp, member.mode)
        os.utime(tmp, (member.mtime, member.mtime))
        os.replace(tmp, finalPath)
    finally:
        src.close()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def untarGsm(config, fileName, pkg, status=INSTALL):
    targetDir = "."
    strip_components = 1
    installFiles = []
    holdFiles = []
    i = 0
    pkgName, _ = getPackageName(pkg)
    fileCount = 0

    try:
        with tarfile.open(fileName, "r") as tar:
            setExtractionFilter(tar)
            members = tar.getmembers()
            fileTotal = sum(1 for m in members if m.isfile())
            progress = progressBar(None, status, pkgName, total=fileTotal)
            for member in members:
                i = i + 1
                components = member.name.split("/")
                member.name = "/".join(components[strip_components:])
                if not member.name:
                    continue
                installFiles.append(member.name)
                if member.isfile():
                    fileCount += 1
                    progress.update(1)
                extractMemberAtomic(tar, member, targetDir)

            log.logResult(progress, status, pkgName)
        config.makeMigration(False)
        return True, fileCount, installFiles, holdFiles
    except (IOError, OSError) as err:
        extractFailed(pkgName, err, status)

    return 0, None, None, None


def untar(config, fileName, path, pkg, localCache, status=INSTALL):

    installFiles = []
    holdFiles = []

    pkgName, installScript = getPackageName(pkg)

    fileCount = 0
    if not os.path.isfile(fileName):
        log.logError(f"No such file or directory: {fileName}")
        return fileCount, None, None
    mode = tarMode(fileName)

    try:
        with tarfile.open(fileName, mode) as tar:
            setExtractionFilter(tar)
            members = tar.getmembers()
            fileTotal = sum(1 for m in members if m.isfile())
            progress = progressBar(None, status, pkgName, total=fileTotal)

            if fileName.endswith(DB_EXTENSION):
                for member in members:
                    installFiles.append(member.name)
                    if member.isfile():
                        fileCount += 1
                        progress.update(1)
                    checkMember(member, path)
                    tar.extract(member, path=path)

                log.logResult(progress, status, pkgName)

                return fileCount, None, None
            i = 0
            prefix = SC
            if prefix == config.rootDir:
                prefix = None
            for member in members:
                name = os.path.normpath(member.name)
                if name == os.curdir:
                    continue
                member.name = name
                installFiles.append(member.name)
                i = i + 1
                if prefix:
                    if member.name == prefix:
                        member.name = config.rootDir
                    elif member.name.startswith(prefix + os.sep):
                        member.name = config.rootDir + member.name[len(prefix):]

                if member.isfile() and not localCache.isHold(
                    os.path.join(path, member.name), True
                ):
                    unlinkIfRegularFile(os.path.join(path, member.name))
                    fileCount += 1
                    progress.update(1)

                if installScript and member.name == installScript:
                    continue

                if not localCache.isHold(os.path.join(path, member.name), True):
                    checkMember(member, path)
                    tar.extract(member, path=path)
                else:
                    holdFiles.append(os.path.join(path, member.name))

            log.logResult(progress, status, pkgName)

            return fileCount, installFiles, holdFiles
    except IOError as err:
        extractFailed(pkgName, err, status)

    return 0, None, None


def isOnSameFileSystem(fileName, path):
    try:
        return (
            os.lstat(fileName).st_dev
            == os.lstat(os.path.split(path)[0]).st_dev
        )
    except FileNotFoundError:
        pass

    return False


def install(config, fileName, path, pkg, localCache, status=INSTALL):
    pkgName, _ = getPackageName(pkg)
    try:
        if fileName.endswith((GRD_EXTENSION, MBTILES_EXTENSION)):
            if isOnSameFileSystem(fileName, path):
                progress = progressBar(range(0, 1), status, pkgName)
                for _ in progress:
                    os.replace(fileName, path)
                    if os.path.islink(fileName):
                        os.unlink(fileName)
                    os.symlink(path, fileName)

                log.logResult(progress, status, pkgName)
            else:
                copy(config, fileName, path, pkgName)
                os.unlink(fileName)
                os.symlink(path, fileName)

            return True, 1, None, None

        if fileName.endswith(ZIP_EXTENSION):
            return True, unzip(fileName, path, pkg, status), None, None

        fileCount, installFiles, holdFiles = untar(
            config, fileName, path, pkg, localCache, status
        )
        return True, fileCount, installFiles, holdFiles

    except Exception as ex:
        log.log(status, f"{pkgName} ({ex})", ok=False)
        log.logError(f"Failed to extract {pkgName} ({ex})")

    return False, 0, None, None


def checkFilesExist(tarFile, installPath):
    try:
        with tarfile.open(tarFile, "r") as tar:
            for member in tar.getmembers():
                if os.path.isfile(os.path.join(installPath, member.name)):
                    return member.name
    except tarfile.ReadError:
        pass

    return None


def getLicenseTimeDelta(cert):
    updatesUntilStr = findUpdatesUntil(cert.issuer) or "9999-12-31"

    notValidAfterStr = cert.not_valid_after.strftime(DEFAULT_TIME_FORMAT)
    todayStr = date.today().strftime(DEFAULT_TIME_FORMAT)

    notValidAfter = datetime.strptime(notValidAfterStr, DEFAULT_TIME_FORMAT)
    updatesUntil = datetime.strptime(updatesUntilStr, DEFAULT_TIME_FORMAT)
    today = datetime.strptime(todayStr, DEFAULT_TIME_FORMAT)

    deltaUpdatesUntil = int((updatesUntil - today).days)
    deltaNotValidAfter = int((notValidAfter - today).days)

    return (
        deltaUpdatesUntil,
        deltaNotValidAfter,
        updatesUntilStr,
        notValidAfterStr,
    )


def licenseInfoDays(config):
    """Days before the end of a license that it is mentioned; 0: not at all (an expired license is)."""
    value = config.licenseInfoDays
    return LICENSE_INFO_DAYS if value in (None, "") else int(value)


def prettyFormatLicenseInfo(cert, licenseInfoDays):
    licenseInfoDays = int(licenseInfoDays)
    (
        deltaUpdatesUntil,
        deltaNotValidAfter,
        updatesUntil,
        notValidAfter,
    ) = getLicenseTimeDelta(cert)

    if licenseInfoDays <= deltaUpdatesUntil:
        deltaUpdatesUntil = None

    if licenseInfoDays <= deltaNotValidAfter:
        deltaNotValidAfter = None

    def helper(days, infoType, infoDate):

        if infoType == "valid":
            if days <= 0:
                return f"License expired on {infoDate}"
            return f"License expires in {days} days ({infoDate})"
        if days <= 0:
            return f"Update period expired on {infoDate}"

        return f"Update period ends in {days} days ({infoDate})"

    # 0 days (expires today) is a value to show; None is "far away, say nothing"
    if deltaUpdatesUntil is not None and deltaNotValidAfter is not None:
        if deltaUpdatesUntil == deltaNotValidAfter:
            licenseInfo = (
                f"[{helper(deltaNotValidAfter, 'valid', notValidAfter)}]"
            )
        else:
            licenseInfo = (
                f"[{helper(deltaNotValidAfter,'valid', notValidAfter)}, "
                f"{helper(deltaUpdatesUntil, 'license', updatesUntil)}]"
            )
    elif deltaUpdatesUntil is not None:
        licenseInfo = f"[{helper(deltaUpdatesUntil,'license', updatesUntil)}]"
    elif deltaNotValidAfter is not None:
        licenseInfo = (
            f"[{helper(deltaNotValidAfter,'valid', notValidAfter )}]"
        )
    else:
        licenseInfo = ""

    return licenseInfo


def getDownloadDirectoryURL(pkg, config):
    base = publicOrBaseURL(pkg, config)
    if pkg.type != PT.CONFIG and pkg.filePath:
        path = os.path.join(os.path.dirname(pkg.filePath), pkg.name)
    else:
        path = pkg.name
    return urljoin(base, path)


def splitVersionString(version):
    if version == "VERSION":
        version = "9.9.9"
    return tuple(map(int, (version.split("."))))


@contextmanager
def temporaryValue(obj, attr, newValue):
    originalValue = getattr(obj, attr)
    setattr(obj, attr, newValue)
    try:
        yield
    finally:
        setattr(obj, attr, originalValue)

def backupPath(config):
    return os.path.join(
        os.path.dirname(config.localDir), RESTORE_DIR,
        config.gsmBinary + TARGZ_EXTENSION,
    )


def backupDrop(config):
    try:
        os.remove(backupPath(config))
    except FileNotFoundError:
        pass
    except OSError as err:
        log.logWarning(f"Could not remove {backupPath(config)}: {err}")


def backupStore(config):
    backupDir = os.path.dirname(config.localDir)
    storeDirFile = backupPath(config)
    tmpFile = storeDirFile + ".tmp"

    filesToArchive = []
    if os.path.isfile(config.fileName):
        filesToArchive.append((config.fileName, GSM_CONFIG_FILE))

    if os.path.isdir(config.localDir):
        for dirpath, _, filenames in os.walk(config.localDir):
            for filename in filenames:
                fileToAdd = os.path.join(dirpath, filename)
                filesToArchive.append(
                    (fileToAdd, os.path.relpath(fileToAdd, start=backupDir))
                )

    backupDrop(config)

    if not filesToArchive:
        log.logError(f"No files found in directory: {backupDir}")
        return (False, "")

    try:
        os.makedirs(os.path.dirname(storeDirFile), exist_ok=True)
        fd = os.open(tmpFile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as fobj, tarfile.open(fileobj=fobj, mode="w:gz") as tar:
            progress = progressBar(filesToArchive)
            setDesc(progress, BACKUP, config.gsmBinary)
            for file, arcname in progress:
                tar.add(file, arcname=arcname)

            log.logResult(progress, BACKUP, config.gsmBinary)
        os.replace(tmpFile, storeDirFile)
    except Exception as err:
        log.log(BACKUP, f"{config.gsmBinary} ({err})", ok=False)
        log.logError(f"{config.gsmBinary} ({err})")
        try:
            os.remove(tmpFile)
        except OSError:
            pass
        return (False, "")

    return (True, storeDirFile)


def backupRestore(config):
    backupDir = os.path.dirname(config.localDir)
    restoreDirFile = backupPath(config)

    if not os.path.isfile(restoreDirFile):
        log.logError(f"No such file: {restoreDirFile}")
        return (False, "")

    try:
        with tarfile.open(restoreDirFile, "r:gz") as tar:
            members = tar.getmembers()

            for item in Path(config.localDir).iterdir():
                if item.is_dir() and item.name != GSM and not item.is_symlink():
                    shutil.rmtree(item)

            progress = progressBar(members)
            setDesc(progress, RESTORE, config.gsmBinary)
            for member in progress:
                if member.name.startswith('/') or '..' in member.name:
                    continue

                if member.name == GSM_CONFIG_FILE:
                    memberPath = config.fileName
                else:
                    memberPath = os.path.join(backupDir, member.name)

                if member.isreg():
                    os.makedirs(os.path.dirname(memberPath) or ".", exist_ok=True)

                    with tar.extractfile(member) as fileSrc, open(memberPath, 'wb') as fileDest:
                        fileDest.write(fileSrc.read())
                    os.chmod(memberPath, member.mode & 0o777)

                elif member.isdir():
                    os.makedirs(memberPath, exist_ok=True)

            log.logResult(progress, RESTORE, config.gsmBinary)
    except Exception as err:
        log.log(RESTORE, f"{config.gsmBinary} ({err})", ok=False)
        log.logError(f"{config.gsmBinary} ({err})")
        return (False, restoreDirFile)

    return (True, restoreDirFile)


def requireOneSubArg(args, cmdName, valid, oneArg=True):
    optionText = f"Command '{GSM} {cmdName}' requires exactly one option: {', '.join(valid)}"
    if oneArg:
        if not args or len(args) != 1:
            print(optionText)
            return None
    else:
        if not args or len(args) < 1:
            print(optionText)
            return None

    arg = args[0]
    if arg not in valid:
        print(f"Invalid argument '{arg}'. Valid argument are: {', '.join(valid)}")
        return None
    return arg

def requireNoArgs(args, cmdName):
    if args:
        print(f"Command '{GSM} {cmdName}' takes no arguments")
        return False
    return True

def requireOneArg(args, cmdName):
    if len(args) == 2:
        return True

    print(f"Command '{GSM} {cmdName}' requires a name")

    return False

def getPassMasked(prompt='Password: ', mask='*', default=None):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    if not sys.stdin.isatty():
        line = sys.stdin.readline()
        if not line:
            noInputAvailable()
        sys.stdout.write('\n')
        value = line.rstrip('\r\n')
        if value == '' and default is not None:
            return default
        return value
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    password_chars = []
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if not ch or ch in ('\r', '\n'):
                break
            if ch == '\x03':
                raise KeyboardInterrupt
            if ch in ('\x7f', '\b'):
                if password_chars:
                    password_chars.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                continue
            if ord(ch) < 32:
                continue
            password_chars.append(ch)
            sys.stdout.write(mask)
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if not ch:
        noInputAvailable()
    sys.stdout.write('\n')
    sys.stdout.flush()
    value = ''.join(password_chars)
    if value == '' and default is not None:
        return default
    return value

def getInputPW(question, default=None):
    prompt = f"{question} [{'********' if default else ''}]: "
    return getPassMasked(prompt, mask='*', default=default)
