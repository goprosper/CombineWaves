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
