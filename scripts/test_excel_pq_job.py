import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import excel_pq_job as workflow
from excel_pq_job import (IntegrationPlan, MergeReceipt, Observation, UnresolvedDesktop, VerifiedInput,
                          digest, intake, markdown, publish, register, select_qualification, start)


PLAN = IntegrationPlan(57, '1' * 40, '2' * 64, 'fixture-v1', '3' * 64)
MERGE = MergeReceipt('owner/repo', 12, '4' * 40, 'maintainer', 'main')


class FixtureDesktop:
    qualification = 'fixture-only'
    environment = 'portable fixture'
    evidence_class = 'portable-simulation'

    def __init__(self):
        self.saves = 0
        self.wiring = ('Sheet1!B5:B6', 'Connection')
        self.formulas = {'Loaded': 'new', 'Neighbor': 'unchanged'}

    def preflight(self, base, proposal):
        return self.formulas.copy(), ('Sheet1!B5:B6', 'Connection')

    def save(self, copy, input_sha256):
        self.saves += 1
        copy.write_bytes(b'saved')
        return Observation('save-session', digest(b'saved'), False, False, False)

    def reopen(self, copy, saved_sha256):
        return Observation('read-session', digest(copy.read_bytes()), False, False, False,
                           True, self.formulas, self.wiring)

    def verify_package(self, base, proposal, copy):
        if copy.read_bytes() != b'saved':
            raise ValueError('Invalid fixture copy')


