"""Parmedit file loading and mapping for CombineWaves."""

import csv
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParmeditMapper:
    """Maps parms_question_number to question_number.

    The parmedit file provides a mapping where:
    - Column 1 contains the parms_question_number
    - The row number (1-based) represents the question_number
    """
    _mapping: dict
    file_path: str

    def get_question_number(self, parms_question_number: int) -> Optional[int]:
        """
        Look up question_number for a given parms_question_number.

        Args:
            parms_question_number: The question number from parms file column 1

        Returns:
            The question_number (row position in parmedit file), or None if not found
        """
        return self._mapping.get(parms_question_number)


def load_parmedit(path: str) -> ParmeditMapper:
    """
    Load parmedit file and create mapper.

    Reads the parmedit CSV file and builds a mapping from parms_question_number
    (column 1) to question_number (row number, 1-based).

    Args:
        path: Path to the parmedit CSV file

    Returns:
        ParmeditMapper instance for lookups

    Raises:
        FileNotFoundError: If parmedit file doesn't exist
        ValueError: If parmedit file format is invalid
    """
    mapping = {}

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for row_number, row in enumerate(reader, start=1):
            if not row:
                # Skip empty rows
                continue

            try:
                parms_question_number = int(row[0])
                mapping[parms_question_number] = row_number
            except ValueError:
                raise ValueError(
                    f"Parmedit file {path}, row {row_number}: "
                    f"Invalid parms_question_number: {row[0]}"
                )

    return ParmeditMapper(_mapping=mapping, file_path=path)


def load_parmedit_appended(path: str) -> ParmeditMapper:
    """
    Load parmedit_APPENDED file and create mapper.

    Reads the parmedit_APPENDED CSV file where the question_number from
    the UPLOAD file is appended. Supports two formats:
    - New format: question_number is second-to-last column, question_id is last
    - Old format: question_number is the last column (backward compatibility)

    Args:
        path: Path to the parmedit_APPENDED CSV file

    Returns:
        ParmeditMapper instance for lookups

    Raises:
        FileNotFoundError: If parmedit_APPENDED file doesn't exist
        ValueError: If parmedit_APPENDED file format is invalid
    """
    import sys
    mapping = {}

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for row_number, row in enumerate(reader, start=1):
            if not row:
                # Skip empty rows
                continue

            try:
                parms_question_number = int(row[0])

                # Try new format first: question_number is second-to-last column
                # (question_id is last column)
                question_number_str = ''
                if len(row) >= 2:
                    # Try second-to-last column first (new format)
                    candidate = row[-2].strip() if row[-2] else ''
                    if candidate and candidate.isdigit():
                        question_number_str = candidate
                    else:
                        # Fall back to last column (old format)
                        question_number_str = row[-1].strip() if row[-1] else ''

                if question_number_str:
                    question_number = int(question_number_str)
                    mapping[parms_question_number] = question_number
                else:
                    # No match was found for this row during UPLOAD matching
                    print(
                        f"Warning: No question_number for parms_qn "
                        f"{parms_question_number} in {path}",
                        file=sys.stderr
                    )

            except ValueError as e:
                raise ValueError(
                    f"Parmedit_APPENDED file {path}, row {row_number}: "
                    f"Invalid value: {e}"
                )

    return ParmeditMapper(_mapping=mapping, file_path=path)
