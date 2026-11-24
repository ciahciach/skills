"""Prepare or export one workbook and explicitly accept its first synchronization point.

From an existing Git worktree, use a dedicated private local directory outside
Git, one per workbook, on a filesystem supporting read-only files. On Windows
its ACL may grant access only to the operator, SYSTEM and Administrators. On
POSIX use a directory owned by the operator with mode 0700. Give the script's
full path if it lives outside your worktree. The CLI never launches Excel.

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

Before publishing, review all three text artifacts under <private-dir>/review
for sensitive identifiers, numeric constants and logic. Pass the digest printed
by export. Publication verifies the exact preview against the retained version.
Stage only reviewed text files, never workbook binaries or a redacted preview. Acceptance
checks the published export again; later exports do not advance sync.

Only exact A1 targets of standalone ordinary formulas are editable here. The
inventory summarizes omissions, not instructions. No values, cached formula
results, connection strings, query definitions or names' definitions are
emitted. Shared and array formula records, spill ranges, what-if data tables,
and table-calculated columns are out of scope. Nonempty inline strings,
recognized credential patterns and external formula references block the export.
These checks are conservative, not a substitute for human review of identifiers
and formulas for sensitive information. No redacted export or import is provided.

Versions are named by SHA-256 and never replaced by this tool. Local read-only
files do not protect against storage administrators; use appropriate retention
and backups. For controlled ordinary-formula import, see the Excel repo contract.
This command does not qualify or invoke an Excel runtime or edit workbook internals.
"""

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
from io import BytesIO, TextIOWrapper
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


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