class IntegrationJobTest(unittest.TestCase):
    def test_notification_resolves_github_and_pinned_git_objects(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'project'
            repo.mkdir()
            state = root / 'state'
            state.mkdir()

            def git(*args):
                return workflow.git(repo, *args).decode().strip()

            def commit(message):
                git('add', '--all')
                git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=ignored-hooks', 'commit', '-m', message)
                return git('rev-parse', 'HEAD')

            git('init', '--initial-branch=main')
            proposal = repo / workflow.PROPOSAL
            proposal.parent.mkdir()
            proposal.write_bytes(b'proposal pinned by commit')
            source = commit('Normal M merge')
            manifest = repo / workflow.MANIFEST.format(pr=12)
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({'issue': 57, 'source_sha': source, 'input_version': 'fixture-v1',
                                            'input_sha256': PLAN.input_sha256,
                                            'proposal_sha256': digest(proposal.read_bytes())}), encoding='utf-8')
            dedicated = commit('Dedicated request')
            proposal.write_bytes(b'unrelated new proposal at current HEAD')
            normal = commit('Ordinary follow-up with inherited marker')
            actual = workflow.command
            receipt = {'number': 13, 'state': 'MERGED', 'mergedBy': {'login': 'maintainer', 'is_bot': False},
                       'mergeCommit': {'oid': normal}, 'baseRefName': 'main'}
            mixed_pr = False

            def transport(*args, **kwargs):
                if args[:2] == ('gh', 'api'):
                    files = [{'filename': manifest.relative_to(repo).as_posix(), 'status': 'added'}]
                    if receipt['number'] == 13:
                        files = [{'filename': workflow.PROPOSAL, 'status': 'modified'}]
                    elif mixed_pr:
                        files.append({'filename': workflow.PROPOSAL, 'status': 'modified'})
                    return json.dumps([files]).encode()
                if args[0] == 'gh':
                    return json.dumps(receipt).encode()
                return actual(*args, **kwargs)

            with patch.object(workflow, 'command', side_effect=transport):
                self.assertIsNone(intake(state, repo, 'owner/repo', 13, {'maintainer'}))
                receipt.update(number=12, mergeCommit={'oid': dedicated},
                               mergedBy={'login': 'maintainer', 'is_bot': True})
                self.assertIsNone(intake(state, repo, 'owner/repo', 12, {'maintainer'}))
                receipt['mergedBy']['is_bot'] = False
                self.assertIsNone(intake(state, repo, 'owner/repo', 12, {'different-user'}))
                mixed_pr = True
                self.assertIsNone(intake(state, repo, 'owner/repo', 12, {'maintainer'}))
                mixed_pr = False
                original = intake(state, repo, 'owner/repo', 12, {'maintainer'})
                self.assertIsNotNone(original)
                self.assertEqual(intake(state, repo, 'owner/repo', 12, {'maintainer'}), original)

    def test_job_accepts_only_the_matching_route_from_the_pinned_router(self):
        self.assertEqual(select_qualification('312'), 'https://github.com/ciahciach/skills/pull/58')
        with self.assertRaisesRegex(ValueError, 'did not select'):
            select_qualification('313')

    def test_pilot_blocks_out_of_profile_packages_before_any_native_call(self):
        snapshot = SimpleNamespace(workbook_part='xl/workbook.xml', queries={workflow.LOADED: workflow.BASE_M,
                                   workflow.NEIGHBOR: workflow.NEIGHBOR_M}, wiring={
            'connections': [{'id': '1', 'query': workflow.LOADED}, {'id': '2', 'query': workflow.NEIGHBOR}],
            'worksheetLoads': [{'sheet': 'Odbior', 'range': 'B5:B6', 'table': 'PilotTable', 'connectionId': '1'},
                               {'sheet': 'Odbior', 'range': 'E5:E6', 'table': 'PilotNeighborTable', 'connectionId': '2'}],
        })
        pilot = SimpleNamespace(checked_query_snapshot=lambda base: snapshot, MAX_XML=32768,
                                workbook_artifacts=lambda base, ext: ([], {'definedNames': 0, 'sheets': [
                                    {'sheet': 'Odbior', 'excludedFormulaRecords': 0, 'tables': 2,
                                     'calculatedColumnTemplates': 0}]}, None),
                                M_SOURCE='editable-power-query-m', unique_json_object=dict)
        desktop = workflow.PilotDesktop(pilot, Path('.'), PLAN, 'fixture-only')
        proposal = json.dumps({'kind': pilot.M_SOURCE, 'queries': workflow.EXPECTED}).encode()
        for defect in ('extra-part', 'wrong-part', 'wrong-name', 'wrong-cache', 'duplicate-cache', 'malformed-identity', None):
            with self.subTest(defect=defect):
                package = BytesIO()
                with ZipFile(package, 'w') as book:
                    target = 'different.xml' if defect == 'wrong-part' else 'connections.xml'
                    book.writestr('xl/_rels/workbook.xml.rels', f'<Relationships><Relationship '
                                  f'Type="namespace/connections" Target="{target}"/></Relationships>')
                    first = 'other' if defect == 'wrong-name' else 'Connection'
                    book.writestr('xl/connections.xml', '<connections '
                                  'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                                  f'<connection id="1" name="{first}"/>'
                                  '<connection id="2" name="Connection1"/></connections>')
                    if defect == 'extra-part':
                        book.writestr('xl/pivotCache/pivotCacheDefinition1.xml', '<cache/>')
                    value = '10' if defect == 'wrong-cache' else '9'
                    duplicate = '<c r="B6"><v>2</v></c>' if defect == 'duplicate-cache' else ''
                    book.writestr('xl/worksheets/sheet1.xml', '<worksheet '
                                  'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                                  f'<sheetData><row>{duplicate}<c r="B6"><v>1</v></c>'
                                  f'<c r="E6"><v>{value}</v></c></row></sheetData></worksheet>')
                result = {} if defect == 'malformed-identity' else {'runtime': workflow.RUNTIME}
                with patch.object(workflow, 'command', return_value=json.dumps(result).encode()) as runner:
                    if defect in ('extra-part', 'wrong-part', 'wrong-name', 'wrong-cache', 'duplicate-cache'):
                        with self.assertRaises(ValueError):
                            desktop.preflight(package.getvalue(), proposal)
                        runner.assert_not_called()
                    elif defect == 'malformed-identity':
                        with self.assertRaises(UnresolvedDesktop):
                            desktop.preflight(package.getvalue(), proposal)
                    else:
                        self.assertEqual(desktop.preflight(package.getvalue(), proposal)[0], workflow.EXPECTED)
                        runner.assert_called_once()

    def test_only_an_authorized_dedicated_merge_creates_one_immutable_job(self):
        with TemporaryDirectory() as directory:
            state = Path(directory)
            self.assertIsNone(register(state, MERGE, None, {'maintainer'}))
            self.assertIsNone(register(state, MERGE, PLAN, {'someone-else'}))
            self.assertEqual(list(state.iterdir()), [])
            job = register(state, MERGE, PLAN, {'maintainer'})
            self.assertIsNotNone(job)
            self.assertEqual(register(state, MERGE, PLAN, {'maintainer'}), job)
            with self.assertRaisesRegex(ValueError, 'conflicting'):
                register(state, MERGE, IntegrationPlan(58, '1' * 40, '2' * 64, 'fixture-v1', '3' * 64),
                         {'maintainer'})
            self.assertEqual(len(list(state.iterdir())), 1)

    def test_manual_start_checks_pins_and_publishes_verified_copy_without_resaving(self):
        with TemporaryDirectory() as directory:
            state = Path(directory).resolve()
            base = state / 'input.xlsx'
            base.write_bytes(b'base')
            sync = state / 'sync.json'
            sync.write_bytes(b'sync')
            copy = state / 'copy.xlsx'
            inputs = VerifiedInput(PLAN.source_sha, b'proposal', PLAN.input_version, base, sync, digest(b'sync'))
            plan = IntegrationPlan(57, PLAN.source_sha, digest(b'proposal'), PLAN.input_version, digest(b'base'))
            job = register(state, MERGE, plan, {'maintainer'})
            assert job is not None
            desktop = FixtureDesktop()
            with self.assertRaisesRegex(ValueError, 'Issue'):
                start(state, job, 56, inputs, copy, desktop, single_writer=True)
            with self.assertRaisesRegex(ValueError, 'one writer'):
                start(state, job, 57, inputs, copy, desktop, single_writer=False)
            for bad in (VerifiedInput('0' * 40, b'proposal', PLAN.input_version, base),
                        VerifiedInput(PLAN.source_sha, b'wrong', PLAN.input_version, base),
                        VerifiedInput(PLAN.source_sha, b'proposal', 'fixture-v2', base),
                        VerifiedInput(PLAN.source_sha, b'proposal', PLAN.input_version, state / 'missing.xlsx')):
                with self.subTest(bad=bad), self.assertRaises((ValueError, OSError)):
                    start(state, job, 57, bad, copy, desktop, single_writer=True)
            self.assertFalse(copy.exists())
            self.assertEqual(desktop.saves, 0)
            sync.write_bytes(b'changed sync')
            with self.assertRaisesRegex(ValueError, 'synchronization point changed'):
                start(state, job, 57, inputs, copy, desktop, single_writer=True)
            sync.write_bytes(b'sync')
            report = start(state, job, 57, inputs, copy, desktop, single_writer=True)
            self.assertEqual(report['output_sha256'], digest(b'saved'))
            self.assertEqual(report['acceptance'], 'not-accepted')
            self.assertEqual(base.read_bytes(), b'base')
            self.assertEqual(sync.read_bytes(), b'sync')
            self.assertEqual(report['sync_sha256'], digest(b'sync'))
            self.assertNotIn('Neighbor', str(report))
            self.assertNotIn(str(state), str(report))

            def offline(record):
                raise ConnectionError('Issue unavailable')

            with self.assertRaises(ConnectionError):
                publish(state, job, offline)
            self.assertEqual(publish(state, job, lambda record: record), report)
            rendered = publish(state, job, markdown)
            self.assertIn(f'`{digest(b"saved")}`', rendered)
            self.assertIn('not-accepted', rendered)
            self.assertIn('portable-simulation', rendered)
            self.assertNotIn('read-only desktop attestation', rendered)
            self.assertNotIn(str(state), rendered)
            with self.assertRaisesRegex(ValueError, 'already started'):
                start(state, job, 57, inputs, state / 'other.xlsx', desktop, single_writer=True)
            self.assertEqual(desktop.saves, 1)

    def test_unqualified_or_bad_readback_never_yields_publishable_evidence(self):
        for problem in ('unqualified', 'same-session', 'wrong-m', 'wrong-wiring', 'base-changed'):
            with self.subTest(problem=problem), TemporaryDirectory() as directory:
                state = Path(directory)
                base = state / 'input.xlsx'
                base.write_bytes(b'base')
                plan = IntegrationPlan(57, PLAN.source_sha, digest(b'proposal'), PLAN.input_version, digest(b'base'))
                job = register(state, MERGE, plan, {'maintainer'})
                assert job is not None

                class BadDesktop(FixtureDesktop):
                    qualification = '' if problem == 'unqualified' else 'fixture-only'

                    def reopen(self, copy, saved_sha256):
                        if problem == 'base-changed':
                            base.write_bytes(b'changed elsewhere')
                        return Observation('save-session' if problem == 'same-session' else 'other-session',
                                           saved_sha256, False, False, False, True,
                                           {} if problem == 'wrong-m' else self.formulas,
                                           () if problem == 'wrong-wiring' else self.wiring)

                desktop = BadDesktop()
                copy = state / 'copy.xlsx'
                with self.assertRaises(ValueError):
                    start(state, job, 57, VerifiedInput(PLAN.source_sha, b'proposal', PLAN.input_version, base),
                          copy, desktop, single_writer=True)
                with self.assertRaises(FileNotFoundError):
                    publish(state, job, self.fail)
                self.assertEqual(desktop.saves, 0 if problem == 'unqualified' else 1)

    def test_clean_preflight_block_can_wait_but_uncertain_probe_blocks_future_starts(self):
        for outcome in ('mismatch', 'unresolved', 'interrupted'):
            with self.subTest(outcome=outcome), TemporaryDirectory() as directory:
                state = Path(directory)
                base = state / 'input.xlsx'
                base.write_bytes(b'base')
                plan = IntegrationPlan(57, PLAN.source_sha, digest(b'proposal'), PLAN.input_version, digest(b'base'))
                job = register(state, MERGE, plan, {'maintainer'})
                assert job is not None
                inputs = VerifiedInput(PLAN.source_sha, b'proposal', PLAN.input_version, base)
                copy = state / 'copy.xlsx'

                class BlockedDesktop(FixtureDesktop):
                    def preflight(self, base, proposal):
                        if outcome == 'unresolved':
                            raise UnresolvedDesktop()
                        if outcome == 'interrupted':
                            raise KeyboardInterrupt()
                        raise ValueError('clean version mismatch')

                with self.assertRaises((KeyboardInterrupt, ValueError)):
                    start(state, job, 57, inputs, copy, BlockedDesktop(), single_writer=True)
                self.assertFalse(copy.exists())
                desktop = FixtureDesktop()
                if outcome != 'mismatch':
                    with self.assertRaisesRegex(ValueError, 'unresolved effects'):
                        start(state, job, 57, inputs, copy, desktop, single_writer=True)
                    self.assertEqual(desktop.saves, 0)
                else:
                    self.assertEqual(start(state, job, 57, inputs, copy, desktop, single_writer=True)['verification'],
                                     'simulated')


if __name__ == '__main__':
    unittest.main()
