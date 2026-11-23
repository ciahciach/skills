import hashlib
import json
from pathlib import Path
import runpy
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


def save_fixture(path, expression):
    with ZipFile(path, 'w') as book:
        book.writestr('[Content_Types].xml', '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>''')
        book.writestr('_rels/.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        book.writestr('xl/workbook.xml', f'<workbook xmlns="{SHEET}" xmlns:r="{OFFICE}"><sheets><sheet name="Model" sheetId="1" r:id="rId1"/></sheets></workbook>')
        book.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        book.writestr('xl/worksheets/sheet1.xml', f'''<worksheet xmlns="{SHEET}"><sheetData>
          <row r="1"><c r="A1"><f>{escape(expression)}</f><v>92345</v></c><c r="B1" t="inlineStr"><is><t>PRIVATE_FIXTURE_DATA</t></is></c></row>
          <row r="3"><c r="A3"><f>2*2</f></c></row>
          <row r="4"><c r="A4" cm="1"><f t="array" ref="A4:A5">ROW(A4:A5)</f></c></row>
          <row r="5"><c r="A5"><f>3+2</f><v>5</v></c></row>
          <row r="7"><c r="A7"><f t="shared" ref="A7:A8" si="0">B7+1</f></c></row>
          <row r="8"><c r="A8"><f t="shared" si="0"/></c></row>
        </sheetData></worksheet>''')


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
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:2] == ['--watch-neighbor']:
        def block_neighbor_open(event, args):
            if event == 'open' and isinstance(args[0], str) and Path(args[0]).name == 'neighbor.xlsx':
                raise SystemExit('Export attempted to open the neighboring workbook')

        sys.addaudithook(block_neighbor_open)
        sys.argv = [str(SCRIPT), *sys.argv[2:]]
        runpy.run_path(str(SCRIPT), run_name='__main__')
    unittest.main()
