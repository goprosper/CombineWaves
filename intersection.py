"""Intersection computation for CombineWaves Step 2."""

import csv
import sys
from typing import Dict, List, Optional, Set

from database import DatabaseClient


def read_appended_file(path: str) -> Dict[int, Set[int]]:
    """
    Read an appended file and extract question_id -> answer_ids mapping.

    Args:
        path: Path to the appended file

    Returns:
        Dictionary mapping question_id to set of answer_ids

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    result: Dict[int, Set[int]] = {}

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

            # Parse answer_ids
            answer_ids: Set[int] = set()
            if answer_ids_str:
                for aid in answer_ids_str.split('^'):
                    aid = aid.strip()
                    if aid and aid.isdigit():
                        answer_ids.add(int(aid))

            # Merge with existing entry or create new one
            if question_id in result:
                result[question_id].update(answer_ids)
            else:
                result[question_id] = answer_ids

    return result


def compute_intersection(
    file_data: List[Dict[int, Set[int]]]
) -> Dict[int, Set[int]]:
    """
    Compute intersection of question_ids and union of answer_ids.

    Args:
        file_data: List of question_id -> answer_ids mappings (one per file)

    Returns:
        Dictionary mapping common question_ids to union of answer_ids
    """
    if not file_data:
        return {}

    # Get question_ids from each file
    question_id_sets = [set(fd.keys()) for fd in file_data]

    # Compute intersection of question_ids
    common_ids = question_id_sets[0].copy()
    for qid_set in question_id_sets[1:]:
        common_ids = common_ids.intersection(qid_set)

    # For each common question_id, compute union of answer_ids
    result: Dict[int, Set[int]] = {}
    for qid in common_ids:
        all_answers: Set[int] = set()
        for fd in file_data:
            all_answers.update(fd[qid])
        result[qid] = all_answers

    return result


def generate_common_questions(
    appended_files: List[str],
    study_name: str,
    db_client: DatabaseClient,
    output_path: str
) -> str:
    """
    Generate CommonQuestions.csv from appended files.

    Args:
        appended_files: List of paths to appended files
        study_name: Study name for database lookup
        db_client: Database client instance
        output_path: Path for output file

    Returns:
        Path to generated file
    """
    # Read all appended files
    file_data: List[Dict[int, Set[int]]] = []
    files_read = 0

    for path in appended_files:
        try:
            data = read_appended_file(path)
            file_data.append(data)
            files_read += 1
        except FileNotFoundError:
            print(f"Warning: Appended file not found [{path}]", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error reading appended file [{path}]: {e}", file=sys.stderr)

    if not file_data:
        print("Error: No appended files could be read", file=sys.stderr)
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
        return output_path

    # Compute intersection
    common_questions = compute_intersection(file_data)

    if not common_questions:
        print(
            f"Warning: No common questions found across {files_read} appended files",
            file=sys.stderr
        )
        # Create empty file with header
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
        return output_path

    # Build output rows
    rows = []
    for qid in sorted(common_questions.keys()):
        # Get master question text from database
        question_text = db_client.get_question_text(study_name, qid)
        if question_text is None:
            print(
                f"Warning: No question_text found for question_id {qid} "
                f"(study_name={study_name})",
                file=sys.stderr
            )
            question_text = ''

        # Sort answer_ids and format
        sorted_aids = sorted(common_questions[qid])
        answer_ids_str = '^'.join(str(aid) for aid in sorted_aids)

        rows.append([qid, question_text, answer_ids_str])

    # Write output file
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
        writer.writerows(rows)

    print(f"Found {len(common_questions)} common questions across {files_read} files")

    return output_path
