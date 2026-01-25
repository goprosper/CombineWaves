"""Intersection computation for CombineWaves Step 2."""

import csv
import sys
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

from database import DatabaseClient
from report import get_collector


# Type alias for extended appended file data
# (answer_ids, parms_type, question_text, parms_question_number)
AppendedData = Tuple[Set[int], str, str, int]


def read_appended_file(path: str) -> Dict[int, AppendedData]:
    """
    Read an appended file and extract question_id -> extended data mapping.

    Args:
        path: Path to the appended file

    Returns:
        Dictionary mapping question_id to tuple of:
        (answer_ids, parms_question_type, question_text, parms_question_number)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    result: Dict[int, AppendedData] = {}

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 8:
                continue

            question_id_str = row[6].strip()
            answer_ids_str = row[7].strip()

            # Skip rows with empty question_id
            if not question_id_str:
                continue

            try:
                question_id = int(question_id_str)
            except ValueError:
                continue

            # Extract additional columns
            parms_qn_str = row[0].strip()
            parms_qn = int(parms_qn_str) if parms_qn_str.isdigit() else 0
            question_text = row[2].strip()
            question_type = row[5].strip().upper()

            # Parse answer_ids
            answer_ids: Set[int] = set()
            if answer_ids_str:
                for aid in answer_ids_str.split('^'):
                    aid = aid.strip()
                    if aid and aid.isdigit():
                        answer_ids.add(int(aid))

            # Merge with existing entry or create new one
            if question_id in result:
                existing = result[question_id]
                merged_aids = existing[0].union(answer_ids)
                # Keep first occurrence's metadata
                result[question_id] = (merged_aids, existing[1], existing[2], existing[3])
            else:
                result[question_id] = (answer_ids, question_type, question_text, parms_qn)

    return result


def read_parmedit_appended_file(path: str) -> Dict[int, str]:
    """
    Read parmedit_APPENDED file and return parms_question_number -> question_type mapping.

    Args:
        path: Path to the parmedit_APPENDED file

    Returns:
        Dictionary mapping parms_question_number to parmedit question_type

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    result: Dict[int, str] = {}

    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 6:
                continue

            parms_qn_str = row[0].strip()
            if not parms_qn_str.isdigit():
                continue

            parms_qn = int(parms_qn_str)
            question_type = row[5].strip().upper()

            result[parms_qn] = question_type

    return result


def determine_majority_type(types: List[str]) -> Tuple[str, bool]:
    """
    Determine the majority type from a list of types.

    Args:
        types: List of type strings

    Returns:
        Tuple of (majority_type, had_disagreement)
    """
    valid = [t for t in types if t]
    if not valid:
        return ('', False)

    counter = Counter(valid)
    if len(counter) == 1:
        return (valid[0], False)

    return (counter.most_common(1)[0][0], True)


# Type alias for intersection result
# (answer_ids, parms_types, parmedit_types)
IntersectionData = Tuple[Set[int], List[str], List[str]]


def compute_intersection(
    file_data: List[Dict[int, AppendedData]],
    parmedit_data: List[Dict[int, str]]
) -> Tuple[List[int], Dict[int, IntersectionData]]:
    """
    Compute intersection of question_ids and union of answer_ids.

    Args:
        file_data: List of question_id -> AppendedData mappings (one per file)
        parmedit_data: List of parms_question_number -> parmedit_type mappings

    Returns:
        Tuple of (processing_order, intersection_data) where:
        - processing_order: List of question_ids in order from first file
        - intersection_data: Dict mapping question_id to (answer_ids, parms_types, parmedit_types)
    """
    if not file_data:
        return ([], {})

    # Get question_ids from each file
    question_id_sets = [set(fd.keys()) for fd in file_data]

    # Compute intersection of question_ids
    common_ids = question_id_sets[0].copy()
    for qid_set in question_id_sets[1:]:
        common_ids = common_ids.intersection(qid_set)

    # Preserve processing order from first file
    processing_order: List[int] = []
    result: Dict[int, IntersectionData] = {}

    for qid in file_data[0].keys():
        if qid not in common_ids:
            continue

        # Get data from first file to check filtering
        first_data = file_data[0][qid]
        parms_type = first_data[1]
        question_text = first_data[2]

        # Filter: skip "Other, please specify:" F-type questions
        if parms_type == 'F' and question_text == 'Other, please specify:':
            continue

        processing_order.append(qid)

        # Compute union of answer_ids across all files
        # For F-type questions, leave answer_ids empty
        if parms_type == 'F':
            all_answers: Set[int] = set()
        else:
            all_answers = set()
            for fd in file_data:
                all_answers.update(fd[qid][0])

        # Collect parms_types from all files
        parms_types: List[str] = []
        for fd in file_data:
            parms_types.append(fd[qid][1])

        # Collect parmedit_types from all files
        parmedit_types: List[str] = []
        for i, fd in enumerate(file_data):
            parms_qn = fd[qid][3]  # parms_question_number
            if i < len(parmedit_data) and parms_qn in parmedit_data[i]:
                parmedit_types.append(parmedit_data[i][parms_qn])
            else:
                parmedit_types.append('')

        result[qid] = (all_answers, parms_types, parmedit_types)

    return (processing_order, result)


