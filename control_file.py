"""Control file parsing for CombineWaves."""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class ControlEntry:
    """Represents a single line from the control file."""
    study_name: str
    study_date: str
    parms_file_name: str
    pip_file_name: str
    parmedit_file_name: str


def read_control_file(path: str) -> Iterator[ControlEntry]:
    """
    Read and parse the control file.

    Args:
        path: Path to the control file

    Yields:
        ControlEntry for each valid line

    Raises:
        FileNotFoundError: If control file doesn't exist
        ValueError: If a line has invalid format
    """
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            parts = line.split(',')
            if len(parts) != 5:
                raise ValueError(
                    f"[{path}] Line {line_num}: Expected 5 fields, got {len(parts)}: {line}"
                )

            yield ControlEntry(
                study_name=parts[0].strip(),
                study_date=parts[1].strip(),
                parms_file_name=parts[2].strip(),
                pip_file_name=parts[3].strip(),
                parmedit_file_name=parts[4].strip()
            )
