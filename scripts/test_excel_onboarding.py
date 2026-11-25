import base64
import csv
import hashlib
from io import BytesIO, TextIOWrapper
import json
import os
from pathlib import Path
import runpy
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZipInfo


SCRIPT = Path(__file__).with_name('excel-onboarding.py')
SHEET = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
OFFICE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE = 'http://schemas.openxmlformats.org/package/2006/relationships'


class NativePilotTest(unittest.TestCase):
    def test_formula_import_preserves_only_empty_desktop_style_defaults(self):
        cli = runpy.run_path(str(SCRIPT))
        styles = (f'<styleSheet xmlns="{SHEET}"><extLst>'
                  '<ext uri="{EB79DEF2-80B8-43e5-95BD-54CBDDF9020C}">'
                  '<x14:slicerStyles xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main" '
                  'defaultSlicerStyle="SlicerStyleLight1"/></ext>'
                  '<ext uri="{9260A510-F301-46a8-8635-F512D64BE5F5}">'
                  '<x15:timelineStyles xmlns:x15="http://schemas.microsoft.com/office/spreadsheetml/2010/11/main" '
                  'defaultTimelineStyle="TimeSlicerStyleLight1"/></ext></extLst></styleSheet>')

        def preserved(raw):
            data = BytesIO()
            with ZipFile(data, 'w') as book:
                book.writestr('xl/styles.xml', raw)
            return cli['preservation'](data.getvalue(), {})

        self.assertNotEqual(preserved(styles), preserved(styles.replace('<extLst>', '<extLst><!-- metadata -->')))
        for changed in (styles.replace('SlicerStyleLight1', 'AnotherStyle'),
                        styles.replace('"TimeSlicerStyleLight1"/>', '"TimeSlicerStyleLight1"><x15:timelineStyle/>'
                                       '</x15:timelineStyles>'),
                        styles.replace('{EB79DEF2-80B8-43e5-95BD-54CBDDF9020C}', '{unknown}')):
            with self.assertRaisesRegex(cli['Blocked'], 'unsupported extensions'):
                preserved(changed)

    def test_formula_com_metadata_exception_is_edit_only_and_narrow(self):
        preservation = runpy.run_path(str(SCRIPT))['preservation']
        chain = (f'<calcChain xmlns="{SHEET}"><c r="C1" i="1" l="1"/>'
                 '<c r="B1" i="1"/></calcChain>')
        reversed_chain = chain.replace('C1', '#').replace('B1', 'C1').replace('#', 'B1')
        workbook = (f'<workbook xmlns="{SHEET}" xmlns:xr="http://schemas.microsoft.com/office/'
                    'spreadsheetml/2014/revision"><xr:revisionPtr documentId="old" revIDLastSave="0"/></workbook>')

        def package(chain_xml, workbook_xml, label='<label/>', *, edited=False):
            data = BytesIO()
            with ZipFile(data, 'w') as book:
                book.writestr('xl/calcChain.xml', chain_xml)
                book.writestr('xl/workbook.xml', workbook_xml)
                book.writestr('docProps/custom.xml', label)
            return preservation(data.getvalue(), {}, com_fixture_edit=edited)

        rotated = workbook.replace('"old"', '"new"')
        self.assertNotEqual(package(chain, workbook), package(reversed_chain, rotated))
        base = package(chain, workbook, edited=True)
        self.assertEqual(base, package(reversed_chain, rotated, edited=True))
        self.assertNotEqual(base, package(reversed_chain.replace(' l="1"', ''), rotated, edited=True))
        self.assertNotEqual(base, package(reversed_chain, rotated.replace('revIDLastSave="0"', 'revIDLastSave="1"'),
                                          edited=True))
        self.assertNotEqual(base, package(reversed_chain, rotated, '<label changed="1"/>', edited=True))

    def test_first_excel_save_revision_transition_is_narrow(self):
        verify = runpy.run_path(str(SCRIPT))['excel_copy_metadata_changes']

        def workbook(prefix: str, digit: str, revision: str = '0') -> bytes:
            data = BytesIO()
            guid = f'{digit * 8}-{digit * 4}-{digit * 4}-{digit * 4}-{digit * 12}'
            with ZipFile(data, 'w') as book:
                book.writestr('xl/workbook.xml', f'<workbook xmlns="{SHEET}" '
                              'xmlns:xr="http://schemas.microsoft.com/office/spreadsheetml/2014/revision">'
                              f'<xr:revisionPtr revIDLastSave="{revision}" documentId="{prefix}_{{{guid}}}"/>'
                              '</workbook>')
            return data.getvalue()

        base = workbook('8', '1')
        saved = workbook('13_ncr:1', '2')
        self.assertEqual(verify(base, saved, Path.cwd()), ['revisionPtr.documentId'])
        self.assertIsNone(verify(saved, base, Path.cwd()))
        self.assertIsNone(verify(workbook('9', '1'), saved, Path.cwd()))
        self.assertIsNone(verify(base, workbook('13_ncr:1', '2', revision='1'), Path.cwd()))

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL regression')
    def test_attempt_storage_does_not_inherit_broad_access(self):
        onboarding = runpy.run_path(str(SCRIPT))
        temp_parent = Path(tempfile.gettempdir()).resolve() / 'kilo'
        temp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_parent) as name:
            parent = Path(name).resolve()
            subprocess.run(['icacls.exe', str(parent), '/grant', '*S-1-5-32-545:(OI)(CI)(RX)'],
                           check=True, capture_output=True, timeout=60)
            with self.assertRaisesRegex(onboarding['Blocked'], 'platform administrators'):
                onboarding['require_private'](parent)
            attempt, fixture, store = onboarding['create_pilot_workspace'](parent)
            self.assertEqual(attempt.parent, parent)
            self.assertTrue(fixture.is_dir() and store.is_dir())
            evidence = store / 'report.json'
            evidence.write_text('{}', encoding='utf-8')
            onboarding['require_private'](attempt)
            onboarding['require_private'](fixture, store, evidence, store / 'not-created-yet')
            with self.assertRaisesRegex(onboarding['Blocked'], 'platform administrators'):
                onboarding['require_private'](parent)

    def test_requires_an_explicit_desktop_request(self):
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SCRIPT), 'pq-pilot'],
                                stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8', timeout=90)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires explicit --desktop', result.stderr)
        self.assertEqual(result.stdout, '')


def make_writable(path: Path):
    if path.exists():
        path.chmod(stat.S_IWRITE | stat.S_IRUSR)


