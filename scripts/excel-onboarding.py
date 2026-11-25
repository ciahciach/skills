"""Prepare or export one workbook and explicitly accept its first synchronization point.

From an existing Git worktree, use a dedicated private local directory outside
Git, one per workbook, on a filesystem supporting read-only files. On Windows
its ACL may grant access only to the operator, SYSTEM and Administrators. On
POSIX use a directory owned by the operator with mode 0700. Give the script's
full path if it lives outside your worktree.

For a new XLSX, use the shared Excel entry point to select a Windows desktop
route for creating and saving a blank XLSX. Confirm explicit authorization and
qualification for the backend implementation/version, operation and profile.
If either is missing, stop with the reason; do not fall back to another backend.
Save to a new, Git-ignored .xlsx path and independently reopen/read back the
saved file through the qualified route. Then export with --desktop-verified:

  python -X utf8 <script> export book.xlsx baseline --desktop-verified <workbook-sha256> --store <private-dir>

For a new XLSM, obtain the approved template manifest SHA-256 independently
of the files in the store. Under templates/<manifest-sha256>/ place read-only
template.json, template.xlsm and all required external FRM/FRX companions.
The manifest has this shape (use actual SHA-256 values and immutable version):
  {"version":"v1","workbookSha256":"<sha256>","companions":{"Form.frm":"<sha256>","Form.frx":"<sha256>"}}
List all required sidecars; use {} when none are required. The binary workbook
and its embedded artifacts are copied byte-for-byte, not opened or converted.
External companions remain in the private pinned version as one unit.

  python -X utf8 <script> copy-template book.xlsm --template-sha256 <manifest-sha256> --store <private-dir>
  python -X utf8 <script> export book.xlsm baseline --template-sha256 <manifest-sha256> --desktop-verified <workbook-sha256> --store <private-dir>

Before opening the copied XLSM, qualify and authorize the desktop readback for
the actual template profile, including control of opening effects such as XLM
and refresh-on-open. Reopen only the copy, read-only, without updating links,
running macros or refreshing. Close without saving and then export. If any
qualification, authorization or readback check is missing, stop before review
and acceptance. Do not substitute a save-as or infer qualification from a
successful passive copy. Record desktop create/save and reopen evidence
separately from this CLI's checksum and format checks. By passing
--desktop-verified, the operator attests that authorization, qualification and
readback were verified for those exact saved bytes. The CLI checks the digest,
not the truth of the attestation. Existing XLSX onboarding does not use it.

Review and accept either starting path using the existing onboarding commands:

  python -X utf8 <script> export book.xlsx baseline --store <private-dir>
  python -X utf8 <script> publish baseline baseline --reviewed <manifest-sha256> --store <private-dir>
  python -X utf8 <script> accept-initial baseline --reviewed <manifest-sha256> --store <private-dir>
  python -X utf8 <script> export book.xlsx candidate --store <private-dir>
  git diff --no-index -- baseline/ordinary-formulas.json <private-dir>/review/candidate/ordinary-formulas.json
  python -X utf8 <script> publish candidate candidate --reviewed <candidate-sha256> --store <private-dir>
  git diff --no-index -- baseline/ordinary-formulas.json candidate/ordinary-formulas.json

Before publishing, review all text artifacts under <private-dir>/review
for sensitive identifiers, numeric constants and logic. Pass the digest printed
by export. Publication verifies the exact preview against the retained version.
Stage only reviewed text files, never workbook binaries or a redacted preview. Acceptance
checks the published export again; later exports do not advance sync.

Editable exports list exact A1 targets of standalone ordinary formulas and
metadata-confirmed dynamic-array anchors, plus supported worksheet-scoped name
definitions. The inventory summarizes omissions, not instructions. No values,
cached formula results or connection strings are emitted. Saved Power
Query M and its inventory are separate artifacts for the restricted pilot
profile; see the Excel repo contract for the M import and manual load workflows.
Shared and legacy array formula records, spill outputs, what-if data tables,
and table-calculated columns are out of scope. Nonempty inline strings,
recognized credential patterns and external formula references block the export.
These checks are conservative, not a substitute for human review of identifiers
and formulas for sensitive information. No redacted export or import is provided.

Versions are named by SHA-256 and never replaced by this tool. Local read-only
files do not protect against storage administrators; use appropriate retention
and backups. For controlled formula and name import, see the Excel repo contract.
Only the explicit pq-pilot command launches Excel, and only for
fresh synthetic workbooks in a private attempt directory.
"""

import argparse
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
from io import BytesIO, StringIO, TextIOWrapper
import json
import os
from pathlib import Path, PureWindowsPath
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile

from excel_power_query import MODEL, M_SOURCE, QueryBlocked, check_expression, connection_query, read_mashup
from excel_pq_desktop import BASE_M, EDITED_M, LABEL, LOADED, NEIGHBOR, NEIGHBOR_M


S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
OFFICE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE = '{http://schemas.openxmlformats.org/package/2006/relationships}'
MAX_PACKAGE = 64 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024
CELL = re.compile(r'([A-Z]{1,3})([1-9][0-9]{0,6})\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
PROFILES = {'.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
            '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.main+xml'}
COMPANION = re.compile(r'(?!con\.|prn\.|aux\.|nul\.|(?:com|lpt)[0-9]\.)[a-z0-9_-]+\.(?:frm|frx)\Z',
                       re.IGNORECASE | re.ASCII)
FRX_REFERENCE = re.compile(rb'"([^"\r\n]+\.frx)"\s*:[0-9a-f]+', re.IGNORECASE)
VBA_PROJECT = 'http://schemas.microsoft.com/office/2006/relationships/vbaProject'
TEXT_LITERAL = re.compile(r'"(?:[^"]|"")*"')
CREDENTIAL = re.compile(
    r'(?i)\b(?:gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|sk_(?:test|live)_[a-z0-9_]{12,}'
    r'|(?:akia|asia)[a-z0-9]{16})\b|\b(?:password|passwd|api[_ -]?key|client[_ -]?secret|access[_ -]?token)\s*[:=]'
)
EXTERNAL_FORMULA = re.compile(r'(?i)\[\d+\]|\[[^\]]*\.(?:xlsx?|xlsm|xlsb|xlam|csv)\]|://|\|')
EVIDENCE_REF = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9 .:/_#-]{0,159}')
SCOPED_ARTIFACTS = {
    'dynamic-arrays.json': ('editable-dynamic-arrays', 'cells', ('sheet', 'cell'), ('spill', 'dialect', 'kind', 'formula')),
    'scoped-names.json': ('editable-scoped-names', 'names', ('scope', 'name'), ('refersTo',)),
}


class Blocked(Exception):
    pass


@dataclass
class QuerySnapshot:
    part: str
    workbook_part: str
    queries: dict[str, str]
    metadata: tuple[str, dict[str, bytes], bytes, bytes]
    wiring: dict
    risky_open: bool
    load_parts: dict[tuple[str, str], tuple[str, str]]
    table_ranges: dict[str, dict[str, str]]


def refresh_on_load(node):
    return node.get('refreshOnLoad') not in (None, 'false', '0')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, encoding='utf-8')


def repo_path(root, value):
    relative = Path(value)
    if relative.anchor or '..' in relative.parts or not relative.parts:
        raise Blocked('Use a path relative to the Git worktree root.')
    path = root / relative
    if path.resolve() != path or any(part.lower() == '.git' for part in relative.parts):
        raise Blocked('Git paths must not traverse aliases or Git metadata.')
    return path


def storage_path(root, value):
    path = Path(value).absolute()
    if path.resolve() != path or not path.is_dir() or path.is_relative_to(root) or root.is_relative_to(path):
        raise Blocked('Use an existing dedicated private store outside the worktree.')
    if git(path, 'rev-parse', '--git-dir').returncode == 0 or any((p / '.git').exists() for p in (path, *path.parents)):
        raise Blocked('The private store must be outside Git.')
    return path


