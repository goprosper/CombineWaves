"""UPLOAD file loading and parmedit matching for CombineWaves.

This module handles matching parmedit questions to UPLOAD questions by text
similarity, and generates parmedit_APPENDED files with the correct question_number.
"""

import csv
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from report import get_collector

if TYPE_CHECKING:
    from database import DatabaseClient


@dataclass
class UploadQuestion:
    """A question from the UPLOAD file."""
    question_number: int
    question_text: str


def load_upload_file(path: str) -> List[UploadQuestion]:
    """
    Load UPLOAD file and extract questions.

    The UPLOAD file is a CSV where:
    - Row 1 is a header (skipped)
    - Row 2+: column 1 = question_number, column 4 = question_text

    Args:
        path: Path to the UPLOAD CSV file

    Returns:
        List of UploadQuestion objects (preserving order)

    Raises:
        FileNotFoundError: If UPLOAD file doesn't exist
        ValueError: If UPLOAD file format is invalid
    """
    questions = []

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        # Skip header row
        try:
            next(reader)
        except StopIteration:
            return questions  # Empty file

        for row_num, row in enumerate(reader, start=2):
            if not row or len(row) < 4:
                continue

            try:
                question_number = int(row[0])
                question_text = row[3].strip()
                questions.append(UploadQuestion(question_number, question_text))
            except ValueError:
                raise ValueError(
                    f"UPLOAD file {path}, row {row_num}: "
                    f"Invalid question_number: {row[0]}"
                )

    return questions


def text_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity ratio between two strings.

    Uses difflib.SequenceMatcher for fuzzy matching.
    Comparison is case-insensitive.

    Args:
        text1: First string
        text2: Second string

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def match_parmedit_to_upload(
    parmedit_path: str,
    upload_questions: List[UploadQuestion],
    similarity_threshold: float = 0.90,
    lookahead: int = 15
) -> Tuple[List[Tuple[int, Optional[int], List[str]]], List[int], List[int]]:
    """
    Match parmedit rows to UPLOAD questions by text similarity.

    Uses sequential one-to-one matching with lookahead. Each parmedit row
    attempts to match the current UPLOAD question, or looks ahead up to
    `lookahead` rows to find a match.

    Args:
        parmedit_path: Path to parmedit CSV file
        upload_questions: List of UploadQuestion from UPLOAD file
        similarity_threshold: Minimum similarity for a match (default 0.90)
        lookahead: Maximum rows to look ahead in UPLOAD (default 15)

    Returns:
        Tuple of:
        - List of (parmedit_row_num, upload_question_number, original_row_data)
        - List of unmatched parmedit row numbers
        - List of skipped UPLOAD question numbers
    """
    matched_rows: List[Tuple[int, Optional[int], List[str]]] = []
    unmatched_parmedit: List[int] = []
    skipped_upload: List[int] = []

    upload_idx = 0

    with open(parmedit_path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for parmedit_row_num, row in enumerate(reader, start=1):
            if not row or len(row) < 3:
                # Keep empty/short rows but mark as unmatched
                matched_rows.append((parmedit_row_num, None, row))
                continue

            parmedit_text = row[2].strip()  # Column 3 is question_text

            # Try to match with current or future UPLOAD rows
            matched = False

            for look in range(lookahead + 1):
                if upload_idx + look >= len(upload_questions):
                    break

                upload_q = upload_questions[upload_idx + look]
                sim = text_similarity(parmedit_text, upload_q.question_text)

                if sim >= similarity_threshold:
                    # Mark skipped UPLOAD rows
                    for skip in range(look):
                        skipped_upload.append(
                            upload_questions[upload_idx + skip].question_number
                        )

                    # Record match
                    matched_rows.append(
                        (parmedit_row_num, upload_q.question_number, row)
                    )
                    upload_idx += look + 1
                    matched = True
                    break

            if not matched:
                unmatched_parmedit.append(parmedit_row_num)
                matched_rows.append((parmedit_row_num, None, row))

    return matched_rows, unmatched_parmedit, skipped_upload


def create_parmedit_appended(
    parmedit_path: str,
    upload_path: str,
    output_path: Optional[str] = None,
    similarity_threshold: float = 0.90,
    lookahead: int = 15,
    study_name: Optional[str] = None,
    study_date: Optional[str] = None,
    db_client: Optional['DatabaseClient'] = None
) -> str:
    """
    Create parmedit_APPENDED file with question_number and question_id.

    Matches parmedit questions to UPLOAD questions by text similarity,
    then appends the UPLOAD question_number and database question_id as
    the last two columns.

    Args:
        parmedit_path: Path to parmedit CSV file
        upload_path: Path to UPLOAD CSV file
        output_path: Output path (default: parmedit_path with _APPENDED suffix)
        similarity_threshold: Minimum similarity for a match (default 0.90)
        lookahead: Maximum rows to look ahead (default 15)
        study_name: Study name for database queries (optional)
        study_date: Study date for database queries (optional)
        db_client: Database client for question_id lookup (optional)

    Returns:
        Path to created parmedit_APPENDED file

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If any parmedit row cannot be matched
    """
    if output_path is None:
        # Generate output path by inserting _APPENDED before .csv
        if parmedit_path.lower().endswith('.csv'):
            output_path = parmedit_path[:-4] + '_APPENDED.csv'
        else:
            output_path = parmedit_path + '_APPENDED'

    # Load UPLOAD file
    upload_questions = load_upload_file(upload_path)

    # Match parmedit to UPLOAD
    matched_rows, unmatched_parmedit, skipped_upload = match_parmedit_to_upload(
        parmedit_path, upload_questions, similarity_threshold, lookahead
    )

    report = get_collector()

    # Build lookup for question_text by question_number
    upload_text_lookup = {q.question_number: q.question_text for q in upload_questions}

    # Report skipped UPLOAD rows
    for qn in skipped_upload:
        question_text = upload_text_lookup.get(qn, '')
        report.warning(
            "UploadSkipped",
            f"UPLOAD Q{qn} skipped (no match in parmedit)",
            {
                "question_number": qn,
                "question_text": question_text,
                "upload_file": upload_path,
                "step": "Step1"
            }
        )

    # Report unmatched parmedit rows
    for row_num in unmatched_parmedit:
        report.error(
            "ParmeditUnmatched",
            f"Parmedit row {row_num} has no match in UPLOAD",
            {"row_number": row_num, "parmedit_file": parmedit_path, "step": "Step1"}
        )

    # Build question_number -> question_id mapping (if database is available)
    question_id_map: Dict[int, str] = {}
    if db_client is not None and study_name is not None and study_date is not None:
        for _, upload_qn, _ in matched_rows:
            if upload_qn is not None and upload_qn not in question_id_map:
                record = db_client.get_question_map(study_name, study_date, upload_qn)
                if record:
                    question_id_map[upload_qn] = str(record.question_id)
                else:
                    question_id_map[upload_qn] = ''  # No record found

    # Write parmedit_APPENDED file
    with open(output_path, 'w', encoding='latin-1', newline='') as f:
        writer = csv.writer(f)
        for parmedit_row_num, upload_qn, row in matched_rows:
            # Append question_number and question_id as last two columns
            qn_str = str(upload_qn) if upload_qn else ''
            qid_str = question_id_map.get(upload_qn, '') if upload_qn else ''
            row_with_ids = list(row) + [qn_str, qid_str]
            writer.writerow(row_with_ids)

    if unmatched_parmedit:
        raise ValueError(
            f"{len(unmatched_parmedit)} parmedit row(s) could not be matched "
            f"to UPLOAD: rows {unmatched_parmedit}"
        )

    return output_path
