"""Parms file processing for CombineWaves."""

import csv
import os
import sys
from typing import List

from answer_mapper import compute_answer_ids
from database import DatabaseClient
from parmedit import ParmeditMapper
from report import get_collector


def process_parms_file(
    parms_path: str,
    study_name: str,
    study_date: str,
    db_client: DatabaseClient,
    parmedit_mapper: ParmeditMapper
) -> str:
    """
    Process a parms file and create appended output.

    Reads the parms CSV file, queries the database for each question's
    question_id and answer_value_map, computes answer_ids, and writes
    the appended output file.

    Args:
        parms_path: Path to the input parms file
        study_name: Study name for database lookup
        study_date: Study date for database lookup
        db_client: Database client instance
        parmedit_mapper: Mapper for parms_question_number to question_number

    Returns:
        Path to the generated output file

    Raises:
        FileNotFoundError: If parms file doesn't exist
    """
    output_path = f"{parms_path}.appended"
    temp_path = f"{parms_path}.appended.tmp"

    # Read all rows first to avoid partial output on error
    output_rows: List[List[str]] = []

    with open(parms_path, 'r', encoding='utf-8', newline='') as infile:
        reader = csv.reader(infile)

        for row in reader:
            if len(row) < 6:
                # Malformed row - preserve as-is with empty appended columns
                output_rows.append(row + ['', ''])
                continue

            parms_question_number = int(row[0]) if row[0].isdigit() else 0
            total_answers = int(row[1]) if row[1].isdigit() else 0
            question_text = row[2].strip() if len(row) > 2 else ''

            # Look up question_number from parmedit mapper
            question_number = parmedit_mapper.get_question_number(parms_question_number)

            report = get_collector()

            if question_number is None:
                report.warning(
                    "ParmsQuestionNotInParmedit",
                    f"[{parms_path}] parms_question_number {parms_question_number} not found in parmedit file [{parmedit_mapper.file_path}]",
                    {
                        "parms_file": parms_path,
                        "parms_question_number": parms_question_number,
                        "question_text": question_text,
                        "parmedit_file": parmedit_mapper.file_path,
                        "step": "Step1"
                    }
                )
                question_id = ''
                answer_ids = ''
            else:
                # Query database for this question
                record = db_client.get_question_map(study_name, study_date, question_number)

                if record:
                    question_id = str(record.question_id)
                    answer_ids, valid_count = compute_answer_ids(record.answer_value_map, total_answers)
                    if valid_count != total_answers:
                        row[1] = str(valid_count)
                else:
                    # Question not found in database
                    report.warning(
                        "QuestionNotInDatabase",
                        f"[{parms_path}] No database record for question_number {question_number} (parms_question_number={parms_question_number}, study={study_name}, date={study_date})",
                        {
                            "parms_file": parms_path,
                            "question_number": question_number,
                            "parms_question_number": parms_question_number,
                            "question_text": question_text,
                            "study_name": study_name,
                            "study_date": study_date,
                            "step": "Step1"
                        }
                    )
                    question_id = ''
                    answer_ids = ''

            # Append question_id and answer_ids to row
            output_rows.append(row + [question_id, answer_ids])

    # Write to temporary file first, then rename (atomic write)
    with open(temp_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(output_rows)

    # Rename temp file to final output
    os.replace(temp_path, output_path)

    return output_path
