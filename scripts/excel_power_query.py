"""Read the saved Power Query parts of a bounded OOXML workbook; never edit them."""

import base64
from io import BytesIO
import re
import struct
from xml.etree import ElementTree as ET
from zipfile import ZipFile


class QueryBlocked(Exception):
    pass


MASHUP = '{http://schemas.microsoft.com/DataMashup}DataMashup'
SECTION = 'Formulas/Section1.m'
IDENTIFIER = r'(?:[A-Za-z_][A-Za-z0-9_]*|#"[A-Za-z_][A-Za-z0-9_ ]*")'
MEMBER = re.compile(r'shared\s+(' + IDENTIFIER + r')\s*=')
TOKEN = re.compile(r'//[^\r\n]*|/\*[\s\S]*?\*/|#?"(?:[^"]|"")*"|[;"/]|[^;"/#]+|#')
MODEL = re.compile(r'(?i)(?:^|/)model/|(?:^|/)model\.bin$')
M_SOURCE = 'editable-power-query-m'


def check_expression(expression, credential):
    if not isinstance(expression, str) or not expression.strip() or '\0' in expression:
        raise QueryBlocked('Expected a nonempty M expression.')
    if credential.search(expression):
        raise QueryBlocked('Publication blocked: possible credential in M.')
    for match in TOKEN.finditer(expression):
        token = match[0]
        if token == '"' or (token.startswith('"') and token != '""'):
            raise QueryBlocked('Publication blocked: unreviewable inline text in M.')
        if token.startswith(('#"', '//', '/*')) and not re.fullmatch(IDENTIFIER, token):
            raise QueryBlocked('Publication blocked: unreviewable comment or quoted identifier in M.')
        if token == ';':
            raise QueryBlocked('Expected one M expression, not a section document.')


def read_section(text, credential):
    header = re.match(r'\s*section\s+Section1\s*;', text)
    if header is None:
        raise QueryBlocked('Unsupported Power Query section.')
    start = header.end()
    queries: dict[str, str] = {}
    skeleton = [text[:start]]
    for match in TOKEN.finditer(text, start):
        if match[0] != ';':
            continue
        statement = text[start:match.start()]
        member = MEMBER.match(statement, len(statement) - len(statement.lstrip()))
        if member is None:
            raise QueryBlocked('Unsupported Power Query member declaration.')
        identifier = member[1]
        name = identifier[2:-1] if identifier.startswith('#"') else identifier
        if name.casefold() in {key.casefold() for key in queries} or credential.search(name):
            raise QueryBlocked('Duplicate or unsafe Power Query name.')
        raw = statement[member.end():]
        expression = raw.strip()
        check_expression(expression, credential)
        queries[name] = expression
        skeleton.append(statement[:member.end()] + raw[len(raw.rstrip()):] + ';')
        start = match.end()
    if not queries or text[start:].strip():
        raise QueryBlocked('Unsupported or incomplete Power Query section.')
    return queries, ''.join(skeleton) + text[start:]


def read_mashup(book, credential, limit):
    candidate = None
    remaining = limit
    for name in book.namelist():
        if not re.fullmatch(r'customXml/item\d*\.xml', name):
            continue
        remaining -= book.getinfo(name).file_size
        if remaining < 0:
            raise QueryBlocked('Custom XML exceeds the supported limit.')
        raw = book.read(name)
        encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        text = raw.decode(encoding)
        if '\0' in text or '<!DOCTYPE' in text or '<!ENTITY' in text:
            raise QueryBlocked('Unsupported custom XML.')
        element = ET.fromstring(text)
        if element.tag == MASHUP:
            if candidate is not None:
                raise QueryBlocked('Expected exactly one saved Power Query mashup.')
            candidate = (name, element)
    if candidate is None:
        return None
    name, element = candidate
    if len(element) or not element.text or set(element.attrib) - {'sqmid'}:
        raise QueryBlocked('Unsupported Power Query mashup envelope.')
    payload = base64.b64decode(''.join(element.text.split()), validate=True)
    offset = 4
    chunks = []
    for _ in range(4):
        if offset + 4 > len(payload):
            raise QueryBlocked('Incomplete Power Query mashup.')
        size, = struct.unpack_from('<I', payload, offset)
        offset += 4
        chunks.append(payload[offset:offset + size])
        offset += size
    if payload[:4] != b'\0' * 4 or offset != len(payload):
        raise QueryBlocked('Unsupported Power Query mashup format.')
    with ZipFile(BytesIO(chunks[0])) as package:
        parts = package.infolist()
        if (len({part.filename for part in parts}) != len(parts)
                or sum(part.file_size for part in parts) > limit
                or {part.filename for part in parts} - {SECTION, 'Config/Package.xml', '[Content_Types].xml'}):
            raise QueryBlocked('Unsupported embedded Power Query package.')
        queries, skeleton = read_section(package.read(SECTION).decode('utf-8-sig'), credential)
        config = {part.filename: package.read(part) for part in parts if part.filename != SECTION}
    # The user-bound permission signature covers package bytes and changes when M changes.
    return name, queries, (skeleton, config, chunks[1], chunks[2])


def connection_query(connection, command, names):
    parts = {}
    for pair in connection.strip(';').split(';'):
        key, sep, value = pair.partition('=')
        key = key.strip().casefold()
        if not sep or key in parts:
            return None
        parts[key] = value
    if (parts.get('provider', '').casefold() != 'microsoft.mashup.oledb.1'
            or parts.get('data source') != '$Workbook$'
            or set(parts) - {'provider', 'data source', 'location', 'extended properties'}
            or parts.get('extended properties') not in (None, '', '""')):
        return None
    location = parts.get('location')
    return next((name for name in names if location in (name, '"' + name + '"')
                 and command == f'SELECT * FROM [{name}]'), None)
