# Tasks: Modify append_agile_brain.py for Quartile Data

## Task 1: Update LayoutRow dataclass
Replace the `LayoutRow` dataclass fields to match the new `ABWithQuartilesLayout.csv` structure:
- Remove `field_number` and `answer_code`
- Add `question_type` and `answer_text`

## Task 2: Rewrite load_layout_file()
Replace the function to read `ABWithQuartilesLayout.csv`:
- Skip header row (row 1)
- Read all 198 data rows
- Parse columns: question_id (col 2), question_type (col 3), question_text (col 4), answer_text (col 5)

## Task 3: Remove determine_question_type()
Delete this function entirely. The layout file now provides type and answer information directly.

## Task 4: Modify append_common_parms()
Update to use new LayoutRow fields:
- Use `layout_row.question_text` directly (no longer build "{id}: {text}")
- Use `layout_row.question_type` directly
- Use `layout_row.answer_text` directly
- Compute `total_answers` from answer_text (count ^-delimited items, default 1 if empty)

## Task 5: Rewrite load_agile_brain_index()
Update to read `AB_Data_Quartiles_01272026.csv`:
- ID column at index 0 (was 1850)
- Data columns at indices 1-198 (was 1851-1950)
- Derive data column range from header length rather than hard-coding

## Task 6: Update main() file paths
Change two path assignments:
- `layout_path` → `ABWithQuartilesLayout.csv`
- `agile_data_path` → `AB_Data_Quartiles_01272026.csv`

## Task 7: Test
Run the modified program and verify:
- Layout loads 198 rows
- CommonParmsAppended.csv has correct new rows (198 appended with correct text/type/answers)
- Data index loads from new file with correct ID matching
- CommonDataAppended.pip has 198 appended columns per row
- AgileBrainAlertLevel transformation still works (0→2, 1→1)
- Statistics output reflects 198 instead of 100
