"""Run the #40 desktop qualification. Only self-generated temporary XLSX files."""

import hashlib
import json
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pywintypes
import win32api
import win32event
import win32process
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from win32com.client import DispatchEx


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(stage, **fields):
    print(json.dumps({'stage': stage, **fields}), flush=True)


def profile(path, *, prepared=False):
    # Allow only the parts used by this fixture and its Excel round-trip.
    allowed = {
        '[Content_Types].xml', '_rels/.rels', 'docProps/app.xml', 'docProps/core.xml', 'docProps/custom.xml',
        'xl/workbook.xml', 'xl/_rels/workbook.xml.rels', 'xl/worksheets/sheet1.xml',
        'xl/styles.xml', 'xl/theme/theme1.xml', 'xl/sharedStrings.xml', 'xl/calcChain.xml',
    }
    with ZipFile(path) as package:
        names = package.namelist()
        require(len(names) == len(set(names)), 'Duplicate XLSX parts')
        require(set(names) <= allowed, f'Unexpected XLSX parts: {sorted(set(names) - allowed)}')
        require(prepared or 'docProps/custom.xml' not in names,
                'Unexpected custom properties before fixture preparation')
        for name in names:
            if name.endswith('.rels'):
                require(all(rel.get('TargetMode', 'Internal') == 'Internal'
                            for rel in ET.fromstring(package.read(name))), 'External relationship')
        for name in ('xl/workbook.xml', 'xl/worksheets/sheet1.xml'):
            for node in ET.fromstring(package.read(name)).iter():
                tag = node.tag.rsplit('}', 1)[-1]
                if tag == 'workbookProtection' and not node.attrib and not len(node):
                    continue  # openpyxl emits an empty, inactive protection element.
                if tag == 'extLst' and name == 'xl/workbook.xml':
                    # Modern Excel records supported calculation capabilities, not workbook connections.
                    calc_ns = '{http://schemas.microsoft.com/office/spreadsheetml/2018/calcfeatures}'
                    require(all(child.tag.rsplit('}', 1)[-1] in {'extLst', 'ext'} or
                                child.tag in {calc_ns + 'calcFeatures', calc_ns + 'feature'}
                                for child in node.iter()), 'Unexpected workbook extension')
                    continue
                require(tag not in {'extLst', 'externalReferences', 'definedName', 'oleObjects',
                                    'controls', 'sheetProtection', 'workbookProtection'},
                        f'Unexpected feature: {tag}')
                if tag == 'f':
                    require(not node.attrib and node.text in {'A1*2', 'A1*3', 'A1+1'},
                            'Non-fixture formula')
    require(not path.with_name('~$' + path.name).exists(), 'Excel owner file exists')
    return sorted(names)


def export(path):
    result = {}
    for data_only, key in ((False, 'formula_or_value'), (True, 'cached_or_value')):
        book = load_workbook(path, read_only=False, data_only=data_only)
        try:
            require(book.sheetnames == ['Calc'], 'Unexpected workbook sheets')
            sheet = book['Calc']
            require((sheet.max_row, sheet.max_column) == (2, 3), 'Unexpected sheet shape')
            for row in sheet.iter_rows():
                for cell in row:
                    entry = result.setdefault(cell.coordinate, {})
                    entry[key] = cell.value
                    if not data_only:
                        entry.update(bold=bool(cell.font.bold), format=cell.number_format)
        finally:
            book.close()
    return result


def normalized_package(path, *, edited=False):
    with ZipFile(path) as package:
        parts = {name: package.read(name) for name in package.namelist()}
    # Excel updates the document modification timestamp as part of a save.
    core = ET.fromstring(parts['docProps/core.xml'])
    for node in core.findall('{http://purl.org/dc/terms/}modified'):
        core.remove(node)
    parts['docProps/core.xml'] = ET.tostring(core)
    if edited:
        name = 'xl/worksheets/sheet1.xml'
        sheet = ET.fromstring(parts[name])
        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        for cell in sheet.iter(ns + 'c'):
            if cell.get('r') == 'B1':
                for node in cell:
                    if node.tag in {ns + 'f', ns + 'v'}:
                        node.text = None
        parts[name] = ET.tostring(sheet)
    return parts


def changed_parts(base, copy, *, edited=False):
    before, after = (normalized_package(path, edited=edited) for path in (base, copy))
    return sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))