def save_fixture(path, expression, *, macros=False, missing_vba=False, data=7, simple=False,
                 queries=False, copy_metadata='', extra_cells='', vba_hosts=False):
    content_type = ('application/vnd.ms-excel.sheet.macroEnabled.main+xml' if macros
                    else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
    vba_type = '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>' if macros else ''
    vba_link = ('<Relationship Id="rId2" Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" '
                'Target="vbaProject.bin"/>') if macros else ''
    connections = f'<Relationship Id="rId3" Type="{OFFICE}/connections" Target="connections.xml"/>' if queries else ''
    tables = '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>' if queries else ''
    workbook_props = '<workbookPr codeName="ThisWorkbook"/>' if vba_hosts else ''
    sheet_props = '<sheetPr codeName="Sheet1"/>' if vba_hosts else ''
    query_type = ('<Override PartName="/xl/queryTables/queryTable1.xml" '
                  'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.queryTable+xml"/>') if queries else ''
    with ZipFile(path, 'w') as book:
        book.writestr('[Content_Types].xml', f'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          {vba_type}
          {query_type}
          <Override PartName="/xl/workbook.xml" ContentType="{content_type}"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>''')
        book.writestr('_rels/.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        book.writestr('xl/workbook.xml', f'<workbook xmlns="{SHEET}" xmlns:r="{OFFICE}">{copy_metadata}{workbook_props}'
                      '<sheets><sheet name="Model" sheetId="1" r:id="rId1"/></sheets></workbook>')
        book.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/worksheet" Target="worksheets/sheet1.xml"/>{vba_link}{connections}</Relationships>')
        rows = '' if expression is None else f'''
          <row r="1"><c r="A1"><f>{escape(expression)}</f><v>92345</v></c><c r="B1" t="inlineStr"><is><t>PRIVATE_FIXTURE_DATA</t></is></c>{extra_cells}</row>
          <row r="3"><c r="A3"><f>2*2</f></c></row>
          <row r="4"><c r="A4" cm="1"><f t="array" ref="A4:A5">ROW(A4:A5)</f></c></row>
          <row r="5"><c r="A5"><f>3+2</f><v>5</v></c></row>
          <row r="7"><c r="A7"><f t="shared" ref="A7:A8" si="0">B7+1</f></c></row>
          <row r="8"><c r="A8"><f t="shared" si="0"/></c></row>
        '''
        if simple:
            cached = {'2+2': 4, '2+3': 5, '2+4': 6}[expression]
            rows = (f'<row r="1"><c r="A1"><f>{escape(expression)}</f><v>{cached}</v></c>'
                    f'<c r="B1"><v>{data}</v></c><c r="C1"><f>2*2</f><v>4</v></c></row>')
        book.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{SHEET}" xmlns:r="{OFFICE}">{sheet_props}<sheetData>{rows}</sheetData>{tables}</worksheet>')
        if macros and not missing_vba:
            book.writestr('xl/vbaProject.bin', b'Synthetic opaque VBA bytes')


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        temp_parent = Path(tempfile.gettempdir()) / 'kilo'
        temp = tempfile.TemporaryDirectory(dir=temp_parent if temp_parent.is_dir() else None)
        self.addCleanup(temp.cleanup)
        fixture = Path(temp.name).resolve()
        self.repo = fixture / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True)
        self.store = fixture / 'private-store'
        if sys.platform == 'win32':
            self.store.mkdir()
            identity = subprocess.check_output(['whoami.exe', '/user', '/fo', 'csv', '/nh'],
                                               text=True, errors='replace', timeout=30)
            _, sid = next(csv.reader(identity.splitlines()))
            # Grant the operator access before removing the temp directory's inherited ACEs.
            subprocess.run(['icacls.exe', str(self.store), '/grant:r', f'*{sid}:(OI)(CI)F'],
                           check=True, timeout=30, stdout=subprocess.PIPE)
            subprocess.run(['icacls.exe', str(self.store), '/inheritance:r'],
                           check=True, timeout=30, stdout=subprocess.PIPE)
        else:
            self.store.mkdir(mode=0o700)
        self.book = self.repo / 'model.xlsx'
        (self.repo / 'AGENTS.md').write_text('Prepared fixture. See docs/agents/excel.md.\n', encoding='utf-8')
        (self.repo / 'docs/agents').mkdir(parents=True)
        (self.repo / 'docs/agents/excel.md').write_text(f'Use {SCRIPT} for passive export.\n', encoding='utf-8')

    def import_fixture(self):
        (self.repo / '.gitignore').write_text('*.xlsx\n', encoding='utf-8')
        save_fixture(self.book, '2+2', simple=True)
        self.export('baseline')
        self.publish('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', self.preview_digest('baseline'))
        formulas = self.repo / 'baseline/ordinary-formulas.json'
        proposal = json.loads(formulas.read_bytes())
        proposal['cells'] = [{'sheet': 'Model', 'cell': 'A1', 'formula': '=2+3'}]
        formulas.write_text(json.dumps(proposal), encoding='utf-8')
        (self.repo / 'baseline/inventory.json').unlink()
        subprocess.run(['git', 'add', 'baseline'], cwd=self.repo, check=True)
        subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
                        'commit', '-qm', 'Approve synthetic formula edit'], cwd=self.repo, check=True)
        self.commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.repo, text=True).strip()
        return ['baseline', 'result.xlsx', '--commit', self.commit]

    def simulated_route(self, *, no_op=None, evidence_class='desktop'):
        # External desktop phases are simulated; this is not runtime qualification.
        routes = self.store / 'routes'
        routes.mkdir(mode=0o700, exist_ok=True)
        original = self.book.read_bytes()
        no_op = original if no_op is None else no_op
        receipt = json.dumps({'entryPoint': 'synthetic routing fixture', 'backend': 'fixture backend',
                              'backendVersion': '1', 'excelBuild': 'fixture build', 'qualification': 'test-only',
                              'evidenceClass': evidence_class,
                              'authorization': 'test-only', 'operation': 'ordinary-formula-import',
                              'profile': 'simple-xlsx', 'inputSha256': hashlib.sha256(original).hexdigest(),
                              'noOpSha256': hashlib.sha256(no_op).hexdigest(), 'commit': self.commit,
                              'output': 'result.xlsx'}).encode('utf-8')
        pin = hashlib.sha256(receipt).hexdigest()
        for extension, content in (('json', receipt), ('xlsx', no_op)):
            path = routes / f'{pin}.{extension}'
            path.touch(mode=0o600)
            path.write_bytes(content)
        return ['--route-sha256', pin]

    def test_import_dry_run_is_read_only_and_requires_qualification(self):
        args = self.import_fixture()
        before = (self.store / 'sync.json').read_bytes()
        book = self.book.read_bytes()
        output = self.cli('plan-import', *args, ok=False)
        self.assertIn('qualification', output)
        self.assertIn('=2+3', output)
        self.assertIn('A1', output)
        self.assertEqual((self.store / 'sync.json').read_bytes(), before)
        self.assertEqual(self.book.read_bytes(), book)
        self.assertFalse((self.repo / 'result.xlsx').exists())

    def test_import_reports_both_diffs_and_rejects_failed_no_op(self):
        args = self.import_fixture()
        dry = json.loads(self.cli('plan-import', *args, *self.simulated_route(evidence_class='simulated'), ok=False))
        self.assertIn('Route receipt does not match', ' '.join(dry['blockers']))
        other = self.repo / 'other.xlsx'
        save_fixture(other, '2+2', data=9, simple=True)
        route = self.simulated_route(no_op=other.read_bytes())
        dry = json.loads(self.cli('plan-import', *args, *route, ok=False))
        self.assertIn('Qualified no-op save does not preserve workbook contents.', dry['blockers'])
        save_fixture(self.book, '2+4', simple=True)
        dry = json.loads(self.cli('plan-import', *args, ok=False))
        self.assertEqual(dry['gitDiff'], [{'sheet': 'Model', 'cell': 'A1', 'before': '=2+2', 'after': '=2+3'}])
        self.assertEqual(dry['workbookDiff'], [{'sheet': 'Model', 'cell': 'A1', 'before': '=2+2', 'after': '=2+4'}])
        self.assertIn('Two-sided managed drift; no merge.', dry['blockers'])

    def test_verified_import_recovers_from_partial_save_and_needs_acceptance(self):
        args = self.import_fixture()
        # Numeric input changes on existing cells are allowed, not replayed from Git.
        save_fixture(self.book, '2+2', data=9, simple=True)
        original = self.book.read_bytes()
        sync_path = self.store / 'sync.json'
        sync = sync_path.read_bytes()
        args += self.simulated_route()
        dry = json.loads(self.cli('plan-import', *args))
        args += ['--approved-plan', dry['planSha256']]
        self.assertFalse((self.repo / 'result.xlsx').exists())
        lock = self.repo / '~$model.xlsx'
        lock.touch()
        self.assertIn('Workbook lock file', self.cli('prepare-import', *args, ok=False))
        lock.unlink()
        self.cli('prepare-import', *args)
        result = self.repo / 'result.xlsx'
        self.assertEqual(result.read_bytes(), original)

        def reopen_arg(result_value='5'):
            digest = hashlib.sha256(result.read_bytes()).hexdigest()
            return ['--saved', digest, '--reopened', digest, '--result', result_value]

        save_fixture(result, '2+3', data=1, simple=True)
        error = self.cli('verify-import', *args, *reopen_arg(), ok=False)
        self.assertIn('Desktop save attested', error)
        self.assertIn('preservation requirements', error)
        self.assertEqual(self.book.read_bytes(), original)
        self.assertEqual(sync_path.read_bytes(), sync)
        self.assertIn('Expected a new copy', self.cli('prepare-import', *args, ok=False))
        result.unlink()
        self.cli('prepare-import', *args)
        save_fixture(result, '2+3', data=9, simple=True)
        error = self.cli('verify-import', *args, *reopen_arg('6'), ok=False)
        self.assertIn('does not match the independent desktop readback', error)
        reopened = reopen_arg()
        evidence = self.cli('verify-import', *args, *reopened)
        manifest = evidence.split('Manifest SHA-256: ')[1].splitlines()[0]
        self.assertEqual(sync_path.read_bytes(), sync)
        self.cli('accept-import', *args, *reopened, '--reviewed', '0' * 64, ok=False)
        self.assertEqual(sync_path.read_bytes(), sync)
        self.cli('accept-import', *args, *reopened, '--reviewed', manifest)
        self.assertEqual(self.book.read_bytes(), original)
        self.assertEqual(json.loads(sync_path.read_bytes()), {'schema': 1, 'workbook': result.name,
                         'versionSha256': reopened[1], 'manifestSha256': manifest})

    def cli(self, *args, ok=True, watch_neighbor=False):
        entry = [__file__, '--watch-neighbor'] if watch_neighbor else [str(SCRIPT)]
        result = subprocess.run([sys.executable, '-X', 'utf8', *entry, *args, '--store', str(self.store)],
                                cwd=self.repo, capture_output=True, encoding='utf-8')
        if ok:
            self.assertEqual(result.returncode, 0, f'{args!r}: {result.stderr}')
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stdout + result.stderr

    def export(self, name, *args, **kwargs):
        return self.cli('export', 'model.xlsx', name, *args, **kwargs)

    def publish(self, label, reviewed=None, **kwargs):
        approval = reviewed if reviewed is not None else self.preview_digest(label)
        return self.cli('publish', label, label, '--reviewed', approval, **kwargs)

    def preview_digest(self, label):
        return hashlib.sha256((self.store / 'review' / label / 'manifest.json').read_bytes()).hexdigest()

    def pin_template(self, *, declare_frx=True, missing_vba=False, module_only=False):
        source = self.store / 'fixture.xlsm'
        save_fixture(source, '2+2', macros=True, missing_vba=missing_vba, vba_hosts=module_only)
        files = {'template.xlsm': source.read_bytes()}
        if not module_only:
            files['Form.frm'] = b'Picture = "Form.frx":0000\r\n'
        if declare_frx and not module_only:
            files['Form.frx'] = b'Synthetic form resource'

        def digest(data):
            return hashlib.sha256(data).hexdigest()

        manifest = json.dumps({'version': 'v1', 'workbookSha256': digest(files['template.xlsm']),
                               'companions': {name: digest(data) for name, data in files.items()
                                              if name != 'template.xlsm'}}).encode('utf-8')
        pin = digest(manifest)
        folder = self.store / 'templates' / pin
        folder.parent.mkdir(mode=0o700)
        folder.mkdir(mode=0o700)
        for name, data in {**files, 'template.json': manifest}.items():
            path = folder / name
            path.touch(mode=0o600)
            path.write_bytes(data)
            path.chmod(stat.S_IRUSR)
            self.addCleanup(make_writable, path)
        source.unlink()
        (self.repo / '.gitignore').write_text('*.xlsm\n', encoding='utf-8')
        return pin, folder, files

    def test_vba_workflow_preserves_original_and_verifies_all_module_kinds(self):
        pin, _, files = self.pin_template(module_only=True)
        book = self.repo / 'model.xlsm'
        digest = lambda data: hashlib.sha256(data).hexdigest()
        version = digest(files['template.xlsm'])
        self.cli('copy-template', book.name, '--template-sha256', pin)
        self.cli('export', book.name, 'baseline', '--template-sha256', pin, '--desktop-verified', version)
        self.publish('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', self.preview_digest('baseline'))
        sync = (self.store / 'sync.json').read_bytes()
        modules = {name: {'kind': kind, 'source': 'Option Explicit\n', 'metadataSha256': '1' * 64}
                   for name, kind in [('Module1', 'standard'), ('Class1', 'class'),
                                      ('Sheet1', 'document'), ('ThisWorkbook', 'document'), ('Neighbor', 'standard')]}

        def snapshot(workbook_sha, stage, observed_modules):
            return json.dumps({'workbookSha256': workbook_sha, 'stage': stage, 'evidence': f'fixture {stage}',
                               'projectPolicy': 'editable-unsigned', 'complete': True,
                               'referencesSha256': '2' * 64, 'projectMetadataSha256': '3' * 64,
                               'modules': observed_modules}).encode()

        original = snapshot(version, 'baseline-reopen', modules)
        evidence = self.store / 'baseline-vba.json'
        blocked = original.replace(b'editable-unsigned', b'protected')
        evidence.write_bytes(blocked)
        error = self.cli('vba-export', 'baseline', 'vba-base', '--snapshot', evidence.name,
                         '--snapshot-sha256', digest(blocked), ok=False)
        self.assertIn('VBA project is protected', error)
        secret = b'ghp_' + b'x' * 30
        blocked = original.replace(b'Option Explicit', secret)
        evidence.write_bytes(blocked)
        error = self.cli('vba-export', 'baseline', 'vba-base', '--snapshot', evidence.name,
                         '--snapshot-sha256', digest(blocked), ok=False)
        self.assertIn('Credential-like content', error)
        self.assertNotIn(secret.decode(), error)
        evidence.write_bytes(original)
        self.cli('vba-export', 'baseline', 'vba-base', '--snapshot', 'baseline-vba.json',
                 '--snapshot-sha256', digest(original))
        source = (self.store / 'review/vba-base/vba-modules.json').read_bytes()
        self.assertNotIn(b'PRIVATE_FIXTURE_DATA', source)
        self.assertNotIn(b'metadataSha256', source)
        proposed = json.loads(source)
        self.assertEqual(set(proposed['modules']), set(modules))
        for name in ('Module1', 'Class1', 'Sheet1'):
            proposed['modules'][name]['source'].insert(1, "' reviewed edit")
        edit = self.repo / 'vba-modules.json'
        edit.write_bytes(json.dumps(proposed).encode())
        noop = snapshot(version, 'noop-reopen', modules)
        route = json.dumps({'operation': 'existing-vba-module-import', 'profile': 'restricted-xlsm',
                            'evidenceClass': 'desktop', 'entryPoint': 'fixture router', 'backend': 'fixture',
                            'backendVersion': '1', 'excelBuild': 'fixture build', 'qualification': 'fixture only',
                            'authorization': 'fixture only', 'noOpSave': 'fixture save', 'candidate': 'change',
                            'openingControls': dict.fromkeys(('macros', 'events', 'refresh', 'updateLinks', 'autoSave'), False),
                            'noOpPath': 'noop.xlsm',
                            'inputSha256': version, 'baselineSnapshotSha256': digest(original),
                            'noOpSnapshotSha256': digest(noop), 'noOpSha256': version}).encode()
        routes = self.store / 'vba-routes' / digest(route)
        routes.parent.mkdir(mode=0o700)
        routes.mkdir(mode=0o700)
        (self.store / 'noop.xlsm').write_bytes(book.read_bytes())
        for name, content in {'route.json': route, 'baseline.json': original, 'noop.json': noop}.items():
            (routes / name).write_bytes(content)
        base_args = ('baseline', edit.name, 'change', '--route-sha256', digest(route))
        reviewed = ('--reviewed-vba', self.preview_digest('vba-base'))
        self.cli('vba-plan', 'baseline', edit.name, 'change', *reviewed, ok=False)
        error = self.cli('vba-plan', *base_args, '--reviewed-vba', '0' * 64, ok=False)
        self.assertIn('does not match the reviewed VBA export', error)
        args = (*base_args, *reviewed)
        plan = json.loads(self.cli('vba-plan', *args))
        self.assertEqual(plan['changedModules'], ['Class1', 'Module1', 'Sheet1'])
        self.assertFalse((self.store / 'candidates').exists())
        approval = ('--approved-plan', plan['planSha256'])
        approved_edit = edit.read_bytes()
        edit.write_bytes(approved_edit + b' ')
        self.cli('vba-prepare', *args, *approval, ok=False)
        self.assertFalse((self.store / 'candidates').exists())
        edit.write_bytes(approved_edit)
        self.cli('vba-prepare', *args, *approval)
        candidate = self.store / 'candidates/change/workbook.xlsm'
        self.assertEqual(candidate.read_bytes(), book.read_bytes())
        with ZipFile(book) as base, ZipFile(candidate, 'w') as result:
            for name in base.namelist():
                result.writestr(name, b'Synthetic edited VBA bytes' if name == 'xl/vbaProject.bin' else base.read(name))
        saved = digest(candidate.read_bytes())
        edited_modules = {name: {**module, 'source': '\n'.join(proposed['modules'][name]['source'])}
                          for name, module in modules.items()}
        reopened = candidate.with_name('reopen.json')
        bad = {**edited_modules, 'Sheet1': {**edited_modules['Sheet1'], 'metadataSha256': '4' * 64}}
        for observed, ok in ((bad, False), (edited_modules, True)):
            raw = snapshot(saved, 'candidate-reopen', observed)
            reopened.write_bytes(raw)
            self.cli('vba-verify', *args, *approval, '--reopened', digest(raw), '--saved', saved,
                     '--save-evidence', 'fixture candidate save', ok=ok)
            self.assertEqual((self.store / 'review/change').exists(), ok)
        verified = json.loads((self.store / 'review/change/manifest.json').read_bytes())
        self.assertEqual(verified['checks']['vbeCompilation'], 'NOT_RUN')
        self.assertEqual(verified['checks']['fixtureScenario'], 'NOT_RUN')
        self.assertFalse(verified['checks']['macrosExecutedByCli'])
        self.assertEqual(book.read_bytes(), files['template.xlsm'])
        self.assertEqual((self.store / 'sync.json').read_bytes(), sync)

    def test_pinned_xlsm_is_copied_then_accepted_as_first_sync(self):
        pin, folder, files = self.pin_template()
        copy = self.repo / 'model.xlsm'
        self.cli('copy-template', copy.name, '--template-sha256', pin)
        self.assertEqual(copy.read_bytes(), files['template.xlsm'])
        self.assertTrue(copy.stat().st_mode & stat.S_IWRITE)
        error = self.cli('export', copy.name, 'baseline', '--template-sha256', pin, ok=False)
        self.assertIn('requires qualified, authorized desktop readback', error)
        self.assertFalse((self.store / 'review').exists())
        version = hashlib.sha256(files['template.xlsm']).hexdigest()
        # Exercise the attestation contract with synthetic bytes, not desktop qualification.
        self.cli('export', copy.name, 'baseline', '--template-sha256', pin, '--desktop-verified', version)
        self.assertFalse((self.store / 'sync.json').exists())
        self.publish('baseline')
        reviewed = self.preview_digest('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', reviewed)
        sync = json.loads((self.store / 'sync.json').read_bytes())
        self.assertEqual(sync, {'schema': 1, 'workbook': copy.name, 'versionSha256': version,
                                'manifestSha256': reviewed})
        manifest = json.loads((self.repo / 'baseline/manifest.json').read_bytes())
        self.assertEqual(manifest['templateManifestSha256'], pin)
        self.assertEqual((self.store / 'versions' / f'{version}.xlsm').read_bytes(), files['template.xlsm'])
        for name, data in files.items():
            self.assertEqual((folder / name).read_bytes(), data)

    def test_missing_and_modified_companions_block_before_copy(self):
        pin, folder, files = self.pin_template()
        path = folder / 'Form.frx'
        path.chmod(stat.S_IRUSR | stat.S_IWRITE)
        path.unlink()
        error = self.cli('copy-template', 'model.xlsm', '--template-sha256', pin, ok=False)
        self.assertIn('missing', error)
        path.touch(mode=0o600)
        path.write_bytes(b'not the approved companion')
        path.chmod(stat.S_IRUSR)
        error = self.cli('copy-template', 'model.xlsm', '--template-sha256', pin, ok=False)
        self.assertIn('companion checksum', error)
        self.assertFalse((self.repo / 'model.xlsm').exists())
        self.assertFalse((self.store / 'review').exists())
        self.assertFalse((self.store / 'sync.json').exists())
        self.assertEqual((folder / 'template.xlsm').read_bytes(), files['template.xlsm'])

    def test_pinned_manifest_cannot_omit_referenced_frx(self):
        pin, _, _ = self.pin_template(declare_frx=False)
        error = self.cli('copy-template', 'model.xlsm', '--template-sha256', pin, ok=False)
        self.assertIn('missing or unsupported FRX reference', error)
        self.assertFalse((self.repo / 'model.xlsm').exists())

    def test_pinned_workbook_cannot_omit_referenced_vba_project(self):
        pin, _, _ = self.pin_template(missing_vba=True)
        error = self.cli('copy-template', 'model.xlsm', '--template-sha256', pin, ok=False)
        self.assertIn('missing or unsupported VBA project part', error)
        self.assertFalse((self.repo / 'model.xlsm').exists())

    def test_template_copy_is_never_overwritten_or_converted(self):
        pin, _, _ = self.pin_template()
        for name in ('model.xlsx', 'model.xlsb', 'model.xlam', 'model.xls'):
            with self.subTest(name=name):
                error = self.cli('copy-template', name, '--template-sha256', pin, ok=False)
                self.assertIn('conversion is not supported', error)
                self.assertFalse((self.repo / name).exists())
        occupied = self.repo / 'model.xlsm'
        occupied.write_bytes(b'untouched')
        error = self.cli('copy-template', occupied.name, '--template-sha256', pin, ok=False)
        self.assertIn('Choose a new workbook path', error)
        self.assertEqual(occupied.read_bytes(), b'untouched')

    def test_renaming_xlsm_to_xlsx_does_not_convert_it(self):
        save_fixture(self.book, '2+2', macros=True)
        error = self.export('baseline', ok=False)
        self.assertIn('Saved workbook format does not match .XLSX', error)
        self.assertEqual(list(self.store.iterdir()), [])

    def test_export_rejects_store_readable_by_other_users(self):
        save_fixture(self.book, '2+2')
        if sys.platform == 'win32':
            # Grant Everyone read access to this empty synthetic store only.
            subprocess.run(['icacls.exe', str(self.store), '/grant', '*S-1-1-0:(R)'],
                           check=True, timeout=30)
        else:
            self.store.chmod(0o755)
        error = self.export('baseline', ok=False)
        self.assertIn('private store must grant access only to the operator', error)
        self.assertEqual(list(self.store.iterdir()), [])

    def test_export_rejects_workbook_outside_worktree(self):
        save_fixture(self.repo.parent / 'outside.xlsx', '2+2')
        error = self.cli('export', '../outside.xlsx', 'baseline', ok=False)
        self.assertIn('Use a path relative to the Git worktree root.', error)
        self.assertEqual(list(self.store.iterdir()), [])

    def test_saved_blank_xlsx_uses_the_same_initial_acceptance(self):
        save_fixture(self.book, None)
        version = hashlib.sha256(self.book.read_bytes()).hexdigest()
        error = self.cli('export', self.book.name, 'baseline', '--desktop-verified', '0' * 64, ok=False)
        self.assertIn('desktop-verified checksum does not match', error)
        self.cli('export', self.book.name, 'baseline', '--desktop-verified', version)
        self.assertFalse((self.store / 'sync.json').exists())
        self.publish('baseline')
        reviewed = self.preview_digest('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', reviewed)
        baseline = self.repo / 'baseline'
        self.assertEqual(json.loads((baseline / 'ordinary-formulas.json').read_bytes())['cells'], [])
        self.assertEqual(json.loads((self.store / 'sync.json').read_bytes())['versionSha256'], version)

    def test_saved_versions_and_explicit_initial_sync(self):
        neighbor = self.repo / 'neighbor.xlsx'
        neighbor.write_bytes(b'not a workbook; must not be opened')
        save_fixture(self.book, 'SUM(B2:B4)')
        first = self.book.read_bytes()
        version = hashlib.sha256(first).hexdigest()
        self.export('baseline', watch_neighbor=True)
        retained = self.store / 'versions' / f'{version}.xlsx'
        self.assertEqual(retained.read_bytes(), first)
        self.assertFalse(retained.stat().st_mode & 0o200)
        self.assertFalse((self.store / 'sync.json').exists())
        baseline = self.repo / 'baseline'
        self.assertFalse(baseline.exists(), 'An unreviewed export must stay outside Git')
        self.publish('baseline')
        manifest = (baseline / 'manifest.json').read_bytes()
        self.assertEqual(json.loads(manifest)['versionSha256'], version)
        reviewed = hashlib.sha256(manifest).hexdigest()
        self.cli('accept-initial', 'baseline', '--reviewed', reviewed, ok=True)
        sync = (self.store / 'sync.json').read_bytes()
        self.assertEqual(json.loads(sync)['versionSha256'], version)
        self.assertEqual(self.book.read_bytes(), first)

        save_fixture(self.book, 'SUM(B2:B5)')
        second = self.book.read_bytes()
        self.export('candidate', watch_neighbor=True)
        self.publish('candidate')
        diff = subprocess.run(['git', 'diff', '--no-index', '--', 'baseline/ordinary-formulas.json',
                               'candidate/ordinary-formulas.json'], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(diff.returncode, 1, diff.stderr)
        self.assertIn('-      "formula": "=SUM(B2:B4)"', diff.stdout)
        self.assertIn('+      "formula": "=SUM(B2:B5)"', diff.stdout)
        formulas = json.loads((baseline / 'ordinary-formulas.json').read_bytes())
        self.assertEqual(formulas['cells'], [{'sheet': 'Model', 'cell': 'A1', 'formula': '=SUM(B2:B4)'},
                                             {'sheet': 'Model', 'cell': 'A3', 'formula': '=2*2'}])
        inventory = json.loads((baseline / 'inventory.json').read_bytes())
        self.assertEqual(inventory['sheets'][0]['excludedFormulaRecords'], 4)
        self.assertEqual(inventory['sheets'][0]['excludedByKind'],
                         {'arrayWithMetadata': 1, 'inExcludedRange': 1, 'shared': 2})
        for artifact in baseline.iterdir():
            self.assertNotIn(b'PRIVATE_FIXTURE_DATA', artifact.read_bytes())
            self.assertNotIn(b'92345', artifact.read_bytes())
        self.assertEqual(self.book.read_bytes(), second)
        self.assertEqual(neighbor.read_bytes(), b'not a workbook; must not be opened')
        self.assertEqual((self.store / 'sync.json').read_bytes(), sync)

    def test_secret_blocks_publication_without_disclosing_value(self):
        secret = 'synthetic-' + 'credential-for-publication-test'
        save_fixture(self.book, f'IF(A2=1,"{secret}","")')
        before = self.book.read_bytes()
        output = self.export('candidate', ok=False)
        self.assertIn('publication blocked', output.lower())
        self.assertNotIn(secret, output)
        self.assertFalse((self.repo / 'candidate').exists())
        self.assertEqual(list(self.store.iterdir()), [])
        self.assertEqual(self.book.read_bytes(), before)

    def save_query_fixture(self, path, value, *, cell_formula='2+2', connection_id='1', unsafe=False,
                           refresh_on_load=False, command_query='Loaded Query', copy_metadata='',
                           load_column='D', result_value=1, filter_column=None):
        save_fixture(path, cell_formula, queries=True, copy_metadata=copy_metadata,
                     extra_cells=f'<c r="{load_column}1"><v>{result_value}</v></c>')
        package = BytesIO()
        with ZipFile(package, 'w') as mashup:
            expression = '"PRIVATE_INLINE_SECRET"' if unsafe else f'#table(type table [N = number], {{{{{value}}}}})'
            mashup.writestr(ZipInfo('Formulas/Section1.m'),
                            f'section Section1;\nshared #"Loaded Query" = {expression};\n'
                            'shared Staging = let N = 1 in N;\n')
        payload = b'\0' * 4 + b''.join(struct.pack('<I', len(part)) + part for part in (
            package.getvalue(), b'private permissions', b'PRIVATE_MASHUP_CACHE', b'user-specific binding'))
        with ZipFile(path, 'a') as book:
            book.writestr('customXml/item2.xml', '<DataMashup xmlns="http://schemas.microsoft.com/DataMashup">'
                          + base64.b64encode(payload).decode('ascii') + '</DataMashup>')
            book.writestr('xl/connections.xml', f'<connections xmlns="{SHEET}">'
                          f'<connection id="{connection_id}" name="PRIVATE_CONNECTION_DESCRIPTION" '
                          f'refreshOnLoad="{int(refresh_on_load)}">'
                          '<dbPr connection="Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;'
                          'Location=Loaded Query;Extended Properties=&quot;&quot;;" '
                          f'command="SELECT * FROM [{command_query}]"/></connection></connections>')
            book.writestr('xl/queryTables/queryTable1.xml', f'<queryTable xmlns="{SHEET}" connectionId="{connection_id}"/>')
            book.writestr('xl/tables/_rels/table1.xml.rels', f'<Relationships xmlns="{PACKAGE}">'
                          f'<Relationship Id="rId1" Type="{OFFICE}/queryTable" Target="../queryTables/queryTable1.xml"/>'
                          '</Relationships>')
            book.writestr('xl/tables/table1.xml', f'<table xmlns="{SHEET}" name="Results" '
                          f'ref="{load_column}1:{load_column}2">'
                          f'<autoFilter ref="{filter_column or load_column}1:{filter_column or load_column}2"/>'
                          '<tableColumns count="1"><tableColumn id="1" name="N"/></tableColumns></table>')
            book.writestr('xl/worksheets/_rels/sheet1.xml.rels', f'<Relationships xmlns="{PACKAGE}">'
                          f'<Relationship Id="rId1" Type="{OFFICE}/table" Target="../tables/table1.xml"/>'
                          '</Relationships>')

    def test_power_query_export_separates_editable_m_from_load_inventory(self):
        self.save_query_fixture(self.book, 1)
        self.export('baseline', '--power-query')
        self.publish('baseline')
        baseline = self.repo / 'baseline'
        m = json.loads((baseline / 'power-query.json').read_bytes())
        self.assertEqual(m['queries']['Loaded Query'], '#table(type table [N = number], {{1}})')
        inventory = json.loads((baseline / 'power-query-inventory.json').read_bytes())
        self.assertEqual(inventory['connections'], [{'id': '1', 'query': 'Loaded Query'}])
        self.assertEqual(inventory['worksheetLoads'], [{'connectionId': '1', 'sheet': 'Model',
                                                         'table': 'Results', 'range': 'D1:D2'}])
        self.assertFalse(inventory['hasDataModel'])
        for artifact in baseline.iterdir():
            self.assertNotIn(b'PRIVATE_', artifact.read_bytes())
            self.assertNotIn(b'Provider=', artifact.read_bytes())

    def test_power_query_export_blocks_unreviewable_inline_text(self):
        self.save_query_fixture(self.book, 1, unsafe=True)
        error = self.export('bad', '--power-query', ok=False)
        self.assertIn('inline text in M', error)
        self.assertNotIn('PRIVATE_INLINE_SECRET', error)
        self.assertEqual(list(self.store.iterdir()), [])
        self.export('formulas')
        self.publish('formulas')
        self.assertFalse((self.repo / 'formulas/power-query.json').exists())

    def test_manual_load_move_requires_review_and_explicit_acceptance(self):
        self.save_query_fixture(self.book, 1)
        self.export('baseline', '--power-query')
        self.publish('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', self.preview_digest('baseline'))
        base = self.book.read_bytes()
        sync_file = self.store / 'sync.json'
        sync = sync_file.read_bytes()
        (self.repo / '.gitignore').write_text('*.xlsx\n', encoding='utf-8')
        copy = self.repo / 'moved.xlsx'
        self.save_query_fixture(copy, 1, load_column='F')
        saved = copy.read_bytes()
        version = hashlib.sha256(saved).hexdigest()
        retained = self.store / 'versions' / f'{version}.xlsx'
        args = ('baseline', copy.name, 'new-baseline', '--query', 'Loaded Query', '--to', 'F1:F2',
                '--qualified-route', 'synthetic-test-only', '--save-evidence', 'simulated-manual-move',
                '--reopen-evidence', 'simulated-independent-reopen', '--reopened-sha256', version)
        raw = self.cli('pq-load-review', *args)
        review = json.loads(raw)
        self.assertEqual(review['before']['worksheetLoads'][0]['range'], 'D1:D2')
        self.assertEqual(review['after']['worksheetLoads'][0]['range'], 'F1:F2')
        for private in ('PRIVATE_', 'Provider=', '92345'):
            self.assertNotIn(private, raw)
        self.assertIn('review checksum', self.cli('pq-load-accept', *args, '--accepted', '0' * 64, ok=False))
        self.assertFalse(retained.exists())
        self.assertFalse((self.repo / 'new-baseline').exists())
        self.assertEqual(sync_file.read_bytes(), sync)
        self.save_query_fixture(copy, 1, load_column='F', result_value=98765)
        bad_args = (*args[:-1], hashlib.sha256(copy.read_bytes()).hexdigest())
        self.assertIn('preservation of the table and worksheet', self.cli('pq-load-accept', *bad_args,
                      '--accepted', review['reviewSha256'], ok=False))
        self.assertEqual(sync_file.read_bytes(), sync)
        self.assertFalse(retained.exists())
        self.save_query_fixture(copy, 1, load_column='F', filter_column='D')
        bad_args = (*args[:-1], hashlib.sha256(copy.read_bytes()).hexdigest())
        self.assertIn('table filter range', self.cli('pq-load-review', *bad_args, ok=False))
        self.assertEqual(sync_file.read_bytes(), sync)
        copy.write_bytes(saved)
        if os.name == 'nt':
            with copy.open('r+b'):
                self.assertIn('read-only workbook handle', self.cli('pq-load-accept', *args,
                              '--accepted', review['reviewSha256'], ok=False))
            self.assertEqual(sync_file.read_bytes(), sync)
            self.assertFalse(retained.exists())
            self.assertFalse((self.repo / 'new-baseline').exists())
        self.cli('pq-load-accept', *args, '--accepted', review['reviewSha256'])
        self.assertEqual(retained.read_bytes(), saved)
        manifest = (self.repo / 'new-baseline/manifest.json').read_bytes()
        self.assertEqual(json.loads(sync_file.read_bytes()), {
            'schema': 1, 'workbook': copy.name, 'versionSha256': version,
            'manifestSha256': hashlib.sha256(manifest).hexdigest(),
        })
        self.assertEqual(self.book.read_bytes(), base)
        self.assertEqual(copy.read_bytes(), saved)
        receipt = self.store / 'versions' / f'{review["reviewSha256"]}.load-review.json'
        self.assertEqual(json.loads(receipt.read_bytes()), review)
        self.assertNotIn('desktopVerifiedSha256', json.loads(manifest))

    def test_power_query_import_verifies_a_separate_copy_without_advancing_sync(self):
        candidate = self.store / 'candidates/attempt/workbook.xlsx'

        def metadata(folder, digit, *, revision=0):
            path = ''
            if sys.platform == 'win32':
                path = ('<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
                        '<mc:Choice Requires="x15"><x15ac:absPath '
                        'xmlns:x15ac="http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac" '
                        f'url="{escape(str(folder))}\\"/></mc:Choice></mc:AlternateContent>')
            guid = f'{digit * 8}-{digit * 4}-{digit * 4}-{digit * 4}-{digit * 12}'
            return path + ('<xr:revisionPtr xmlns:xr="http://schemas.microsoft.com/office/spreadsheetml/2014/revision" '
                           f'revIDLastSave="{revision}" documentId="13_ncr:1_{{{guid}}}"/>')

        self.save_query_fixture(self.book, 1, copy_metadata=metadata(self.repo, '1'))
        self.export('baseline', '--power-query')
        self.publish('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', self.preview_digest('baseline'))
        sync = (self.store / 'sync.json').read_bytes()
        base = self.book.read_bytes()
        source = (self.repo / 'baseline/power-query.json').read_bytes()
        (self.repo / 'proposed.json').write_bytes(source.replace(b'{{1}}', b'{{2}}'))
        args = ('baseline', 'proposed.json', 'attempt', '--qualified-route', 'synthetic-test-only')
        plan = json.loads(self.cli('pq-plan', *args))
        self.assertEqual(plan['query'], 'Loaded Query')
        self.assertEqual(plan['baseSha256'], hashlib.sha256(base).hexdigest())
        self.assertFalse(candidate.parent.exists())
        error = self.cli('pq-prepare', *args, '--approved-plan', '0' * 64, ok=False)
        self.assertIn('approved plan', error)
        self.assertFalse(candidate.parent.exists())
        approval = ('--approved-plan', plan['planSha256'])
        evidence = ('--save-evidence', 'simulated-save', '--reopen-evidence', 'simulated-reopen')
        self.assertIn('No matching preparation receipt', self.cli(
            'pq-verify', *args, *approval, *evidence, '--reopened-sha256', '0' * 64, ok=False))
        self.cli('pq-prepare', *args, *approval)
        self.assertEqual(candidate.read_bytes(), base)

        # Simulate the route's saved result. This does not qualify a desktop runtime.
        cases = [(metadata(candidate.parent, '2'), {'connection_id': '2'}, 'load wiring'),
                 (metadata(candidate.parent, '2'), {'cell_formula': '2+3'}, 'adjacent workbook parts'),
                 (metadata(candidate.parent, '2', revision=1), {}, 'adjacent workbook parts')]
        if sys.platform == 'win32':
            cases.append((metadata(candidate.parent.parent, '2'), {}, 'adjacent workbook parts'))
        cases.append((metadata(candidate.parent, '2'), {}, ''))
        for workbook_metadata, change, expected in cases:
            self.save_query_fixture(candidate, 2, copy_metadata=workbook_metadata, **change)
            reopened = hashlib.sha256(candidate.read_bytes()).hexdigest()
            message = self.cli('pq-verify', *args, *approval, *evidence, '--reopened-sha256', reopened, ok=not expected)
            if expected:
                self.assertIn(expected, message)
                self.assertFalse((self.store / 'review/attempt').exists())
        self.assertEqual((self.store / 'review/attempt/power-query.json').read_bytes(),
                         (self.repo / 'proposed.json').read_bytes())
        self.assertEqual((self.store / 'review/attempt/power-query-inventory.json').read_bytes(),
                         (self.repo / 'baseline/power-query-inventory.json').read_bytes())
        manifest = json.loads((self.store / 'review/attempt/manifest.json').read_bytes())
        expected_metadata = ['revisionPtr.documentId']
        if sys.platform == 'win32':
            expected_metadata.insert(0, 'absPath.url')
        self.assertEqual(manifest['excelSaveMetadataChanges'], expected_metadata)
        self.assertEqual(manifest['operatorAttestations']['reopen'], 'simulated-reopen')
        self.assertEqual(self.book.read_bytes(), base)
        self.assertEqual((self.store / 'sync.json').read_bytes(), sync)

    def test_power_query_plan_blocks_inventory_new_queries_and_two_sided_drift(self):
        self.save_query_fixture(self.book, 1)
        self.export('baseline', '--power-query')
        self.publish('baseline')
        self.cli('accept-initial', 'baseline', '--reviewed', self.preview_digest('baseline'))
        args = ('attempt', '--qualified-route', 'synthetic-test-only')
        error = self.cli('pq-plan', 'baseline', 'baseline/power-query-inventory.json', *args, ok=False)
        self.assertIn('not an inventory', error)
        proposed = self.repo / 'proposed.json'
        edit = (self.repo / 'baseline/power-query.json').read_bytes().replace(b'{{1}}', b'{{2}}')
        proposed.write_bytes(edit.replace(b'"Staging"', b'"Created Query"'))
        error = self.cli('pq-plan', 'baseline', proposed.name, *args, ok=False)
        self.assertIn('does not create, rename, or remove queries', error)
        proposed.write_bytes(edit.replace(b'{{2}}', b'{{1}}').replace(b'N = 1 in N', b'N = 2 in N'))
        self.assertIn('verified worksheet load', self.cli('pq-plan', 'baseline', proposed.name, *args, ok=False))
        proposed.write_bytes(edit)
        plan = ('pq-plan', 'baseline', proposed.name, *args)
        self.save_query_fixture(self.book, 1, refresh_on_load=True)
        self.assertIn('unsafe opening effects', self.cli(*plan, ok=False))
        self.save_query_fixture(self.book, 1, command_query='Staging')
        self.assertIn('unknown connections', self.cli(*plan, ok=False))
        self.save_query_fixture(self.book, 3)
        self.assertIn('Managed drift', self.cli(*plan, ok=False))
        self.assertFalse((self.store / 'candidates').exists())

    def test_acceptance_rejects_changed_artifacts_and_is_write_once(self):
        save_fixture(self.book, '2+2')
        self.export('candidate')
        approval = self.preview_digest('candidate')
        error = self.publish('candidate', '0' * 64, ok=False)
        self.assertIn('reviewed manifest checksum does not match', error)
        self.assertFalse((self.repo / 'candidate').exists())
        self.publish('candidate', approval)
        folder = self.repo / 'candidate'
        sync = self.store / 'sync.json'
        error = self.cli('accept-initial', 'candidate', '--reviewed', '0' * 64, ok=False)
        self.assertIn('reviewed manifest checksum does not match', error)
        unexpected = folder / 'unreviewed.json'
        unexpected.write_text('{}', encoding='utf-8')
        error = self.cli('accept-initial', 'candidate', '--reviewed', approval, ok=False)
        self.assertIn('no longer matches the retained workbook', error)
        unexpected.unlink()
        formulas = folder / 'ordinary-formulas.json'
        original = formulas.read_bytes()
        formulas.write_bytes(original.replace(b'=2+2', b'=2+3'))
        error = self.cli('accept-initial', 'candidate', '--reviewed', approval, ok=False)
        self.assertIn('no longer matches the retained workbook', error)
        self.assertFalse(sync.exists())
        formulas.write_bytes(original)
        self.cli('accept-initial', 'candidate', '--reviewed', approval)
        approved = sync.read_bytes()
        error = self.cli('accept-initial', 'candidate', '--reviewed', approval, ok=False)
        self.assertIn('first synchronization point is already set', error)
        self.assertEqual(sync.read_bytes(), approved)


if __name__ == '__main__':
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:2] == ['--watch-neighbor']:
        def block_neighbor_open(event, args):
            if event == 'open' and isinstance(args[0], str) and Path(args[0]).name == 'neighbor.xlsx':
                raise SystemExit('Export attempted to open the neighboring workbook')

        sys.addaudithook(block_neighbor_open)
        sys.argv = [str(SCRIPT), *sys.argv[2:]]
        runpy.run_path(str(SCRIPT), run_name='__main__')
    unittest.main()
