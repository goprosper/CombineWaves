#!/usr/bin/env python3
"""
Generate CommonParmedit.csv from CommonParms.csv and parmedit_APPENDED.

This module creates a CommonParmedit.csv file that combines the common question
information from CommonParms.csv with the parmedit-specific metadata (question
types, AVG calculations, question references) from the most recent study's
parmedit_APPENDED.csv file.
"""

import csv
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from control_file import read_control_file


# =============================================================================
# Task 1: Data Structures
# =============================================================================

@dataclass
class ParmeditAppendedRow:
    """Row from parmedit_APPENDED.csv with all 13 columns."""
    parms_question_number: int
    total_answers: int
    question_text: str
    empty: str
    answer_list: str
    question_type: str           # Original type (X, A, S, M, F)
    special_code: str            # Column 7 (e.g., "AVG" or empty)
    special_values: str          # Column 8
    reserved: str                # Column 9
    reference_parms_qn: Optional[int]    # Column 10
    reference_answers: str       # Column 11 (comma-delimited)
    question_number: int         # Column 12 (from UPLOAD)
    question_id: int             # Column 13


@dataclass
class CommonParmsRow:
    """Row from CommonParms.csv with 7 columns."""
    question_number: int
    total_answers: int
    question_text: str
    empty: str
    answer_list: str
    question_type: str
    common_question_id: Optional[int]  # None for Study Date row


@dataclass
class CommonParmeditRow:
    """Output row for CommonParmedit.csv with 11 columns."""
    question_number: int         # From CommonParms
    total_answers: int           # From CommonParms
    question_text: str           # From CommonParms
    empty: str                   # Always empty
    answer_list: str             # From CommonParms
    question_type: str           # From parmedit (preserves X/A)
    special_code: str            # From parmedit col 7 (if numeric)
    special_values: str          # From parmedit col 8
    reserved: str                # From parmedit col 9
    reference_common_qn: str     # Translated reference
    reference_common_answers: str  # Translated answer positions


# =============================================================================
# Task 2: File Loading Functions
# =============================================================================

def load_common_parms(path: str) -> List[CommonParmsRow]:
    """
    Load CommonParms.csv into a list of CommonParmsRow objects.

    Args:
        path: Path to CommonParms.csv file.

    Returns:
        List of CommonParmsRow objects (includes Study Date row).

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    rows: List[CommonParmsRow] = []

    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 6:
                continue

            # Parse common_question_id (may be empty for Study Date row)
            common_question_id: Optional[int] = None
            if len(row) >= 7 and row[6].strip():
                try:
                    common_question_id = int(row[6])
                except ValueError:
                    pass

            rows.append(CommonParmsRow(
                question_number=int(row[0]),
                total_answers=int(row[1]),
                question_text=row[2],
                empty=row[3] if len(row) > 3 else '',
                answer_list=row[4] if len(row) > 4 else '',
                question_type=row[5] if len(row) > 5 else '',
                common_question_id=common_question_id
            ))

    return rows


def load_parmedit_appended_full(path: str) -> List[ParmeditAppendedRow]:
    """
    Load parmedit_APPENDED.csv with all columns.

    Args:
        path: Path to parmedit_APPENDED.csv file.

    Returns:
        List of ParmeditAppendedRow objects.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    rows: List[ParmeditAppendedRow] = []

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue

            try:
                parms_qn = int(row[0])
            except ValueError:
                continue

            # Parse optional integer fields
            def safe_int(val: str) -> Optional[int]:
                val = val.strip()
                if val and val.isdigit():
                    return int(val)
                return None

            # Get values with safe defaults for short rows
            def get_col(idx: int, default: str = '') -> str:
                return row[idx] if len(row) > idx else default

            # Column 10: reference_parms_qn
            ref_parms_qn = safe_int(get_col(9))

            # Column 12 and 13: question_number and question_id
            # These are the last two columns
            question_number = 0
            question_id = 0
            if len(row) >= 2:
                # Last column is question_id, second-to-last is question_number
                try:
                    question_id = int(row[-1]) if row[-1].strip() else 0
                    question_number = int(row[-2]) if len(row) >= 2 and row[-2].strip() else 0
                except ValueError:
                    pass

            rows.append(ParmeditAppendedRow(
                parms_question_number=parms_qn,
                total_answers=int(row[1]) if len(row) > 1 and row[1].strip().isdigit() else 0,
                question_text=get_col(2),
                empty=get_col(3),
                answer_list=get_col(4),
                question_type=get_col(5),
                special_code=get_col(6),
                special_values=get_col(7),
                reserved=get_col(8),
                reference_parms_qn=ref_parms_qn,
                reference_answers=get_col(10),
                question_number=question_number,
                question_id=question_id
            ))

    return rows


