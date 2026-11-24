import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


if sys.platform != 'win32':
    raise unittest.SkipTest('Direct COM qualification requires Windows')


compare = runpy.run_path(str(Path(__file__).with_name('qualify-excel-com.py')))['changed_parts']


class PackagePreservationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()) / 'kilo')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.base = self.package('base')

    def package(self, name, *, cells=('B1', 'C1'), document_id='original', revision='0',
                first_attr='', second_attr='', custom='original label', chain=None):
        path = self.root / f'{name}.xlsx'
        with ZipFile(path, 'w') as package:
            package.writestr('docProps/core.xml', '<core/>')
            package.writestr('docProps/custom.xml', custom)
            package.writestr('xl/worksheets/sheet1.xml', '<worksheet/>')
            package.writestr('xl/calcChain.xml', chain or (
                             '<calcChain xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                             f'<c r="{cells[0]}" i="1"{first_attr}/>'
                             f'<c r="{cells[1]}" i="1"{second_attr}/></calcChain>'))
            id_attr = f' documentId="{document_id}"' if document_id is not None else ''
            package.writestr('xl/workbook.xml',
                             '<workbook xmlns:xr="http://schemas.microsoft.com/office/spreadsheetml/2014/revision">'
                             f'<xr:revisionPtr revIDLastSave="{revision}"{id_attr}/></workbook>')
        return path

    def test_only_targeted_save_allows_reordering_and_local_document_id_rotation(self):
        candidate = self.package('edited', cells=('C1', 'B1'), document_id='new')
        self.assertEqual(compare(self.base, candidate, edited=True), [])
        self.assertEqual(compare(self.base, candidate), ['xl/calcChain.xml', 'xl/workbook.xml'])

    def test_other_chain_edits_are_still_detected(self):
        for kwargs in ({'cells': ('B1', 'D1')}, {'cells': ('B1', 'B1')}, {'second_attr': ' s="1"'}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(compare(self.base, self.package('bad', **kwargs), edited=True),
                                 ['xl/calcChain.xml'])
        flagged = self.package('flagged', second_attr=' s="1"')
        moved_flag = self.package('moved_flag', cells=('C1', 'B1'), second_attr=' s="1"')
        self.assertEqual(compare(flagged, moved_flag, edited=True), ['xl/calcChain.xml'])

    def test_reorder_keeps_the_initial_level_boundary(self):
        baseline = self.package('level', first_attr=' l="1"')
        candidate = self.package('reordered', cells=('C1', 'B1'), first_attr=' l="1"')
        self.assertEqual(compare(baseline, candidate, edited=True), [])
        self.assertEqual(compare(baseline, candidate), ['xl/calcChain.xml'])
        moved = self.package('level_moved', cells=('C1', 'B1'), second_attr=' l="1"')
        self.assertEqual(compare(baseline, moved, edited=True), ['xl/calcChain.xml'])

    def test_comment_contents_are_not_masked_as_chain_entries(self):
        chain = ('<x:calcChain xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<x:c r="B1" i="1"/><x:c r="C1" i="1"/>'
                 '<!-- <c r="{address}"/><c r="C1"/> --></x:calcChain>')
        baseline = self.package('comment_before', chain=chain.format(address='B1'))
        candidate = self.package('comment_after', chain=chain.format(address='C1'))
        self.assertEqual(compare(baseline, candidate, edited=True), ['xl/calcChain.xml'])

    def test_revision_field_removals_and_label_updates_are_still_detected(self):
        for kwargs in ({'document_id': None}, {'document_id': ''}, {'revision': '1', 'document_id': 'new'}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(compare(self.base, self.package('bad', **kwargs), edited=True),
                                 ['xl/workbook.xml'])
        self.assertEqual(compare(self.base, self.package('bad', custom='other label'), edited=True),
                         ['docProps/custom.xml'])
