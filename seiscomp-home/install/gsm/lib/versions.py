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

"""Comparing package versions, without the package 'packaging'."""

import re

# A version of gempa is numbers and dots: "7.4.0", "2026.272", "1.3". Everything else ("nightly")
# is text. gsm does not know suffixes like rc, dev or post (gempa has none: of the 226 versions in
# the repository, 225 are numbers and dots, and one is "nightly"): they are text as well.
_NUMBERS = re.compile(r"[0-9]+(?:\.[0-9]+)*")


def _numbers(version):
    """The numbers of a version made of numbers and dots, without the zeros at its end ("7.4" and
    "7.4.0" are the same version); None for anything else."""
    text = str(version).strip()
    if not _NUMBERS.fullmatch(text):
        return None
    try:
        numbers = [int(part) for part in text.split(".")]
    except ValueError:  # a number of thousands of digits: Python does not read it
        return None
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers.pop()
    return tuple(numbers)


def isOlder(version, reference):
    """True if 'version' is older than 'reference'.

    Numbers and dots are compared as numbers ("7.9" is older than "7.10"). Anything else (e.g.
    "nightly") is compared as text, like gsm always did.
    """
    before, after = _numbers(version), _numbers(reference)
    if before is None or after is None:
        return str(version) < str(reference)
    return before < after


def sameVersion(version, reference):
    """True if both strings denote the same version ("2026.5" == "2026.05", "7.4" == "7.4.0")."""
    before, after = _numbers(version), _numbers(reference)
    if before is None or after is None:
        return version == reference
    return before == after
