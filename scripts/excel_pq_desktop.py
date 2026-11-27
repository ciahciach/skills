"""Process-isolated Excel worker for the synthetic pq-pilot command only."""

import hashlib
from importlib import import_module
from importlib.metadata import version
from io import TextIOWrapper
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any
from uuid import uuid4


LOADED = 'PilotLoaded'
NEIGHBOR = 'PilotNeighbor'
LABEL = 'formula-only'
BASE_M = '#table(type table [N = number], {{1}})'
EDITED_M = '#table(type table [N = number], {{2}})'
NEIGHBOR_M = '#table(type table [N = number], {{9}})'


def run(action: str, path: Path, approved_sha: str,
        expected_runtime: dict[str, str] | None = None) -> dict[str, Any]:
    candidate = ('private', 'candidates', LABEL, 'workbook.xlsx')
    noop = ('noop', 'workbook.xlsx')
    layouts: dict[str, set[tuple[str, ...]]] = {'create': {('fixture', 'base.xlsx')}, 'noop': {noop},
                                                'save': {candidate}, 'reopen': {noop, candidate}}
    prefix = Path(tempfile.gettempdir()).resolve() / 'kilo'
    probe = action == 'identity'
    if not probe:
        relative = path.relative_to(prefix).parts
        if (len(relative) < 2 or not relative[0].startswith('pq-pilot-') or path.resolve() != path
                or relative[1:] not in layouts[action]):
            raise ValueError('Expected a fresh synthetic pilot path.')
    lock = path.with_name('~$' + path.name)
    if not probe and (lock.exists() or (action == 'create' and path.exists())):
        raise RuntimeError('Workbook is locked or already exists.')

    def digest() -> str:
        if path.stat().st_nlink != 1:
            raise RuntimeError('Expected a disposable workbook without hard links.')
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    def step(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    if action not in ('create', 'identity') and digest() != approved_sha:
        raise RuntimeError('Workbook no longer matches the supplied SHA-256.')
    if not probe and action != 'create':
        attempt = prefix / relative[0]
        phases = json.loads((attempt / 'report.json').read_bytes())['phases']
        approval = phases['plan']
        plan = approval['plan']
        if not approval['approved'] or approval['afterM'] != EDITED_M:
            raise RuntimeError('The synthetic plan was not approved.')
        if action in ('noop', 'save') and plan['baseSha256'] != approved_sha:
            raise RuntimeError('The copy does not match the approved base SHA-256.')
        if action == 'save':
            receipt = json.loads(path.with_name('plan.json').read_bytes())
            if receipt != {'planSha256': plan['planSha256']}:
                raise RuntimeError('The copy has no matching pq-prepare receipt.')
        if action == 'reopen':
            save = phases['noop']['save'] if relative[1:] == noop else phases['save']
            if save['sha256'] != approved_sha:
                raise RuntimeError('The reopen does not match the reported save SHA-256.')

    step('check desktop runtime')
    backend = version('pywin32')
    if not probe and expected_runtime is not None and expected_runtime['pywin32'] != backend:
        raise RuntimeError('The installed pywin32 does not match the qualified runtime.')
    client = import_module('win32com.client')
    api = import_module('win32api')
    jobs = import_module('win32job')
    processes = import_module('win32process')
    desktop = import_module('win32service').OpenInputDesktop(0, False, 1)  # DESKTOP_READOBJECTS
    desktop.CloseDesktop()

    existing = set(processes.EnumProcesses())
    step('start dedicated Excel')
    app = client.DispatchEx('Excel.Application')
    _, pid = processes.GetWindowThreadProcessId(app.Hwnd)
    if not pid or pid in existing:
        raise RuntimeError('Excel did not start in a dedicated process.')

    job = None
    try:
        step('attach Excel to timeout job')
        # If the runner times out, closing the worker closes this job, not other Excel sessions.
        job = jobs.CreateJobObject(None, f'Local\\pq-pilot-{uuid4()}')
        policy = jobs.QueryInformationJobObject(job, jobs.JobObjectExtendedLimitInformation)
        policy['BasicLimitInformation']['LimitFlags'] |= jobs.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        jobs.SetInformationJobObject(job, jobs.JobObjectExtendedLimitInformation, policy)
        process = api.OpenProcess(0x101, False, pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        try:
            jobs.AssignProcessToJobObject(job, process)
        finally:
            process.Close()
        step('Excel attached to timeout job')

        step('configure Excel opening effects')
        runtime = {'excel': f'{app.Version} build {app.Build}', 'pywin32': backend}
        if probe:
            return {'runtime': runtime}
        if expected_runtime is not None and runtime != expected_runtime:
            raise RuntimeError('Excel does not match the qualified runtime; no workbook was opened.')
        observed: dict[str, Any] = {'runtime': runtime}
        if expected_runtime is not None:
            observed['session'] = uuid4().hex
        app.Visible = False
        app.DisplayAlerts = False
        app.ScreenUpdating = False
        security, events = app.AutomationSecurity, app.EnableEvents
        app.EnableEvents = False
        app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        book = None
        try:
            if lock.exists() or (action != 'create' and digest() != approved_sha):
                raise RuntimeError('Workbook was locked or changed before Open.')
            if action == 'create':
                step('create synthetic queries and worksheet table')
                book = app.Workbooks.Add(-4167)  # xlWBATWorksheet
                sheet = book.Worksheets(1)
                sheet.Name = 'Odbior'
                book.Queries.Add(LOADED, BASE_M)
                book.Queries.Add(NEIGHBOR, NEIGHBOR_M)
                # Load both literal queries once so Excel initializes their save metadata symmetrically.
                for query, name, column, value in ((LOADED, 'PilotTable', 'B', 1),
                                                   (NEIGHBOR, 'PilotNeighborTable', 'E', 9)):
                    connection = (f'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;'
                                  f'Location={query};Extended Properties=""')
                    table = sheet.ListObjects.Add(SourceType=0, Source=connection,
                                                  Destination=sheet.Range(f'{column}5'))
                    table.Name = name
                    query_table = table.QueryTable
                    query_table.CommandType = 2  # xlCmdSql
                    query_table.CommandText = f'SELECT * FROM [{query}]'
                    query_table.RefreshOnFileOpen = False
                    query_table.RefreshPeriod = 0
                    oledb = query_table.WorkbookConnection.OLEDBConnection
                    oledb.RefreshOnFileOpen = False
                    oledb.RefreshPeriod = 0
                    step(f'populate fixture from literal M: {query}')
                    if not query_table.Refresh(False) or sheet.Range(f'{column}6').Value2 != value:
                        raise RuntimeError(f'Could not initialize synthetic {column}6 to {value}.')
                step('save synthetic fixture')
                book.SaveAs(str(path), 51, AddToMru=False)  # xlOpenXMLWorkbook (.xlsx)
                observed['fixtureOnlyRefresh'] = True
            else:
                read_only = action == 'reopen'
                step('open disposable copy')
                book = app.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=read_only,
                                          IgnoreReadOnlyRecommended=True, AddToMru=False)
                for _ in range(20):
                    if app.Ready:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError('Excel did not become ready within 20 seconds.')
                if bool(book.ReadOnly) != read_only:
                    raise RuntimeError('Workbook opened in an unexpected access mode.')
                if read_only:
                    step('read saved formulas and load destination')
                    sheet = book.Worksheets('Odbior')
                    table = sheet.ListObjects('PilotTable')
                    value = sheet.Range('B6').Value2
                    if value != 1 or table.Range.Address != '$B$5:$B$6':
                        raise RuntimeError('Native reopen did not preserve the loaded range and B6 = 1.')
                    observed.update(readOnly=True, b6=value, loadRange='Odbior!B5:B6',
                                    connection=table.QueryTable.WorkbookConnection.Name,
                                    queries={query.Name: query.Formula.strip() for query in book.Queries})
                    if expected_runtime is not None:
                        neighbor = sheet.ListObjects('PilotNeighborTable')
                        if sheet.Range('E6').Value2 != 9 or len(book.Connections) != 2:
                            raise RuntimeError('Native reopen did not preserve the neighboring worksheet load.')
                        observed['wiring'] = [item for load in (table, neighbor) for item in
                                              (load.Name, f'{sheet.Name}!{load.Range.Address.replace("$", "")}',
                                               load.QueryTable.WorkbookConnection.Name)]
                else:
                    step('save disposable copy')
                    if book.AutoSaveOn:
                        raise RuntimeError('AutoSave must be off before native save.')
                    if action == 'save':
                        book.Queries(LOADED).Formula = EDITED_M
                    else:
                        book.Saved = False  # Force a physical save without changing workbook content.
                    book.Save()
                observed.update(refresh=False, macros=False, linksUpdated=False)
        finally:
            try:
                if book is not None:
                    step('close without saving again')
                    book.Close(SaveChanges=False)
            finally:
                app.AutomationSecurity = security
                app.EnableEvents = events
    finally:
        try:
            step('quit dedicated Excel')
            app.Quit()
        finally:
            if job is not None:
                job.Close()

    observed['sha256'] = digest()
    if lock.exists() or (action == 'reopen' and observed['sha256'] != approved_sha):
        raise RuntimeError('Closing Excel left a lock or the read-only workbook bytes changed.')
    return observed


if __name__ == '__main__':
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        action, filename, expected_sha, *guard = sys.argv[1:]
        if ((guard and (len(guard) != 1 or action not in ('identity', 'save', 'reopen')))
                or (action == 'identity' and not guard)):
            raise ValueError('Expected the runtime guard for identity, formula save or independent reopen.')
        print(json.dumps(run(action, Path(filename), expected_sha, json.loads(guard[0]) if guard else None)))
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        raise SystemExit(1)