def xml_changes(base, copy, names):
    def compare(before, after, path):
        if before.tag != after.tag:
            yield {'path': path, 'change': 'element replaced'}
            return
        attributes = sorted(key.rsplit('}', 1)[-1] for key in before.attrib.keys() | after.attrib.keys()
                            if before.get(key) != after.get(key))
        if attributes:
            yield {'path': path, 'attributes': attributes}
        if (before.text, before.tail) != (after.text, after.tail):
            yield {'path': path, 'change': 'text'}
        if len(before) != len(after):
            yield {'path': path, 'change': 'child count', 'before': len(before), 'after': len(after)}
        for index, (left, right) in enumerate(zip(before, after), start=1):
            yield from compare(left, right, f'{path}/{left.tag.rsplit("}", 1)[-1]}[{index}]')

    with ZipFile(base) as before, ZipFile(copy) as after:
        for name in ('xl/calcChain.xml', 'xl/workbook.xml'):
            if name in names and name in before.namelist() and name in after.namelist():
                left, right = (ET.fromstring(package.read(name)) for package in (before, after))
                yield {'part': name, 'changes': list(compare(left, right, left.tag.rsplit('}', 1)[-1]))}


@contextmanager
def excel(stage):
    existing = set(win32process.EnumProcesses())
    app = DispatchEx('Excel.Application')
    _, pid = win32process.GetWindowThreadProcessId(app.Hwnd)
    require(pid and pid not in existing, 'Could not verify new Excel process; refusing to change it')
    process = None
    settings = {}
    try:
        process = win32api.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE: wait, never terminate.
        for name in ('Visible', 'DisplayAlerts', 'ScreenUpdating', 'EnableEvents'):
            settings[name] = getattr(app, name)
            setattr(app, name, False)
        require(app.Workbooks.Count == 0, 'Unexpected startup workbook')
        report(stage + '_instance', pid=pid, version=app.Version, build=app.Build,
               visible=app.Visible, events=app.EnableEvents)
        require(not app.Visible and not app.EnableEvents, 'Application guards not active')
        yield app, pid
    finally:
        try:
            if settings and app.Workbooks.Count == 0:
                for name, value in reversed(settings.items()):
                    setattr(app, name, value)
        finally:
            try:
                app.Quit()
                del app
                if process is not None:
                    require(win32event.WaitForSingleObject(process, 15_000) == 0,
                            f'Owned Excel PID {pid} did not exit; no further phases')
            finally:
                if process is not None:
                    process.Close()


def open_guarded(app, path, read_only, stage, *, expect_open_error=False):
    previous = app.AutomationSecurity
    opened = None
    forced = None
    try:
        app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        forced = app.AutomationSecurity
        require(forced == 3 and not app.EnableEvents, 'Scoped open guards not active')
        try:
            opened = app.Workbooks.Open(Filename=str(path), UpdateLinks=0, ReadOnly=read_only,
                                        IgnoreReadOnlyRecommended=True, Notify=False, AddToMru=False)
        except pywintypes.com_error:
            if not expect_open_error:
                raise
        else:
            require(not expect_open_error, 'Expected missing-file Open to fail')
    finally:
        app.AutomationSecurity = previous
        restored = app.AutomationSecurity
        report(stage + '_open', outcome='opened' if opened is not None else 'error',
               update_links=0, requested_read_only=read_only, security_before=previous,
               security_during=forced, security_after=restored)
        require(restored == previous, 'AutomationSecurity restoration failed')
    return opened


def phase(stage, path, *, prepared=True, read_only=False, edit=False, expected_formula, expected_value):
    profile(path, prepared=prepared)
    before = digest(path)
    with excel(stage) as (app, pid):
        book = cell = None
        try:
            book = open_guarded(app, path, read_only, stage)
            for _ in range(20):
                if app.Ready:
                    break
                time.sleep(1)
            require(app.Ready and bool(book.ReadOnly) == read_only, 'Unexpected workbook readiness/access')
            require(not book.LinkSources(1) and book.Connections.Count == 0 and book.Queries.Count == 0,
                    'Workbook unexpectedly contains links, connections, or queries')
            autosave = book.AutoSaveOn
            require(autosave is False, 'AutoSave is enabled or unknown')
            cell = book.Worksheets('Calc').Range('B1')
            if edit:
                require(cell.Formula == '=A1*2' and not cell.HasArray and not cell.MergeCells,
                        'Unexpected target formula or type')
                cell.Formula = '=A1*3'
                cell.Calculate()
            require(cell.Formula == expected_formula and cell.Value2 == expected_value,
                    f'Unexpected runtime formula or result for {stage}')
            if not read_only:
                book.Save()
            report(stage + '_runtime', pid=pid, read_only=book.ReadOnly, autosave=autosave,
                   formula=cell.Formula, value=cell.Value2, saved=not read_only)
        finally:
            try:
                if book is not None:
                    book.Close(SaveChanges=False)
            finally:
                del cell, book, app
    if read_only:
        require(digest(path) == before, 'Read-only phase changed saved bytes')
    return pid