def require_private(*paths):
    code = 'The private store must grant access only to the operator and platform administrators.'
    existing = [path for path in paths if path.exists()]
    if any(path.resolve() != path for path in paths):
        raise Blocked('The private store must not contain path aliases.')
    if not existing:
        return
    if os.name == 'posix':
        uid = os.geteuid()  # type: ignore[attr-defined]  # POSIX only
        if any(path.stat().st_uid != uid or path.stat().st_mode & 0o077 for path in existing):
            raise Blocked(code)
    elif os.name == 'nt':
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', r'''
                $ErrorActionPreference = 'Stop'
                try {
                    $sid = [Security.Principal.SecurityIdentifier]
                    $allowed = @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,
                                 'S-1-5-18', 'S-1-5-32-544')
                    $sections = [Security.AccessControl.AccessControlSections]'Access, Owner'
                    foreach ($path in $env:EXCEL_ONBOARDING_ACL_PATHS.Split("`n")) {
                        if ([IO.Directory]::Exists($path)) {
                            $acl = [IO.Directory]::GetAccessControl($path, $sections)
                        } else {
                            $acl = [IO.File]::GetAccessControl($path, $sections)
                        }
                        $raw = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(), 0)
                        if ($null -eq $raw.DiscretionaryAcl -or $raw.Owner.Value -notin $allowed) { exit 1 }
                        foreach ($rule in $acl.GetAccessRules($true, $true, $sid)) {
                            if ($rule.AccessControlType -eq 'Allow' -and
                                $rule.IdentityReference.Value -notin ($allowed + 'S-1-3-4')) {
                                exit 1
                            }
                        }
                    }
                } catch {
                    [Console]::Error.WriteLine($_.Exception.GetBaseException().GetType().Name)
                    exit 2
                }
                exit 0
            '''], env={**os.environ, 'EXCEL_ONBOARDING_ACL_PATHS': '\n'.join(map(str, existing))},
            capture_output=True,
        )
        if result.returncode != 0 and result.returncode != 1:
            detail = result.stderr.decode('ascii', errors='ignore').strip()
            if not re.fullmatch(r'[A-Za-z]+Exception', detail):
                detail = f'exit {result.returncode}'
            raise Blocked(f'Could not read the Windows private-store ACL ({detail}).')
        if result.returncode:
            raise Blocked(code)
    else:
        raise Blocked('Private storage cannot be verified on this platform.')


def read_bounded(path, limit):
    if path.resolve() != path or not path.is_file():
        raise Blocked('Expected a regular file, not an alias.')
    with path.open('rb') as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise Blocked('File exceeds the supported size limit.')
    return data


def write_once(path, data, *, writable=False):
    # Publish a complete file without overwriting an existing destination.
    fd, name = tempfile.mkstemp(dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if not writable:
            pending.chmod(stat.S_IRUSR)
        if os.name == 'nt':
            pending.rename(path)  # Windows rename fails if the destination exists.
        else:
            os.link(pending, path)
    finally:
        if pending.exists():
            if os.name == 'nt':
                pending.chmod(stat.S_IWRITE)
            pending.unlink()


def coordinates(address):
    match = CELL.fullmatch(address)
    if not match:
        raise Blocked('Unsupported cell address or range.')
    column = 0
    for letter in match[1]:
        column = column * 26 + ord(letter) - 64
    row = int(match[2])
    if column > 16384 or row > 1048576:
        raise Blocked('Unsupported cell address or range.')
    return column, row


def rectangle(reference):
    first, _, last = reference.partition(':')
    left, top = coordinates(first)
    right, bottom = coordinates(last or first)
    if left > right or top > bottom:
        raise Blocked('Unsupported cell address or range.')
    return left, top, right, bottom


def overlaps(first, second):
    l, t, r, b = first
    x, y, right, bottom = second
    return l <= right and x <= r and t <= bottom and y <= b


def dynamic_metadata_indices(metadata):
    xda = '{http://schemas.microsoft.com/office/spreadsheetml/2017/dynamicarray}'
    types = metadata.findall(f'{S}metadataTypes/{S}metadataType')
    dynamic = [i for i, entry in enumerate(types, 1)
               if entry.get('name') == 'XLDAPR' and entry.get('cellMeta') in ('1', 'true')]
    future = metadata.findall(f'{S}futureMetadata[@name="XLDAPR"]')
    if metadata.tag != f'{S}metadata' or len(dynamic) != 1 or len(future) != 1:
        return set()
    records = set()
    for i, block in enumerate(future[0].findall(f'{S}bk')):
        extension = block.findall(f'{S}extLst/{S}ext')
        if len(extension) != 1 or extension[0].get('uri', '').lower() != '{bdbb8cdc-fa1e-496e-a857-3c3f30c029c3}':
            continue
        props = extension[0].findall(f'{xda}dynamicArrayProperties')
        if (len(props) == 1 and props[0].get('fDynamic') in ('1', 'true')
                and props[0].get('fCollapsed', '0') in ('0', 'false')):
            records.add(str(i))
    return {str(i) for i, block in enumerate(metadata.findall(f'{S}cellMetadata/{S}bk'), 1)
            if len(block) == 1 and block[0].tag == f'{S}rc'
            and block[0].get('t') == str(dynamic[0]) and block[0].get('v') in records}


def scoped_reference(formula, sheet):
    match = re.fullmatch(r"=(.+)!(\$[A-Z]{1,3}\$[1-9][0-9]{0,6}(?::\$[A-Z]{1,3}\$[1-9][0-9]{0,6})?)", formula)
    quoted = "'" + sheet.replace("'", "''") + "'"
    if match and (match[1] == quoted or (re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', sheet) and match[1] == sheet)):
        return rectangle(match[2].replace('$', ''))
    return None


def workbook_artifacts(data, profile, *, format_only=False, power_query=False, worksheet_parts=None, editable=None):
    cells, sheets = [], []
    remaining = MAX_PACKAGE
    with ZipFile(BytesIO(data)) as book:
        names = set(book.namelist())
        if len(names) != len(book.infolist()):
            raise Blocked('Workbook contains duplicate package parts.')

        def xml(part):
            nonlocal remaining
            size = book.getinfo(part).file_size
            if size > MAX_XML or size > remaining:
                raise Blocked('Workbook XML exceeds the supported size limit.')
            remaining -= size
            text = book.read(part).decode('utf-8-sig')
            if '\0' in text or '<!DOCTYPE' in text or '<!ENTITY' in text:
                raise Blocked('Unsupported workbook XML.')
            return ET.fromstring(text)

        def relationships(part):
            folder, filename = posixpath.split(part)
            rels = posixpath.join(folder, '_rels', filename + '.rels')
            if rels not in names:
                return {}
            rows = xml(rels).findall(f'{PACKAGE}Relationship')
            result = {row.attrib['Id']: row.attrib for row in rows}
            if len(result) != len(rows):
                raise Blocked('Workbook contains duplicate relationship IDs.')
            return result

        def target(part, relation, kind):
            if relation.get('Type') != kind or relation.get('TargetMode', 'Internal') != 'Internal':
                raise Blocked('Unsupported workbook part relationship.')
            ref = relation['Target']
            if any(c in ref for c in '\\:%?#'):
                raise Blocked('Unsupported workbook part relationship.')
            return posixpath.normpath(ref[1:] if ref.startswith('/') else posixpath.join(posixpath.dirname(part), ref))

        workbook_parts = [row for row in relationships('').values() if row.get('Type') == f'{OFFICE}/officeDocument']
        if len(workbook_parts) != 1:
            raise Blocked('Expected one workbook document.')
        part = target('', workbook_parts[0], f'{OFFICE}/officeDocument')
        content_types = xml('[Content_Types].xml')
        types = [item.get('ContentType') for item in content_types if item.get('PartName') == '/' + part]
        if types != [PROFILES[profile]]:
            raise Blocked(f'Saved workbook format does not match {profile.upper()}; conversion is not supported.')
        workbook = xml(part)
        sheet_nodes = workbook.find(f'{S}sheets')
        if workbook.tag != f'{S}workbook' or sheet_nodes is None or not len(sheet_nodes):
            raise Blocked('Unsupported workbook structure.')
        links = relationships(part)
        vba_projects = [row for row in links.values() if row.get('Type') == VBA_PROJECT]
        if vba_projects and (profile != '.xlsm' or len(vba_projects) != 1
                             or target(part, vba_projects[0], VBA_PROJECT) not in names):
            raise Blocked('Saved workbook has a missing or unsupported VBA project part.')
        if format_only:
            return [], {}, None
        metadata_links = [row for row in links.values() if row.get('Type') == f'{OFFICE}/sheetMetadata']
        dynamic_indices = (dynamic_metadata_indices(xml(target(part, metadata_links[0], f'{OFFICE}/sheetMetadata')))
                           if editable is not None and len(metadata_links) == 1 else set())
        mashup = read_mashup(book, CREDENTIAL, min(MAX_XML, remaining)) if power_query else None
        loads = []
        load_parts: dict[tuple[str, str], tuple[str, str]] = {}
        table_ranges: dict[str, dict[str, str]] = {}
        query_tables = set()
        risky_open = (bool(vba_projects) or any(row.get('TargetMode') == 'External' for row in links.values())
                      or any('macrosheet' in row.get('Type', '').lower() for row in links.values())
                      or any('macrosheet' in item.get('ContentType', '').lower() for item in content_types)
                      or workbook.find(f'{S}externalReferences') is not None)
        sheet_names, sheet_parts = set(), set()
        scopes = {}
        for sheet_index, sheet in enumerate(sheet_nodes.findall(f'{S}sheet')):
            name = sheet.attrib['name']
            relation = links[sheet.attrib[f'{{{OFFICE}}}id']]
            if not name or name.casefold() in sheet_names:
                raise Blocked('Invalid or duplicate sheet name.')
            sheet_names.add(name.casefold())
            if relation.get('Type') != f'{OFFICE}/worksheet':
                sheets.append({'sheet': name, 'type': 'non-worksheet'})
                continue
            scopes[str(sheet_index)] = name
            sheet_part = target(part, relation, f'{OFFICE}/worksheet')
            if sheet_part in sheet_parts:
                raise Blocked('Duplicate worksheet part.')
            sheet_parts.add(sheet_part)
            if worksheet_parts is not None:
                worksheet_parts[name] = sheet_part
            worksheet = xml(sheet_part)
            if worksheet.tag != f'{S}worksheet':
                raise Blocked('Unsupported worksheet structure.')
            table_parts = worksheet.findall(f'{S}tableParts/{S}tablePart')
            excluded_ranges = []
            all_tables = []
            table_templates = 0
            if table_parts:
                table_links = relationships(sheet_part)
            for table in table_parts:
                relation = table_links[table.attrib[f'{{{OFFICE}}}id']]
                table_part = target(sheet_part, relation, f'{OFFICE}/table')
                definition = xml(table_part)
                left, top, right, bottom = rectangle(definition.attrib['ref'])
                all_tables.append((left, top, right, bottom))
                columns = definition.findall(f'{S}tableColumns/{S}tableColumn')
                if definition.tag != f'{S}table' or len(columns) != right - left + 1:
                    raise Blocked('Unsupported table structure.')
                if mashup is not None:
                    table_ranges.setdefault(name, {})[table_part] = definition.attrib['ref']
                    for link in relationships(table_part).values():
                        if link.get('Type') != f'{OFFICE}/queryTable':
                            continue
                        query_part = target(table_part, link, f'{OFFICE}/queryTable')
                        query_table = xml(query_part)
                        if query_part in query_tables or query_table.tag != f'{S}queryTable':
                            raise Blocked('Unsupported query table mapping.')
                        query_tables.add(query_part)
                        key = (name, definition.attrib['name'])
                        if key in load_parts:
                            raise Blocked('Ambiguous worksheet load table.')
                        load_parts[key] = (sheet_part, table_part)
                        risky_open |= refresh_on_load(query_table)
                        loads.append({'connectionId': query_table.attrib['connectionId'], 'sheet': name,
                                      'table': definition.attrib['name'], 'range': definition.attrib['ref']})
                for col, column in enumerate(columns, left):
                    calculated = column.find(f'{S}calculatedColumnFormula') is not None
                    table_templates += calculated
                    if calculated or column.find(f'{S}totalsRowFormula') is not None:
                        excluded_ranges.append((col, top, col, bottom))

            formulas = {}
            anchors = {}
            excluded_kinds: Counter[str] = Counter()
            for cell in worksheet.findall(f'{S}sheetData/{S}row/{S}c'):
                formula = cell.find(f'{S}f')
                if formula is None:
                    continue
                address = cell.attrib['r']
                if address in formulas:
                    raise Blocked('Duplicate formula target.')
                coords = coordinates(address)
                kind = formula.get('t', 'normal')
                ordinary = (kind == 'normal' and not cell.get('cm')
                            and 'ref' not in formula.attrib and not len(formula) and bool(formula.text))
                ref = formula.get('ref')
                if (kind == 'array' and cell.get('cm') in dynamic_indices and not cell.get('vm')
                        and ref and not len(formula) and formula.text and rectangle(ref)[:2] == coords):
                    anchors[address] = (rectangle(ref), ref, formula.text)
                    formulas[address] = (coords, False, formula.text)
                    continue
                if not ordinary:
                    if kind == 'array' and cell.get('cm'):
                        kind = 'arrayWithMetadata'
                    excluded_kinds[kind if kind in ('array', 'arrayWithMetadata', 'shared', 'dataTable')
                                   else 'other'] += 1
                if not ordinary and 'ref' in formula.attrib:
                    excluded_ranges.append(rectangle(formula.attrib['ref']))
                formulas[address] = (coords, ordinary, formula.text)

            merges = [rectangle(node.attrib['ref']) for node in worksheet.findall(f'{S}mergeCells/{S}mergeCell')]
            exported_anchors = 0
            for address, (area, ref, text) in sorted(anchors.items()):
                if (worksheet.find(f'{S}sheetProtection') is not None
                        or any(overlaps(area, other) for other in excluded_ranges + all_tables + merges)
                        or any(overlaps(area, other) for key, (other, _, _) in anchors.items() if address != key)
                        or any(overlaps(area, (*coords, *coords)) for key, (coords, _, _) in formulas.items()
                               if address != key)):
                    excluded_kinds['arrayWithMetadata'] += 1
                elif editable is not None:
                    exported_anchors += 1
                    editable['dynamic-arrays.json'].append({'sheet': name, 'cell': address, 'spill': ref,
                        'dialect': 'Formula2', 'kind': 'dynamic-array-anchor', 'formula': '=' + text})
            excluded_ranges.extend(area for area, _, _ in anchors.values())
            count = 0
            for address, ((x, y), ordinary, text) in sorted(formulas.items()):
                if ordinary and not any(l <= x <= r and t <= y <= b for l, t, r, b in excluded_ranges):
                    cells.append({'sheet': name, 'cell': address, 'formula': '=' + text})
                    count += 1
                elif ordinary:
                    excluded_kinds['inExcludedRange'] += 1
            sheets.append({'sheet': name, 'type': 'worksheet', 'editableFormulaRecords': count + exported_anchors,
                           'excludedFormulaRecords': len(formulas) - count - exported_anchors,
                           'excludedByKind': dict(sorted(excluded_kinds.items())),
                           'tables': len(table_parts), 'calculatedColumnTemplates': table_templates})

        query_snapshot = None
        if mashup is not None:
            mashup_part, queries, preservation = mashup
            connections = []
            connection_links = [link for link in links.values() if link.get('Type') == f'{OFFICE}/connections']
            if len(connection_links) > 1:
                raise Blocked('Unsupported workbook connection mapping.')
            if connection_links:
                connection_root = xml(target(part, connection_links[0], f'{OFFICE}/connections'))
                if connection_root.tag != f'{S}connections':
                    raise Blocked('Unsupported workbook connection mapping.')
                for connection in connection_root.findall(f'{S}connection'):
                    db = connection.find(f'{S}dbPr')
                    mapping = (connection_query(db.get('connection', ''), db.get('command'), queries)
                               if db is not None and db.get('commandType', '2') == '2' else None)
                    connection_id = connection.attrib['id']
                    if not re.fullmatch(r'[1-9][0-9]{0,9}', connection_id):
                        raise Blocked('Unsupported workbook connection ID.')
                    connections.append({'id': connection_id, 'query': mapping})
                    risky_open |= mapping is None or refresh_on_load(connection) or connection.get('interval', '0') != '0'
            ids = {item['id'] for item in connections}
            declared_tables = {item.get('PartName', '').lstrip('/') for item in content_types
                               if item.get('ContentType', '').endswith('spreadsheetml.queryTable+xml')}
            if (len(ids) != len(connections) or any(load['connectionId'] not in ids for load in loads)
                    or declared_tables != query_tables):
                raise Blocked('Incomplete Power Query load wiring.')
            for item in content_types:
                if item.get('ContentType', '').endswith('spreadsheetml.pivotCacheDefinition+xml'):
                    cache = xml(item.attrib['PartName'].lstrip('/'))
                    risky_open |= refresh_on_load(cache)
            for load in loads:
                if CREDENTIAL.search(load['table']):
                    raise Blocked('Publication blocked: possible credential in table name.')
            has_model = (any(MODEL.search(name) for name in names)
                         or any('model+data' in item.get('ContentType', '').lower() for item in content_types)
                         or any(link.get('Type', '').endswith('/model') for link in links.values()))
            wiring = {'kind': 'inventory-only', 'hasDataModel': has_model,
                      'connections': sorted(connections, key=lambda row: int(row['id'])),
                      'worksheetLoads': sorted(loads, key=lambda row: (row['sheet'], row['table']))}
            query_snapshot = QuerySnapshot(mashup_part, part, queries, preservation, wiring, risky_open,
                                           load_parts, table_ranges)

    defined_names = workbook.findall(f'{S}definedNames/{S}definedName')
    if editable is not None:
        keys = set()
        for node in defined_names:
            name, scope = node.get('name', ''), scopes.get(node.get('localSheetId', ''))
            if scope is None:
                continue
            key = (scope, name.casefold())
            if key in keys:
                raise Blocked('Duplicate worksheet-scoped defined name.')
            keys.add(key)
            if (re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,254}', name) and not name.lower().startswith('_xl')
                    and node.attrib.keys() == {'name', 'localSheetId'} and not len(node) and node.text
                    and scoped_reference('=' + node.text, scope)):
                editable['scoped-names.json'].append({'scope': scope, 'name': name, 'refersTo': '=' + node.text})
        editable['scoped-names.json'].sort(key=lambda row: (row['scope'], row['name']))
    inventory = {'kind': 'inventory-only', 'sheets': sheets,
                 'definedNames': len(defined_names),
                 'externalReferences': len(workbook.findall(f'{S}externalReferences/{S}externalReference')),
                 'hasConnectionsPart': any(row.get('Type') == f'{OFFICE}/connections' for row in links.values())}
    return cells, inventory, query_snapshot


def build_export(data, workbook, template=None, desktop_verified=None, *, power_query=False, worksheet_parts=None):
    editable: dict[str, list[dict[str, str]]] = {name: [] for name in SCOPED_ARTIFACTS}
    cells, inventory, query_snapshot = workbook_artifacts(
        data, Path(workbook).suffix.lower(), power_query=power_query, worksheet_parts=worksheet_parts, editable=editable)
    for value in [workbook, *(sheet['sheet'] for sheet in inventory['sheets'])]:
        if CREDENTIAL.search(value):
            raise Blocked('Publication blocked: possible credential in workbook metadata.')
    for cell in cells + editable['dynamic-arrays.json']:
        formula = cell['formula']
        if CREDENTIAL.search(formula) or any(m[0] != '""' for m in TEXT_LITERAL.finditer(formula)):
            raise Blocked('Publication blocked: possible credential or unreviewable inline text in a formula.')
        if EXTERNAL_FORMULA.search(formula):
            raise Blocked('Publication blocked: an external formula is outside the supported export profile.')
    artifacts = {'ordinary-formulas.json': json_bytes({'kind': 'editable-ordinary-formulas', 'cells': cells}),
                 'inventory.json': json_bytes(inventory)}
    if any(CREDENTIAL.search(value) for row in editable['scoped-names.json'] for value in row.values()):
        raise Blocked('Publication blocked: possible credential in a defined name.')
    for name, rows in editable.items():
        if rows:
            kind, collection, _, _ = SCOPED_ARTIFACTS[name]
            artifacts[name] = json_bytes({'kind': kind, collection: rows})
    if power_query:
        if query_snapshot is None:
            raise Blocked('No supported saved Power Query M was found.')
        artifacts['power-query.json'] = json_bytes({'kind': M_SOURCE, 'queries': dict(sorted(query_snapshot.queries.items()))})
        artifacts['power-query-inventory.json'] = json_bytes(query_snapshot.wiring)
    metadata = {'schema': 1, 'workbook': workbook, 'versionSha256': sha(data),
                'files': {name: sha(content) for name, content in artifacts.items()}}
    if template is not None:
        metadata['templateManifestSha256'] = template
    if desktop_verified is not None:
        metadata['desktopVerifiedSha256'] = desktop_verified
    artifacts['manifest.json'] = json_bytes(metadata)
    return artifacts


def write_export(output, artifacts):
    if output.exists() or not output.parent.is_dir():
        raise Blocked('Choose a new export directory under an existing parent.')
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        ready = Path(staging) / 'export'
        ready.mkdir(mode=0o700)
        for name, content in artifacts.items():
            (ready / name).write_bytes(content)
        ready.rename(output)


def preview_path(store, label):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', label):
        raise Blocked('Use a short preview label containing only letters, digits, underscores or hyphens.')
    return repo_path(store, 'review/' + label)


def retained_bytes(path, version):
    data = read_bounded(path, MAX_PACKAGE)
    if path.stat().st_mode & stat.S_IWRITE or sha(data) != version:
        raise Blocked('Retained workbook checksum or read-only status does not match.')
    return data


def verified_template(store, pin):
    if not SHA.fullmatch(pin):
        raise Blocked('Use the approved template manifest SHA-256.')
    folder = store / 'templates' / pin
    manifest = folder / 'template.json'
    workbook = folder / 'template.xlsm'
    require_private(store, folder.parent, folder, manifest, workbook)
    if not manifest.is_file() or not workbook.is_file():
        raise Blocked('Pinned template manifest or workbook is missing.')
    raw = read_bounded(manifest, MAX_XML)
    if sha(raw) != pin or manifest.stat().st_mode & stat.S_IWRITE:
        raise Blocked('Pinned template manifest checksum or read-only status does not match.')
    metadata = json.loads(raw)
    if (not isinstance(metadata, dict) or set(metadata) != {'version', 'workbookSha256', 'companions'}
            or not isinstance(metadata['version'], str) or not metadata['version'].strip()
            or not isinstance(metadata['workbookSha256'], str) or not SHA.fullmatch(metadata['workbookSha256'])):
        raise Blocked('Pinned template manifest must identify an immutable version and workbook checksum.')
    companions = metadata['companions']
    if (not isinstance(companions, dict) or len(companions) > 100
            or any(not COMPANION.fullmatch(name)
                   or not isinstance(digest, str) or not SHA.fullmatch(digest) for name, digest in companions.items())):
        raise Blocked('Pinned template manifest has an invalid FRM/FRX companion inventory.')
    names = {name.lower() for name in companions}
    if len(names) != len(companions) or {path.name for path in folder.iterdir()} != {
            manifest.name, workbook.name, *companions}:
        raise Blocked('Pinned template has missing, duplicate, or unlisted required artifacts.')
    require_private(*(folder / name for name in companions))
    for name, digest in companions.items():
        path = folder / name
        if not path.is_file():
            raise Blocked('Pinned template companion is missing or is not a file.')
        data = read_bounded(path, MAX_PACKAGE)
        if sha(data) != digest or path.stat().st_mode & stat.S_IWRITE:
            raise Blocked('Pinned template companion checksum or read-only status does not match.')
        lower = name.lower()
        if lower.endswith('.frx') and lower[:-4] + '.frm' not in names:
            raise Blocked('Pinned FRX requires its matching FRM.')
        if lower.endswith('.frm'):
            expected = lower[:-4] + '.frx'
            for line in data.splitlines():
                references = FRX_REFERENCE.findall(line)
                if ((not references and line.lstrip().lower().startswith(b'oleobjectblob'))
                        or any(name.lower() != expected.encode('ascii') or expected not in names for name in references)):
                    raise Blocked('Pinned FRM has a missing or unsupported FRX reference.')
    return retained_bytes(workbook, metadata['workbookSha256'])


def workbook_profile(source, template):
    profile = source.suffix.lower()
    if profile not in PROFILES or source.name.startswith('~$'):
        raise Blocked('Only .xlsx and pinned .xlsm profiles are supported; conversion is not supported.')
    if profile == '.xlsm' and template is None:
        raise Blocked('XLSM requires an approved template manifest SHA-256.')
    if profile == '.xlsx' and template is not None:
        raise Blocked('The pinned template route requires an .xlsm destination; conversion is not supported.')
    return profile


def workbook_path(root, workbook, template):
    source = repo_path(root, workbook)
    workbook_profile(source, template)
    if source.with_name('~$' + source.name).exists():
        raise Blocked('Workbook lock file exists; close Excel before exporting.')
    return source


def copy_template(root, store, workbook, template):
    destination = workbook_path(root, workbook, template)
    if (store / 'sync.json').exists():
        raise Blocked('The first synchronization point is already set.')
    if destination.exists() or not destination.parent.is_dir():
        raise Blocked('Choose a new workbook path under an existing parent.')
    if git(root, 'check-ignore', '--quiet', '--', workbook).returncode != 0:
        raise Blocked('The working workbook path must be ignored by Git.')
    data = verified_template(store, template)
    workbook_artifacts(data, '.xlsm', format_only=True)
    write_once(destination, data, writable=True)
    print(f'Copied pinned XLSM without conversion. Workbook SHA-256: {sha(data)}')


def verify_desktop_attestation(template, attested, version):
    if template is not None and attested is None:
        raise Blocked('Pinned XLSM export requires qualified, authorized desktop readback of the copy.')
    if attested is not None and attested != version:
        raise Blocked('The desktop-verified checksum does not match the saved workbook.')


def export(root, store, workbook, label, template=None, desktop_verified=None, *, power_query=False):
    source = workbook_path(root, workbook, template)
    preview = preview_path(store, label)
    if preview.exists():
        raise Blocked('Choose a new preview label.')
    data = read_bounded(source, MAX_PACKAGE)
    version = sha(data)
    verify_desktop_attestation(template, desktop_verified, version)
    if template is not None and verified_template(store, template) != data:
        raise Blocked('Saved XLSM differs from the pinned template; no initial export was produced.')
    artifacts = build_export(data, source.relative_to(root).as_posix(), template, desktop_verified,
                             power_query=power_query)
    retained = store / 'versions' / f'{version}{source.suffix.lower()}'
    require_private(store, preview.parent, retained.parent, retained)
    retained.parent.mkdir(mode=0o700, exist_ok=True)
    if not retained.exists():
        write_once(retained, data)
    retained_bytes(retained, version)
    preview.parent.mkdir(mode=0o700, exist_ok=True)
    write_export(preview, artifacts)
    print(f'Exported for private review. Manifest SHA-256: {sha(artifacts["manifest.json"])}')


def verified_export(root, store, folder, reviewed):
    manifest = read_bounded(folder / 'manifest.json', MAX_XML)
    if not SHA.fullmatch(reviewed) or sha(manifest) != reviewed:
        raise Blocked('The reviewed manifest checksum does not match.')
    metadata = json.loads(manifest)
    version = metadata['versionSha256']
    if not SHA.fullmatch(version):
        raise Blocked('Invalid workbook version checksum.')
    template = metadata.get('templateManifestSha256')
    desktop_verified = metadata.get('desktopVerifiedSha256')
    verify_desktop_attestation(template, desktop_verified, version)
    workbook = repo_path(root, metadata['workbook'])
    profile = workbook_profile(workbook, template)
    retained = store / 'versions' / f'{version}{profile}'
    require_private(store, retained.parent, retained)
    data = retained_bytes(retained, version)
    if template is not None and verified_template(store, template) != data:
        raise Blocked('Retained XLSM does not match the pinned template.')
    artifacts = build_export(data, workbook.relative_to(root).as_posix(), template, desktop_verified,
                             power_query='power-query.json' in metadata['files'])
    if ({file.name for file in folder.iterdir()} != artifacts.keys()
            or any(read_bounded(folder / name, MAX_PACKAGE) != content for name, content in artifacts.items())):
        raise Blocked('Export no longer matches the retained workbook and reviewed manifest.')
    return metadata, artifacts


def accept_initial(root, store, candidate, reviewed):
    sync = store / 'sync.json'
    if sync.exists():
        raise Blocked('The first synchronization point is already set.')
    metadata, _ = verified_export(root, store, repo_path(root, candidate), reviewed)
    write_once(sync, json_bytes({'schema': 1, 'workbook': metadata['workbook'],
                                 'versionSha256': metadata['versionSha256'], 'manifestSha256': reviewed}))
    print('Accepted the first synchronization point.')


IMPORT_OPERATION = 'ordinary-formula-import'
IMPORT_PROFILE = 'simple-xlsx'
REFERENCE = r'\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}'
OPERAND = rf'(?:{REFERENCE}|[0-9]{{1,15}}(?:\.[0-9]{{1,15}})?)'
SAFE_FORMULA = re.compile(rf'=(?:{OPERAND}(?:[+*/-]{OPERAND})*|SUM\({REFERENCE}:{REFERENCE}\))\Z')


def formula_map(raw):
    artifact = json.loads(raw)
    if artifact['kind'] != 'editable-ordinary-formulas' or not isinstance(artifact['cells'], list):
        raise Blocked('Expected the editable ordinary formula artifact.')
    result = {}
    for row in artifact['cells']:
        key = (row['sheet'], row['cell'])
        if (not isinstance(key[0], str) or CREDENTIAL.search(key[0]) or key in result
                or not isinstance(row['formula'], str) or CREDENTIAL.search(row['formula'])
                or any(m[0] != '""' for m in TEXT_LITERAL.finditer(row['formula']))):
            raise Blocked('Invalid, duplicate, or potentially sensitive Git formula entry.')
        coordinates(key[1])
        result[key] = row['formula']
    return result


def formula_diff(before, after, *, omissions=False):
    keys = before.keys() | after.keys() if omissions else after.keys()
    return [{'sheet': sheet, 'cell': cell, 'before': before.get((sheet, cell)),
             'after': after.get((sheet, cell))} for sheet, cell in sorted(keys)
            if before.get((sheet, cell)) != after.get((sheet, cell))]


def import_snapshot(data, workbook):
    parts: dict[str, str] = {}
    artifacts = build_export(data, workbook, worksheet_parts=parts)
    return parts, artifacts, formula_map(artifacts['ordinary-formulas.json'])


COM_QUALIFICATION = 'https://github.com/ciahciach/skills/pull/63'
COM_FIXTURE_EDIT = {'sheet': 'Calc', 'cell': 'B1', 'before': '=A1*2', 'after': '=A1*3'}
SCOPED_OPERATION = 'scoped-array-name-import'
SCOPED_PROFILE = 'scoped-array-xlsx'
SEQUENCE = re.compile(r'=_xlfn\.SEQUENCE\(([1-9][0-9]{0,6}),([1-9][0-9]{0,4})'
                      r'(?:,(-?[0-9]{1,12})(?:,(-?[0-9]{1,12}))?)?\)\Z')


def scoped_map(filename, raw):
    if raw is None:
        return {}
    kind, collection, keys, fields = SCOPED_ARTIFACTS[filename]
    artifact = json.loads(raw, object_pairs_hook=unique_json_object)
    if not isinstance(artifact, dict) or artifact.keys() != {'kind', collection} or artifact['kind'] != kind or not isinstance(artifact[collection], list):
        raise Blocked('Invalid scoped import artifact.')
    result = {}
    seen = set()
    for row in artifact[collection]:
        if (not isinstance(row, dict) or row.keys() != set(keys + fields)
                or any(not isinstance(value, str) or not value or len(value) > 8192 or CREDENTIAL.search(value)
                       for value in row.values())
                or ('refersTo' in row and not scoped_reference(row['refersTo'], row['scope']))
                or ('formula' in row and (EXTERNAL_FORMULA.search(row['formula'])
                    or any(m[0] != '""' for m in TEXT_LITERAL.finditer(row['formula']))))):
            raise Blocked('Invalid or potentially sensitive scoped import entry.')
        key = (row[keys[0]], row[keys[1]])
        canonical = (key[0].casefold(), key[1].casefold())
        if canonical in seen:
            raise Blocked('Duplicate scoped import entry.')
        seen.add(canonical)
        result[key] = row
    return result


def scoped_diff(before, after, *, omissions=False):
    keys = before.keys() | after.keys() if omissions else after.keys()
    return [{'before': before.get(key), 'after': after.get(key)} for key in sorted(keys)
            if before.get(key) != after.get(key)]


def validate_scoped_pair(diffs):
    if any(len(rows) != 1 or any(row is None for row in rows[0].values()) for rows in diffs.values()):
        raise Blocked('Expected one existing dynamic-array anchor and one existing scoped name edit.')
    array = diffs['dynamic-arrays.json'][0]
    name = diffs['scoped-names.json'][0]
    anchor = array['before']
    if (any(array['after'][key] != anchor[key] for key in ('sheet', 'cell', 'kind', 'dialect', 'spill'))
            or any(name['after'][key] != name['before'][key] for key in ('scope', 'name'))):
        raise Blocked('Scope, targets, kind, dialect and spill footprint cannot change.')
    l, t, r, b = rectangle(anchor['spill'])
    dimensions = (b - t + 1, r - l + 1)
    for row in array.values():
        match = SEQUENCE.fullmatch(row['formula'])
        if not match or (int(match[1]), int(match[2])) != dimensions or dimensions[0] * dimensions[1] > 256:
            raise Blocked('Scoped import requires a bounded integer SEQUENCE with unchanged spill dimensions.')
    return anchor, name['before']


def preservation(data, parts, change=None, *, data_only=False, verified_result=None, com_fixture_edit=False,
                 scoped=False, scoped_pair=None, scoped_com_edit=False):
    """Conservative package comparison for simple XLSX; return hashes, never values."""
    allowed = re.compile(r'(?:\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app|custom)\.xml|'
                         r'xl/(?:_rels/workbook\.xml\.rels|workbook\.xml|styles\.xml|sharedStrings\.xml|calcChain\.xml|'
                         r'theme/theme[0-9]+\.xml|worksheets/sheet[0-9]+\.xml))\Z')
    scoped_parts = re.compile(r'xl/(?:metadata\.xml|tables/table[0-9]+\.xml|worksheets/_rels/sheet[0-9]+\.xml\.rels)\Z')
    slots: set[tuple[int, int]] = set()
    matched_name = 0
    anchor, name = scoped_pair if scoped_pair else (None, None)
    area = rectangle(anchor['spill']) if anchor else None
    with ZipFile(BytesIO(data)) as book:
        entries = book.infolist()
        if len(set(book.namelist())) != len(entries):
            raise Blocked('Workbook contains duplicate package parts.')
        if sum(info.file_size for info in entries) > MAX_PACKAGE:
            raise Blocked('Workbook exceeds the preservation comparison limit.')
        hashes = {}
        for part in book.namelist():
            if not allowed.fullmatch(part) and not (scoped and scoped_parts.fullmatch(part)):
                raise Blocked('Workbook has parts outside the simple XLSX import profile.')
            raw = book.read(part)
            if b'\0' in raw or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                raise Blocked('Unsupported preservation XML.')
            parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)) if scoped else None
            xml = ET.fromstring(raw, parser=parser)
            if (any(node.get('TargetMode', 'Internal') != 'Internal' for node in xml)
                    or any(node.tag in {f'{S}{tag}' for tag in
                           ('definedName', 'externalReference', 'oleObject', 'control',
                             'workbookProtection', 'sheetProtection', 'oleObjects', 'controls')}
                            and not (scoped and part == 'xl/workbook.xml' and node.tag == f'{S}definedName')
                            for node in xml.iter())):
                raise Blocked('Workbook has features outside the simple XLSX import profile.')
            if scoped and part == 'xl/metadata.xml':
                if not dynamic_metadata_indices(xml):
                    raise Blocked('Unrecognized dynamic-array metadata.')
                hashes[part] = sha(raw)
                continue
            if scoped and part.startswith('xl/tables/') and (
                    xml.tag != f'{S}table' or xml.get('tableType', 'worksheet') != 'worksheet'
                    or 'connectionId' in xml.attrib):
                raise Blocked('Only static worksheet tables may be preserved in a scoped import.')
            for extension_list in xml.iter(f'{S}extLst'):
                calc = '{http://schemas.microsoft.com/office/spreadsheetml/2018/calcfeatures}'
                if part == 'xl/workbook.xml' and extension_list in xml:
                    native_properties = {
                        '{140A7094-0E35-4892-8432-C4D2E57EDEB5}': (
                            '{http://schemas.microsoft.com/office/spreadsheetml/2010/11/main}workbookPr',
                            'chartTrackingRefBase', r'0|1|true|false'),
                        '{D14903EA-33C4-47F7-8F05-3474C54BE107}': (
                            '{http://schemas.microsoft.com/office/spreadsheetml/2024/workbookCompatibilityVersion}version',
                            'setVersion', r'[0-9]{1,10}'),
                    }
                    for ext in extension_list:
                        if all(node.tag in {f'{S}ext', calc + 'calcFeatures', calc + 'feature'}
                               for node in ext.iter()):
                            continue
                        property_spec = native_properties.get(ext.get('uri', '')) if scoped else None
                        if property_spec and ext.tag == f'{S}ext' and ext.attrib.keys() == {'uri'} and len(ext) == 1:
                            tag, attribute, pattern = property_spec
                            prop = ext[0]
                            if (prop.tag == tag and prop.attrib.keys() == {attribute} and not len(prop)
                                    and re.fullmatch(pattern, prop.attrib[attribute])
                                    and not any((text or '').strip() for text in (ext.text, prop.text, prop.tail))):
                                continue  # Still included in the preservation hash.
                        break
                    else:
                        continue
                if (part == 'xl/styles.xml' and xml.tag == f'{S}styleSheet' and extension_list in xml
                        and len(xml.findall(f'{S}extLst')) == 1 and not extension_list.attrib and len(extension_list) == 2
                        and all(not (node.text or '').strip() and not (node.tail or '').strip()
                                for node in extension_list.iter())
                        and all(ext.tag == f'{S}ext' and ext.attrib == {'uri': uri} and len(ext) == 1
                                and ext[0].tag == tag and ext[0].attrib == attributes and not len(ext[0])
                                for ext, (uri, tag, attributes) in zip(extension_list, (
                                    ('{EB79DEF2-80B8-43e5-95BD-54CBDDF9020C}',
                                     '{http://schemas.microsoft.com/office/spreadsheetml/2009/9/main}slicerStyles',
                                     {'defaultSlicerStyle': 'SlicerStyleLight1'}),
                                    ('{9260A510-F301-46a8-8635-F512D64BE5F5}',
                                     '{http://schemas.microsoft.com/office/spreadsheetml/2010/11/main}timelineStyles',
                                     {'defaultTimelineStyle': 'TimeSlicerStyleLight1'}))))):
                    continue
                raise Blocked('Workbook has unsupported extensions.')
            if part == 'xl/styles.xml' and xml.find(f'{S}extLst') is not None:
                # Desktop Excel emits these empty defaults with no slicer or timeline parts.
                hashes[part] = sha(raw)
                continue
            if scoped and part == 'xl/workbook.xml':
                if scoped_com_edit and scoped_pair:
                    pointers = xml.findall('{http://schemas.microsoft.com/office/spreadsheetml/2014/revision}revisionPtr')
                    if len(pointers) == 1 and pointers[0].get('documentId', '').strip():
                        pointers[0].set('documentId', '')
                sheets = [node.attrib['name'] for node in xml.findall(f'{S}sheets/{S}sheet')]
                for node in xml.findall(f'{S}definedNames/{S}definedName'):
                    if (not node.text or not (any(scoped_reference('=' + node.text, sheet) for sheet in parts)
                            or re.fullmatch(r'-?[0-9]{1,12}(?:\.[0-9]{1,8})?', node.text))):
                        raise Blocked('Only local absolute-range or numeric constant names may be preserved in a scoped import.')
                    if (name and node.get('name') == name['name']
                            and node.get('localSheetId') == str(sheets.index(name['scope']))):
                        matched_name += 1
                        node.text = None
            elif part in ('docProps/custom.xml', 'xl/calcChain.xml', 'xl/workbook.xml'):
                # The qualified copy may rotate a revision ID and reorder exactly two peer cells.
                # Keep every other byte, including the label, XML comments and namespace bindings.
                if com_fixture_edit and part == 'xl/workbook.xml':
                    pointer = '{http://schemas.microsoft.com/office/spreadsheetml/2014/revision}revisionPtr'
                    nodes = xml.findall(pointer)
                    if len(nodes) == 1 and nodes[0].get('documentId'):
                        masked, count = re.subn(rb'(<xr:revisionPtr\b[^<>]*?\sdocumentId=")[^"]+("[^<>]*/>)',
                                                rb'\1#\2', raw)
                        if count == 1 and ET.fromstring(masked).findall(pointer)[0].get('documentId') == '#':
                            raw = masked
                elif (com_fixture_edit and part == 'xl/calcChain.xml' and xml.tag == f'{S}calcChain'
                      and len(xml) == 2 and all(node.tag == f'{S}c' and not len(node) for node in xml)
                      and {node.get('r') for node in xml} == {'B1', 'C1'}
                      and xml[0].get('i') == '1' and xml[1].get('i', '1') == '1'
                      and xml[0].attrib.keys() <= {'i', 'r', 'l'} and xml[0].get('l', '1') == '1'
                      and xml[1].attrib.keys() <= {'i', 'r'}):
                    masked, count = re.subn(rb'(<c\b[^<>]*?\sr=")[BC]1(")', rb'\1#\2', raw)
                    if count == 2 and [node.get('r') for node in ET.fromstring(masked)] == ['#', '#']:
                        raw = masked
                hashes[part] = sha(raw)
                continue
            if part == 'docProps/core.xml':
                modified = xml.find('{http://purl.org/dc/terms/}modified')
                if modified is not None:
                    modified.text = None
            elif part in parts.values():
                for cell in xml.findall(f'{S}sheetData/{S}row/{S}c'):
                    formula = cell.find(f'{S}f')
                    value = cell.find(f'{S}v')
                    if not scoped and formula is not None and (formula.attrib or cell.get('cm') or cell.get('vm')):
                        raise Blocked('Special formula records are outside the simple XLSX import profile.')
                    if anchor and area and part == parts[anchor['sheet']]:
                        l, t, r, b = area
                        x, y = coordinates(cell.attrib['r'])
                        if l <= x <= r and t <= y <= b:
                            if ((x, y) in slots or value is None or not value.text or cell.get('t', 'n') != 'n'
                                    or ((x, y) == (l, t)) != (formula is not None)
                                    or ((x, y) != (l, t) and (cell.get('cm') or cell.get('vm')))):
                                raise Blocked('Expected only the anchor and numeric spill values at the approved footprint.')
                            slots.add((x, y))
                            try:
                                spill_value = Decimal(value.text)
                            except InvalidOperation:
                                raise Blocked('Saved spill lacks a valid numeric result.') from None
                            if (not spill_value.is_finite()
                                    or (verified_result is not None and spill_value != verified_result[y - t][x - l])):
                                raise Blocked('Saved value does not match the independent spill readback.')
                            value.text = None
                            if formula is not None:
                                formula.text = None
                    if change and part == parts[change['sheet']] and cell.get('r') == change['cell']:
                        x, y = coordinates(change['cell'])
                        merges = (rectangle(node.attrib['ref']) for node in xml.findall(f'{S}mergeCells/{S}mergeCell'))
                        if (formula is None or cell.get('cm') or cell.get('vm')
                                or xml.find(f'{S}sheetProtection') is not None
                                or any(l <= x <= r and t <= y <= b for l, t, r, b in merges)):
                            raise Blocked('Unsafe target: not an unprotected, standalone, unmerged ordinary formula.')
                        if verified_result is not None:
                            try:
                                cached = Decimal(value.text) if value is not None and value.text else None
                                if (cached is None or not cached.is_finite() or cell.get('t', 'n') != 'n'
                                        or cached != verified_result):
                                    raise Blocked('Saved numeric result does not match the independent desktop readback.')
                            except InvalidOperation:
                                raise Blocked('Saved formula lacks a valid numeric result.') from None
                        formula.text = None
                        if value is not None:
                            cell.remove(value)
                    elif data_only and formula is None and value is not None and cell.get('t', 'n') == 'n':
                        value.text = None
                    elif data_only and formula is None and cell.get('t') == 'inlineStr':
                        for text in cell.findall(f'{S}is//{S}t'):
                            text.text = None
            if scoped and part not in parts.values() and part not in ('xl/workbook.xml', 'docProps/core.xml'):
                hashes[part] = sha(raw)
                continue
            namespaces = list(event for _, event in ET.iterparse(BytesIO(raw), events=('start-ns',)))
            hashes[part] = sha(json_bytes(namespaces) + ET.tostring(xml))
    if area and (matched_name != 1 or len(slots) != (area[2] - area[0] + 1) * (area[3] - area[1] + 1)):
        raise Blocked('Approved scope or complete spill footprint not found.')
    return hashes


def scoped_preserves_edit(current, saved, parts, pair, matrix, *, com_edit=False):
    before = preservation(current, parts, scoped=True, scoped_pair=pair, scoped_com_edit=com_edit)
    after = preservation(saved, parts, scoped=True, scoped_pair=pair, verified_result=matrix,
                         scoped_com_edit=com_edit)
    metadata = 'xl/metadata.xml'
    if com_edit and metadata in before and metadata in after and before[metadata] != after[metadata]:
        with ZipFile(BytesIO(saved)) as book:
            raw = book.read(metadata)
        # Permit only an added, unused root binding, not its removal or changes to metadata records.
        if raw.count(b'xlrd') == 1 and b'&#' not in raw:
            normalized, count = re.subn(
                rb'\A((?:<\?xml[^?]*\?>\s*)?<metadata\b[^<>]*?)'
                rb' xmlns:xlrd="http://schemas\.microsoft\.com/office/spreadsheetml/2017/richdata"(?=[\s>])',
                rb'\1', raw, count=1)
            if count and sha(normalized) == before[metadata]:
                namespaces = ET.iterparse(BytesIO(raw), events=('start-ns', 'start'))
                for event, node in namespaces:
                    if event == 'start':
                        break
                    if node == ('xlrd', 'http://schemas.microsoft.com/office/spreadsheetml/2017/richdata'):
                        after[metadata] = before[metadata]
                        break
    return before == after


def committed_artifact(root, oid, path):
    entry = git(root, '--literal-pathspecs', 'ls-tree', oid, '--', path)
    if entry.returncode or (entry.stdout and not entry.stdout.startswith(('100644 blob ', '100755 blob '))):
        raise Blocked('Expected a regular committed import artifact.')
    if not entry.stdout:
        return None
    object_id = entry.stdout.split(None, 3)[2]
    size = git(root, 'cat-file', '-s', object_id)
    if size.returncode or int(size.stdout) > MAX_XML:
        raise Blocked('Cannot read the committed artifact within the supported size limit.')
    content = git(root, 'cat-file', 'blob', object_id)
    if content.returncode:
        raise Blocked('Cannot read the committed artifact.')
    return content.stdout


def import_plan(root, store, args):
    sync_path = store / 'sync.json'
    require_private(store, sync_path)
    sync_bytes = read_bounded(sync_path, MAX_XML)
    sync = json.loads(sync_bytes)
    version = sync['versionSha256']
    if sync['schema'] != 1 or not SHA.fullmatch(version) or Path(sync['workbook']).suffix.lower() != '.xlsx':
        raise Blocked('Import requires an approved XLSX synchronization point.')
    retained = store / 'versions' / f'{version}.xlsx'
    require_private(retained.parent, retained)
    base = retained_bytes(retained, version)
    base_parts, base_export, old = import_snapshot(base, sync['workbook'])
    if sha(base_export['manifest.json']) != sync['manifestSha256']:
        # Initial onboarding can include a desktop readback attestation.
        if sha(build_export(base, sync['workbook'], desktop_verified=version)['manifest.json']) != sync['manifestSha256']:
            raise Blocked('Approved synchronization manifest does not match the retained workbook.')
    source = repo_path(root, sync['workbook'])
    output = repo_path(root, args.output)
    artifact_dir = repo_path(root, args.artifacts).relative_to(root)
    path = (artifact_dir / 'ordinary-formulas.json').as_posix()
    commit = git(root, 'rev-parse', '--verify', '--end-of-options', f'{args.commit}^{{commit}}')
    if commit.returncode:
        raise Blocked('Expected an approved Git commit.')
    oid = commit.stdout.strip()
    content = committed_artifact(root, oid, path)
    edited = formula_map(content) if content is not None else {}
    base_scoped = {key: scoped_map(key, base_export.get(key)) for key in SCOPED_ARTIFACTS}
    git_scoped = {key: scoped_diff(base_scoped[key], scoped_map(key, committed_artifact(root, oid,
                  (artifact_dir / key).as_posix()))) for key in SCOPED_ARTIFACTS}
    scoped = any(git_scoped.values())
    plan = {'operation': SCOPED_OPERATION if scoped else IMPORT_OPERATION,
            'profile': SCOPED_PROFILE if scoped else IMPORT_PROFILE, 'commit': oid, 'artifact': path, 'base': sync,
            'output': output.relative_to(root).as_posix(), 'gitDiff': formula_diff(old, edited),
            'workbookDiff': [], 'blockers': []}
    if scoped:
        plan['gitScopedDiff'] = git_scoped
        plan['scopedArtifacts'] = [(artifact_dir / key).as_posix() for key in SCOPED_ARTIFACTS]
    blockers = plan['blockers']
    if (source == output or output.suffix.lower() != '.xlsx' or not output.parent.is_dir()
            or git(root, 'check-ignore', '--quiet', '--', plan['output']).returncode):
        blockers.append('Choose a distinct new Git-ignored XLSX copy.')
    if any(file.name.startswith('~$') or file.with_name('~$' + file.name).exists() for file in (source, output)):
        blockers.append('Workbook lock file exists; close Excel before continuing.')
        return plan, source, output, None, {}, sync_path, sync_bytes
    if output.exists() != (args.command in ('verify-import', 'accept-import')):
        blockers.append('Expected a new copy before apply, or the saved copy for verification.')
    try:
        current = read_bounded(source, MAX_PACKAGE)
        plan['inputSha256'] = sha(current)
        parts, current_export, live = import_snapshot(current, sync['workbook'])
    except (Blocked, OSError, ValueError, KeyError, ET.ParseError, BadZipFile):
        blockers.append('Cannot read and verify the saved source workbook.')
        return plan, source, output, None, {}, sync_path, sync_bytes
    plan['workbookDiff'] = formula_diff(old, live, omissions=True)
    workbook_scoped = {key: scoped_diff(base_scoped[key], scoped_map(key, current_export.get(key)), omissions=True)
                       for key in SCOPED_ARTIFACTS}
    if scoped or any(workbook_scoped.values()):
        plan['workbookScopedDiff'] = workbook_scoped
    changes = plan['gitDiff']
    change = changes[0] if len(changes) == 1 else None
    if plan['workbookDiff'] or any(workbook_scoped.values()):
        blockers.append('Two-sided managed drift; no merge.' if changes or scoped else 'Workbook managed drift; export and review first.')
    if scoped:
        if current != base:
            blockers.append('Unsafe address drift: scoped edits require the exact approved workbook bytes; no row remapping.')
        if changes:
            blockers.append('Ordinary formula edits cannot be mixed with the scoped pair.')
        try:
            pair = validate_scoped_pair(git_scoped)
            preservation(current, parts, scoped=True, scoped_pair=pair)
        except Blocked as error:
            blockers.append(str(error))
    elif not change or any(value is None or len(value) > 8192 or not SAFE_FORMULA.fullmatch(value)
                         for value in (change['before'], change['after'])):
        blockers.append('Expected exactly one existing ordinary formula edit using simple arithmetic or SUM.')
    else:
        try:
            for address in re.findall(REFERENCE, change['after']):
                coordinates(address.replace('$', ''))
            if preservation(current, parts, change, data_only=True) != preservation(base, base_parts, change, data_only=True):
                blockers.append('Workbook structure or unmanaged content drift; target preservation is not verified.')
        except Blocked as error:
            blockers.append(str(error))
    if not args.route_sha256:
        blockers.append('Shared Excel route, authorization and backend qualification are required.')
    else:
        try:
            pin = args.route_sha256
            if not SHA.fullmatch(pin):
                raise Blocked('Expected a pinned route receipt SHA-256.')
            receipt = store / 'routes' / f'{pin}.json'
            require_private(receipt.parent, receipt)
            raw = read_bounded(receipt, MAX_XML)
            route = json.loads(raw)
            fields = ('entryPoint', 'backend', 'backendVersion', 'excelBuild', 'qualification', 'authorization')
            if (sha(raw) != pin or not isinstance(route, dict) or route.get('evidenceClass') != 'desktop'
                    or any(not isinstance(route.get(key), str) or not route[key].strip() for key in fields)
                    or route.get('operation') != plan['operation'] or route.get('profile') != plan['profile']
                    or route.get('inputSha256') != sha(current) or route.get('commit') != oid
                    or route.get('output') != plan['output']):
                raise Blocked('Route receipt does not match the approved backend, operation, profile and inputs.')
            no_op_path = store / 'routes' / f'{pin}.xlsx'
            require_private(no_op_path)
            no_op = read_bounded(no_op_path, MAX_PACKAGE)
            if (route.get('noOpSha256') != sha(no_op)
                    or preservation(no_op, parts, scoped=scoped) != preservation(current, parts, scoped=scoped)):
                raise Blocked('Qualified no-op save does not preserve workbook contents.')
            plan.update({key: route[key] for key in fields[:4]})
            plan.update(routeSha256=pin, noOpSha256=sha(no_op), preservation='verified no-op')
            native_com = (route['backend'] == 'pywin32 DispatchEx' and route['backendVersion'] == '312'
                          and route['excelBuild'] == '16.0.20527.20194 x64')
            if scoped and native_com:
                plan['copyMetadataPolicy'] = 'scoped-com-edit'
            elif (not scoped and native_com and route['qualification'] == COM_QUALIFICATION
                    and change == COM_FIXTURE_EDIT and parts == {'Calc': 'xl/worksheets/sheet1.xml'}
                    and live == {('Calc', 'B1'): '=A1*2', ('Calc', 'C1'): '=A1+1'}):
                plan['copyMetadataPolicy'] = 'qualified-com-fixture'
        except (Blocked, OSError, ValueError, TypeError, ET.ParseError, BadZipFile) as error:
            blockers.append(str(error) if isinstance(error, Blocked) else 'Invalid or missing route qualification or no-op evidence.')
    return plan, source, output, current, parts, sync_path, sync_bytes


def controlled_import(root, store, args):
    plan, source, output, current, parts, sync, previous = import_plan(root, store, args)
    plan_sha = sha(json_bytes(plan))
    if args.command == 'plan-import':
        print(json_bytes({'stage': 'dry-run', **plan, 'planSha256': plan_sha}).decode('utf-8'), end='')
        return int(bool(plan['blockers']))
    if plan['blockers']:
        raise Blocked(' '.join(plan['blockers']))
    if args.approved_plan != plan_sha or sync.read_bytes() != previous or read_bounded(source, MAX_PACKAGE) != current:
        raise Blocked('Approved plan, synchronization point or workbook changed; run a new dry-run.')
    if args.command == 'prepare-import':
        write_once(output, current, writable=True)
        print('Prepared byte-exact working copy. Desktop save and readback have not run.')
        return 0
    saved = read_bounded(output, MAX_PACKAGE)
    version = sha(saved)
    if version == sha(current) or args.saved != version:
        raise Blocked('Desktop save attestation must match the changed bytes.')
    print(f'Desktop save attested: {version}')
    if args.reopened != version:
        raise Blocked('Independent desktop reopen attestation must match the saved bytes.')
    result_parts, exported, formulas = import_snapshot(saved, plan['output'])
    _, current_export, original = import_snapshot(current, plan['base']['workbook'])
    if plan['operation'] == SCOPED_OPERATION:
        scoped_diffs = plan['gitScopedDiff']
        pair = validate_scoped_pair(scoped_diffs)
        l, t, r, b = rectangle(pair[0]['spill'])
        matrix = json.loads(args.result, parse_int=Decimal, parse_float=Decimal)
        if (not isinstance(matrix, list) or len(matrix) != b - t + 1
                or any(not isinstance(row, list) or len(row) != r - l + 1
                       or any(not isinstance(value, Decimal) or not value.is_finite() for value in row) for row in matrix)):
            raise Blocked('Independent spill readback must be a finite numeric JSON matrix for the exact footprint.')
        sequence = SEQUENCE.fullmatch(scoped_diffs['dynamic-arrays.json'][0]['after']['formula'])
        assert sequence is not None  # validate_scoped_pair checked the plan formula.
        start, step = int(sequence[3] or 1), int(sequence[4] or 1)
        if any(value != start + step * (y * (r - l + 1) + x)
               for y, row in enumerate(matrix) for x, value in enumerate(row)):
            raise Blocked('Independent spill readback does not match the approved SEQUENCE.')
        scoped_matches = all(scoped_diff(scoped_map(key, current_export.get(key)), scoped_map(key, exported.get(key)),
                                         omissions=True) == scoped_diffs[key] for key in SCOPED_ARTIFACTS)
        matches = (scoped_matches and formulas == original and result_parts == parts
                   and scoped_preserves_edit(current, saved, parts, pair, matrix,
                                             com_edit=plan.get('copyMetadataPolicy') == 'scoped-com-edit'))
    else:
        try:
            verified_result = Decimal(args.result)
        except InvalidOperation:
            raise Blocked('Independent desktop readback must record a numeric result.') from None
        if not verified_result.is_finite():
            raise Blocked('Independent desktop readback must record a finite numeric result.')
        change = plan['gitDiff'][0]
        original[change['sheet'], change['cell']] = change['after']
        com_fixture_edit = plan.get('copyMetadataPolicy') == 'qualified-com-fixture'
        matches = (formulas == original and result_parts == parts
                   and preservation(saved, result_parts, change, verified_result=verified_result,
                                    com_fixture_edit=com_fixture_edit)
                   == preservation(current, parts, change, com_fixture_edit=com_fixture_edit))
    if not matches:
        raise Blocked('Independent re-export does not match the approved edit and preservation requirements.')
    manifest = sha(exported['manifest.json'])
    print(f'Verified readback and re-export. Manifest SHA-256: {manifest}')
    if args.command == 'verify-import':
        print(json_bytes({name: json.loads(raw) for name, raw in exported.items()}).decode('utf-8'), end='')
    if args.command == 'accept-import':
        if args.reviewed != manifest:
            raise Blocked('Acceptance requires the reviewed re-export manifest SHA-256.')
        lock = store / 'accept-import.lock'
        lock.mkdir(mode=0o700)
        try:
            if (read_bounded(sync, MAX_XML) != previous or read_bounded(source, MAX_PACKAGE) != current
                    or read_bounded(output, MAX_PACKAGE) != saved
                    or any(file.with_name('~$' + file.name).exists() for file in (source, output))):
                raise Blocked('Workbook or synchronization point changed before acceptance.')
            retained = store / 'versions' / f'{version}.xlsx'
            require_private(retained)
            if not retained.exists():
                write_once(retained, saved)
            retained_bytes(retained, version)
            with tempfile.TemporaryDirectory(dir=store) as staging:
                next_sync = Path(staging) / 'sync.json'
                write_once(next_sync, json_bytes({'schema': 1, 'workbook': plan['output'], 'versionSha256': version,
                                                  'manifestSha256': manifest}), writable=True)
                # Windows cannot replace a read-only target. Keep the old bytes until atomic promotion.
                mode = sync.stat().st_mode
                if os.name == 'nt':
                    sync.chmod(stat.S_IRUSR | stat.S_IWRITE)
                try:
                    next_sync.replace(sync)
                except OSError:
                    if os.name == 'nt':
                        sync.chmod(mode)
                    raise
        finally:
            lock.rmdir()
        print('Accepted the verified copy as the new synchronization point; original unchanged.')
    return 0


def preserved_parts(data, mashup_part, *, allow_cell_values=False):
    with ZipFile(BytesIO(data)) as book:
        if sum(part.file_size for part in book.infolist()) > MAX_PACKAGE:
            raise Blocked('Workbook exceeds the package comparison limit.')
        checked = {}
        for name in book.namelist():
            if name == mashup_part:
                continue
            raw = book.read(name)
            if name == 'docProps/core.xml':
                if b'xmlns:dcterms="http://purl.org/dc/terms/"' in raw and b'<!' not in raw:
                    raw = re.sub(rb'(<dcterms:modified(?:\s+[^<>]*)?>)\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ'
                                 rb'(</dcterms:modified>)', rb'\1\2', raw, count=1)
            elif allow_cell_values and re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                text = raw.decode('utf-8-sig')
                if '\0' in text or '<!DOCTYPE' in text or '<!ENTITY' in text:
                    raise Blocked('Unsupported workbook XML.')
                node = ET.fromstring(text, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
                if node.tag == f'{S}worksheet':
                    for cell in node.findall(f'{S}sheetData/{S}row/{S}c'):
                        if cell.get('t') not in (None, 'n', 'b') or cell.find(f'{S}f') is not None:
                            continue
                        for value in cell.findall(f'{S}v'):
                            value.text = None
                raw = ET.tostring(node)
            checked[name] = sha(raw)
    return checked


def excel_copy_metadata_changes(base, result, folder):
    part = 'xl/workbook.xml'
    with ZipFile(BytesIO(base)) as before, ZipFile(BytesIO(result)) as after:
        old, new = before.read(part), after.read(part)
    if old == new:
        return []

    workbook = S[1:-1] + ' workbook'
    mc = 'http://schemas.openxmlformats.org/markup-compatibility/2006 '
    targets = {
        (workbook, mc + 'AlternateContent', mc + 'Choice',
         'http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac absPath'): ('absPath.url', 'url'),
        (workbook, 'http://schemas.microsoft.com/office/spreadsheetml/2014/revision revisionPtr'):
            ('revisionPtr.documentId', 'documentId'),
    }
    attribute = rb'''[ \t\r\n]+([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')'''
    start_tag = re.compile(rb'<[^\s/>]+((?:' + attribute + rb')*)\s*/?>')

    def spans(raw):
        found: dict[str, list[tuple[str, int, int]]] = {}
        if b'<!' in raw or b'\0' in raw:
            return found
        parser = expat.ParserCreate(namespace_separator=' ')
        stack: list[str] = []

        def start(name, attrs):
            stack.append(name)
            target = targets.get(tuple(stack))
            if target is None:
                return
            field, key = target
            offset = parser.CurrentByteIndex
            tag = start_tag.match(raw, offset)
            if tag is None:
                return
            for match in re.finditer(attribute, tag[1]):
                if match[1] == key.encode('ascii'):
                    left, right = match.span(2 if match[2] is not None else 3)
                    found.setdefault(field, []).append((attrs[key], tag.start(1) + left, tag.start(1) + right))

        parser.StartElementHandler = start
        parser.EndElementHandler = lambda _: stack.pop()
        parser.Parse(raw, True)
        return found

    try:
        left, right = spans(old), spans(new)
    except expat.ExpatError:
        return None
    changes = []
    edits: tuple[list[tuple[int, int]], list[tuple[int, int]]] = ([], [])
    for field, _ in targets.values():
        if len(left.get(field, [])) != 1 or len(right.get(field, [])) != 1:
            continue
        (a, a_start, a_end), = left[field]
        (b, b_start, b_end), = right[field]
        if a == b:
            continue
        if field == 'absPath.url':
            # The original may have been copied since Excel last saved it.
            local = r'[A-Za-z]:\\(?:[^<>:"/\\|?*\x00-\x1f]+\\)*'
            if (not re.fullmatch(local, a) or not re.fullmatch(local, b)
                    or '..' in PureWindowsPath(a).parts or b != str(folder).rstrip('\\') + '\\'):
                continue
        else:
            guid = r'\{[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\}'
            # Fresh local SaveAs can emit 8_{GUID}; reopening and saving switches to 13_ncr:1_{GUID}.
            if not re.fullmatch(r'(?:8|13_ncr:1)_' + guid, a) or not re.fullmatch(r'13_ncr:1_' + guid, b):
                continue
        changes.append(field)
        edits[0].append((a_start, a_end))
        edits[1].append((b_start, b_end))

    def masked(raw, ranges):
        for start, end in sorted(ranges, reverse=True):
            raw = raw[:start] + raw[end:]
        return raw

    # Compare original XML bytes except for the two validated attribute values.
    return changes if masked(old, edits[0]) == masked(new, edits[1]) else None


def checked_query_snapshot(data):
    _, _, snapshot = workbook_artifacts(data, '.xlsx', power_query=True)
    if snapshot is None:
        raise Blocked('No supported saved Power Query M was found.')
    if snapshot.wiring['hasDataModel'] or snapshot.risky_open:
        raise Blocked('Data Model, unknown connections, or unsafe opening effects are outside the Power Query pilot.')
    return snapshot


def verify_load_move(data, result, before: QuerySnapshot, after: QuerySnapshot, query, destination, folder):
    if query not in before.queries:
        raise Blocked('The intended query is not in the approved baseline.')
    ids = {row['id'] for row in before.wiring['connections'] if row['query'] == query}
    loads = [row for row in before.wiring['worksheetLoads'] if row['connectionId'] in ids]
    if len(ids) != 1 or len(loads) != 1:
        raise Blocked('The load pilot requires exactly one mapped worksheet table for the query.')
    old, = loads
    expected = {**before.wiring, 'worksheetLoads': [
        {**row, 'range': destination} if row == old else row for row in before.wiring['worksheetLoads']]}
    left, top, right, bottom = rectangle(old['range'])
    new_left, new_top, new_right, new_bottom = rectangle(destination)
    if ((top, bottom, right - left) != (new_top, new_bottom, new_right - new_left)
            or not (new_right < left or right < new_left)):
        raise Blocked('The new range must be disjoint, same-size, and on the same rows of the same sheet.')
    if after.wiring != expected or before.load_parts != after.load_parts:
        raise Blocked('Saved load wiring does not match the intended move.')

    sheet, table = before.load_parts[old['sheet'], old['table']]

    def overlaps_destination(reference):
        x1, y1, x2, y2 = rectangle(reference)
        return x1 <= new_right and new_left <= x2 and y1 <= bottom and top <= y2

    if any(overlaps_destination(ref) for part, ref in before.table_ranges[old['sheet']].items() if part != table):
        raise Blocked('The new range intersects another table.')
    old_parts = preserved_parts(data, None)
    new_parts = preserved_parts(result, None)
    for part in (sheet, table):
        del old_parts[part], new_parts[part]
    if before.workbook_part == after.workbook_part == 'xl/workbook.xml':
        if old_parts.pop('xl/workbook.xml') != new_parts.pop('xl/workbook.xml'):
            if excel_copy_metadata_changes(data, result, folder) is None:
                raise Blocked('Could not verify preservation of the workbook document.')
    if old_parts != new_parts:
        raise Blocked('Could not verify preservation of adjacent workbook parts.')

    def normalize(package, moved):
        def xml(book, part):
            raw = book.read(part).decode('utf-8-sig')
            if '\0' in raw or '<!' in raw:
                raise Blocked('Unsupported XML in moved table or worksheet.')
            # Keep namespace bindings and processing instructions in the preservation check.
            events = ET.iterparse(StringIO(raw), events=('start', 'end', 'start-ns', 'end-ns', 'pi'))
            position = 0
            metadata = []
            document = None
            for event, item in events:
                if event in ('start', 'end'):
                    position += 1
                    if document is None and event == 'start':
                        document = item
                else:
                    metadata.append((position, event, ET.tostring(item) if event == 'pi' else item))
            return document, metadata

        with ZipFile(BytesIO(package)) as book:
            definition, table_metadata = xml(book, table)
            worksheet, sheet_metadata = xml(book, sheet)
        expected_range = destination if moved else old['range']
        for node in definition.findall(f'{S}autoFilter'):
            if node.get('ref') != expected_range:
                raise Blocked('The table filter range does not match its load range.')
            node.set('ref', old['range'])
        if moved:
            definition.set('ref', old['range'])
        if any(overlaps_destination(node.attrib['ref']) for node in worksheet.findall(f'{S}mergeCells/{S}mergeCell')):
            raise Blocked('The new range intersects merged cells.')
        offset = new_left - left
        occupied = set()
        for row in worksheet.findall(f'{S}sheetData/{S}row'):
            cells = row.findall(f'{S}c')
            for cell in cells:
                address = cell.attrib['r']
                x, y = coordinates(address)
                if address in occupied or int(row.attrib['r']) != y:
                    raise Blocked('Unsupported worksheet cell layout.')
                occupied.add(address)
                formula = cell.find(f'{S}f')
                if formula is not None and 'ref' in formula.attrib and overlaps_destination(formula.attrib['ref']):
                    raise Blocked('The new range intersects a reserved formula range.')
                if not top <= y <= bottom:
                    continue
                empty_left, empty_right = (left, right) if moved else (new_left, new_right)
                if empty_left <= x <= empty_right:
                    raise Blocked('The old range after the move and the new range before it must be empty.')
                if (new_left <= x <= new_right if moved else left <= x <= right):
                    if formula is not None:
                        raise Blocked('Formulas in moved cells are outside the load pilot.')
                    if moved:
                        col, label = x - offset, ''
                        while col:
                            col, digit = divmod(col - 1, 26)
                            label = chr(65 + digit) + label
                        cell.set('r', f'{label}{y}')
            if cells:
                if len(cells) != len(row):
                    raise Blocked('Unsupported worksheet row structure.')
                row[:] = sorted(cells, key=lambda cell: coordinates(cell.attrib['r']))
        return ET.tostring(definition), ET.tostring(worksheet), table_metadata, sheet_metadata

    if normalize(data, False) != normalize(result, True):
        raise Blocked('Could not verify preservation of the table and worksheet outside the intended move.')
    return old


def power_query_load_change(root, store, args):
    sync_file = store / 'sync.json'
    lock = store / 'load-accept.lock'
    require_private(store, sync_file, lock)
    sync_bytes = read_bounded(sync_file, MAX_XML)
    sync = json.loads(sync_bytes)
    meta, artifacts = verified_export(root, store, repo_path(root, args.baseline), sync['manifestSha256'])
    if ('power-query-inventory.json' not in artifacts or Path(meta['workbook']).suffix.lower() != '.xlsx'
            or any(sync.get(key) != meta[key] for key in ('schema', 'workbook', 'versionSha256'))):
        raise Blocked('Use the approved Power Query XLSX baseline.')
    source = workbook_path(root, meta['workbook'], None)
    candidate = workbook_path(root, args.copy, None)
    output = repo_path(root, args.destination)
    if (candidate.suffix.lower() != '.xlsx' or source.samefile(candidate)
            or git(root, 'check-ignore', '--quiet', '--', args.copy).returncode != 0):
        raise Blocked('Use a separate Git-ignored XLSX working copy.')
    if output.exists() or not output.parent.is_dir():
        raise Blocked('Choose a new export directory under an existing parent.')
    if CREDENTIAL.search(args.destination):
        raise Blocked('Publication blocked: possible credential in the export path.')
    for evidence in (args.qualified_route, args.save_evidence, args.reopen_evidence):
        if not EVIDENCE_REF.fullmatch(evidence) or CREDENTIAL.search(evidence):
            raise Blocked('Supply safe references for qualified route, save and independent reopen evidence.')
    if args.save_evidence == args.reopen_evidence:
        raise Blocked('Save and independent reopen require separate evidence references.')
    data = read_bounded(source, MAX_PACKAGE)
    if sha(data) != sync['versionSha256']:
        raise Blocked('The original workbook differs from the approved baseline.')
    result = read_bounded(candidate, MAX_PACKAGE)
    version = sha(result)
    if version != args.reopened_sha256 or version == sync['versionSha256']:
        raise Blocked('Independent reopen must attest the exact changed candidate checksum.')
    before, after = checked_query_snapshot(data), checked_query_snapshot(result)
    old = verify_load_move(data, result, before, after, args.query, args.to, candidate.parent)
    exported = build_export(result, candidate.relative_to(root).as_posix(), power_query=True)
    review = {'kind': 'power-query-manual-load-review', 'syncSha256': sha(sync_bytes),
              'manifestSha256': sha(exported['manifest.json']), 'candidateSha256': version,
              'exportDestination': output.relative_to(root).as_posix(),
              'change': {'query': args.query, 'from': old, 'to': {**old, 'range': args.to}},
              'before': before.wiring, 'after': after.wiring,
              'operatorAttestations': {'route': args.qualified_route, 'save': args.save_evidence,
                                       'reopen': args.reopen_evidence},
              'dataAccessOrRefreshByCli': False}
    digest = sha(json_bytes(review))
    if args.command == 'pq-load-review':
        print(json_bytes({**review, 'reviewSha256': digest}).decode('utf-8'), end='')
        return
    if args.accepted != digest:
        raise Blocked('The accepted review checksum does not match the current inputs.')

    retained = store / 'versions' / f'{version}.xlsx'
    receipt = retained.parent / f'{digest}.load-review.json'
    require_private(store, retained.parent, retained, receipt)
    next_sync = json_bytes({'schema': 1, 'workbook': candidate.relative_to(root).as_posix(),
                            'versionSha256': version, 'manifestSha256': review['manifestSha256']})
    # Serialize acceptance. The sync pointer is the final commit, not the presence of an export.
    lock.mkdir(mode=0o700)
    created = []
    published = committed = False
    pending = lock / 'sync.json'
    try:
        if not retained.exists():
            write_once(retained, result)
            created.append(retained)
        retained_bytes(retained, version)
        evidence = json_bytes({**review, 'reviewSha256': digest})
        if not receipt.exists():
            write_once(receipt, evidence)
            created.append(receipt)
        retained_bytes(receipt, sha(evidence))
        write_export(output, exported)
        published = True
        write_once(pending, next_sync)
        with ExitStack() as handles:
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes

                kernel = ctypes.WinDLL('kernel32', use_last_error=True)  # type: ignore[attr-defined]
                open_file = kernel.CreateFileW
                open_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
                open_file.restype = wintypes.HANDLE
                kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
                for path in (source, candidate):
                    # GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING: deny writes and replacement until commit.
                    handle = open_file(str(path), 0x80000000, 1, None, 3, 0, None)
                    if handle == ctypes.c_void_p(-1).value:
                        raise Blocked('Could not hold a read-only workbook handle through acceptance.')
                    handles.callback(kernel.CloseHandle, handle)
            if (read_bounded(sync_file, MAX_XML) != sync_bytes
                    or read_bounded(workbook_path(root, meta['workbook'], None), MAX_PACKAGE) != data
                    or read_bounded(workbook_path(root, args.copy, None), MAX_PACKAGE) != result):
                raise Blocked('Inputs changed during acceptance.')
            if os.name == 'nt':
                sync_file.chmod(stat.S_IWRITE | stat.S_IRUSR)
            pending.replace(sync_file)
            committed = True
    except BaseException:
        if read_bounded(sync_file, MAX_XML) != next_sync:
            if os.name == 'nt':
                sync_file.chmod(stat.S_IRUSR)
            if published:
                shutil.rmtree(output)
            for path in created:
                path.chmod(stat.S_IWRITE | stat.S_IRUSR)
                path.unlink()
        raise
    finally:
        try:
            if pending.exists():
                pending.chmod(stat.S_IWRITE | stat.S_IRUSR)
                pending.unlink()
            lock.rmdir()
        except OSError:
            if not committed:
                raise
            print('Acceptance committed; inspect the stale acceptance lock before another attempt.', file=sys.stderr)
    print('Accepted the verified copy and advanced the synchronization point.')


def unique_json_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise Blocked('Duplicate keys in the M edit are not allowed.')
    return result


def verify_query_copy(data, snapshot, result, expected, folder):
    observed = checked_query_snapshot(result)
    if observed.queries != expected:
        raise Blocked('Saved M differs from the approved edit or an adjacent query changed.')
    if observed.wiring != snapshot.wiring:
        raise Blocked('Power Query load wiring changed.')
    before = preserved_parts(data, snapshot.part)
    after = preserved_parts(result, observed.part)
    workbook_changed = False
    if snapshot.workbook_part == observed.workbook_part == 'xl/workbook.xml':
        workbook_changed = before.pop('xl/workbook.xml') != after.pop('xl/workbook.xml')
    if observed.part != snapshot.part or observed.metadata != snapshot.metadata or before != after:
        raise Blocked('Could not verify preservation of adjacent workbook parts.')
    save_metadata = excel_copy_metadata_changes(data, result, folder) if workbook_changed else []
    if save_metadata is None:
        raise Blocked('Could not verify preservation of adjacent workbook parts.')
    return save_metadata


def power_query_import(root, store, args):
    # Every phase recomputes the plan against the original and the approved sync.
    sync_file = store / 'sync.json'
    preview = preview_path(store, args.label)
    attempt = repo_path(store, f'candidates/{args.label}')
    candidate = attempt / 'workbook.xlsx'
    receipt = attempt / 'plan.json'
    lock = candidate.with_name('~$' + candidate.name)
    require_private(store, sync_file, preview.parent, attempt.parent, attempt, candidate, receipt)
    if lock.exists():
        raise Blocked('Candidate workbook lock file exists; close Excel before proceeding.')
    if preview.exists() or (args.command != 'pq-verify' and attempt.exists()):
        raise Blocked('Choose a new candidate label; a failed attempt must not be reused.')
    if not EVIDENCE_REF.fullmatch(args.qualified_route) or CREDENTIAL.search(args.qualified_route):
        raise Blocked('Supply a qualified route and version evidence reference.')
    sync_bytes = read_bounded(sync_file, MAX_XML)
    sync = json.loads(sync_bytes)
    metadata, baseline = verified_export(root, store, repo_path(root, args.baseline), sync['manifestSha256'])
    profile = Path(metadata['workbook']).suffix.lower()
    if profile != '.xlsx':
        raise Blocked('The Power Query pilot supports synthetic XLSX only.')
    if any(sync.get(key) != metadata[key] for key in ('schema', 'workbook', 'versionSha256')):
        raise Blocked('The approved sync does not identify the retained workbook.')
    source = workbook_path(root, metadata['workbook'], None)
    data = read_bounded(source, MAX_PACKAGE)
    base_digest = sha(data)
    snapshot = checked_query_snapshot(data)
    edit = read_bounded(repo_path(root, args.edit), MAX_XML)
    proposed = json.loads(edit, object_pairs_hook=unique_json_object)
    if (not isinstance(proposed, dict) or set(proposed) != {'kind', 'queries'} or proposed['kind'] != M_SOURCE
            or not isinstance(proposed['queries'], dict) or baseline.get('power-query.json') is None):
        raise Blocked('Use the editable M artifact, not an inventory or other edit input.')
    expected = proposed['queries']
    approved_queries = json.loads(baseline['power-query.json'])['queries']
    if expected.keys() != approved_queries.keys():
        raise Blocked('Standard M import does not create, rename, or remove queries.')
    changes = [name for name in approved_queries if approved_queries[name] != expected[name]]
    if len(changes) != 1:
        raise Blocked('The M pilot requires one changed existing query.')
    query, = changes
    check_expression(expected[query], CREDENTIAL)
    if snapshot.queries != approved_queries:
        changed = sorted(name for name in snapshot.queries.keys() | approved_queries.keys()
                         if snapshot.queries.get(name) != approved_queries.get(name))
        raise Blocked('Managed drift; no merge was attempted. Saved workbook vs sync: changed M or membership for '
                      f'{", ".join(changed)}. Proposed M vs sync: changed M for {query}.')
    target_ids = {connection['id'] for connection in snapshot.wiring['connections'] if connection['query'] == query}
    if (len(snapshot.queries) < 2 or not any(load['connectionId'] in target_ids
                                           for load in snapshot.wiring['worksheetLoads'])):
        raise Blocked('The pilot requires a verified worksheet load for the edited query and an adjacent query.')
    if base_digest != metadata['versionSha256']:
        version = metadata['versionSha256']
        retained = retained_bytes(store / 'versions' / f'{version}.xlsx', version)
        previous = checked_query_snapshot(retained)
        if previous != snapshot or (preserved_parts(retained, previous.part, allow_cell_values=True)
                                    != preserved_parts(data, snapshot.part, allow_cell_values=True)):
            raise Blocked('Saved workbook differs from approved sync beyond supported data-only drift.')
    plan = {'kind': 'power-query-import-plan', 'workbook': metadata['workbook'], 'baseSha256': base_digest,
            'syncSha256': sha(sync_bytes), 'editSha256': sha(edit), 'query': query, 'candidate': args.label,
            'qualifiedRoute': args.qualified_route, 'profile': 'synthetic-xlsx',
            'checks': ['all saved M', 'load wiring', 'adjacent workbook parts'],
            'excelSaveMetadataPolicy': 'local-copy-path-and-revision-id-v2', 'refresh': False}
    plan_digest = sha(json_bytes(plan))
    if args.command == 'pq-plan':
        print(json_bytes({**plan, 'planSha256': plan_digest}).decode('utf-8'), end='')
        return
    if args.approved_plan != plan_digest:
        raise Blocked('The approved plan checksum does not match the current inputs.')
    workbook_path(root, metadata['workbook'], None)
    if (read_bounded(source, MAX_PACKAGE) != data or read_bounded(sync_file, MAX_XML) != sync_bytes
            or read_bounded(repo_path(root, args.edit), MAX_XML) != edit or lock.exists()):
        raise Blocked('Inputs changed during the eligibility recheck.')
    if args.command == 'pq-prepare':
        attempt.parent.mkdir(mode=0o700, exist_ok=True)
        write_export(attempt, {candidate.name: data, receipt.name: json_bytes({'planSha256': plan_digest})})
        print('Prepared a disposable private copy. No Excel write or refresh was performed.')
        return

    if not receipt.is_file() or read_bounded(receipt, MAX_XML) != json_bytes({'planSha256': plan_digest}):
        raise Blocked('No matching preparation receipt for this candidate.')
    for evidence in (args.save_evidence, args.reopen_evidence):
        if not EVIDENCE_REF.fullmatch(evidence) or CREDENTIAL.search(evidence):
            raise Blocked('Supply separate operator evidence references for save and independent reopen.')
    result = read_bounded(candidate, MAX_PACKAGE)
    digest = sha(result)
    if args.reopened_sha256 != digest or digest == base_digest:
        raise Blocked('Independent desktop reopen must attest the exact changed candidate checksum.')
    save_metadata = verify_query_copy(data, snapshot, result, expected, candidate.parent)
    artifacts = build_export(result, metadata['workbook'], power_query=True)
    # This evidence is intentionally not a publishable onboarding export or a sync update.
    artifacts['manifest.json'] = json_bytes({'kind': 'power-query-saved-package-verification', 'planSha256': plan_digest,
                                            'candidateSha256': digest,
                                            'excelSaveMetadataChanges': save_metadata,
                                            'operatorAttestations': {'qualifiedRoute': args.qualified_route,
                                                                     'save': args.save_evidence,
                                                                     'reopen': args.reopen_evidence},
                                            'files': {name: sha(content) for name, content in artifacts.items()
                                                      if name != 'manifest.json'}})
    preview.parent.mkdir(mode=0o700, exist_ok=True)
    write_export(preview, artifacts)
    print('Verified saved M, load wiring and adjacent parts. Desktop save and reopen were operator-attested.')


def create_pilot_workspace(parent: Path) -> tuple[Path, Path, Path]:
    work = parent / f'pq-pilot-{uuid4().hex}'
    # Set a protected, inheritable DACL at creation; do not alter the temp parent's ACL.
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', r'''
            $ErrorActionPreference = 'Stop'
            $path = $env:EXCEL_PILOT_ATTEMPT_PATH
            if ([IO.Directory]::Exists($path) -or [IO.File]::Exists($path)) { exit 1 }
            $operator = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
            $security = [Security.AccessControl.DirectorySecurity]::new()
            $security.SetSecurityDescriptorSddlForm("D:P(A;OICI;FA;;;$operator)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)",
                                                    [Security.AccessControl.AccessControlSections]::Access)
            [System.IO.DirectoryInfo]::new($path).Create($security)
        '''], env={**os.environ, 'EXCEL_PILOT_ATTEMPT_PATH': str(work)}, capture_output=True,
    )
    if result.returncode or not work.is_dir():
        raise Blocked('Could not create a private pilot attempt directory with an explicit Windows ACL.')
    require_private(work)
    root = work / 'fixture'
    store = work / 'private'
    root.mkdir()
    store.mkdir()
    store = storage_path(root, store)
    require_private(work, root, store)
    return work, root, store


def native_pq_pilot(desktop: bool) -> None:
    if not desktop:
        raise Blocked('The native pilot requires explicit --desktop.')
    if os.name != 'nt':
        raise Blocked('The native pilot requires a logged-in Windows desktop with Excel and pywin32.')

    parent = Path(tempfile.gettempdir()).resolve() / 'kilo'
    parent.mkdir(exist_ok=True)
    work, root, store = create_pilot_workspace(parent)
    print(f'Private pilot directory: {work}', flush=True)

    base, sync = root / 'base.xlsx', store / 'sync.json'
    report = work / 'report.json'
    phases: dict[str, Any] = {}
    evidence: dict[str, Any] = {'kind': 'native-power-query-pilot', 'status': 'blocked', 'phases': phases,
                                'promoted': False}
    runtime = None
    stage = 'fixture'
    worker = Path(__file__).resolve().with_name('excel_pq_desktop.py')

    def digest_of(path: Path) -> str:
        return sha(read_bounded(path, MAX_PACKAGE))

    def native(action: str, path: Path, digest: str = '') -> dict:
        try:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(worker), action, str(path), digest],
                                    stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8', timeout=180)
        except subprocess.TimeoutExpired as error:
            steps = (error.stderr or b'').decode('utf-8', errors='replace').splitlines()
            last = steps[-1] if steps else 'not started'
            cleanup = ('Dedicated Excel was assigned to the timeout job.' if 'Excel attached to timeout job' in steps
                       else 'Excel startup/cleanup was not confirmed.')
            raise Blocked(f'Native {action} timed out after 180 seconds (last step: {last}). '
                          f'{cleanup} Do not use this copy.') from error
        if result.returncode:
            raise Blocked(f'Native {action}: {result.stderr.strip()}')
        observed = json.loads(result.stdout)
        if runtime is not None and observed['runtime'] != runtime:
            raise Blocked('Excel or backend version changed between native phases.')
        return observed

    def checkpoint() -> None:
        pending = report.with_suffix('.tmp')
        pending.write_bytes(json_bytes(evidence))
        pending.replace(report)

    try:
        evidence['desktopWorkerSha256'] = digest_of(worker)
        checkpoint()
        phases['fixture'] = native('create', base)
        runtime = phases['fixture']['runtime']
        data = read_bounded(base, MAX_PACKAGE)
        snapshot = checked_query_snapshot(data)
        evidence['baseSha256'] = sha(data)
        if snapshot.queries != {LOADED: BASE_M, NEIGHBOR: NEIGHBOR_M}:
            raise Blocked('The fixture did not save the expected synthetic queries.')

        stage = 'plan'
        baseline = root / 'baseline'
        with redirect_stdout(StringIO()):
            export(root, store, base.name, 'baseline', power_query=True)
            preview = preview_path(store, 'baseline')
            reviewed = digest_of(preview / 'manifest.json')
            _, artifacts = verified_export(root, store, preview, reviewed)
            write_export(baseline, artifacts)
            accept_initial(root, store, baseline.name, reviewed)
        evidence['syncSha256'] = digest_of(sync)
        expected = {**snapshot.queries, LOADED: EDITED_M}
        edit = root / 'proposed.json'
        write_once(edit, json_bytes({'kind': M_SOURCE, 'queries': expected}))
        args = argparse.Namespace(command='pq-plan', baseline=baseline.name, edit=edit.name, label=LABEL,
                                  qualified_route=f"synthetic qualification trial #52 pywin32 {runtime['pywin32']} "
                                                  f"Excel {runtime['excel']}")
        with redirect_stdout(StringIO()) as output:
            power_query_import(root, store, args)
        plan = json.loads(output.getvalue())
        phases['plan'] = {'plan': plan, 'approved': False, 'beforeM': snapshot.queries[LOADED], 'afterM': EDITED_M,
                          'wiring': snapshot.wiring}
        checkpoint()
        print(json_bytes(phases['plan']).decode('utf-8'), end='', flush=True)
        try:
            approved = input('Approve this plan and both copy saves by entering planSha256: ').strip()
        except EOFError:
            approved = ''
        if approved != plan['planSha256']:
            raise Blocked('Plan was not approved; no copies were saved.')
        phases['plan']['approved'] = True
        args.approved_plan = approved
        checkpoint()

        stage = 'noop'
        noop = work / 'noop' / 'workbook.xlsx'
        noop.parent.mkdir()
        shutil.copyfile(base, noop)
        phases['noop'] = {'save': native('noop', noop, evidence['baseSha256'])}
        checkpoint()
        noop_data = read_bounded(noop, MAX_PACKAGE)
        if sha(noop_data) != phases['noop']['save']['sha256']:
            raise Blocked('No-op copy changed after native save.')
        changes = verify_query_copy(data, snapshot, noop_data, snapshot.queries, noop.parent)
        phases['noop']['excelSaveMetadataChanges'] = changes
        noop_read = native('reopen', noop, phases['noop']['save']['sha256'])
        phases['noop']['reopen'] = noop_read
        if noop_read['queries'] != snapshot.queries:
            raise Blocked('No-op native reopen did not preserve both formulas.')
        checkpoint()

        stage = 'prepare'
        args.command = 'pq-prepare'
        power_query_import(root, store, args)
        candidate = store / 'candidates' / args.label / 'workbook.xlsx'
        phases['prepare'] = {'baseSha256': digest_of(candidate)}
        stage = 'save'
        phases['save'] = native('save', candidate, evidence['baseSha256'])
        checkpoint()
        stage = 'reopen'
        # Read-only Open does not disable refresh-on-open. Inspect the saved package first.
        saved = read_bounded(candidate, MAX_PACKAGE)
        if sha(saved) != phases['save']['sha256']:
            raise Blocked('Candidate changed after native save.')
        checked_query_snapshot(saved)
        phases['reopen'] = native('reopen', candidate, phases['save']['sha256'])
        if (phases['reopen']['queries'] != expected
                or phases['reopen']['connection'] != noop_read['connection']):
            raise Blocked('Independent native reopen did not read the approved formulas or original connection.')
        checkpoint()
        stage = 'verify'
        args.command = 'pq-verify'
        args.reopened_sha256 = phases['reopen']['sha256']
        args.save_evidence = 'report.json phases/save'
        args.reopen_evidence = 'report.json phases/reopen'
        power_query_import(root, store, args)
        verification = preview_path(store, args.label) / 'manifest.json'
        phases['verify'] = json.loads(read_bounded(verification, MAX_XML))
        evidence['status'] = 'verified'
    except BaseException as error:
        evidence['failure'] = {'phase': stage, 'reason': str(error) or type(error).__name__}
        raise
    finally:
        for key, path in (('base', base), ('sync', sync)):
            before = evidence.get(f'{key}Sha256')
            if before is not None:
                try:
                    unchanged = digest_of(path) == before
                except (OSError, Blocked):
                    unchanged = False
                evidence[f'{key}Unchanged'] = unchanged
                if not unchanged:
                    evidence['status'] = 'blocked'
                    evidence.setdefault('failure', {'phase': 'integrity', 'reason': f'The {key} changed.'})
        checkpoint()
    if evidence['status'] != 'verified':
        raise Blocked('Base or sync changed; do not use this copy.')
    print(f'Verified disposable candidate: {candidate}\nPrivate evidence: {report}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    export_cmd = commands.add_parser('export', help='Export one saved workbook for private review.')
    export_cmd.add_argument('workbook', help='Workbook path relative to the Git worktree root.')
    export_cmd.add_argument('label', help='New label for the private review directory.')
    export_cmd.add_argument('--power-query', action='store_true', help='Also export the restricted saved M and load inventory.')
    export_cmd.add_argument('--desktop-verified', metavar='WORKBOOK_SHA256',
                            help='Attest qualified, authorized desktop readback for the exact saved workbook.')
    copy_cmd = commands.add_parser('copy-template', help='Make a byte-exact working copy of a pinned XLSM.')
    copy_cmd.add_argument('workbook', help='New, Git-ignored XLSM path relative to the worktree root.')
    for command in (copy_cmd, export_cmd):
        command.add_argument('--template-sha256', required=command is copy_cmd,
                             help='Approved template manifest SHA-256 (required for XLSM).')
    publish_cmd = commands.add_parser('publish', help='Publish a reviewed private export into Git.')
    publish_cmd.add_argument('label', help='Reviewed private export label.')
    publish_cmd.add_argument('destination', help='New export directory relative to the Git worktree root.')
    accept_cmd = commands.add_parser('accept-initial', help='Record the first synchronization point after review.')
    accept_cmd.add_argument('candidate', help='Reviewed export directory relative to the Git worktree root.')
    for command in (publish_cmd, accept_cmd):
        command.add_argument('--reviewed', required=True, help='SHA-256 of the manifest you reviewed.')
    plan_cmd = commands.add_parser('pq-plan', help='Plan an existing-query M edit without writing anything.')
    prepare_cmd = commands.add_parser('pq-prepare', help='Recheck the approved plan and stage an XLSX copy.')
    verify_cmd = commands.add_parser('pq-verify', help='Re-export and verify an independently reopened XLSX copy.')
    for command in (plan_cmd, prepare_cmd, verify_cmd):
        command.add_argument('baseline', help='Published export at the approved synchronization point.')
        command.add_argument('edit', help='Worktree-relative path to the proposed power-query.json.')
        command.add_argument('label', help='Private candidate label, unique for each attempt.')
        command.add_argument('--qualified-route', required=True,
                             help='Attest a qualified, authorized desktop route; identify implementation/version and evidence.')
    for command in (prepare_cmd, verify_cmd):
        command.add_argument('--approved-plan', required=True, help='SHA-256 from the reviewed dry-run.')
    verify_cmd.add_argument('--reopened-sha256', required=True,
                            help='Attest independent desktop readback of the exact saved candidate bytes.')
    verify_cmd.add_argument('--save-evidence', required=True, help='Reference to the operator record of desktop save.')
    verify_cmd.add_argument('--reopen-evidence', required=True, help='Reference to independent desktop reopen evidence.')
    load_review = commands.add_parser('pq-load-review', help='Review a manually moved query table without writing.')
    load_accept = commands.add_parser('pq-load-accept', help='Accept the exact reviewed load move as the new baseline.')
    for command in (load_review, load_accept):
        command.add_argument('baseline', help='Published export at the approved synchronization point.')
        command.add_argument('copy', help='Separate Git-ignored XLSX, manually changed and independently reopened.')
        command.add_argument('destination', help='New worktree-relative directory for the accepted export.')
        command.add_argument('--query', required=True, help='Existing query whose worksheet table was moved.')
        command.add_argument('--to', required=True, help='Intended new A1 range in the same sheet.')
        command.add_argument('--qualified-route', required=True)
        command.add_argument('--save-evidence', required=True)
        command.add_argument('--reopen-evidence', required=True)
        command.add_argument('--reopened-sha256', required=True)
    load_accept.add_argument('--accepted', required=True, help='SHA-256 of the review you explicitly accept.')
    for command in (copy_cmd, export_cmd, publish_cmd, accept_cmd, plan_cmd, prepare_cmd, verify_cmd,
                    load_review, load_accept):
        command.add_argument('--store', required=True, help='Existing private, access-controlled directory outside Git.')
    for name in ('plan-import', 'prepare-import', 'verify-import', 'accept-import'):
        command = commands.add_parser(name)
        command.add_argument('artifacts', help='Directory containing the editable formula artifact in Git.')
        command.add_argument('output', help='Distinct Git-ignored working XLSX path.')
        command.add_argument('--store', required=True)
        command.add_argument('--commit', required=True, help='Approved Git commit containing the edit.')
        command.add_argument('--route-sha256', required=name != 'plan-import')
        if name != 'plan-import':
            command.add_argument('--approved-plan', required=True)
        if name in ('verify-import', 'accept-import'):
            command.add_argument('--saved', required=True, help='SHA-256 attested after desktop save and close.')
            command.add_argument('--reopened', required=True, help='SHA-256 attested after independent desktop reopen.')
            command.add_argument('--result', required=True,
                                 help='Independent numeric readback, or a row-major JSON matrix for a spill (synthetic data only).')
        if name == 'accept-import':
            command.add_argument('--reviewed', required=True, help='Verified re-export manifest SHA-256.')
    pilot = commands.add_parser('pq-pilot', help='Run the disposable native Power Query pilot on Windows.')
    pilot.add_argument('--desktop', action='store_true', help='Authorize Excel to create a fresh synthetic fixture.')
    args = parser.parse_args()
    try:
        if args.command == 'pq-pilot':
            native_pq_pilot(args.desktop)
            return 0
        result = git(Path.cwd(), 'rev-parse', '--show-toplevel')
        if result.returncode:
            raise Blocked('Run from a Git worktree.')
        root = Path(result.stdout.rstrip('\r\n')).resolve()
        store = storage_path(root, args.store)
        if args.command == 'copy-template':
            copy_template(root, store, args.workbook, args.template_sha256)
        elif args.command == 'export':
            export(root, store, args.workbook, args.label, args.template_sha256, args.desktop_verified,
                   power_query=args.power_query)
        elif args.command == 'publish':
            _, artifacts = verified_export(root, store, preview_path(store, args.label), args.reviewed)
            write_export(repo_path(root, args.destination), artifacts)
            print('Published the reviewed export. No Git staging or synchronization performed.')
        elif args.command == 'accept-initial':
            accept_initial(root, store, args.candidate, args.reviewed)
        elif args.command in ('plan-import', 'prepare-import', 'verify-import', 'accept-import'):
            return controlled_import(root, store, args)
        elif args.command in ('pq-load-review', 'pq-load-accept'):
            power_query_load_change(root, store, args)
        else:
            power_query_import(root, store, args)
    except (Blocked, QueryBlocked) as error:
        print(f'Blocked: {error}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, BadZipFile, RuntimeError, NotImplementedError):
        print('Blocked: invalid, unsupported, or inaccessible workbook, export, or storage.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
