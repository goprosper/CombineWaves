#!/usr/bin/env python3
"""
Append Agile Brain emotional profiling data to CommonParms.csv and CommonData.pip.

This program:
1. Reads Agile_Brain_Data_Layout.csv to generate new parms rows
2. Appends them to CommonParms.csv creating CommonParmsAppended.csv
3. Matches CommonData.pip rows against Agile_Brain_Data.csv by Prosper ID
4. Appends Agile Brain columns to matched rows creating CommonDataAppended.pip
"""

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class LayoutRow:
    """Represents a row from Agile_Brain_Data_Layout.csv (starting at row 4)."""
    field_number: int       # Column 1: e.g., 1852
    question_id: str        # Column 2: e.g., "AgileBrainAlertLevel"
    question_text: str      # Column 3: description
    answer_code: str        # Column 4: e.g., "Binary (0 or 1)"


@dataclass
class AppendStatistics:
    """Statistics about the append operation."""
    parms_rows_appended: int
    data_columns_appended: int
    data_rows_matched: int
    data_rows_unmatched: int
    total_parms_rows: int
    total_data_rows: int


def load_layout_file(filepath: str) -> List[LayoutRow]:
    """
    Parse Agile_Brain_Data_Layout.csv starting from row 4 (1-based).

    Args:
        filepath: Path to Agile_Brain_Data_Layout.csv

    Returns:
        List of LayoutRow objects for fields 1852-1951
    """
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, start=1):
            # Skip rows 1-3 (headers)
            if i < 4:
                continue
            # Stop after row 103 (100 data rows: 4-103)
            if i > 103:
                break
            if len(row) >= 4:
                try:
                    field_number = int(row[0])
                except ValueError:
                    continue
                question_id = row[1]
                question_text = row[2]
                answer_code = row[3]
                rows.append(LayoutRow(
                    field_number=field_number,
                    question_id=question_id,
                    question_text=question_text,
                    answer_code=answer_code
                ))
    return rows


def determine_question_type(answer_code: str) -> Tuple[str, int, str]:
    """
    Map answer code to (answer_text_list, total_answers, question_type).

    Args:
        answer_code: The answer code from the layout file

    Returns:
        Tuple of (answer_text_list, total_answers, question_type)
    """
    if "Binary (0 or 1)" in answer_code:
        return ("Yes^No", 2, "S")
    elif "Integer (1-10)" in answer_code:
        return ("1^2^3^4^5^6^7^8^9^10", 10, "S")
    else:
        # Free-form (Numeric, etc.)
        return ("", 0, "F")


def load_agile_brain_index(filepath: str) -> Dict[str, List[str]]:
    """
    Build an index from Prosper ID to Agile Brain data columns.

    Args:
        filepath: Path to Agile_Brain_Data.csv

    Returns:
        Dict mapping Prosper ID to list of 100 column values (1852-1951)
    """
    index = {}
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header

        # Column indices (0-based): 1851 is ID #1, 1852-1951 are data columns
        # In 0-based indexing: 1850 is ID, 1851-1950 are data columns
        id_col = 1850
        data_start = 1851
        data_end = 1951  # exclusive

        for row in reader:
            if len(row) > data_end - 1:
                prosper_id = row[id_col]
                data_values = row[data_start:data_end]
                index[prosper_id] = data_values
    return index


def find_sid_psid_columns(filepath: str) -> Tuple[int, int]:
    """
    Find SID and psid column positions in CommonParms.csv.

    Args:
        filepath: Path to CommonParms.csv

    Returns:
        Tuple of (sid_column_number, psid_column_number), 1-based
    """
    sid_col = None
    psid_col = None

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                question_num = row[0]
                question_text = row[2]
                if question_text == "SID":
                    sid_col = int(question_num)
                elif question_text == "psid":
                    psid_col = int(question_num)
            if sid_col and psid_col:
                break

    return (sid_col or 250, psid_col or 251)


def transform_agile_value(value: str, column_index: int) -> str:
    """
    Transform Agile Brain value for output.

    For column 1852 (index 0): value "0" becomes "2" (No in Yes^No list)

    Args:
        value: The value from the Agile Brain data
        column_index: 0-based index within the 100 Agile Brain columns

    Returns:
        Transformed value
    """
    if column_index == 0:  # Column 1852 - AgileBrainAlertLevel
        if value == "0":
            return "2"
        elif value == "1":
            return "1"
    return value


