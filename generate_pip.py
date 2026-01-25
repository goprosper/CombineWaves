"""Generate combined pip file for CombineWaves Step 3."""

import csv
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from control_file import ControlEntry


@dataclass
class CommonQuestion:
    """Question from CommonQuestions.csv."""
    question_id: int
    master_question_text: str
    common_answer_ids: List[int]


@dataclass
class AppendedRow:
    """Relevant data from an appended file row."""
    parms_question_number: int
    question_type: str  # F, S, or M
    answer_ids: List[int]


def load_common_questions(path: str) -> List[CommonQuestion]:
    """
    Load CommonQuestions.csv.

    Args:
        path: Path to CommonQuestions.csv

    Returns:
        List of CommonQuestion objects, ordered as in file

    Raises:
        FileNotFoundError: If file doesn't exist

    Note:
        Handles both 3-column (legacy) and 5-column (with ParmsQuestionType,
        ParmeditQuestionType) formats. Extra columns are ignored.
    """
    questions = []

    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 3:
                continue

            # Only use first 3 columns (ignore ParmsQuestionType, ParmeditQuestionType)
            question_id = int(row[0])
            master_text = row[1]
            common_aids_str = row[2]

            common_aids = []
            if common_aids_str:
                for aid in common_aids_str.split('^'):
                    aid = aid.strip()
                    if aid and aid.lstrip('-').isdigit():
                        common_aids.append(int(aid))

            questions.append(CommonQuestion(
                question_id=question_id,
                master_question_text=master_text,
                common_answer_ids=common_aids
            ))

    return questions


