"""One controlled, manually started Power Query integration job."""

import argparse
from dataclasses import asdict, dataclass
from functools import cache
import hashlib
from importlib.metadata import version
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
import json
import os
from pathlib import Path
import re
from string import Template
import subprocess
import sys
import tempfile
from typing import Any, Callable, Protocol, TypeVar
from uuid import uuid4
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from excel_pq_desktop import BASE_M, EDITED_M, LABEL, LOADED, NEIGHBOR, NEIGHBOR_M


TOOLS = Path(__file__).resolve().parent
ROUTER = 'skills/in-progress/excel-router/route.py'
# Exact route.py blob at 45ed737f330a9b4dfd4a9ad6f43fa631bdf6313e.
ROUTER_BLOB = '1f01a9e7c1654ad61b67b0ce2691a74ded5d7546'
MANIFEST = 'excel/integration-jobs/{pr}.json'
PROPOSAL = 'excel/power-query.json'
MAX_PACKAGE = 64 * 1024 * 1024
QUALIFICATION = 'https://github.com/ciahciach/skills/pull/58'
RUNTIME = {'excel': '16.0 build 20527.0', 'pywin32': '312'}
LOADS = (('PilotTable', 'Odbior!B5:B6', 'Connection'), ('PilotNeighborTable', 'Odbior!E5:E6', 'Connection1'))
WIRING = tuple(value for load in LOADS for value in load)
EXPECTED = {LOADED: EDITED_M, NEIGHBOR: NEIGHBOR_M}


@dataclass(frozen=True)
class IntegrationPlan:
    issue: int
    source_sha: str
    proposal_sha256: str
    input_version: str
    input_sha256: str


@dataclass(frozen=True)
class MergeReceipt:
    """Authoritative merged-PR metadata, not an Issue status or notification body."""

    repository: str
    pr: int
    merge_sha: str
    merged_by: str
    base: str


def write_once(path: Path, record: dict[str, Any]) -> None:
    onboarding().write_once(path, json.dumps(record, sort_keys=True).encode('utf-8'), writable=True)


