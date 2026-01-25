#!/usr/bin/env python3
"""
CombineWaves - Survey data processing tool.

Reads survey question/answer mappings from CSV files and appends database IDs
by querying a MySQL database.

Usage:
    python combinewaves.py <control_file>

The control file contains lines in the format:
    study_name,study_date,parms_file_name,pip_file_name,parmedit_file_name,upload_file_name
"""

import os
import sys
from typing import List

from control_file import read_control_file
from database import DatabaseClient
from generate_common_parms import generate_common_parms
from generate_pip import generate_common_pip
from intersection import generate_common_questions
from parmedit import load_parmedit_appended
from parms_processor import process_parms_file
from report import reset_collector
from upload_matcher import create_parmedit_appended


def main(argv: List[str]) -> int:
    """
    Main entry point.

    Args:
        argv: Command-line arguments (sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Validate command-line arguments
    if len(argv) != 1:
        print("Usage: python combinewaves.py <control_file>", file=sys.stderr)
        return 1

    control_path = argv[0]

    # Initialize report collector
    report = reset_collector()

    # Read control file
    try:
        entries = list(read_control_file(control_path))
    except FileNotFoundError:
        report.error("ControlFile", f"Control file not found: {control_path}")
        return 1
    except ValueError as e:
        report.error("ControlFile", f"Invalid control file format: {e}")
        return 1

    if not entries:
        report.warning("ControlFile", f"Control file is empty [{control_path}]")
        return 0

    # Track success/failure and appended files
    success_count = 0
    error_count = 0
    common_questions_count = 0
    rows_processed = 0
    appended_files: List[str] = []

    # Step 1: Process each entry
    print("Step 1: Processing parms files...")
    for entry in entries:
        try:
            # Generate parmedit_APPENDED file by matching to UPLOAD
            parmedit_appended_path = create_parmedit_appended(
                entry.parmedit_file_name,
                entry.upload_file_name
            )
            print(f"Created: {parmedit_appended_path}")

            # Load parmedit_APPENDED (question_number from UPLOAD file)
            parmedit_mapper = load_parmedit_appended(parmedit_appended_path)

            with DatabaseClient() as db:
                output_path = process_parms_file(
                    entry.parms_file_name,
                    entry.study_name,
                    entry.study_date,
                    db,
                    parmedit_mapper
                )
                print(f"Created: {output_path}")
                appended_files.append(output_path)
                success_count += 1

        except FileNotFoundError as e:
            # Could be parms file, parmedit file, or upload file
            report.error(
                "FileNotFound",
                f"File not found: {e}",
                {"error": str(e), "parms_file": entry.parms_file_name, "step": "Step1"}
            )
            error_count += 1

        except Exception as e:
            report.error(
                "ProcessingError",
                f"Error processing {entry.parms_file_name}: {e}",
                {"error": str(e), "parms_file": entry.parms_file_name, "step": "Step1"}
            )
            error_count += 1

    # Step 1 Summary
    if error_count > 0:
        print(
            f"\nStep 1 completed with {success_count} succeeded, {error_count} failed",
            file=sys.stderr
        )

    # Step 2: Compute intersection and generate CommonQuestions.csv
    if appended_files:
        print("\nStep 2: Computing intersection...")
        study_name = entries[0].study_name  # Use first entry's study_name

        # Build parmedit_APPENDED paths
        parmedit_appended_files: List[str] = []
        for entry in entries:
            if entry.parmedit_file_name.lower().endswith('.csv'):
                path = entry.parmedit_file_name[:-4] + '_APPENDED.csv'
            else:
                path = entry.parmedit_file_name + '_APPENDED'
            parmedit_appended_files.append(path)

        try:
            with DatabaseClient() as db:
                common_output = generate_common_questions(
                    appended_files,
                    parmedit_appended_files,
                    study_name,
                    db,
                    "CommonQuestions.csv"
                )
                print(f"Created: {common_output}")

                # Count common questions for report
                try:
                    with open("CommonQuestions.csv", 'r') as f:
                        common_questions_count = sum(1 for _ in f) - 1  # Subtract header
                except Exception:
                    pass
        except Exception as e:
            report.error(
                "Step2Error",
                f"Error in Step 2: {e}",
                {"error": str(e), "step": "Step2"}
            )
            error_count += 1
    else:
        report.warning(
            "Step2Skipped",
            "Step 2 skipped: No appended files were created",
            {"step": "Step2"}
        )

    # Step 3: Generate combined pip
    if os.path.exists("CommonQuestions.csv"):
        print("\nStep 3: Generating combined pip...")
        try:
            pip_output = generate_common_pip(
                "CommonQuestions.csv",
                entries,
                "CommonData.pip"
            )
            print(f"Created: {pip_output}")

            # Count rows processed for report
            try:
                with open("CommonData.pip", 'r') as f:
                    rows_processed = sum(1 for line in f if line.strip())
            except Exception:
                pass
        except Exception as e:
            report.error(
                "Step3Error",
                f"Error in Step 3: {e}",
                {"error": str(e), "step": "Step3"}
            )
            error_count += 1
    else:
        report.warning(
            "Step3Skipped",
            "Step 3 skipped: CommonQuestions.csv not found",
            {"step": "Step3"}
        )

    # Step 4: Generate common parms
    if os.path.exists("CommonQuestions.csv"):
        print("\nStep 4: Generating common parms...")
        try:
            study_name = entries[0].study_name
            with DatabaseClient() as db:
                parms_output = generate_common_parms(
                    "CommonQuestions.csv",
                    study_name,
                    db,
                    "CommonParms.csv"
                )
                print(f"Created: {parms_output}")
        except Exception as e:
            report.error(
                "Step4Error",
                f"Error in Step 4: {e}",
                {"error": str(e), "step": "Step4"}
            )
            error_count += 1
    else:
        report.warning(
            "Step4Skipped",
            "Step 4 skipped: CommonQuestions.csv not found",
            {"step": "Step4"}
        )

    # Generate execution report
    report_path = report.generate_report(
        "CombineWaves_Report.txt",
        control_path,
        files_processed=success_count,
        common_questions=common_questions_count,
        rows_processed=rows_processed
    )
    print(f"\nReport saved: {report_path}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