class Blocked(Exception):
    pass


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
                    foreach ($path in (ConvertFrom-Json -InputObject $env:EXCEL_ONBOARDING_ACL_PATHS)) {
                        $acl = Get-Acl -LiteralPath $path
                        $raw = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(), 0)
                        if ($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner($sid).Value -notin $allowed) { exit 1 }
                        foreach ($rule in $acl.GetAccessRules($true, $true, $sid)) {
                            if ($rule.AccessControlType -eq 'Allow' -and
                                $rule.IdentityReference.Value -notin ($allowed + 'S-1-3-4')) {
                                exit 1
                            }
                        }
                    }
                } catch { exit 1 }
                exit 0
            '''], env={**os.environ, 'EXCEL_ONBOARDING_ACL_PATHS': json.dumps([str(path) for path in existing])},
            capture_output=True,
        )
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


def workbook_artifacts(data, profile, *, format_only=False, worksheet_parts=None):
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
            return [], {}
        sheet_names, sheet_parts = set(), set()
        for sheet in sheet_nodes.findall(f'{S}sheet'):
            name = sheet.attrib['name']
            relation = links[sheet.attrib[f'{{{OFFICE}}}id']]
            if not name or name.casefold() in sheet_names:
                raise Blocked('Invalid or duplicate sheet name.')
            sheet_names.add(name.casefold())
            if relation.get('Type') != f'{OFFICE}/worksheet':
                sheets.append({'sheet': name, 'type': 'non-worksheet'})
                continue
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
            table_templates = 0
            if table_parts:
                table_links = relationships(sheet_part)
            for table in table_parts:
                relation = table_links[table.attrib[f'{{{OFFICE}}}id']]
                definition = xml(target(sheet_part, relation, f'{OFFICE}/table'))
                left, top, right, bottom = rectangle(definition.attrib['ref'])
                columns = definition.findall(f'{S}tableColumns/{S}tableColumn')
                if definition.tag != f'{S}table' or len(columns) != right - left + 1:
                    raise Blocked('Unsupported table structure.')
                for col, column in enumerate(columns, left):
                    calculated = column.find(f'{S}calculatedColumnFormula') is not None
                    table_templates += calculated
                    if calculated or column.find(f'{S}totalsRowFormula') is not None:
                        excluded_ranges.append((col, top, col, bottom))

            formulas = {}
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
                if not ordinary:
                    if kind == 'array' and cell.get('cm'):
                        kind = 'arrayWithMetadata'
                    excluded_kinds[kind if kind in ('array', 'arrayWithMetadata', 'shared', 'dataTable')
                                   else 'other'] += 1
                if not ordinary and 'ref' in formula.attrib:
                    excluded_ranges.append(rectangle(formula.attrib['ref']))
                formulas[address] = (coords, ordinary, formula.text)

            count = 0
            for address, ((x, y), ordinary, text) in sorted(formulas.items()):
                if ordinary and not any(l <= x <= r and t <= y <= b for l, t, r, b in excluded_ranges):
                    cells.append({'sheet': name, 'cell': address, 'formula': '=' + text})
                    count += 1
                elif ordinary:
                    excluded_kinds['inExcludedRange'] += 1
            sheets.append({'sheet': name, 'type': 'worksheet', 'editableFormulaRecords': count,
                           'excludedFormulaRecords': len(formulas) - count,
                           'excludedByKind': dict(sorted(excluded_kinds.items())),
                           'tables': len(table_parts), 'calculatedColumnTemplates': table_templates})

    inventory = {'kind': 'inventory-only', 'sheets': sheets,
                 'definedNames': len(workbook.findall(f'{S}definedNames/{S}definedName')),
                 'externalReferences': len(workbook.findall(f'{S}externalReferences/{S}externalReference')),
                 'hasConnectionsPart': any(row.get('Type') == f'{OFFICE}/connections' for row in links.values())}
    return cells, inventory


def build_export(data, workbook, template=None, desktop_verified=None, *, worksheet_parts=None):
    cells, inventory = workbook_artifacts(data, Path(workbook).suffix.lower(), worksheet_parts=worksheet_parts)
    for value in [workbook, *(sheet['sheet'] for sheet in inventory['sheets'])]:
        if CREDENTIAL.search(value):
            raise Blocked('Publication blocked: possible credential in workbook metadata.')
    for cell in cells:
        formula = cell['formula']
        if CREDENTIAL.search(formula) or any(m[0] != '""' for m in TEXT_LITERAL.finditer(formula)):
            raise Blocked('Publication blocked: possible credential or unreviewable inline text in a formula.')
        if EXTERNAL_FORMULA.search(formula):
            raise Blocked('Publication blocked: an external formula is outside the supported export profile.')
    artifacts = {'ordinary-formulas.json': json_bytes({'kind': 'editable-ordinary-formulas', 'cells': cells}),
                 'inventory.json': json_bytes(inventory)}
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


def export(root, store, workbook, label, template=None, desktop_verified=None):
    source = workbook_path(root, workbook, template)
    preview = preview_path(store, label)
    if preview.exists():
        raise Blocked('Choose a new preview label.')
    data = read_bounded(source, MAX_PACKAGE)
    version = sha(data)
    verify_desktop_attestation(template, desktop_verified, version)
    if template is not None and verified_template(store, template) != data:
        raise Blocked('Saved XLSM differs from the pinned template; no initial export was produced.')
    artifacts = build_export(data, source.relative_to(root).as_posix(), template, desktop_verified)
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
    artifacts = build_export(data, workbook.relative_to(root).as_posix(), template, desktop_verified)
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


def preservation(data, parts, change=None, *, data_only=False, verified_result=None):
    """Conservative package comparison for simple XLSX; return hashes, never values."""
    allowed = re.compile(r'(?:\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app)\.xml|'
                         r'xl/(?:_rels/workbook\.xml\.rels|workbook\.xml|styles\.xml|sharedStrings\.xml|'
                         r'theme/theme[0-9]+\.xml|worksheets/sheet[0-9]+\.xml))\Z')
    with ZipFile(BytesIO(data)) as book:
        entries = book.infolist()
        if len(set(book.namelist())) != len(entries):
            raise Blocked('Workbook contains duplicate package parts.')
        if sum(info.file_size for info in entries) > MAX_PACKAGE:
            raise Blocked('Workbook exceeds the preservation comparison limit.')
        hashes = {}
        for part in book.namelist():
            if not allowed.fullmatch(part):
                raise Blocked('Workbook has parts outside the simple XLSX import profile.')
            raw = book.read(part)
            if b'\0' in raw or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                raise Blocked('Unsupported preservation XML.')
            xml = ET.fromstring(raw)
            if (any(node.get('TargetMode', 'Internal') != 'Internal' for node in xml)
                    or any(node.tag in {f'{S}{tag}' for tag in
                           ('extLst', 'definedName', 'externalReference', 'oleObject', 'control')} for node in xml.iter())):
                raise Blocked('Workbook has features outside the simple XLSX import profile.')
            if part == 'docProps/core.xml':
                modified = xml.find('{http://purl.org/dc/terms/}modified')
                if modified is not None:
                    modified.text = None
            elif part in parts.values():
                for cell in xml.findall(f'{S}sheetData/{S}row/{S}c'):
                    formula = cell.find(f'{S}f')
                    value = cell.find(f'{S}v')
                    if formula is not None and (formula.attrib or cell.get('cm') or cell.get('vm')):
                        raise Blocked('Special formula records are outside the simple XLSX import profile.')
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
            namespaces = list(event for _, event in ET.iterparse(BytesIO(raw), events=('start-ns',)))
            hashes[part] = sha(json_bytes(namespaces) + ET.tostring(xml))
    return hashes


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
    artifact = repo_path(root, args.artifacts) / 'ordinary-formulas.json'
    path = artifact.relative_to(root).as_posix()
    commit = git(root, 'rev-parse', '--verify', '--end-of-options', f'{args.commit}^{{commit}}')
    if commit.returncode:
        raise Blocked('Expected an approved Git commit.')
    oid = commit.stdout.strip()
    entry = git(root, '--literal-pathspecs', 'ls-tree', oid, '--', path)
    if entry.returncode or (entry.stdout and not entry.stdout.startswith(('100644 blob ', '100755 blob '))):
        raise Blocked('Expected a regular committed formula artifact.')
    edited = {}
    if entry.stdout:
        object_id = entry.stdout.split(None, 3)[2]
        size = git(root, 'cat-file', '-s', object_id)
        if size.returncode or int(size.stdout) > MAX_XML:
            raise Blocked('Cannot read the committed formula artifact within the supported size limit.')
        content = git(root, 'cat-file', 'blob', object_id)
        if content.returncode:
            raise Blocked('Cannot read the committed formula artifact.')
        edited = formula_map(content.stdout)
    plan = {'operation': IMPORT_OPERATION, 'profile': IMPORT_PROFILE, 'commit': oid, 'artifact': path, 'base': sync,
            'output': output.relative_to(root).as_posix(), 'gitDiff': formula_diff(old, edited),
            'workbookDiff': [], 'blockers': []}
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
        parts, _, live = import_snapshot(current, sync['workbook'])
    except (Blocked, OSError, ValueError, KeyError, ET.ParseError, BadZipFile):
        blockers.append('Cannot read and verify the saved source workbook.')
        return plan, source, output, None, {}, sync_path, sync_bytes
    plan['workbookDiff'] = formula_diff(old, live, omissions=True)
    changes = plan['gitDiff']
    change = changes[0] if len(changes) == 1 else None
    if plan['workbookDiff']:
        blockers.append('Two-sided managed drift; no merge.' if changes else 'Workbook managed drift; export and review first.')
    if not change or any(value is None or len(value) > 8192 or not SAFE_FORMULA.fullmatch(value)
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
                    or route.get('operation') != IMPORT_OPERATION or route.get('profile') != IMPORT_PROFILE
                    or route.get('inputSha256') != sha(current) or route.get('commit') != oid
                    or route.get('output') != plan['output']):
                raise Blocked('Route receipt does not match the approved backend, operation, profile and inputs.')
            no_op_path = store / 'routes' / f'{pin}.xlsx'
            require_private(no_op_path)
            no_op = read_bounded(no_op_path, MAX_PACKAGE)
            if (route.get('noOpSha256') != sha(no_op)
                    or preservation(no_op, parts) != preservation(current, parts)):
                raise Blocked('Qualified no-op save does not preserve workbook contents.')
            plan.update({key: route[key] for key in fields[:4]})
            plan.update(routeSha256=pin, noOpSha256=sha(no_op), preservation='verified no-op')
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
    try:
        verified_result = Decimal(args.result)
    except InvalidOperation:
        raise Blocked('Independent desktop readback must record a numeric result.') from None
    if not verified_result.is_finite():
        raise Blocked('Independent desktop readback must record a finite numeric result.')
    result_parts, exported, formulas = import_snapshot(saved, plan['output'])
    _, _, original = import_snapshot(current, plan['base']['workbook'])
    change = plan['gitDiff'][0]
    original[change['sheet'], change['cell']] = change['after']
    if (formulas != original or result_parts != parts
            or preservation(saved, result_parts, change, verified_result=verified_result)
            != preservation(current, parts, change)):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    export_cmd = commands.add_parser('export', help='Export one saved workbook for private review.')
    export_cmd.add_argument('workbook', help='Workbook path relative to the Git worktree root.')
    export_cmd.add_argument('label', help='New label for the private review directory.')
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
    for command in (copy_cmd, export_cmd, publish_cmd, accept_cmd):
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
            command.add_argument('--result', required=True, help='Independently read numeric result (synthetic data only).')
        if name == 'accept-import':
            command.add_argument('--reviewed', required=True, help='Verified re-export manifest SHA-256.')
    args = parser.parse_args()
    try:
        result = git(Path.cwd(), 'rev-parse', '--show-toplevel')
        if result.returncode:
            raise Blocked('Run from a Git worktree.')
        root = Path(result.stdout.rstrip('\r\n')).resolve()
        store = storage_path(root, args.store)
        if args.command == 'copy-template':
            copy_template(root, store, args.workbook, args.template_sha256)
        elif args.command == 'export':
            export(root, store, args.workbook, args.label, args.template_sha256, args.desktop_verified)
        elif args.command == 'publish':
            _, artifacts = verified_export(root, store, preview_path(store, args.label), args.reviewed)
            write_export(repo_path(root, args.destination), artifacts)
            print('Published the reviewed export. No Git staging or synchronization performed.')
        elif args.command == 'accept-initial':
            accept_initial(root, store, args.candidate, args.reviewed)
        else:
            return controlled_import(root, store, args)
    except Blocked as error:
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