def build_appended_index(path: str) -> Dict[int, AppendedRow]:
    """
    Build index from appended file mapping question_id to row data.

    Args:
        path: Path to appended file

    Returns:
        Dictionary mapping question_id to AppendedRow

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    index: Dict[int, AppendedRow] = {}

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 8:
                continue

            question_id_str = row[6].strip()
            if not question_id_str:
                continue

            try:
                question_id = int(question_id_str)
            except ValueError:
                continue

            parms_qn = int(row[0]) if row[0].strip().isdigit() else 0
            question_type = row[5].strip().upper()
            answer_ids_str = row[7].strip()

            answer_ids = []
            if answer_ids_str:
                for aid in answer_ids_str.split('^'):
                    aid = aid.strip()
                    if aid and aid.lstrip('-').isdigit():
                        answer_ids.append(int(aid))

            index[question_id] = AppendedRow(
                parms_question_number=parms_qn,
                question_type=question_type,
                answer_ids=answer_ids
            )

    return index


def transform_answer_single(
    data_input: str,
    answer_ids: List[int],
    common_answer_ids: List[int]
) -> str:
    """
    Transform a single answer (type S).

    Args:
        data_input: Raw value from pip file
        answer_ids: Answer IDs from appended file
        common_answer_ids: Common answer IDs from CommonQuestions

    Returns:
        Transformed value or original if transformation not applicable
    """
    # Pass through if empty or "0"
    if not data_input or data_input == "0":
        return data_input

    # Try to parse as integer
    try:
        value = int(data_input)
    except ValueError:
        return data_input  # Non-numeric, pass through

    if value <= 0:
        return data_input

    # Get answer_id from answer_ids list (data_input is 1-based)
    idx = value - 1
    if idx < 0 or idx >= len(answer_ids):
        return data_input  # Out of bounds

    answer_id = answer_ids[idx]

    # Find position in common_answer_ids (return 1-based)
    try:
        common_idx = common_answer_ids.index(answer_id)
        return str(common_idx + 1)  # 1-based position
    except ValueError:
        return data_input  # answer_id not in common list


def transform_answer_multiple(
    data_input: str,
    answer_ids: List[int],
    common_answer_ids: List[int]
) -> str:
    """
    Transform multiple answers (type M).

    Args:
        data_input: ^-delimited values from pip file
        answer_ids: Answer IDs from appended file
        common_answer_ids: Common answer IDs from CommonQuestions

    Returns:
        Transformed ^-delimited values or original if transformation not applicable
    """
    if not data_input:
        return data_input

    # Split by ^ and validate each part
    parts = data_input.split('^')

    # Check if all non-empty parts are positive integers
    valid_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
            if value <= 0:
                return data_input  # Not a positive integer
            valid_parts.append((part, value))
        except ValueError:
            return data_input  # Not a valid integer

    if not valid_parts:
        return data_input

    # Transform each value
    transformed = []
    for original, value in valid_parts:
        idx = value - 1
        if idx < 0 or idx >= len(answer_ids):
            transformed.append(original)  # Keep original if out of bounds
            continue

        answer_id = answer_ids[idx]

        try:
            common_idx = common_answer_ids.index(answer_id)
            transformed.append(str(common_idx + 1))
        except ValueError:
            transformed.append(original)  # Keep original if not found

    return '^'.join(transformed)


def generate_common_pip(
    common_questions_path: str,
    control_entries: List[ControlEntry],
    output_path: str
) -> str:
    """
    Generate CommonData.pip from pip files.

    Args:
        common_questions_path: Path to CommonQuestions.csv
        control_entries: List of control file entries
        output_path: Path for output file

    Returns:
        Path to generated file
    """
    # Load common questions
    try:
        common_questions = load_common_questions(common_questions_path)
    except FileNotFoundError:
        print(f"Error: CommonQuestions.csv not found [{common_questions_path}]",
              file=sys.stderr)
        return output_path

    if not common_questions:
        print("Warning: No common questions found, creating empty output",
              file=sys.stderr)
        with open(output_path, 'w', encoding='utf-8') as f:
            pass
        return output_path

    total_rows = 0
    files_processed = 0

    with open(output_path, 'w', encoding='utf-8') as outfile:
        for entry in control_entries:
            appended_path = f"{entry.parms_file_name}.appended"
            pip_path = entry.pip_file_name

            # Build index from appended file
            try:
                appended_index = build_appended_index(appended_path)
            except FileNotFoundError:
                print(f"Warning: Appended file not found [{appended_path}], skipping",
                      file=sys.stderr)
                continue

            # Process pip file
            try:
                with open(pip_path, 'r', encoding='latin-1') as pip_file:
                    for line in pip_file:
                        line = line.rstrip('\r\n')
                        if not line:
                            continue

                        pip_columns = line.split('|')
                        output_values = []

                        for cq in common_questions:
                            # Find matching row in appended file
                            if cq.question_id not in appended_index:
                                output_values.append('')
                                continue

                            appended_row = appended_index[cq.question_id]
                            parms_qn = appended_row.parms_question_number

                            # Get data_input from pip (1-based column)
                            if parms_qn < 1 or parms_qn > len(pip_columns):
                                output_values.append('')
                                continue

                            data_input = pip_columns[parms_qn - 1]

                            # Transform based on question type
                            if appended_row.question_type == 'F':
                                data_output = data_input
                            elif appended_row.question_type == 'S':
                                data_output = transform_answer_single(
                                    data_input,
                                    appended_row.answer_ids,
                                    cq.common_answer_ids
                                )
                            elif appended_row.question_type == 'M':
                                data_output = transform_answer_multiple(
                                    data_input,
                                    appended_row.answer_ids,
                                    cq.common_answer_ids
                                )
                            else:
                                data_output = data_input

                            output_values.append(data_output)

                        # Append study_date as the last column
                        output_values.append(entry.study_date)

                        # Write output line
                        outfile.write('|'.join(output_values) + '\n')
                        total_rows += 1

                files_processed += 1

            except FileNotFoundError:
                print(f"Warning: Pip file not found [{pip_path}], skipping",
                      file=sys.stderr)
                continue

    print(f"Processed {total_rows} rows from {files_processed} pip files")
    return output_path
