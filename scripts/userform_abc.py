"""Build and independently verify the synthetic UserForm A/B/C fixture (#20)."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from io import TextIOWrapper
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory, gettempdir, mkdtemp
from time import monotonic, sleep
from traceback import extract_tb
from typing import Any, Iterator
from zipfile import ZipFile

from userform_abc_model import (
    BACKGROUND, FONT, FONT_SIZE, FOREGROUND, INPUT_BACKGROUND, INVALID_QUANTITY,
    LAYOUTS, MISSING_CODE, MISSING_STATUS, STATUSES, SUCCESS, Control, Layout,
)

SOURCE = Path(__file__).parent
WORKBOOK = "userform-abc.prototype.xlsm"
PREVIEW = "userform-abc.prototype.html"
RECEIPT = "build-evidence.json"
PROJECT = "UserFormABCFixture"
LAUNCHERS = "FixtureLaunchers"
LIST_STYLE = 2  # fmStyleDropDownList
CONTROLS_WITH_CAPTION = {"Label", "Frame", "CommandButton"}


def render_preview(path: Path) -> None:
    model = dict(
        layouts=[dict(asdict(layout), caption=layout.caption) for layout in LAYOUTS], statuses=STATUSES,
        font=FONT, fontSize=FONT_SIZE, background=BACKGROUND, foreground=FOREGROUND,
        inputBackground=INPUT_BACKGROUND, missingCode=MISSING_CODE,
        missingStatus=MISSING_STATUS, invalidQuantity=INVALID_QUANTITY, success=SUCCESS,
    )
    template = (SOURCE / "userform_abc_preview.html").read_text(encoding="utf-8")
    with path.open("x", encoding="utf-8") as output:
        output.write(template.replace("/* SHARED_MODEL */", json.dumps(model).replace("<", r"\u003c")))


def check_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected!r}, got {actual!r}")


def color(value: str) -> int:
    return int.from_bytes(bytes.fromhex(value[1:]), "little")


@contextmanager
def excel() -> Iterator[Any]:
    if sys.platform != "win32":
        raise RuntimeError("This phase requires Windows desktop Excel and pywin32.")
    from win32com.client import DispatchEx
    from win32process import GetWindowThreadProcessId

    app = DispatchEx("Excel.Application")
    try:
        app.Visible = False
        print(f"Isolated Excel PID: {GetWindowThreadProcessId(app.Hwnd)[1]}", flush=True)
        app.DisplayAlerts = False
        app.ScreenUpdating = False
        events = app.EnableEvents
        try:
            app.EnableEvents = False
            yield app
        finally:
            app.EnableEvents = events
    finally:
        app.Quit()


def handlers(layout: Layout) -> str:
    def literal(text: str) -> str:
        return '"' + text.replace('"', '""') + '"'

    source = (SOURCE / "userform_abc_handlers.vba").read_text(encoding="utf-8")
    replacements = {
        "STATUS_OPTIONS": "\n    ".join(f"Me.SampleStatus.AddItem {literal(s)}" for s in STATUSES),
        "STATUS_COUNT": str(len(STATUSES)),
        "STATUS_LIST": literal("|".join(STATUSES)),
        "FORM_CAPTION": literal(layout.caption),
        "MISSING_CODE": literal(MISSING_CODE), "MISSING_STATUS": literal(MISSING_STATUS),
        "INVALID_QUANTITY": literal(INVALID_QUANTITY), "SUCCESS": literal(SUCCESS),
    }
    for name, value in replacements.items():
        source = source.replace(f"@{name}@", value)
    return source


def export_form(project: Any, layout: Layout, scratch: Path) -> Path:
    component = project.VBComponents.Add(3)  # vbext_ct_MSForm
    component.Name = layout.form_name
    for key, value in {
        "Caption": layout.caption, "Width": layout.width, "Height": layout.height,
        "BackColor": color(BACKGROUND), "ForeColor": color(FOREGROUND),
    }.items():
        component.Properties.Item(key).Value = value

    designer = component.Designer
    containers = {"": designer}
    for spec in layout.controls:
        control = containers[spec.parent].Controls.Add(f"Forms.{spec.kind}.1", spec.name, True)
        control.Left, control.Top, control.Width, control.Height = spec.rect
        control.Font.Name = FONT
        control.Font.Size = FONT_SIZE
        control.ForeColor = color(FOREGROUND)
        control.BackColor = color(INPUT_BACKGROUND if spec.kind in {"TextBox", "ComboBox"} else BACKGROUND)
        if spec.kind in CONTROLS_WITH_CAPTION:
            control.Caption = spec.caption
        if spec.kind == "ComboBox":
            control.Style = LIST_STYLE
        if spec.kind == "Frame":
            containers[spec.name] = control

    path = scratch / f"{layout.form_name}.frm"
    component.Export(str(path))
    with path.open("ab") as output:
        output.write(("\r\n" + handlers(layout).replace("\n", "\r\n") + "\r\n").encode("ascii"))
    return path


def add_launchers(project: Any, sheet: Any, scratch: Path) -> None:
    lines = [f'Attribute VB_Name = "{LAUNCHERS}"', "Option Explicit"]
    for index, layout in enumerate(LAYOUTS):
        lines.extend((
            f"Public Sub {layout.launcher}()", f"    {layout.form_name}.Show", "End Sub",
            f"Public Function TestSampleForm{layout.key}() As String",
            f"    TestSampleForm{layout.key} = {layout.form_name}.RunFixture()",
            f"    Unload {layout.form_name}", "End Function",
        ))
        button = sheet.Shapes.AddFormControl(0, 18, 50 + index * 32, 134, 24)
        button.Name = f"Launch{layout.key}"
        button.TextFrame.Characters().Text = layout.caption
        button.OnAction = layout.launcher
    path = scratch / f"{LAUNCHERS}.bas"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    project.VBComponents.Import(str(path))


def compile_project(app: Any, book: Any) -> None:
    for attempt in range(3):
        project = app.VBE.ActiveVBProject
        if project is not None and project.Name == PROJECT and project.FileName == book.FullName:
            break
        if attempt < 2:
            sleep(2)
    else:
        raise RuntimeError("The fixture is not the active VBE project.")
    for layout in LAYOUTS:
        check_equal(project.VBComponents.Item(layout.form_name).Type, 3, layout.form_name)
    command = app.VBE.CommandBars.FindControl(1, 578)
    if command is None or not command.Enabled:
        raise RuntimeError("Explicit VBE Compile command unavailable or already disabled.")
    command.Execute()
    if command.Enabled:
        raise RuntimeError("VBE Compile did not transition to disabled.")


def build(directory: Path, attempt_compile: bool, evidence: dict[str, Any]) -> None:
    with excel() as app:
        evidence["backend"] = {"excel": str(app.Version), "build": str(app.Build), "pywin32": version("pywin32")}
        book = app.Workbooks.Add(-4167)  # xlWBATWorksheet
        try:
            sheet = book.Worksheets.Item(1)
            sheet.Name = "Start"
            sheet.Range("A1").Value = "Synthetic UserForm A/B/C comparison"
            sheet.Range("A2").Value = "Compare all three layouts; no production data or default."
            project = book.VBProject  # Requires existing trusted access; never change it.
            project.Name = PROJECT
            with TemporaryDirectory(dir=directory) as scratch:
                scaffold = app.Workbooks.Add(-4167)
                try:
                    paths = []
                    for layout in LAYOUTS:
                        print(f"Creating designer scaffold {layout.form_name}", flush=True)
                        paths.append(export_form(scaffold.VBProject, layout, Path(scratch)))
                finally:
                    scaffold.Close(False)
                for path in paths:
                    print(f"Importing {path.stem}", flush=True)
                    project.VBComponents.Import(str(path))
                add_launchers(project, sheet, Path(scratch))
            path = directory / WORKBOOK
            if path.exists():
                raise FileExistsError(path)
            book.SaveAs(str(path), 52)  # xlOpenXMLWorkbookMacroEnabled
            check_equal(book.Saved, True, "Excel saved flag")
            evidence["save"] = {"status": "PASS", "sha256": sha256(path.read_bytes()).hexdigest()}
            (directory / RECEIPT).write_text(json.dumps(evidence, indent=2), encoding="utf-8")

            if attempt_compile:
                evidence["full_vbe_compile"] = {"status": "NOT VERIFIED", "detail": "Compile in progress"}
                (directory / RECEIPT).write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                try:
                    compile_project(app, book)
                    evidence["full_vbe_compile"] = {"status": "PASS", "detail": "Explicit command changed from enabled to disabled"}
                except Exception as exc:
                    evidence["full_vbe_compile"] = {"status": "NOT VERIFIED", "detail": str(exc)}

            results = {}
            for layout in LAYOUTS:
                try:
                    result = app.Run(f"'{book.Name}'!TestSampleForm{layout.key}")
                    check_equal(result, "list options, missing code, missing status, zero, fraction, valid, reset", layout.form_name)
                    results[layout.key] = {"status": "PASS", "detail": result}
                except Exception as exc:
                    results[layout.key] = {"status": "FAIL", "detail": str(exc)}
            evidence["vba_scenarios"] = {
                "status": "PASS" if all(r["status"] == "PASS" for r in results.values()) else "FAIL",
                "layouts": results,
            }
        finally:
            book.Close(False)


def check_control(spec: Control, control: Any) -> None:
    check_equal(tuple(float(getattr(control, p)) for p in ("Left", "Top", "Width", "Height")), spec.rect, spec.name)
    check_equal((control.Font.Name, control.Font.Size), (FONT, FONT_SIZE), f"{spec.name} font")
    check_equal(control.ForeColor, color(FOREGROUND), f"{spec.name} foreground")
    back = INPUT_BACKGROUND if spec.kind in {"TextBox", "ComboBox"} else BACKGROUND
    check_equal(control.BackColor, color(back), f"{spec.name} background")
    if spec.kind in CONTROLS_WITH_CAPTION:
        check_equal(control.Caption, spec.caption, f"{spec.name} caption")
    if spec.kind == "ComboBox":
        check_equal(control.Style, LIST_STYLE, f"{spec.name} list style")


def verify(directory: Path) -> dict[str, Any]:
    path = directory / WORKBOOK
    receipt = json.loads((directory / RECEIPT).read_text(encoding="utf-8"))
    check_equal(receipt["save"]["status"], "PASS", "build receipt")
    digest = sha256(path.read_bytes()).hexdigest()
    check_equal(digest, receipt["save"]["sha256"], "fixture digest")
    for lock_name in (f"~${WORKBOOK}", f"~${WORKBOOK[2:]}"):
        if (directory / lock_name).exists():
            raise RuntimeError("Fixture is already open; close it before readback.")
    # ForceDisable covers VBA but not XLM. Exclude other active content before Open.
    with ZipFile(path) as package:
        for part in package.namelist():
            if part.lower().startswith(("xl/macrosheets/", "xl/intlmacrosheets/", "xl/externallinks/", "xl/querytables/", "xl/activex/")) or part.lower() == "xl/connections.xml":
                raise RuntimeError(f"Unexpected active content: {part}")
    if sys.platform != "win32":
        raise RuntimeError("Readback requires Windows desktop Excel and pywin32.")
    from pywintypes import com_error

    for attempt in range(3):
        opened = False
        try:
            with excel() as app:
                security = app.AutomationSecurity
                try:
                    app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
                    book = app.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=True, AddToMru=False)
                    opened = True
                finally:
                    app.AutomationSecurity = security
                try:
                    end = monotonic() + 20
                    while not app.Ready:
                        if monotonic() >= end:
                            raise TimeoutError("Excel did not become ready after opening the fixture.")
                        sleep(0.2)
                    result = read_workbook(book)
                finally:
                    book.Close(False)
            break
        except com_error as exc:
            if opened or exc.hresult != -2147352567 or attempt == 2:
                raise
            sleep(2)
    else:
        raise RuntimeError("Could not open the fixture.")
    check_equal(sha256(path.read_bytes()).hexdigest(), digest, "post-readback fixture digest")
    return {"status": "PASS", "sha256": digest, "forms": result}


def read_workbook(book: Any) -> dict[str, Any]:
    check_equal(book.ReadOnly, True, "read-only open")
    check_equal(book.FileFormat, 52, "XLSM format")
    project = book.VBProject
    check_equal(project.Name, PROJECT, "fixture VBA project")
    forms = {c.Name: c for c in project.VBComponents if c.Type == 3}
    check_equal(set(forms), {layout.form_name for layout in LAYOUTS}, "persisted UserForms")
    module = project.VBComponents.Item(LAUNCHERS).CodeModule
    launcher_code = "\n".join(line.strip() for line in module.Lines(1, module.CountOfLines).splitlines())
    sheet = book.Worksheets.Item("Start")
    check_equal(sheet.Shapes.Count, len(LAYOUTS), "Start launch buttons")
    results = {}
    for layout in LAYOUTS:
        component = forms[layout.form_name]
        designer = component.Designer
        containers = {"": designer}
        tabs: dict[str, list[int]] = {}
        for spec in layout.controls:
            control = containers[spec.parent].Controls.Item(spec.name)
            check_control(spec, control)
            if spec.kind != "Label":
                tabs.setdefault(spec.parent, []).append(control.TabIndex)
            if spec.kind == "Frame":
                containers[spec.name] = control
        for name, container in containers.items():
            # MSForms lists nested controls in the form-wide collection as well as in each frame.
            expected = sum(s.parent == name for s in layout.controls) if name else len(layout.controls)
            check_equal(container.Controls.Count, expected, name or layout.form_name)
        for parent, indices in tabs.items():
            check_equal(indices, sorted(set(indices)), f"{layout.form_name}/{parent} tab order")
        button = sheet.Shapes.Item(f"Launch{layout.key}")
        check_equal(button.FormControlType, 0, button.Name)
        check_equal(button.TextFrame.Characters().Text, layout.caption, f"{button.Name} caption")
        action = button.OnAction
        if action not in {layout.launcher, f"{book.Name}!{layout.launcher}", f"'{book.Name}'!{layout.launcher}"}:
            raise RuntimeError(f"{button.Name}: unexpected launcher {action!r}")
        definition = f"\nPublic Sub {layout.launcher}()\n{layout.form_name}.Show\nEnd Sub\n"
        if definition not in launcher_code:
            raise RuntimeError(f"{button.Name}: launcher does not show {layout.form_name}")
        results[layout.key] = {"form": layout.form_name, "controls": len(layout.controls), "launcher": action}
    return results


def main() -> int:
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
From the repository root:
  python -B -X utf8 scripts/userform_abc.py preview
  python -B -X utf8 scripts/userform_abc.py build
  python -B -X utf8 scripts/userform_abc.py verify "<Run directory printed by build>"

Build and readback require Windows desktop Excel, pywin32 and existing trusted
access to the VBA project object model. Outputs go in %TEMP%\\kilo.
Use only run directories produced by this tool on this machine. The receipt
checks integrity, not provenance. The files are disposable and not committed.
The controlled handler scenarios are not interactive native UI tests or proof
of full compilation. Use build --compile only in a supervised desktop run;
it can surface an Excel dialog. No settings or target workbooks are changed.
Source: https://github.com/ciahciach/skills/issues/14#issuecomment-7115225734
""",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preview", help="Generate HTML only; does not start Excel.")
    builder = commands.add_parser("build", help="Create HTML and a fresh XLSM, then exercise fixture VBA.")
    builder.add_argument("--compile", action="store_true", help="Attempt explicit VBE Compile (may open a modal dialog).")
    reader = commands.add_parser("verify", help="Reopen this tool's saved fixture in a separate Excel instance.")
    reader.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    evidence: dict[str, Any] = {}
    directory = None
    try:
        if args.command == "verify":
            directory = args.run_directory.resolve(strict=True)
            evidence["readback"] = verify(directory)
        else:
            root = Path(gettempdir()) / "kilo"
            root.mkdir(exist_ok=True)
            directory = Path(mkdtemp(prefix="userform-abc-", dir=root))
            print(f"Run directory: {directory}", flush=True)
            render_preview(directory / PREVIEW)
            if args.command == "build":
                evidence.update(save={"status": "NOT VERIFIED"}, vba_scenarios={"status": "NOT RUN"},
                                full_vbe_compile={"status": "NOT VERIFIED", "detail": "Explicit compile not attempted"})
                build(directory, args.compile, evidence)
    except Exception as exc:
        phase = "readback" if args.command == "verify" else "save"
        location = next((frame for frame in reversed(extract_tb(exc.__traceback__))
                         if Path(frame.filename).resolve() == Path(__file__).resolve()), None)
        detail = f"{location.name}:{location.lineno}: {exc}" if location else str(exc)
        if evidence.get(phase, {}).get("status") == "PASS":
            evidence["error"] = detail
        else:
            evidence[phase] = {"status": "FAIL", "detail": detail}
    if evidence:
        report = json.dumps(evidence, indent=2)
        if args.command == "build" and directory is not None:
            (directory / RECEIPT).write_text(report + "\n", encoding="utf-8")
        print(report)
    compile_unverified = (args.command == "build" and args.compile
                          and evidence.get("full_vbe_compile", {}).get("status") != "PASS")
    return int(compile_unverified or "error" in evidence or any(v.get("status") == "FAIL" for v in evidence.values()))


if __name__ == "__main__":
    raise SystemExit(main())
