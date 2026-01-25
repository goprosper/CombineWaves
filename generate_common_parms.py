"""
Generate CommonParms.csv from CommonQuestions.csv.

This module reads the CommonQuestions.csv file (produced by the intersection step)
and generates a CommonParms.csv file that contains the parms-format representation
of the common questions across all survey waves.
"""

import csv
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CommonQuestion:
    """Parsed row from CommonQuestions.csv."""
    common_question_id: int
    master_question_text: str
    common_answer_ids: List[int]
    parms_question_type: str


@dataclass
class ParmsRow:
    """Output row for CommonParms.csv."""
    question_number: int
    total_answers: int
    question_text: str
    answer_text_list: str
    question_type: str
    common_question_id: int


def load_common_questions_for_parms(filepath: str) -> List[CommonQuestion]:
    """
    Load and parse CommonQuestions.csv into a list of CommonQuestion objects.

    Args:
        filepath: Path to the CommonQuestions.csv file.

    Returns:
        List of CommonQuestion objects parsed from the file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CommonQuestions.csv not found: {filepath}")

    result: List[CommonQuestion] = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header row
        next(reader)
        for row in reader:
            common_question_id = int(row[0])
            master_question_text = row[1]
            # Parse common_answer_ids: ^-delimited list of integers, empty string = empty list
            if row[2]:
                common_answer_ids = [int(x) for x in row[2].split('^')]
            else:
                common_answer_ids = []
            parms_question_type = row[3]
            result.append(CommonQuestion(
                common_question_id=common_question_id,
                master_question_text=master_question_text,
                common_answer_ids=common_answer_ids,
                parms_question_type=parms_question_type
            ))
    return result


def transform_answer_ids_to_text(common_answer_ids: List[int], answer_text_map: str) -> str:
    """
    Transform a list of answer IDs into a ^-delimited string of answer texts.

    Args:
        common_answer_ids: List of answer IDs to transform.
        answer_text_map: The answer text mapping from the database.

    Returns:
        A ^-delimited string of answer texts corresponding to the answer IDs.
    """
    # Handle edge cases
    if not common_answer_ids:
        return ""
    if not answer_text_map:
        return ""

    # Parse the answer_text_map into a list
    answer_texts = answer_text_map.split("^")

    # Look up each answer_id and collect the corresponding texts
    result_texts = []
    for answer_id in common_answer_ids:
        if 0 <= answer_id < len(answer_texts):
            result_texts.append(answer_texts[answer_id])
        # Out-of-bounds indices are skipped

    return "^".join(result_texts)


def generate_common_parms(
    common_questions_path: str,
    study_name: str,
    db,
    output_path: str = "CommonParms.csv"
) -> str:
    """
    Generate CommonParms.csv from CommonQuestions.csv.

    Args:
        common_questions_path: Path to the CommonQuestions.csv input file.
        study_name: Name of the study for database queries.
        db: Database connection object.
        output_path: Path for the output CommonParms.csv file.

    Returns:
        Path to the generated CommonParms.csv file.
    """
    # Step 1: Load common questions
    common_questions = load_common_questions_for_parms(common_questions_path)

    # Build parms rows
    parms_rows: List[ParmsRow] = []
    for question_number, question in enumerate(common_questions, start=1):
        # Step 2a: Query database for question master record
        record = db.get_question_master(study_name, question.common_question_id)

        if record is not None:
            # Step 2b: Record found
            # Use alternate_text, fallback to master_question_text if empty
            if record.alternate_text:
                question_text = record.alternate_text
            else:
                question_text = question.master_question_text
            # Transform answer IDs to text
            answer_text_list = transform_answer_ids_to_text(
                question.common_answer_ids, record.answer_text
            )
        else:
            # Step 2c: Record not found - use fallback values
            question_text = question.master_question_text
            answer_text_list = ""

        # Step 2d: Build ParmsRow
        parms_row = ParmsRow(
            question_number=question_number,
            total_answers=len(question.common_answer_ids),
            question_text=question_text,
            answer_text_list=answer_text_list,
            question_type=question.parms_question_type,
            common_question_id=question.common_question_id
        )
        parms_rows.append(parms_row)

    # Step 3: Write CSV output (no header row)
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in parms_rows:
            writer.writerow([
                row.question_number,
                row.total_answers,
                row.question_text,
                "",  # empty column 4
                row.answer_text_list,
                row.question_type,
                row.common_question_id  # column 7
            ])

        # Step 3b: Write study_date metadata row
        study_date_question_number = len(parms_rows) + 1
        writer.writerow([
            study_date_question_number,
            0,  # total_answers (F type has no answer list)
            "Study Date",
            "",  # empty column 4
            "",  # empty answer_text_list
            "F",  # question_type
            ""  # empty common_question_id for Study Date row
        ])

    # Step 4: Return output path
    return output_path
