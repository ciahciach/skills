"""Shared design for the synthetic UserForm comparison in issue #20."""

from dataclasses import dataclass

FONT = "Tahoma"
FONT_SIZE = 9
BACKGROUND = "#f0f0f0"
FOREGROUND = "#202020"
INPUT_BACKGROUND = "#ffffff"
STATUSES = ("Draft", "Ready")
MISSING_CODE = "Enter a sample code."
MISSING_STATUS = "Select a status."
INVALID_QUANTITY = "Enter a whole quantity greater than zero."
SUCCESS = "Sample is valid."


@dataclass(frozen=True)
class Control:
    name: str
    kind: str
    rect: tuple[int, int, int, int]
    caption: str = ""
    parent: str = ""


@dataclass(frozen=True)
class Layout:
    key: str
    title: str
    height: int
    controls: tuple[Control, ...]
    width: int = 276

    @property
    def form_name(self) -> str:
        return f"SampleForm{self.key}"

    @property
    def launcher(self) -> str:
        return f"ShowSampleForm{self.key}"

    @property
    def caption(self) -> str:
        return f"{self.key}: {self.title}"


FIELDS = (
    ("SampleCode", "TextBox", "Sample code"),
    ("SampleStatus", "ComboBox", "Status"),
    ("Quantity", "TextBox", "Quantity"),
)


def fields(
    positions: tuple[tuple[int, int, int, int, int, int, str], ...],
) -> tuple[Control, ...]:
    controls: list[Control] = []
    for (name, kind, caption), (x, y, label_width, input_x, input_y, width, parent) in zip(
        FIELDS, positions, strict=True
    ):
        controls.extend((
            Control(f"Label{name}", "Label", (x, y, label_width, 14), caption, parent),
            Control(name, kind, (input_x, input_y, width, 18), parent=parent),
        ))
    return tuple(controls)


def actions(y: int) -> tuple[Control, ...]:
    return (
        Control("CheckSample", "CommandButton", (12, y, 64, 20), "Check"),
        Control("ResetSample", "CommandButton", (82, y, 64, 20), "Reset"),
        Control("ResultText", "Label", (12, y + 28, 240, 16)),
    )


LAYOUTS = (
    Layout("A", "Vertical", 210, fields((
        (12, 10, 100, 12, 26, 170, ""),
        (12, 49, 100, 12, 65, 170, ""),
        (12, 88, 100, 12, 104, 170, ""),
    )) + actions(134)),
    Layout("B", "Tabular", 172, fields((
        (12, 15, 78, 96, 12, 156, ""),
        (12, 41, 78, 96, 38, 156, ""),
        (12, 67, 78, 96, 64, 156, ""),
    )) + actions(94)),
    Layout("C", "Sections", 222, (
        Control("IdentityFrame", "Frame", (12, 8, 240, 77), "Identity"),
        Control("QuantityFrame", "Frame", (12, 94, 240, 50), "Count"),
    ) + fields((
        (8, 16, 74, 87, 13, 140, "IdentityFrame"),
        (8, 42, 74, 87, 39, 140, "IdentityFrame"),
        (8, 16, 74, 87, 13, 140, "QuantityFrame"),
    )) + actions(152)),
)
