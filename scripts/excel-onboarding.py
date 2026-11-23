"""Export one saved XLSX and explicitly accept its first synchronization point.

From an existing Git worktree, use a dedicated private local directory outside
Git, one per workbook, on a filesystem supporting read-only files. On Windows
its ACL may grant access only to the operator, SYSTEM and Administrators. On
POSIX use a directory owned by the operator with mode 0700. Give the script's
full path if it lives outside your worktree. No setup skill or Excel needed.

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
Stage only reviewed text files, never the XLSX or a redacted preview. Acceptance
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
and backups. This command does not qualify an Excel runtime or write to a workbook.
"""

import argparse
from collections import Counter
import hashlib
from io import BytesIO
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
        if any(path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077 for path in existing):
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


def write_once(path, data):
    # Publish a complete read-only file without overwriting any existing version.
    fd, name = tempfile.mkstemp(dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
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


def workbook_artifacts(data):
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
            if relation.get('Type') != f'{OFFICE}/{kind}' or relation.get('TargetMode', 'Internal') != 'Internal':
                raise Blocked('Unsupported workbook part relationship.')
            ref = relation['Target']
            if any(c in ref for c in '\\:%?#'):
                raise Blocked('Unsupported workbook part relationship.')
            return posixpath.normpath(ref[1:] if ref.startswith('/') else posixpath.join(posixpath.dirname(part), ref))

        workbook_parts = [row for row in relationships('').values() if row.get('Type') == f'{OFFICE}/officeDocument']
        if len(workbook_parts) != 1:
            raise Blocked('Expected one workbook document.')
        part = target('', workbook_parts[0], 'officeDocument')
        content_types = xml('[Content_Types].xml')
        expected = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'
        if not any(item.get('PartName') == '/' + part and item.get('ContentType') == expected for item in content_types):
            raise Blocked('Only saved XLSX packages are supported.')
        workbook = xml(part)
        sheet_nodes = workbook.find(f'{S}sheets')
        if workbook.tag != f'{S}workbook' or sheet_nodes is None or not len(sheet_nodes):
            raise Blocked('Unsupported workbook structure.')
        links = relationships(part)
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
            sheet_part = target(part, relation, 'worksheet')
            if sheet_part in sheet_parts:
                raise Blocked('Duplicate worksheet part.')
            sheet_parts.add(sheet_part)
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
                definition = xml(target(sheet_part, relation, 'table'))
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
            excluded_kinds = Counter()
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


def build_export(data, workbook):
    cells, inventory = workbook_artifacts(data)
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
    artifacts['manifest.json'] = json_bytes({'schema': 1, 'workbook': workbook, 'versionSha256': sha(data),
                                             'files': {name: sha(content) for name, content in artifacts.items()}})
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


def export(root, store, workbook, label):
    source = repo_path(root, workbook)
    preview = preview_path(store, label)
    if source.suffix.lower() != '.xlsx' or source.name.startswith('~$'):
        raise Blocked('Identify one saved XLSX workbook.')
    if source.with_name('~$' + source.name).exists():
        raise Blocked('Workbook lock file exists; close Excel before exporting.')
    if preview.exists():
        raise Blocked('Choose a new preview label.')
    data = read_bounded(source, MAX_PACKAGE)
    artifacts = build_export(data, source.relative_to(root).as_posix())
    version = sha(data)
    retained = store / 'versions' / f'{version}.xlsx'
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
    workbook = repo_path(root, metadata['workbook'])
    retained = store / 'versions' / f'{version}.xlsx'
    require_private(store, retained.parent, retained)
    data = retained_bytes(retained, version)
    artifacts = build_export(data, workbook.relative_to(root).as_posix())
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    export_cmd = commands.add_parser('export', help='Export one saved workbook for private review.')
    export_cmd.add_argument('workbook', help='Workbook path relative to the Git worktree root.')
    export_cmd.add_argument('label', help='New label for the private review directory.')
    publish_cmd = commands.add_parser('publish', help='Publish a reviewed private export into Git.')
    publish_cmd.add_argument('label', help='Reviewed private export label.')
    publish_cmd.add_argument('destination', help='New export directory relative to the Git worktree root.')
    accept_cmd = commands.add_parser('accept-initial', help='Record the first synchronization point after review.')
    accept_cmd.add_argument('candidate', help='Reviewed export directory relative to the Git worktree root.')
    for command in (publish_cmd, accept_cmd):
        command.add_argument('--reviewed', required=True, help='SHA-256 of the manifest you reviewed.')
    for command in (export_cmd, publish_cmd, accept_cmd):
        command.add_argument('--store', required=True, help='Existing private, access-controlled directory outside Git.')
    args = parser.parse_args()
    try:
        result = git(Path.cwd(), 'rev-parse', '--show-toplevel')
        if result.returncode:
            raise Blocked('Run from a Git worktree.')
        root = Path(result.stdout.rstrip('\r\n')).resolve()
        store = storage_path(root, args.store)
        if args.command == 'export':
            export(root, store, args.workbook, args.label)
        elif args.command == 'publish':
            _, artifacts = verified_export(root, store, preview_path(store, args.label), args.reviewed)
            write_export(repo_path(root, args.destination), artifacts)
            print('Published the reviewed export. No Git staging or synchronization performed.')
        else:
            accept_initial(root, store, args.candidate, args.reviewed)
    except Blocked as error:
        print(f'Blocked: {error}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, BadZipFile, RuntimeError, NotImplementedError):
        print('Blocked: invalid, unsupported, or inaccessible workbook, export, or storage.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