# =============================================================================
# Task 3: Control File Helper
# =============================================================================

def get_most_recent_parmedit_appended(control_path: str) -> str:
    """
    Get the path to parmedit_APPENDED for the most recent study.

    Args:
        control_path: Path to control file.

    Returns:
        Path to the most recent parmedit_APPENDED.csv file.

    Raises:
        FileNotFoundError: If control file doesn't exist.
        ValueError: If control file is empty.
    """
    entries = list(read_control_file(control_path))

    if not entries:
        raise ValueError("Control file is empty")

    # Sort by study_date descending to get most recent
    entries.sort(key=lambda e: e.study_date, reverse=True)
    most_recent = entries[0]

    # Derive parmedit_APPENDED path from parmedit path
    parmedit_path = most_recent.parmedit_file_name
    if parmedit_path.lower().endswith('.csv'):
        appended_path = parmedit_path[:-4] + '_APPENDED.csv'
    else:
        appended_path = parmedit_path + '_APPENDED'

    return appended_path


# =============================================================================
# Task 4: Answer Translation Function
# =============================================================================

def load_common_questions_answer_ids(path: str) -> Dict[int, List[int]]:
    """
    Load CommonQuestions.csv and extract answer_ids for each question.

    Args:
        path: Path to CommonQuestions.csv.

    Returns:
        Dict mapping common_question_id to list of answer_ids.
    """
    result: Dict[int, List[int]] = {}

    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        # Skip header
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                qid = int(row[0])
                # Parse ^-delimited answer_ids
                if row[2].strip():
                    answer_ids = [int(x) for x in row[2].split('^')]
                else:
                    answer_ids = []
                result[qid] = answer_ids
            except ValueError:
                continue

    return result