def register(state: Path, merge: MergeReceipt, plan: IntegrationPlan | None,
             authorized_mergers: set[str]) -> str | None:
    """Record the plan found in the dedicated merge, supplied by a trusted intake."""
    if plan is None or merge.base != 'main' or merge.merged_by not in authorized_mergers:
        return None
    if (not re.fullmatch(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+', merge.repository)
            or type(merge.pr) is not int or merge.pr < 1 or type(plan.issue) is not int or plan.issue < 1
            or not all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (merge.merge_sha, plan.source_sha))
            or not all(re.fullmatch(r'[0-9a-f]{64}', value) for value in (plan.proposal_sha256, plan.input_sha256))
            or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', plan.input_version)):
        raise ValueError('Invalid merge or pinned integration plan.')
    job = hashlib.sha256(f'{merge.repository.lower()}@{merge.merge_sha}'.encode()).hexdigest()
    path = state / f'{job}.json'
    record = {'merge': {**asdict(merge), 'repository': merge.repository.lower()}, 'plan': asdict(plan)}
    try:
        write_once(path, record)
    except FileExistsError:
        if json.loads(path.read_bytes()) != record:
            raise ValueError('The merge has a conflicting integration plan.') from None
    return job


@dataclass(frozen=True)
class VerifiedInput:
    source_sha: str
    proposal: bytes
    version: str
    workbook: Path
    sync_path: Path | None = None
    sync_sha256: str | None = None


@dataclass(frozen=True)
class Observation:
    session: str
    sha256: str
    refresh: bool
    macros: bool
    links: bool
    read_only: bool = False
    formulas: dict[str, str] | None = None
    wiring: tuple[str, ...] = ()


class Desktop(Protocol):
    @property
    def qualification(self) -> str: ...

    @property
    def environment(self) -> str: ...

    @property
    def evidence_class(self) -> str: ...

    def preflight(self, base: bytes, proposal: bytes) -> tuple[dict[str, str], tuple[str, ...]]: ...
    def save(self, copy: Path, input_sha256: str) -> Observation: ...
    def reopen(self, copy: Path, saved_sha256: str) -> Observation: ...
    def verify_package(self, base: bytes, proposal: bytes, copy: Path) -> None: ...


class UnresolvedDesktop(Exception):
    """A desktop probe did not return a clean process result."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def workbook_bytes(path: Path) -> bytes:
    if path.stat().st_nlink != 1 or path.with_name('~$' + path.name).exists():
        raise ValueError('The workbook has a hard link or an Excel lock.')
    with path.open('rb') as stream:
        data = stream.read(MAX_PACKAGE + 1)
    if len(data) > MAX_PACKAGE:
        raise ValueError('The workbook is larger than the pilot limit.')
    return data


def job_path(state: Path, job: str, phase: str = '') -> Path:
    if not re.fullmatch(r'[0-9a-f]{64}', job):
        raise ValueError('Invalid job identifier.')
    return state / f'{job}{phase}.json'


def start(state: Path, job: str, issue: int, inputs: VerifiedInput, copy: Path,
          desktop: Desktop, *, single_writer: bool) -> dict[str, Any]:
    record = json.loads(job_path(state, job).read_bytes())
    plan = IntegrationPlan(**record['plan'])
    if type(issue) is not int or issue != plan.issue:
        raise ValueError('Start manually from the Issue assigned to this job.')
    attempt_path = job_path(state, job, '.started')
    if attempt_path.exists():
        raise ValueError('This job already started; no restart or recovery is supported.')
    inspection_hold = job_path(state, job, '.inspection-blocked')
    if inspection_hold.exists():
        raise ValueError('Desktop preflight has unresolved effects; operator intervention is required.')
    if single_writer is not True:
        raise ValueError('The controlled session must guarantee one writer.')
    if not desktop.qualification:
        raise ValueError('No matching desktop qualification.')
    base = workbook_bytes(inputs.workbook)
    if (inputs.source_sha != plan.source_sha or digest(inputs.proposal) != plan.proposal_sha256
            or inputs.version != plan.input_version or digest(base) != plan.input_sha256):
        raise ValueError('The input does not match its pinned identity.')
    def check_sync() -> None:
        if inputs.sync_path is not None and digest(onboarding().read_bounded(
                inputs.sync_path, onboarding().MAX_XML)) != inputs.sync_sha256:
            raise ValueError('The approved synchronization point changed.')

    check_sync()
    if copy.resolve() == inputs.workbook.resolve() or copy.exists():
        raise ValueError('Use a separate, new workbook copy.')
    try:
        write_once(inspection_hold, {'phase': 'preflight'})
    except FileExistsError:
        raise ValueError('Desktop preflight is in progress or has unresolved effects.') from None
    if attempt_path.exists():
        inspection_hold.unlink()
        raise ValueError('This job already started; no restart or recovery is supported.')
    try:
        expected_formulas, expected_wiring = desktop.preflight(base, inputs.proposal)
    except UnresolvedDesktop:
        raise ValueError('Desktop preflight has unresolved effects; operator intervention is required.') from None
    except Exception:
        inspection_hold.unlink()
        raise

    attempt = uuid4().hex
    try:
        write_once(attempt_path, {'attempt': attempt})
    except FileExistsError:
        raise ValueError('This job already started; no restart or recovery is supported.') from None
    inspection_hold.unlink()
    if workbook_bytes(inputs.workbook) != base:
        raise ValueError('The input changed before staging.')
    check_sync()
    with copy.open('xb') as stream:
        stream.write(base)
    saved = desktop.save(copy, plan.input_sha256)
    if (saved.refresh, saved.macros, saved.links, saved.read_only) != (False, False, False, False):
        raise ValueError('Unexpected save effects.')
    if not saved.session or saved.sha256 == plan.input_sha256 or digest(workbook_bytes(copy)) != saved.sha256:
        raise ValueError('The save did not produce the reported changed copy.')
    # Passive checks must pass before opening the saved file, including refresh-on-open settings.
    desktop.verify_package(base, inputs.proposal, copy)
    reopened = desktop.reopen(copy, saved.sha256)
    if (not reopened.session or reopened.session == saved.session
            or (reopened.refresh, reopened.macros, reopened.links, reopened.read_only) != (False, False, False, True)
            or reopened.sha256 != saved.sha256 or digest(workbook_bytes(copy)) != saved.sha256
            or reopened.formulas != expected_formulas or reopened.wiring != expected_wiring):
        raise ValueError('Independent readback did not match the approved M and original load wiring.')
    if workbook_bytes(inputs.workbook) != base:
        raise ValueError('The input changed during the integration.')
    check_sync()
    merge = MergeReceipt(**record['merge'])
    native = desktop.evidence_class == 'native-desktop'
    report = {**asdict(plan), 'repository': merge.repository, 'pr': merge.pr, 'merge_sha': merge.merge_sha,
              'job': job, 'attempt': attempt, 'mode': 'synthetic', 'environment': desktop.environment,
              'evidence_class': desktop.evidence_class,
              'qualification': desktop.qualification, 'output_version': f'pq-{attempt}',
              'output_sha256': saved.sha256, 'verification': 'verified' if native else 'simulated',
              'acceptance': 'not-accepted',
              'eligibility': 'passed before write' if native else 'simulated',
              'save_evidence': 'copy save attestation and output SHA-256' if native else 'simulated',
              'package_evidence': 'passive M, load wiring and adjacent parts comparison' if native else 'simulated',
              'reopen_evidence': 'independent read-only desktop attestation and byte comparison' if native else 'simulated',
              'sync_sha256': inputs.sync_sha256 or 'not applicable to this fixture',
              'load_destinations': '; '.join(reopened.wiring),
              'connection_queries': '; '.join(f'{load[2]} -> {query}' for load, query in
                                              zip(LOADS, (LOADED, NEIGHBOR), strict=True)) if native else 'simulated',
              'data_model_present': 'no' if native else 'simulated',
              'checks': {'copy_only': True, 'independent_readback': True, 'm_matches': True,
                         'load_wiring_preserved': True, 'base_unchanged': True, 'refresh': False,
                         'macros': False, 'links_updated': False}}
    write_once(job_path(state, job, '.verified'), report)
    return report


T = TypeVar('T')


def publish(state: Path, job: str, send: Callable[[dict[str, Any]], T]) -> T:
    """Publication uses only the persisted, redacted result; it has no desktop dependency."""
    return send(json.loads(job_path(state, job, '.verified').read_bytes()))


def command(*args: str, cwd: Path | None = None, data: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(args, cwd=cwd, input=data, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise ValueError('A subprocess timed out; process exit and workbook effects are not established') from None
    if proc.returncode:
        raise ValueError(f'{Path(args[0]).name} failed; reconcile local inputs or external state before continuing.')
    return proc.stdout


def git(repo: Path, *args: str) -> bytes:
    return command('git', '--no-replace-objects', *args, cwd=repo)


def intake(state: Path, repo: Path, repository: str, pr: int, authorized_mergers: set[str]) -> str | None:
    """Resolve a notification against GitHub and read the plan from the immutable merge tree."""
    if type(pr) is not int or pr < 1 or not re.fullmatch(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+', repository):
        raise ValueError('Expected an owner/repo and a positive PR number.')
    row = json.loads(command('gh', 'pr', 'view', str(pr), '--repo', repository, '--json',
                             'number,state,mergedBy,mergeCommit,baseRefName'))
    if row['state'] != 'MERGED' or row['baseRefName'] != 'main' or row['number'] != pr:
        return None
    actor = row['mergedBy'] or {}
    if actor.get('is_bot') is not False or actor.get('login') not in authorized_mergers:
        return None
    merge_sha = row['mergeCommit']['oid']
    if not re.fullmatch(r'[0-9a-f]{40}', merge_sha):
        raise ValueError('GitHub did not return a full merge SHA.')
    manifest = MANIFEST.format(pr=pr)
    # The entire merged PR must add the marker, including when GitHub rebases multiple commits.
    pages = json.loads(command('gh', 'api', '--paginate', '--slurp', f'repos/{repository}/pulls/{pr}/files'))
    if [(row['filename'], row['status']) for page in pages for row in page] != [(manifest, 'added')]:
        return None
    plan = IntegrationPlan(**json.loads(git(repo, 'show', f'{merge_sha}:{manifest}')))
    if not re.fullmatch(r'[0-9a-f]{40}', plan.source_sha):
        raise ValueError('The dedicated integration plan needs a full source SHA.')
    git(repo, 'merge-base', '--is-ancestor', plan.source_sha, merge_sha + '^1')
    if digest(git(repo, 'show', f'{plan.source_sha}:{PROPOSAL}')) != plan.proposal_sha256:
        raise ValueError('The proposal blob at the pinned source does not match the plan.')
    return register(state, MergeReceipt(repository, pr, merge_sha, actor['login'], 'main'), plan, authorized_mergers)


def select_qualification(backend: str) -> str:
    router = git(TOOLS.parent, 'show', f'HEAD:{ROUTER}')
    if hashlib.sha1(f'blob {len(router)}\0'.encode() + router).hexdigest() != ROUTER_BLOB:
        raise ValueError('The pinned router implementation does not match.')
    scope = {'class': 'save', 'operation': 'power-query-existing-formula', 'profile': 'application',
             'target_kind': 'synthetic', 'environment': 'logged-in Windows / Excel ' + RUNTIME['excel'],
             'boundary': '#52 two worksheet loads, one literal M edit', 'effects': ['save-copy'],
             'controls': ['copy-only', 'no-refresh-macros-links', 'independent-readback', 'preserve-wiring']}
    method = 'pq-pilot formula-only'
    decision = json.loads(command(sys.executable, '-I', '-c', router.decode('utf-8'), data=json.dumps({
        'scope': scope, 'candidates': [{'interface': 'direct COM', 'version': backend, 'methods': [method]}],
        'evidence': [{'scope': scope, 'interface': 'direct COM', 'version': RUNTIME['pywin32'],
                      'method': method, 'outcome': 'verified', 'reference': QUALIFICATION}],
    }).encode()))
    if decision.get('decision') != 'selected' or decision.get('qualification') != QUALIFICATION:
        raise ValueError('The pinned router did not select the qualified Power Query method.')
    return QUALIFICATION


@cache
def onboarding() -> Any:
    spec = spec_from_file_location('excel_onboarding', TOOLS / 'excel-onboarding.py')
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PilotDesktop:
    environment = f"Windows desktop / Excel {RUNTIME['excel']} / pywin32 {RUNTIME['pywin32']}"
    evidence_class = 'native-desktop'

    def __init__(self, pilot: Any, work: Path, plan: IntegrationPlan, qualification: str):
        self.pilot = pilot
        self.work = work
        self.plan = plan
        self.qualification = qualification

    def preflight(self, base: bytes, proposal: bytes) -> tuple[dict[str, str], tuple[str, ...]]:
        snapshot = self.pilot.checked_query_snapshot(base)
        cells, inventory, _ = self.pilot.workbook_artifacts(base, '.xlsx')
        wiring = snapshot.wiring
        connections = {row['id']: row['query'] for row in wiring['connections']}
        with ZipFile(BytesIO(base)) as book:
            allowed = (r'xl/(?:workbook\.xml|_rels/workbook\.xml\.rels|styles\.xml|sharedStrings\.xml|'
                       r'theme/theme1\.xml|worksheets/(?:sheet1\.xml|_rels/sheet1\.xml\.rels)|'
                       r'connections\.xml|tables/(?:table[12]\.xml|_rels/table[12]\.xml\.rels)|'
                       r'queryTables/queryTable[12]\.xml)')
            if (snapshot.workbook_part != 'xl/workbook.xml'
                    or any(name.startswith('xl/') and not re.fullmatch(allowed, name) for name in book.namelist())):
                raise ValueError('Unexpected parts outside the synthetic worksheet-load profile.')
            def xml(name: str) -> ET.Element:
                part = book.getinfo(name)
                if part.file_size > self.pilot.MAX_XML:
                    raise ValueError('Unexpected synthetic XML part size.')
                return ET.fromstring(book.read(part))

            relations = xml('xl/_rels/workbook.xml.rels')
            targets = [row.get('Target') for row in relations if (row.get('Type') or '').endswith('/connections')]
            if targets not in (['connections.xml'], ['/xl/connections.xml']):
                raise ValueError('The qualified profile requires the canonical workbook connections part.')
            root = xml('xl/connections.xml')
            sheet_ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
            sheet = xml('xl/worksheets/sheet1.xml')
            cached = []
            for cell in sheet.findall(f'{sheet_ns}sheetData/{sheet_ns}row/{sheet_ns}c'):
                address = cell.get('r')
                if address in ('B6', 'E6'):
                    cached.append((address, cell.get('t', 'n'),
                                   [value.text for value in cell.findall(f'{sheet_ns}v')]))
        connection_names = {connections[row.attrib['id']]: row.get('name') for row in root.findall(
            '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}connection')}
        sheets = inventory['sheets']
        if (cells or inventory['definedNames'] or len(sheets) != 1 or sheets[0]['sheet'] != 'Odbior'
                or sheets[0].get('excludedFormulaRecords') != 0 or sheets[0].get('tables') != 2
                or sheets[0].get('calculatedColumnTemplates') != 0
                or sorted(cached, key=lambda cell: cell[0] or '') != [('B6', 'n', ['1']), ('E6', 'n', ['9'])]
                or snapshot.queries != {LOADED: BASE_M, NEIGHBOR: NEIGHBOR_M}
                or connection_names != {query: load[2] for query, load in zip((LOADED, NEIGHBOR), LOADS, strict=True)}
                or len(connections) != 2 or {(row['sheet'], row['range'], row['table'],
                                             connections[row['connectionId']]) for row in wiring['worksheetLoads']}
                    != {(sheet, address, table, query)
                        for (table, location, _), query in zip(LOADS, (LOADED, NEIGHBOR), strict=True)
                        for sheet, address in (location.split('!'),)}
                or json.loads(proposal, object_pairs_hook=self.pilot.unique_json_object)
                    != {'kind': self.pilot.M_SOURCE, 'queries': EXPECTED}):
            raise ValueError('Workbook or proposal is outside the qualified #52 synthetic worksheet-load profile.')
        try:
            observed = json.loads(command(sys.executable, '-B', '-X', 'utf8', str(TOOLS / 'excel_pq_desktop.py'),
                                          'identity', '-', '', json.dumps(RUNTIME)))
        except Exception as error:
            raise UnresolvedDesktop from error
        runtime = observed.get('runtime') if isinstance(observed, dict) else None
        if (not isinstance(runtime, dict) or runtime.keys() != RUNTIME.keys()
                or any(not isinstance(item, str) or not item.strip() for item in runtime.values())):
            raise UnresolvedDesktop('Desktop identity returned incomplete evidence.')
        if runtime != RUNTIME:
            raise ValueError('Excel does not match the qualified runtime; no workbook was opened.')
        return EXPECTED.copy(), WIRING

    def native(self, action: str, copy: Path, sha256: str) -> Observation:
        row = json.loads(command(sys.executable, '-B', '-X', 'utf8', str(TOOLS / 'excel_pq_desktop.py'),
                                 action, str(copy), sha256, json.dumps(RUNTIME)))
        return Observation(row['session'], row['sha256'], row['refresh'], row['macros'], row['linksUpdated'],
                           row.get('readOnly', False), row.get('queries'), tuple(row.get('wiring', ())))

    def save(self, copy: Path, input_sha256: str) -> Observation:
        approval = {'baseSha256': input_sha256, 'integration': asdict(self.plan)}
        approval['planSha256'] = digest(json.dumps(approval, sort_keys=True).encode())
        write_once(copy.with_name('plan.json'), {'planSha256': approval['planSha256']})
        write_once(self.work / 'report.json', {'phases': {'plan': {'plan': approval, 'approved': True,
                                                                 'afterM': EDITED_M}}})
        saved = self.native('save', copy, input_sha256)
        report = self.work / 'report.json'
        data = json.loads(report.read_bytes())
        data['phases']['save'] = {'sha256': saved.sha256}
        report.write_text(json.dumps(data), encoding='utf-8')
        return saved

    def reopen(self, copy: Path, saved_sha256: str) -> Observation:
        return self.native('reopen', copy, saved_sha256)

    def verify_package(self, base: bytes, proposal: bytes, copy: Path) -> None:
        self.pilot.verify_query_copy(base, self.pilot.checked_query_snapshot(base), workbook_bytes(copy),
                                     EXPECTED, copy.parent)


def run_desktop(state: Path, job: str, issue: int, repo: Path, base: Path, sync_store: Path,
                baseline: str, single_writer: bool) -> dict[str, Any]:
    if not single_writer or os.name != 'nt':
        raise ValueError('Requires a controlled, logged-in Windows session guaranteed to have one writer.')
    plan = IntegrationPlan(**json.loads(job_path(state, job).read_bytes())['plan'])
    if not base.is_file() or not base.is_relative_to(repo) or base.suffix.lower() != '.xlsx':
        raise ValueError('Provide the pinned local synthetic XLSX in the project repository.')
    name = base.relative_to(repo).as_posix()
    if git(repo, 'ls-files', '--', f':(literal){name}') or not git(repo, 'check-ignore', '--', name):
        raise ValueError('The synthetic input must be ignored and untracked.')
    source = git(repo, 'rev-parse', '--verify', f'{plan.source_sha}^{{commit}}').decode().strip()
    pilot = onboarding()
    pilot.require_private(state, base)
    sync_store = pilot.storage_path(repo, sync_store)
    sync_path = sync_store / 'sync.json'
    pilot.require_private(sync_store, sync_path)
    sync_bytes = pilot.read_bounded(sync_path, pilot.MAX_XML)
    sync = json.loads(sync_bytes)
    metadata, artifacts = pilot.verified_export(repo, sync_store, pilot.repo_path(repo, baseline),
                                                sync['manifestSha256'])
    version_sha = digest(workbook_bytes(base))
    if (version_sha != sync['versionSha256'] or 'power-query.json' not in artifacts
            or sync['schema'] != metadata['schema'] or sync['versionSha256'] != metadata['versionSha256']
            or sync['workbook'] != name or metadata['workbook'] != name):
        raise ValueError('The input does not match the approved Power Query synchronization point.')
    inputs = VerifiedInput(source, git(repo, 'show', f'{source}:{PROPOSAL}'), version_sha, base,
                           sync_path, digest(sync_bytes))
    qualification = select_qualification(version('pywin32'))
    parent = Path(tempfile.gettempdir()).resolve() / 'kilo'
    parent.mkdir(exist_ok=True)
    work, _, store = pilot.create_pilot_workspace(parent)
    candidate = store / 'candidates' / LABEL / 'workbook.xlsx'
    candidate.parent.mkdir(parents=True)
    report = start(state, job, issue, inputs, candidate, PilotDesktop(pilot, work, plan, qualification),
                   single_writer=single_writer)
    print(f'Private verified copy ({report["output_version"]}): {candidate}', file=sys.stderr)
    return report


def markdown(record: dict[str, Any]) -> str:
    path = TOOLS.parent / 'skills/in-progress/setup-excel-repo/pq-integration-evidence.md'
    return Template(path.read_text(encoding='utf-8')).substitute(
        **record, **record['checks'], claim_limit='Single synthetic #52 worksheet-load profile only.')


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--state', type=Path, required=True, help='Existing trusted, private job directory outside Git.')
    commands = cli.add_subparsers(dest='action', required=True)
    incoming = commands.add_parser('intake')
    incoming.add_argument('--repo', type=Path, required=True)
    incoming.add_argument('--repository', required=True)
    incoming.add_argument('--pr', type=int, help='Reconcile a PR explicitly; otherwise read a closed-PR event on stdin.')
    incoming.add_argument('--authorized-merger', action='append', required=True)
    manual = commands.add_parser('start')
    manual.add_argument('--job', required=True)
    manual.add_argument('--issue', type=int, required=True)
    manual.add_argument('--repo', type=Path, required=True)
    manual.add_argument('--input', type=Path, required=True)
    manual.add_argument('--sync-store', type=Path, required=True, help='Private store of approved onboarding state.')
    manual.add_argument('--baseline', required=True, help='Reviewed Power Query export relative to the project root.')
    manual.add_argument('--controlled-one-writer', action='store_true')
    evidence = commands.add_parser('publish', help='Emit the persisted Markdown only; never open or save a workbook.')
    evidence.add_argument('--job', required=True)
    args = cli.parse_args()
    try:
        state = args.state.resolve(strict=True)
        pilot = onboarding()
        pilot.storage_path(TOOLS.parent, state)
        pilot.require_private(state)
        if args.action == 'publish':
            print(publish(state, args.job, markdown), end='')
            return
        repo = Path(git(args.repo.resolve(strict=True), 'rev-parse', '--show-toplevel').decode().strip()).resolve()
        pilot.storage_path(repo, state)
        if args.action == 'intake':
            pr = args.pr
            if pr is None:
                event = json.load(sys.stdin)
                if (event.get('action') != 'closed' or event.get('pull_request', {}).get('merged') is not True
                        or event.get('repository', {}).get('full_name', '').lower() != args.repository.lower()):
                    print('no integration job')
                    return
                pr = event['number']
            print(intake(state, repo, args.repository, pr, set(args.authorized_merger)) or 'no integration job')
        else:
            record = run_desktop(state, args.job, args.issue, repo, args.input.resolve(strict=True),
                                 args.sync_store.resolve(strict=True), args.baseline, args.controlled_one_writer)
            print(markdown(record), end='')
    except Exception as error:
        if type(error) is ValueError:
            cli.exit(1, f'Blocked: {error}. Do not retry a started write.\n')
        cli.exit(1, f'Blocked ({type(error).__name__}). Inspect private state; do not retry a started write.\n')


if __name__ == '__main__':
    main()
