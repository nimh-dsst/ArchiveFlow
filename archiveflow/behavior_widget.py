import json
import string
from io import BytesIO
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Final, Literal
from xml.etree import ElementTree as ET

import pandas as pd
from requests import Response


class EmptyResults(Exception):
    def __init__(self, message: str | None):
        super().__init__(message)


class FormIdError(Exception):
    def __init__(self, message: str | None):
        super().__init__(message)


class BehaviorFormV4:
    FORM_ID: Final[int] = 20058
    FORM_VERSION: Final[int] = 4
    FORM_METADATA: Final[dict[str, str]] = {
        "date_date": "Date",
        "start": "Start Time",
        "personnel": "Personnel Running Task",
        "room": "Behavior Room",
        "experiment": "Experiment",
        "subjects": "Subjects",
        "manipulation": "Manipulation",
        "video_file_path": "Video File Path",
        "protocol": "AnyMaze Protocol",
        "cue": "Cue Information",
        "reward": "Reward Information",
    }
    FIRST_TABLE_NUM_COLS: Final[int] = 6
    FIRST_TABLE_NUM_SUBJECTS: Final[int] = 12
    FIRST_TABLE_DATA_INPUTS: Final[list[list[str]]] = []
    for i in range(FIRST_TABLE_NUM_SUBJECTS):
        subject_row: list[str] = []
        subject_letter: str = string.ascii_lowercase[i]
        for j in range(FIRST_TABLE_NUM_COLS):
            subject_row.append(f"{subject_letter}{j + 1}")
        FIRST_TABLE_DATA_INPUTS.append(subject_row)
    FIRST_TABLE_HEADERS: Final[list[str]] = [
        "p6",
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
    ]
    # The order of the subjects is scrambled at the end in the form
    # the list is in the proper order to match to form
    FIRST_TABLE_SUBJECTS: Final[list[str]] = [
        "m1",
        "m2",
        "m3",
        "m4",
        "m5",
        "m6",
        "m7",
        "m8",
        "m9",
        "m12",
        "m10",
        "m11",
    ]
    FIRST_TABLE: pd.DataFrame = pd.DataFrame(
        data=FIRST_TABLE_DATA_INPUTS,
        columns=FIRST_TABLE_HEADERS,
        index=FIRST_TABLE_SUBJECTS,
    )
    SECOND_TABLE_NUM_COLS: Final[int] = 6
    SECOND_TABLE_NUM_SUBJECTS: Final[int] = 8
    SECOND_TABLE_HEADERS: Final[list[str]] = [
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
        "p6",
    ]
    SECOND_TABLE_SUBJECTS: Final[list[str]] = [
        "m1",
        "m2",
        "m3",
        "m4",
        "m5",
        "m6",
        "m7",
        "m8",
    ]
    SECOND_TABLE_DATA_INPUTS: Final[list[list[str]]] = []
    for i in range(SECOND_TABLE_NUM_SUBJECTS):
        subject_row = []
        subject_letter = string.ascii_lowercase[i]
        for j in range(SECOND_TABLE_NUM_COLS):
            if subject_letter == "g" and j == 0:
                subject_row.append("f7")
            else:
                subject_row.append(f"{subject_letter}{j + 1}")
        SECOND_TABLE_DATA_INPUTS.append(subject_row)
    SECOND_TABLE: pd.DataFrame = pd.DataFrame(
        data=SECOND_TABLE_DATA_INPUTS,
        columns=SECOND_TABLE_HEADERS,
        index=SECOND_TABLE_SUBJECTS,
    )
    FLAT_FIRST_TABLE: list[Any] = [
        item
        for sublist in FIRST_TABLE.reset_index().values  # type: ignore
        for item in sublist
    ]
    FLAT_SECOND_TABLE: list[Any] = [
        item
        for sublist in SECOND_TABLE.reset_index().values  # type: ignore
        for item in sublist
    ]
    METADATA_KEYS: list[str] = list(FORM_METADATA.keys())
    INPUTS: list[str] = (
        METADATA_KEYS
        + FIRST_TABLE_HEADERS
        + FLAT_FIRST_TABLE
        + SECOND_TABLE_HEADERS
        + FLAT_SECOND_TABLE
        + ["notes"]
    )

    def _reconstruct_table(
        self, form_values: list[Any], table_type: Literal["First", "Second"]
    ) -> list[Any]:
        if table_type == "First":
            table_headers: list[str] = self.FIRST_TABLE_HEADERS
            flat_table: list[Any] = self.FLAT_FIRST_TABLE
            num_cols: int = self.FIRST_TABLE_NUM_COLS + 1
        else:
            table_headers = self.SECOND_TABLE_HEADERS
            flat_table = self.FLAT_SECOND_TABLE
            num_cols = self.SECOND_TABLE_NUM_COLS + 1
        table_header_values: list[str] = form_values[: len(table_headers)]
        del form_values[: len(table_headers)]
        table_values: list[list[Any]] = form_values[: len(flat_table)]
        del form_values[: len(flat_table)]
        # chunk size is the number of metric columns plus the mouse column
        chunk_size: int = num_cols
        table_lists: list[list[Any]] = [
            table_values[i : i + chunk_size]
            for i in range(
                0,
                len(table_values),
                chunk_size,
            )
        ]
        table_columns: list[str] = ["Mouse"] + table_header_values
        table: pd.DataFrame = pd.DataFrame(
            data=table_lists, columns=table_columns
        )
        table.set_index("Mouse")  # type: ignore
        if table_type == "First":
            self.first_table = table
        else:
            self.second_table = table
        return form_values

    def __init__(self, forms: list[list[dict[str, Any]]]) -> None:
        for form_pairs in forms:
            # ensure that the form pairs are in the correct order
            form_inputs: list[str] = [pair["name"] for pair in form_pairs]
            form_values: list[Any] = [pair["value"] for pair in form_pairs]
            if form_inputs != self.INPUTS:
                raise ValueError("Form inputs do not match expected inputs!")
            # parse metadata
            metadata: dict[str, Any] = dict(
                zip(
                    self.FORM_METADATA.values(),
                    form_values[: len(self.FORM_METADATA)],
                )
            )
            del form_values[: len(self.FORM_METADATA)]
            self.metadata = metadata
            form_values = self._reconstruct_table(form_values, "First")
            form_values = self._reconstruct_table(form_values, "Second")
            self.notes = form_values[0]