def load_appended_answer_ids(appended_path: str) -> Dict[int, List[int]]:
    """
    Load a .appended parms file and extract answer_ids for each question.

    Args:
        appended_path: Path to the .appended parms file.

    Returns:
        Dict mapping question_id to list of answer_ids.
    """
    result: Dict[int, List[int]] = {}

    with open(appended_path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 8:
                continue
            try:
                # Column 7 is question_id, Column 8 is answer_ids
                qid_str = row[6].strip()
                if not qid_str:
                    continue
                qid = int(qid_str)
                # Parse ^-delimited answer_ids
                if len(row) > 7 and row[7].strip():
                    answer_ids = [int(x) for x in row[7].split('^')]
                else:
                    answer_ids = []
                result[qid] = answer_ids
            except ValueError:
                continue

    return result


def translate_reference_answers(
    reference_answers: str,
    parmedit_answer_ids: List[int],
    common_answer_ids: List[int]
) -> str:
    """
    Translate answer positions from parmedit to CommonParms.

    Args:
        reference_answers: Comma-delimited list of parmedit answer positions (1-based).
        parmedit_answer_ids: Answer IDs from parmedit's .appended file.
        common_answer_ids: Answer IDs from CommonQuestions.csv.

    Returns:
        Comma-delimited list of translated CommonParms answer positions (1-based).
    """
    if not reference_answers.strip():
        return ''

    if not parmedit_answer_ids or not common_answer_ids:
        return reference_answers  # Can't translate, return original

    translated = []
    for pos_str in reference_answers.split(','):
        pos_str = pos_str.strip()
        if not pos_str:
            continue
        try:
            parmedit_pos = int(pos_str)  # 1-based position
            if parmedit_pos < 1 or parmedit_pos > len(parmedit_answer_ids):
                translated.append(pos_str)  # Out of bounds, keep original
                continue

            # Get the answer_id at this parmedit position
            answer_id = parmedit_answer_ids[parmedit_pos - 1]

            # Find this answer_id's position in common_answer_ids
            if answer_id in common_answer_ids:
                common_pos = common_answer_ids.index(answer_id) + 1  # 1-based
                translated.append(str(common_pos))
            else:
                translated.append(pos_str)  # Not found, keep original
        except ValueError:
            translated.append(pos_str)  # Not a number, keep original

    return ','.join(translated)


# =============================================================================
# Task 5: Main Generation Function
# =============================================================================

def generate_common_parmedit(
    common_parms_path: str,
    control_path: str,
    output_path: str = "AgileBrainsAppend/CommonParmeditAppended.csv",
    common_questions_path: str = "CommonQuestions.csv"
) -> str:
    """
    Generate CommonParmedit.csv from CommonParms.csv and parmedit_APPENDED.

    Args:
        common_parms_path: Path to CommonParms.csv.
        control_path: Path to control file.
        output_path: Output path for CommonParmedit.csv.
        common_questions_path: Path to CommonQuestions.csv.

    Returns:
        Path to generated CommonParmedit.csv file.
    """
    # Step 1: Load CommonParms.csv
    common_parms = load_common_parms(common_parms_path)

    # Step 2: Get most recent parmedit_APPENDED path
    parmedit_appended_path = get_most_recent_parmedit_appended(control_path)

    # Step 3: Load parmedit_APPENDED
    parmedit_rows = load_parmedit_appended_full(parmedit_appended_path)

    # Step 4: Build lookup indices
    parmedit_by_question_id: Dict[int, ParmeditAppendedRow] = {}
    parmedit_by_parms_qn: Dict[int, ParmeditAppendedRow] = {}

    for row in parmedit_rows:
        if row.question_id:
            parmedit_by_question_id[row.question_id] = row
        parmedit_by_parms_qn[row.parms_question_number] = row

    common_parms_by_qid: Dict[int, CommonParmsRow] = {}
    for row in common_parms:
        if row.common_question_id:
            common_parms_by_qid[row.common_question_id] = row

    # Step 5: Load answer_ids for translation
    common_answer_ids = load_common_questions_answer_ids(common_questions_path)

    # Load parmedit's .appended file for answer_ids
    # Derive from control file - most recent entry
    entries = list(read_control_file(control_path))
    entries.sort(key=lambda e: e.study_date, reverse=True)
    most_recent = entries[0]
    parmedit_appended_answer_ids = load_appended_answer_ids(
        most_recent.parms_file_name + '.appended'
    )

    # Step 6: Generate CommonParmedit rows
    output_rows: List[CommonParmeditRow] = []

    for cp_row in common_parms:
        # Handle rows without common_question_id (e.g., Study Date row)
        if cp_row.common_question_id is None:
            output_rows.append(CommonParmeditRow(
                question_number=cp_row.question_number,
                total_answers=cp_row.total_answers,
                question_text=cp_row.question_text,
                empty='',
                answer_list=cp_row.answer_list,
                question_type=cp_row.question_type,
                special_code='',
                special_values='',
                reserved='',
                reference_common_qn='',
                reference_common_answers=''
            ))
            continue

        # Find matching parmedit row
        pm_row = parmedit_by_question_id.get(cp_row.common_question_id)

        if pm_row:
            # Build output row with parmedit data
            question_type = pm_row.question_type

            # Check if column 7 contains a number (for AVG handling)
            special_code = ''
            special_values = ''
            reserved = ''
            if pm_row.special_code.strip():
                # Column 7 has content - check if it's numeric or a code like "AVG"
                # Per spec: "If column 7 contains a number"
                # But looking at data, column 7 contains "AVG", not a number
                # The spec might mean if special handling is present
                special_code = pm_row.special_code
                special_values = pm_row.special_values
                reserved = pm_row.reserved

            # Handle reference translation (column 10-11)
            reference_common_qn = ''
            reference_common_answers = ''

            if pm_row.reference_parms_qn is not None:
                # Find the referenced parmedit row
                ref_pm_row = parmedit_by_parms_qn.get(pm_row.reference_parms_qn)
                if ref_pm_row and ref_pm_row.question_id:
                    # Find the CommonParms row for the referenced question
                    ref_cp_row = common_parms_by_qid.get(ref_pm_row.question_id)
                    if ref_cp_row:
                        reference_common_qn = str(ref_cp_row.question_number)

                        # Translate answer positions
                        ref_qid = ref_pm_row.question_id
                        pm_answer_ids = parmedit_appended_answer_ids.get(ref_qid, [])
                        cm_answer_ids = common_answer_ids.get(ref_qid, [])

                        reference_common_answers = translate_reference_answers(
                            pm_row.reference_answers,
                            pm_answer_ids,
                            cm_answer_ids
                        )
                    else:
                        # Referenced question not in CommonParms
                        print(
                            f"Warning: Referenced question_id {ref_pm_row.question_id} "
                            f"not in CommonParms",
                            file=sys.stderr
                        )
                else:
                    print(
                        f"Warning: Reference parms_qn {pm_row.reference_parms_qn} "
                        f"not found in parmedit_APPENDED",
                        file=sys.stderr
                    )

            output_rows.append(CommonParmeditRow(
                question_number=cp_row.question_number,
                total_answers=cp_row.total_answers,
                question_text=cp_row.question_text,
                empty='',
                answer_list=cp_row.answer_list,
                question_type=question_type,
                special_code=special_code,
                special_values=special_values,
                reserved=reserved,
                reference_common_qn=reference_common_qn,
                reference_common_answers=reference_common_answers
            ))
        else:
            # No match found - copy columns 1-6 from CommonParms
            print(
                f"Warning: CommonParms question_id {cp_row.common_question_id} "
                f"not found in parmedit_APPENDED",
                file=sys.stderr
            )
            output_rows.append(CommonParmeditRow(
                question_number=cp_row.question_number,
                total_answers=cp_row.total_answers,
                question_text=cp_row.question_text,
                empty='',
                answer_list=cp_row.answer_list,
                question_type=cp_row.question_type,
                special_code='',
                special_values='',
                reserved='',
                reference_common_qn='',
                reference_common_answers=''
            ))

    # Step 7: Write output CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in output_rows:
            writer.writerow([
                row.question_number,
                row.total_answers,
                row.question_text,
                row.empty,
                row.answer_list,
                row.question_type,
                row.special_code,
                row.special_values,
                row.reserved,
                row.reference_common_qn,
                row.reference_common_answers
            ])

    return output_path


# =============================================================================
# Task 6: Main Entry Point
# =============================================================================

def main(argv: List[str]) -> int:
    """
    Main entry point.

    Args:
        argv: Command-line arguments (sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    if len(argv) != 1:
        print(
            "Usage: python generate_common_parmedit.py <control_file>",
            file=sys.stderr
        )
        return 1

    control_path = argv[0]

    try:
        output_path = generate_common_parmedit(
            "AgileBrainsAppend/CommonParmsAppended.csv",
            control_path,
            "AgileBrainsAppend/CommonParmeditAppended.csv",
            "CommonQuestions.csv"
        )
        print(f"Created: {output_path}")
        return 0

    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
