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

import re
import shlex
from typing import Union

from lib import log
from lib.const import FILE_ENCODING

Symbols = dict[str, Union[str, list[str]]]

_ASSIGNMENT_RE = re.compile(r"([A-Za-z_]\w*)=(.*)$")


def splitTokens(text: str) -> list[str]:
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def parseValue(rhs: str, fileName: str, name: str) -> Union[str, list[str]]:
    if rhs.startswith("("):
        inner = rhs[1:]
        if inner.endswith(")"):
            inner = inner[:-1]
        else:
            log.logWarning(
                f"{fileName}: unterminated array for '{name}', parsing best-effort"
            )
        return splitTokens(inner)

    tokens = splitTokens(rhs)
    return tokens[0] if tokens else ""


def readPkgsDescFile(fileName: str) -> Symbols:
    symbols: Symbols = {}
    with open(fileName, "r", encoding=FILE_ENCODING) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = _ASSIGNMENT_RE.match(line)
            if not match:
                continue
            name, rhs = match.group(1), match.group(2).strip()
            try:
                symbols[name] = parseValue(rhs, fileName, name)
            except ValueError as exc:
                log.logWarning(f"{fileName}: cannot parse '{name}' ({exc}), skipping")
    return symbols