class BehaviorFormV6:
    FORM_ID: Final[int] = 20058
    FORM_VERSION: Final[int] = 6
    FORM_METADATA: Final[dict[str, str]] = {
        "date_date": "Date",
        "start": "Start Time",
        "personnel": "Personnel Running Task",
        "room": "Behavior Room",
        "experiment": "Experiment",
        "subjects": "Subjects",
        "manipulation": "Manipulation",
        "video_file_path": "Video File Path",
        "protocol": "AnyMaze Protocol",
        "cue": "Cue Information",
        "reward": "Reward Information",
    }
    FIRST_TABLE_NUM_COLS: Final[int] = 6
    FIRST_TABLE_NUM_SUBJECTS: Final[int] = 12
    FIRST_TABLE_DATA_INPUTS: Final[list[list[str]]] = []
    # for some unfathomable reason, the -a suffix is dropped
    # at i2 of table 1 in v6 of the form and g1 is actually f7
    a_toggle: bool = True
    for i in range(FIRST_TABLE_NUM_SUBJECTS):
        subject_row: list[str] = []
        subject_letter: str = string.ascii_lowercase[i]
        for j in range(FIRST_TABLE_NUM_COLS):
            if a_toggle:
                subject_row.append(f"{subject_letter}{j + 1}-a")
            else:
                subject_row.append(f"{subject_letter}{j + 1}")
            if i == 8 and j == 0:
                a_toggle = False
        FIRST_TABLE_DATA_INPUTS.append(subject_row)
    FIRST_TABLE_HEADERS: Final[list[str]] = [
        "p65-a",
        "p1-a",
        "p2-a",
        "p3-a",
        "p4-a",
        "p5-a",
    ]
    # The order of the subjects is scrambled at the end in the form
    # the list is in the proper order to match to form
    FIRST_TABLE_SUBJECTS: Final[list[str]] = [
        "m1-a",
        "m2-a",
        "m3-a",
        "m4-a",
        "m5-a",
        "m6-a",
        "m7-a",
        "m8-a",
        "m9",
        "m12",
        "m10",
        "m11",
    ]
    FIRST_TABLE: pd.DataFrame = pd.DataFrame(
        data=FIRST_TABLE_DATA_INPUTS,
        columns=FIRST_TABLE_HEADERS,
        index=FIRST_TABLE_SUBJECTS,
    )
    SECOND_TABLE_NUM_COLS: Final[int] = 6
    SECOND_TABLE_NUM_SUBJECTS: Final[int] = 8
    SECOND_TABLE_HEADERS: Final[list[str]] = [
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
        "p6",
    ]
    SECOND_TABLE_SUBJECTS: Final[list[str]] = [
        "m1",
        "m2",
        "m3",
        "m4",
        "m5",
        "m6",
        "m7",
        "m8",
    ]
    SECOND_TABLE_DATA_INPUTS: Final[list[list[str]]] = []
    for i in range(SECOND_TABLE_NUM_SUBJECTS):
        subject_row = []
        subject_letter = string.ascii_lowercase[i]
        for j in range(SECOND_TABLE_NUM_COLS):
            if subject_letter == "g" and j == 0:
                subject_row.append("f7")
            else:
                subject_row.append(f"{subject_letter}{j + 1}")
        SECOND_TABLE_DATA_INPUTS.append(subject_row)
    SECOND_TABLE: pd.DataFrame = pd.DataFrame(
        data=SECOND_TABLE_DATA_INPUTS,
        columns=SECOND_TABLE_HEADERS,
        index=SECOND_TABLE_SUBJECTS,
    )
    FLAT_FIRST_TABLE: list[Any] = [
        item
        for sublist in FIRST_TABLE.reset_index().values  # type: ignore
        for item in sublist
    ]
    FLAT_SECOND_TABLE: list[Any] = [
        item
        for sublist in SECOND_TABLE.reset_index().values  # type: ignore
        for item in sublist
    ]
    METADATA_KEYS: list[str] = list(FORM_METADATA.keys())
    INPUTS: list[str] = (
        METADATA_KEYS
        + FIRST_TABLE_HEADERS
        + FLAT_FIRST_TABLE
        + SECOND_TABLE_HEADERS
        + FLAT_SECOND_TABLE
        + ["notes"]
    )

    def _reconstruct_table(
        self, form_values: list[Any], table_type: Literal["First", "Second"]
    ) -> list[Any]:
        if table_type == "First":
            table_headers: list[str] = self.FIRST_TABLE_HEADERS
            flat_table: list[Any] = self.FLAT_FIRST_TABLE
            num_cols: int = self.FIRST_TABLE_NUM_COLS + 1
        else:
            table_headers = self.SECOND_TABLE_HEADERS
            flat_table = self.FLAT_SECOND_TABLE
            num_cols = self.SECOND_TABLE_NUM_COLS + 1
        table_header_values: list[str] = form_values[: len(table_headers)]
        del form_values[: len(table_headers)]
        table_values: list[list[Any]] = form_values[: len(flat_table)]
        del form_values[: len(flat_table)]
        # chunk size is the number of metric columns plus the mouse column
        chunk_size: int = num_cols
        table_lists: list[list[Any]] = [
            table_values[i : i + chunk_size]
            for i in range(
                0,
                len(table_values),
                chunk_size,
            )
        ]
        table_columns: list[str] = ["Mouse"] + table_header_values
        table: pd.DataFrame = pd.DataFrame(
            data=table_lists, columns=table_columns
        )
        table.set_index("Mouse")  # type: ignore
        if table_type == "First":
            self.first_table = table
        else:
            self.second_table = table
        return form_values

    def __init__(self, forms: list[list[dict[str, Any]]]) -> None:
        for form_pairs in forms:
            # ensure that the form pairs are in the correct order
            form_inputs: list[str] = [pair["name"] for pair in form_pairs]
            form_values: list[Any] = [pair["value"] for pair in form_pairs]
            if form_inputs != self.INPUTS:
                raise ValueError("Form inputs do not match expected inputs!")
            # parse metadata
            metadata: dict[str, Any] = dict(
                zip(
                    self.FORM_METADATA.values(),
                    form_values[: len(self.FORM_METADATA)],
                )
            )
            del form_values[: len(self.FORM_METADATA)]
            self.metadata = metadata
            form_values = self._reconstruct_table(form_values, "First")
            form_values = self._reconstruct_table(form_values, "Second")
            self.notes = form_values[0]


