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

"""Read a license certificate: when it expires and who issued it.

gsm needs two things of a license certificate (see utils.readCertificateFile): the date it expires, and the
text of its issuer, which holds 'updatesUntil=<date>'. It does not check a signature or a chain.
That is a small part of X.509, so it is read here with the standard library only, and not with a
package that has to be compiled for every system and every Python version. gsm then needs no
such package: a computer without a network can run it from the files of the gsm directory.

A certificate is a DER structure in a PEM envelope:

    Certificate  ::= SEQUENCE { tbsCertificate, signatureAlgorithm, signature }
    tbsCertificate ::= SEQUENCE { [0] version OPTIONAL, serialNumber, signature,
                                  issuer, validity, subject, ... }
    validity     ::= SEQUENCE { notBefore, notAfter }
    issuer       ::= SEQUENCE OF SET OF SEQUENCE { type OID, value string }

This module only returns data (or raises ValueError); utils.py decides what it means.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Tuple

SEQUENCE, SET, INTEGER, OID, VERSION = 0x30, 0x31, 0x02, 0x06, 0xA0
UTC_TIME, GENERALIZED_TIME = 0x17, 0x18

# The label is what cryptography took before: CERTIFICATE and X509 CERTIFICATE, but not
# TRUSTED CERTIFICATE (the file of OpenSSL with trust settings behind it).
_PEM = re.compile(
    rb"-----BEGIN (?:X509 )?CERTIFICATE-----(.*?)-----END (?:X509 )?CERTIFICATE-----", re.S)

# tag of a string in DER -> how its bytes are read
_CODECS = {
    0x0C: "utf-8",       # UTF8String
    0x13: "latin-1",     # PrintableString
    0x16: "latin-1",     # IA5String
    0x14: "latin-1",     # TeletexString (T61String)
    0x12: "latin-1",     # NumericString
    0x1A: "latin-1",     # VisibleString
    0x1E: "utf-16-be",   # BMPString
    0x1C: "utf-32-be",   # UniversalString
}


@dataclass(frozen=True)
class Certificate:
    notAfter: datetime  # UTC
    # The values of the attributes of the issuer, in the order of the certificate: without the
    # names of the attributes, a comma between the parts, '+' between the attributes of one part.
    # The first 'updatesUntil=' in it counts. (With two of them in one issuer, which one
    # cryptography gave depended on its version; a certificate of gempa has one.)
    issuer: str


def readCertificate(data: bytes) -> Certificate:
    """The first certificate in data (PEM). Raises ValueError if there is none, or it is broken."""
    der = _pemToDer(data)
    tag, start, end = _element(der, 0)
    if tag != SEQUENCE:
        raise ValueError("not a certificate (no SEQUENCE)")
    if end != len(der):
        raise ValueError("data behind the certificate")
    outer = list(_children(der, start, end))
    if not outer or outer[0][0] != SEQUENCE:
        raise ValueError("not a certificate (no tbsCertificate)")
    fields = list(_children(der, outer[0][1], outer[0][2]))
    if fields and fields[0][0] == VERSION:  # a certificate of version 1 has no version field
        fields = fields[1:]
    if len(fields) < 4:
        raise ValueError("tbsCertificate is too short")
    serial, algorithm, issuer, validity = fields[:4]
    if (serial[0], algorithm[0], issuer[0], validity[0]) != (INTEGER, SEQUENCE, SEQUENCE, SEQUENCE):
        raise ValueError("tbsCertificate: unexpected fields")
    times = list(_children(der, validity[1], validity[2]))
    if len(times) != 2:
        raise ValueError("validity is not two times")
    notAfter = _time(times[1][0], der[times[1][1]:times[1][2]])
    return Certificate(notAfter, _name(der, issuer[1], issuer[2]))


def _pemToDer(data: bytes) -> bytes:
    match = _PEM.search(data)
    if not match:
        raise ValueError("no PEM certificate found")
    try:
        return base64.b64decode(re.sub(rb"\s+", b"", match.group(1)), validate=True)
    except ValueError as err:
        raise ValueError(f"bad base64 ({err})") from err


def _element(data: bytes, pos: int) -> Tuple[int, int, int]:
    """(tag, start, end) of the element at pos: its content is data[start:end]."""
    if pos + 2 > len(data):
        raise ValueError("truncated")
    tag = data[pos]
    if tag & 0x1F == 0x1F:
        raise ValueError("tag number too large")
    first = data[pos + 1]
    pos += 2
    if first < 0x80:
        length = first
    else:  # the length is in the next 'first & 0x7f' bytes
        count = first & 0x7F
        if count == 0 or count > 4 or pos + count > len(data):
            raise ValueError("bad length")
        length = int.from_bytes(data[pos:pos + count], "big")
        pos += count
    if pos + length > len(data):
        raise ValueError("truncated")
    return tag, pos, pos + length


def _children(data: bytes, start: int, end: int) -> Iterator[Tuple[int, int, int]]:
    pos = start
    while pos < end:
        tag, childStart, childEnd = _element(data, pos)
        if childEnd > end:
            raise ValueError("an element runs out of its parent")
        yield tag, childStart, childEnd
        pos = childEnd


def _time(tag: int, raw: bytes) -> datetime:
    text = raw.decode("ascii", errors="replace")
    if tag == UTC_TIME:
        match = re.fullmatch(r"(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)Z", text)
        if not match:
            raise ValueError("bad UTCTime")
        year = int(match.group(1))
        year += 1900 if year >= 50 else 2000  # RFC 5280: 50 to 99 are 1950 to 1999
    elif tag == GENERALIZED_TIME:
        match = re.fullmatch(r"(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)Z", text)
        if not match:
            raise ValueError("bad GeneralizedTime")
        year = int(match.group(1))
    else:
        raise ValueError(f"not a time (tag {tag:#x})")
    # the seconds are not optional (RFC 5280, and cryptography did not take a time without them)
    month, day, hour, minute, second = (int(match.group(i)) for i in range(2, 7))
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _name(data: bytes, start: int, end: int) -> str:
    parts = []
    for tag, partStart, partEnd in _children(data, start, end):
        if tag != SET:
            raise ValueError("bad name (no SET)")
        values = []
        for attributeTag, attributeStart, attributeEnd in _children(data, partStart, partEnd):
            pair = list(_children(data, attributeStart, attributeEnd))
            if attributeTag != SEQUENCE or len(pair) != 2 or pair[0][0] != OID:
                raise ValueError("bad name (attribute)")
            valueTag, valueStart, valueEnd = pair[1]
            raw = data[valueStart:valueEnd]
            if valueTag in _CODECS:
                values.append(raw.decode(_CODECS[valueTag], errors="replace"))
            else:  # not a string: kept as it is, so that nothing is lost
                values.append("#" + raw.hex())
        parts.append("+".join(values))
    return ",".join(parts)