def generate_common_questions(
    appended_files: List[str],
    parmedit_appended_files: List[str],
    study_name: str,
    db_client: DatabaseClient,
    output_path: str
) -> str:
    """
    Generate CommonQuestions.csv from appended files.

    Args:
        appended_files: List of paths to appended files
        parmedit_appended_files: List of paths to parmedit_APPENDED files
        study_name: Study name for database lookup
        db_client: Database client instance
        output_path: Path for output file

    Returns:
        Path to generated file
    """
    header = [
        'common_question_id',
        'master_question_text',
        'common_answer_ids',
        'ParmsQuestionType',
        'ParmeditQuestionType'
    ]

    # Read all appended files
    file_data: List[Dict[int, AppendedData]] = []
    files_read = 0

    report = get_collector()

    for path in appended_files:
        try:
            data = read_appended_file(path)
            file_data.append(data)
            files_read += 1
        except FileNotFoundError:
            report.warning(
                "FileNotFound",
                f"Appended file not found [{path}]",
                {"file": path, "step": "Step2"}
            )
        except Exception as e:
            report.warning(
                "FileReadError",
                f"Error reading appended file [{path}]: {e}",
                {"file": path, "error": str(e), "step": "Step2"}
            )

    if not file_data:
        report.error(
            "NoData",
            "No appended files could be read",
            {"step": "Step2"}
        )
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
        return output_path

    # Read all parmedit_APPENDED files
    parmedit_data: List[Dict[int, str]] = []
    for path in parmedit_appended_files:
        try:
            data = read_parmedit_appended_file(path)
            parmedit_data.append(data)
        except FileNotFoundError:
            report.warning(
                "FileNotFound",
                f"Parmedit appended file not found [{path}]",
                {"file": path, "step": "Step2"}
            )
            parmedit_data.append({})
        except Exception as e:
            report.warning(
                "FileReadError",
                f"Error reading parmedit appended file [{path}]: {e}",
                {"file": path, "error": str(e), "step": "Step2"}
            )
            parmedit_data.append({})

    # Compute intersection
    processing_order, common_questions = compute_intersection(file_data, parmedit_data)

    if not common_questions:
        report.warning(
            "NoCommonQuestions",
            f"No common questions found across {files_read} appended files",
            {"files_read": files_read, "step": "Step2"}
        )
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
        return output_path

    # Build output rows (in processing order, not sorted)
    rows = []
    for qid in processing_order:
        intersection_data = common_questions[qid]
        answer_ids, parms_types, parmedit_types = intersection_data

        # Get question_text from first file (fallback)
        parms_question_text = file_data[0][qid][2] if qid in file_data[0] else ''

        # Get master question text from database
        question_text = db_client.get_question_text(study_name, qid)
        if question_text is None:
            report.warning(
                "MissingQuestionText",
                f"No question_text found for question_id {qid} (study_name={study_name})",
                {
                    "question_id": qid,
                    "question_text_from_parms": parms_question_text,
                    "study_name": study_name,
                    "step": "Step2"
                }
            )
            question_text = parms_question_text  # Use parms text as fallback

        # Determine majority parms type
        parms_type, parms_mismatch = determine_majority_type(parms_types)
        if parms_mismatch:
            report.warning(
                "ParmsTypeMismatch",
                f"ParmsQuestionType mismatch for question_id {qid}: {parms_types}, using majority: {parms_type}",
                {
                    "question_id": qid,
                    "question_text": question_text,
                    "types": parms_types,
                    "majority": parms_type,
                    "step": "Step2"
                }
            )

        # Determine majority parmedit type
        parmedit_type, parmedit_mismatch = determine_majority_type(parmedit_types)
        if parmedit_mismatch:
            report.warning(
                "ParmeditTypeMismatch",
                f"ParmeditQuestionType mismatch for question_id {qid}: {parmedit_types}, using majority: {parmedit_type}",
                {
                    "question_id": qid,
                    "question_text": question_text,
                    "types": parmedit_types,
                    "majority": parmedit_type,
                    "step": "Step2"
                }
            )

        # Format answer_ids (empty for F-type)
        if parms_type == 'F':
            answer_ids_str = ''
        else:
            sorted_aids = sorted(answer_ids)
            answer_ids_str = '^'.join(str(aid) for aid in sorted_aids)

        rows.append([qid, question_text, answer_ids_str, parms_type, parmedit_type])

    # Write output file
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Found {len(common_questions)} common questions across {files_read} files")

    return output_path