def parse_behavior_widget(
    response: Response | Path,
) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
    if isinstance(response, Path):
        tree: ET.ElementTree = ET.parse(response)
    else:
        tree = ET.parse(BytesIO(response.content))
    root: ET.Element = tree.getroot()
    # make sure the get entries for page method yielded entries
    total_returned: ET.Element | None = root.find("results/total-returned")
    if isinstance(total_returned, ET.Element):
        total_returned_text: str | None = total_returned.text
        if total_returned_text == "0":
            raise EmptyResults(
                "No entries found in get_entries_for_page response!"
            )
    entries: ET.Element | None = root.find("entries")
    if entries is None:
        raise ValueError("No entries found in response!")
    # entry-data tag is also in response element, so need to
    # limit search to children of entries
    entry_data: list[ET.Element] = entries.findall(".//entry-data")
    forms: list[list[dict[str, Any]]] = []
    forms_metadata: list[dict[str, Any]] = []
    for entry in entry_data:
        entry_text: str | None = entry.text
        if isinstance(entry_text, str):
            try:
                entry_dict: dict[str, Any] = json.loads(entry_text)
            except JSONDecodeError:
                entry_dict = json.loads(entry_text.replace("\n", ""))
            if entry_dict["form_id"] == 20058:
                form_metadata: dict[str, Any] = {
                    "form_id": entry_dict["form_id"],
                    "form_version": entry_dict["form_version"],
                }
                form_data: list[dict[str, Any]] = json.loads(
                    entry_dict["form_data"]
                )
                forms_metadata.append(form_metadata)
                forms.append(form_data)
            else:
                raise ValueError("Form ID not 20058, not behavior form!")
    return forms_metadata, forms


def recontruct_behavior_form(
    forms_metadata: list[dict[str, Any]], forms: list[list[dict[str, Any]]]
) -> Any:
    if len(forms_metadata) > 1:
        raise ValueError("More than one form found in response!")
    if forms_metadata[0]["form_version"] == 4:
        behavior_version: BehaviorFormV4 | BehaviorFormV6 = BehaviorFormV4(
            forms
        )
    elif forms_metadata[0]["form_version"] == 6:
        behavior_version = BehaviorFormV6(forms)
    else:
        raise ValueError("Form version not known!")
    return behavior_version
