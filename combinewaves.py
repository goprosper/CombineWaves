#!/usr/bin/env python3
"""
CombineWaves - Survey data processing tool.

Reads survey question/answer mappings from CSV files and appends database IDs
by querying a MySQL database.

Usage:
    python combinewaves.py <control_file>

The control file contains lines in the format:
    study_name,study_date,parms_file_name,pip_file_name,parmedit_file_name
"""

import sys
from typing import List

from control_file import read_control_file
from database import DatabaseClient
from parmedit import load_parmedit
from parms_processor import process_parms_file


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

    # Read control file
    try:
        entries = list(read_control_file(control_path))
    except FileNotFoundError:
        print(f"Error: Control file not found: {control_path}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid control file format: {e}", file=sys.stderr)
        return 1

    if not entries:
        print(f"Warning: Control file is empty [{control_path}]", file=sys.stderr)
        return 0

    # Track success/failure
    success_count = 0
    error_count = 0

    # Process each entry
    for entry in entries:
        try:
            # Load parmedit file
            parmedit_mapper = load_parmedit(entry.parmedit_file_name)

            with DatabaseClient() as db:
                output_path = process_parms_file(
                    entry.parms_file_name,
                    entry.study_name,
                    entry.study_date,
                    db,
                    parmedit_mapper
                )
                print(f"Created: {output_path}")
                success_count += 1

        except FileNotFoundError as e:
            # Could be parms file or parmedit file
            print(f"Error: File not found: {e}", file=sys.stderr)
            error_count += 1

        except Exception as e:
            print(
                f"Error processing {entry.parms_file_name}: {e}",
                file=sys.stderr
            )
            error_count += 1

    # Summary
    if error_count > 0:
        print(
            f"\nCompleted with {success_count} succeeded, {error_count} failed",
            file=sys.stderr
        )

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