def run(root):
    seed = root / 'seed.xlsx'
    book = Workbook()
    sheet = book.active
    sheet.title = 'Calc'
    sheet.append([10, '=A1*2', '=A1+1'])
    sheet['A2'] = 'sentinel'
    sheet['A2'].font = Font(bold=True)
    sheet['B1'].number_format = '0.00'
    book.save(seed)
    book.close()
    report('scope', python=sys.version.split()[0], pywin32=version('pywin32'),
           openpyxl=version('openpyxl'), parts=profile(seed))
    seed_sha = digest(seed)
    original = export(seed)

    with excel('open_error_probe') as (app, _):
        try:
            open_guarded(app, root / 'intentionally-missing.xlsx', True, 'open_error_probe',
                         expect_open_error=True)
        finally:
            del app

    # Let Excel apply its normal save policy before sealing the qualification baseline.
    base = root / 'base.xlsx'
    shutil.copyfile(seed, base)
    phase('prepare', base, prepared=False, expected_formula='=A1*2', expected_value=20)
    base_parts = profile(base, prepared=True)
    base_sha = digest(base)
    baseline = export(base)
    for address, value in {'B1': 20, 'C1': 11}.items():
        original[address]['cached_or_value'] = value  # The generated input has no formula cache.
    require(baseline == original, 'Preparation changed the fixture cell export')
    report('prepared_baseline', sha256=base_sha, parts=base_parts)

    noop = root / 'noop.xlsx'
    shutil.copyfile(base, noop)
    phase('noop', noop, expected_formula='=A1*2', expected_value=20)
    profile(noop, prepared=True)
    changed = changed_parts(base, noop)
    require(not changed, f'No-op changed unrelated parts: {changed}')
    require(export(noop) == baseline, 'No-op changed the fixture cell export')
    report('noop', status='PASS', base_sha256=base_sha, copy_sha256=digest(noop), cells=baseline)

    before_plan = {file.name: digest(file) for file in root.iterdir()}
    require(profile(base, prepared=True) and export(base)['B1']['formula_or_value'] == '=A1*2', 'Wrong dry-run target')
    require(before_plan == {file.name: digest(file) for file in root.iterdir()}, 'Dry-run wrote files')
    report('dry_run', status='PASS', base=base.name, base_sha256=base_sha,
           target='Calc!B1', old='=A1*2', new='=A1*3', blockers=[], wrote_files=False)

    require(digest(base) == base_sha, 'Base drifted before applying')
    candidate = root / 'candidate.xlsx'
    shutil.copyfile(base, candidate)
    writer_pid = phase('save', candidate, edit=True, expected_formula='=A1*3', expected_value=30)
    candidate_sha = digest(candidate)
    report('save', status='PASS', file=candidate.name, sha256=candidate_sha)
    reader_pid = phase('readback', candidate, read_only=True, expected_formula='=A1*3', expected_value=30)
    require(reader_pid != writer_pid, 'Readback PID was not distinct')
    profile(candidate, prepared=True)
    candidate_export = export(candidate)
    baseline['B1'].update(formula_or_value='=A1*3', cached_or_value=30)
    require(candidate_export == baseline, 'Candidate changed cells outside the intended formula and result')
    require(digest(seed) == seed_sha and digest(base) == base_sha and digest(candidate) == candidate_sha,
             'Original or readback bytes changed')
    changed = changed_parts(base, candidate, edited=True)
    report('readback', status='PASS', sha256=candidate_sha, unchanged_base_sha256=base_sha,
           unchanged_seed_sha256=seed_sha, cells=candidate_export, accepted=False)
    if changed:
        report('package_preservation', status='NOT_VERIFIED', changed_parts=changed,
               xml_changes=list(xml_changes(base, candidate, changed)))
        raise RuntimeError(f'Candidate changed unrelated parts: {changed}')
    report('package_preservation', status='PASS')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    require(len(sys.argv) == 1, 'This qualification accepts no inputs or file paths')
    parent = Path(tempfile.gettempdir()) / 'kilo'
    require(parent.is_dir(), 'Expected the preapproved TEMP/kilo directory')
    with tempfile.TemporaryDirectory(dir=parent, prefix='excel-com-40-') as directory:
        run(Path(directory).resolve())