def append_common_parms(
    common_parms_path: str,
    layout_rows: List[LayoutRow],
    output_path: str
) -> int:
    """
    Copy CommonParms.csv and append new rows from layout file.

    Args:
        common_parms_path: Path to CommonParms.csv
        layout_rows: List of LayoutRow objects from layout file
        output_path: Path for output file

    Returns:
        Number of rows appended
    """
    # Read existing parms
    existing_rows = []
    with open(common_parms_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            existing_rows.append(row)

    # Generate new rows
    next_question_num = len(existing_rows) + 1
    new_rows = []

    for layout_row in layout_rows:
        question_text = f"{layout_row.question_id}: {layout_row.question_text}"
        answer_text_list, total_answers, question_type = determine_question_type(layout_row.answer_code)

        new_row = [
            str(next_question_num),
            str(total_answers),
            question_text,
            "",
            answer_text_list,
            question_type
        ]
        new_rows.append(new_row)
        next_question_num += 1

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in existing_rows:
            writer.writerow(row)
        for row in new_rows:
            writer.writerow(row)

    return len(new_rows)


def append_common_data(
    common_data_path: str,
    agile_index: Dict[str, List[str]],
    sid_col: int,
    psid_col: int,
    output_path: str
) -> Tuple[int, int]:
    """
    Match CommonData.pip rows against Agile Brain index and append columns.

    Args:
        common_data_path: Path to CommonData.pip
        agile_index: Dict mapping Prosper ID to Agile Brain data
        sid_col: SID column number (1-based)
        psid_col: psid column number (1-based)
        output_path: Path for output file

    Returns:
        Tuple of (rows_matched, rows_unmatched)
    """
    matched = 0
    unmatched = 0

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(common_data_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:

        for line in infile:
            line = line.rstrip('\n')
            columns = line.split('|')

            # Get SID and psid values (convert to 0-based index)
            sid_value = columns[sid_col - 1] if len(columns) >= sid_col else ""
            psid_value = columns[psid_col - 1] if len(columns) >= psid_col else ""

            # Try to match against Agile Brain index
            agile_data = None
            if sid_value and sid_value in agile_index:
                agile_data = agile_index[sid_value]
            elif psid_value and psid_value in agile_index:
                agile_data = agile_index[psid_value]

            if agile_data:
                # Transform values and append
                transformed_data = [
                    transform_agile_value(val, i)
                    for i, val in enumerate(agile_data)
                ]
                new_line = line + '|' + '|'.join(transformed_data)
                outfile.write(new_line + '\n')
                matched += 1
            else:
                unmatched += 1

    return matched, unmatched


def main():
    """Main entry point."""
    # File paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    agile_dir = os.path.join(base_dir, "AgileBrainsAppend")

    layout_path = os.path.join(agile_dir, "Agile_Brain_Data_Layout.csv")
    agile_data_path = os.path.join(agile_dir, "Agile_Brain_Data.csv")
    common_parms_path = os.path.join(base_dir, "CommonParms.csv")
    common_data_path = os.path.join(base_dir, "CommonData.pip")

    output_parms_path = os.path.join(agile_dir, "CommonParmsAppended.csv")
    output_data_path = os.path.join(agile_dir, "CommonDataAppended.pip")

    print("Append Agile Brain Data")
    print("=" * 50)

    # Step 1: Load layout file
    print("\n1. Loading layout file...")
    layout_rows = load_layout_file(layout_path)
    print(f"   Loaded {len(layout_rows)} rows from layout file")

    # Step 2: Append CommonParms
    print("\n2. Appending CommonParms.csv...")
    parms_appended = append_common_parms(common_parms_path, layout_rows, output_parms_path)
    print(f"   Appended {parms_appended} rows")

    # Count total rows in output
    with open(output_parms_path, 'r', encoding='utf-8') as f:
        total_parms = sum(1 for _ in f)
    print(f"   Total rows in output: {total_parms}")

    # Step 3: Load Agile Brain index
    print("\n3. Loading Agile Brain data index...")
    agile_index = load_agile_brain_index(agile_data_path)
    print(f"   Loaded {len(agile_index)} Prosper IDs")

    # Step 4: Find SID/psid columns
    print("\n4. Finding SID/psid columns...")
    sid_col, psid_col = find_sid_psid_columns(common_parms_path)
    print(f"   SID column: {sid_col}")
    print(f"   psid column: {psid_col}")

    # Step 5: Append CommonData
    print("\n5. Appending CommonData.pip...")
    matched, unmatched = append_common_data(
        common_data_path,
        agile_index,
        sid_col,
        psid_col,
        output_data_path
    )
    print(f"   Rows matched: {matched}")
    print(f"   Rows unmatched: {unmatched}")

    # Count columns in output
    with open(output_data_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        total_columns = len(first_line.split('|'))
    print(f"   Total columns in output: {total_columns}")

    # Summary statistics
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    stats = AppendStatistics(
        parms_rows_appended=parms_appended,
        data_columns_appended=len(layout_rows),
        data_rows_matched=matched,
        data_rows_unmatched=unmatched,
        total_parms_rows=total_parms,
        total_data_rows=matched
    )
    print(f"Parms rows appended: {stats.parms_rows_appended}")
    print(f"Data columns appended: {stats.data_columns_appended}")
    print(f"Data rows matched: {stats.data_rows_matched}")
    print(f"Data rows unmatched: {stats.data_rows_unmatched}")
    print(f"Total CommonParms rows: {stats.total_parms_rows}")
    print(f"Total CommonData rows: {stats.total_data_rows}")
    print(f"\nOutput files:")
    print(f"  {output_parms_path}")
    print(f"  {output_data_path}")


if __name__ == "__main__":
    main()
