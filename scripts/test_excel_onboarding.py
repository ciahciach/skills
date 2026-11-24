import hashlib
from io import TextIOWrapper
import json
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
from zipfile import ZipFile


SCRIPT = Path(__file__).with_name('excel-onboarding.py')
SHEET = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
OFFICE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE = 'http://schemas.openxmlformats.org/package/2006/relationships'


def make_writable(path: Path):
    if path.exists():
        path.chmod(stat.S_IWRITE | stat.S_IRUSR)


def save_fixture(path, expression, *, macros=False, missing_vba=False, data=7, simple=False):
    content_type = ('application/vnd.ms-excel.sheet.macroEnabled.main+xml' if macros
                    else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
    vba_type = '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>' if macros else ''
    vba_link = ('<Relationship Id="rId2" Type="http://schemas.microsoft.com/office/2006/relationships/vbaProject" '
                'Target="vbaProject.bin"/>') if macros else ''
    with ZipFile(path, 'w') as book:
        book.writestr('[Content_Types].xml', f'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          {vba_type}
          <Override PartName="/xl/workbook.xml" ContentType="{content_type}"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>''')
        book.writestr('_rels/.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        book.writestr('xl/workbook.xml', f'<workbook xmlns="{SHEET}" xmlns:r="{OFFICE}"><sheets><sheet name="Model" sheetId="1" r:id="rId1"/></sheets></workbook>')
        book.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/worksheet" Target="worksheets/sheet1.xml"/>{vba_link}</Relationships>')
        rows = '' if expression is None else f'''
          <row r="1"><c r="A1"><f>{escape(expression)}</f><v>92345</v></c><c r="B1" t="inlineStr"><is><t>PRIVATE_FIXTURE_DATA</t></is></c></row>
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
        book.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{SHEET}"><sheetData>{rows}</sheetData></worksheet>')
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
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stdout + result.stderr

    def export(self, name, **kwargs):
        return self.cli('export', 'model.xlsx', name, **kwargs)

    def publish(self, label, reviewed=None, **kwargs):
        approval = reviewed if reviewed is not None else self.preview_digest(label)
        return self.cli('publish', label, label, '--reviewed', approval, **kwargs)

    def preview_digest(self, label):
        return hashlib.sha256((self.store / 'review' / label / 'manifest.json').read_bytes()).hexdigest()

    def pin_template(self, *, declare_frx=True, missing_vba=False):
        source = self.store / 'fixture.xlsm'
        save_fixture(source, '2+2', macros=True, missing_vba=missing_vba)
        files = {'template.xlsm': source.read_bytes(), 'Form.frm': b'Picture = "Form.frx":0000\r\n'}
        if declare_frx:
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
