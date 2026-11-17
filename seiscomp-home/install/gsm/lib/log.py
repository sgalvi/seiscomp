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

import functools
import inspect
import logging
import os
import re
import sys
from tqdm import tqdm


from .const import (
    BAR_WIDTH,
    FAILED,
    INFO,
    MARK_WIDTH,
    OK,
    SKIP,
    blue,
    eraseEOL,
    gray,
    white,
    percent,
    reset,
)


def statusField(status, ok=None):
    if ok is None:
        marker = "   "
    else:
        marker = OK if ok else FAILED

    return f"{status: <{MARK_WIDTH}} {marker}"


def getLogPrefix(status, ok=None):
    return f"{statusField(status, ok)} "


def label(text):
    return f"{blue}{text}{reset}"


def counter(n, total, unitScale=False):
    if unitScale:
        n = tqdm.format_sizeof(n, divisor=1024)
        if total is not None:
            total = tqdm.format_sizeof(total, divisor=1024)

    if total is None:
        total = "?"

    return f"{gray}{n}/{total}{reset}"


def barFormat(status, ok=None):
    return (
        getLogPrefix(status, ok)
        + f"{percent}["
        + "{percentage:3.0f}%"
        + f"]{reset}"
        + "|{bar:"
        + str(BAR_WIDTH)
        + "}"
        + reset
        + "| "
        + "{desc}  "
        + f"{white}" + "{n_fmt}/{total_fmt}" + reset
        + f"  {gray}" + "{elapsed}<{remaining}" + reset
        + f"  {blue}" + "{rate_fmt}" + reset
    )


def resetTerminal():
    if not reset:
        return

    sys.stdout.write(f"\r{reset}{eraseEOL}")
    sys.stdout.flush()


def log(logType, msg, ok=None, file=None):
    tqdm.write(f"{getLogPrefix(logType, ok)}{msg}{reset}{eraseEOL}", file=file)


def logResult(progress, status, text="", n=None, total=None, ok=True):
    state = progress.format_dict
    if n is None:
        n = state["n"]
    if total is None:
        total = state["total"]

    parts = (
        label(text) if text else "",
        counter(n, total, state["unit_scale"]),
        f"{gray}{tqdm.format_interval(state['elapsed'])}{reset}",
    )
    log(status, "  ".join(part for part in parts if part), ok)


history = logging.getLogger("gsm")
history.addHandler(logging.NullHandler())
history.propagate = False

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def addFileHandler(logger, path, formatter):
    path = os.path.abspath(path)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == path:
            return handler

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler


def setupLogFile(path, dateFormat=None):
    handler = addFileHandler(
        history, path, logging.Formatter("%(asctime)s - %(message)s", dateFormat)
    )
    history.setLevel(logging.INFO)
    return handler


def record(level, msg):
    text = " ".join(_ANSI.sub("", str(msg)).split())
    history.log(level, "%s: %s", logging.getLevelName(level), text)


def logError(msg):
    log("ERROR", msg, file=sys.stderr)
    record(logging.ERROR, msg)


def logFailed(msg):
    log("FAILED", msg, file=sys.stderr)
    record(logging.ERROR, msg)


def logSkip(msg):
    log(SKIP, msg)


def logWarning(msg):
    log("WARNING", msg, file=sys.stderr)
    record(logging.WARNING, msg)


def logInfo(msg):
    log(INFO, msg)


_debugLog = logging.getLogger("gsm.debug")


def setupDebug(config):
    if config.debug:
        _debugLog.setLevel(logging.DEBUG)


def trace(func):
    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _debugLog.isEnabledFor(logging.DEBUG):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            params = bound.arguments
            params.pop("self", None)
            arglist = ", ".join(f"{k}={v!r}" for k, v in params.items())
            _debugLog.debug("DEBUG: \u2192 %s(%s)", func.__qualname__, arglist)

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            _debugLog.debug("DEBUG: \u2717 %s raised %r", func.__qualname__, e)
            raise

        if (_debugLog.isEnabledFor(logging.DEBUG)
                and result is not None
                and not isinstance(result, bool)):
            _debugLog.debug("DEBUG: \u2190 %s = %r", func.__qualname__, result)

        return result

    return wrapper
