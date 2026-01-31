# Requirements: Modify append_agile_brain.py for Quartile Data

## Overview

Modify `append_agile_brain.py` to use the new quartile-enriched data file and layout file instead of the original Agile Brain files. The new data file contains 198 columns (the original 100 fields plus 98 quartile variants) and uses a simpler structure where the ID column is column 1.

## Functional Requirements

### FR-1: New Data File

Replace `AgileBrainsAppend/Agile_Brain_Data.csv` with `AgileBrainsAppend/AB_Data_Quartiles_01272026.csv` as the source of Agile Brain data.

- **ID column**: Column 1 (`ID #1`) contains the Prosper ID used for matching.
- **Data columns**: Columns 2-199 contain the 198 data fields (matching the layout file order).
- The file has a header row.

### FR-2: New Layout File

Replace `AgileBrainsAppend/Agile_Brain_Data_Layout.csv` with `AgileBrainsAppend/ABWithQuartilesLayout.csv` as the source of parms metadata.

- **Column 1**: Sequential number (not used for logic)
- **Column 2**: Variable name (`ID #1` header) - used for identification
- **Column 3**: Question type (`S` or `F`)
- **Column 4**: Question text (pre-populated, e.g., "ActivationOverall: Mean activation score...")
- **Column 5**: Answer text (^-delimited, e.g., "Yes^No" or quartile labels)
- The file has a header row; data starts at row 2.
- 198 data rows (versus 100 in the original).

### FR-3: Parms Generation

When appending rows to `CommonParms.csv`:

- **question_number**: Sequential, starting after the last existing row.
- **total_answers**: Derived from AnswerText in the layout file. Count of ^-delimited items. If AnswerText is empty, total_answers = 1.
- **question_text**: Use the QuestionText column directly from the layout file (already formatted as `"{variable}: {description}"`).
- **answer_text_list**: Use the AnswerText column directly from the layout file.
- **question_type**: Use the Type column directly from the layout file (`S` or `F`).

### FR-4: Data Index

Build the Prosper ID index from `AB_Data_Quartiles_01272026.csv`:

- Index key: Column 1 (index 0) - the Prosper ID.
- Index value: Columns 2-199 (indices 1-198) - the 198 data values.

### FR-5: AgileBrainAlertLevel Transformation

Preserve the existing transformation for AgileBrainAlertLevel (the first data column, index 0):

- Value `"0"` becomes `"2"` (No)
- Value `"1"` becomes `"1"` (Yes)

### FR-6: Matching Logic (Unchanged)

The SID/psid matching logic remains the same:

- Find SID and psid column positions from CommonParms.csv.
- For each CommonData.pip row, try matching SID first, then psid against the index.
- Only matched rows are written to output.
- Unmatched rows are dropped.

### FR-7: Output Files (Unchanged)

- `AgileBrainsAppend/CommonParmsAppended.csv` - Original CommonParms + 198 new rows.
- `AgileBrainsAppend/CommonDataAppended.pip` - Matched rows + 198 appended columns.

## Non-Functional Requirements

- Encoding: Read input with `utf-8-sig` (BOM handling), write output as `utf-8`.
- All existing reporting/statistics output remains functional, reflecting the new counts (198 instead of 100).
