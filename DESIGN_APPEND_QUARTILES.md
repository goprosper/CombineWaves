# Design: Modify append_agile_brain.py for Quartile Data

## Changes Summary

Modify `append_agile_brain.py` to use two new input files with a simpler, more direct structure. The core matching and output logic is unchanged.

## File: append_agile_brain.py

### 1. Replace `LayoutRow` dataclass

**Current:**
```python
@dataclass
class LayoutRow:
    field_number: int
    question_id: str
    question_text: str
    answer_code: str
```

**New:**
```python
@dataclass
class LayoutRow:
    question_id: str        # Column 2: variable name
    question_type: str      # Column 3: "S" or "F"
    question_text: str      # Column 4: pre-formatted question text
    answer_text: str        # Column 5: ^-delimited answer list
```

The `field_number` is no longer needed since the new layout has a simple sequential number. The `answer_code` is replaced by explicit `question_type` and `answer_text` fields.

### 2. Replace `load_layout_file()`

**Current:** Reads `Agile_Brain_Data_Layout.csv`, skips rows 1-3, parses field_number/question_id/question_text/answer_code from rows 4-103.

**New:** Reads `ABWithQuartilesLayout.csv`, skips header row 1, reads all 198 data rows. Parses:
- `row[1]` → `question_id`
- `row[2]` → `question_type`
- `row[3]` → `question_text`
- `row[4]` → `answer_text`

### 3. Remove `determine_question_type()`

This function is no longer needed. The layout file now provides `question_type` and `answer_text` directly.

### 4. Modify `append_common_parms()`

**Current:** Calls `determine_question_type(layout_row.answer_code)` to derive answer_text_list, total_answers, question_type. Builds question_text as `"{question_id}: {question_text}"`.

**New:** Reads directly from LayoutRow fields:
- `question_text` = `layout_row.question_text` (already formatted)
- `question_type` = `layout_row.question_type`
- `answer_text_list` = `layout_row.answer_text`
- `total_answers` = count of ^-delimited items in `answer_text`. If empty, default to `1`.

### 5. Replace `load_agile_brain_index()`

**Current:** Reads `Agile_Brain_Data.csv`. ID at column index 1850, data at indices 1851-1950 (100 columns).

**New:** Reads `AB_Data_Quartiles_01272026.csv`. ID at column index 0, data at indices 1-198 (198 columns).

The data column count is derived from the header row length minus 1 (for the ID column), rather than hard-coded. This makes the function resilient to future layout changes.

### 6. `transform_agile_value()` - Unchanged

The AgileBrainAlertLevel transformation (column index 0: "0"→"2", "1"→"1") is preserved as-is, since AgileBrainAlertLevel remains the first data column.

### 7. `find_sid_psid_columns()` - Unchanged

No changes needed.

### 8. `append_common_data()` - Unchanged

No changes needed. It already works generically with whatever data the index contains.

### 9. `main()` - Update file paths

Change two file path assignments:
- `layout_path`: `Agile_Brain_Data_Layout.csv` → `ABWithQuartilesLayout.csv`
- `agile_data_path`: `Agile_Brain_Data.csv` → `AB_Data_Quartiles_01272026.csv`

## Data Flow (Updated)

```
ABWithQuartilesLayout.csv (198 rows)
    → load_layout_file() → List[LayoutRow]
    → append_common_parms() → CommonParmsAppended.csv (+198 rows)

AB_Data_Quartiles_01272026.csv (ID in col 1, 198 data cols)
    → load_agile_brain_index() → {prosper_id: [198 values]}

CommonParms.csv → find_sid_psid_columns() → sid_col, psid_col

CommonData.pip + agile_index + sid_col/psid_col
    → append_common_data() → CommonDataAppended.pip (+198 cols)
```

## Functions Changed vs Unchanged

| Function | Status | Reason |
|----------|--------|--------|
| `LayoutRow` | Modified | New fields match new layout file structure |
| `load_layout_file()` | Modified | New file format, simpler parsing |
| `determine_question_type()` | Removed | Layout now has type/answers directly |
| `load_agile_brain_index()` | Modified | ID at col 0, data at cols 1-198 |
| `append_common_parms()` | Modified | Use LayoutRow fields directly |
| `transform_agile_value()` | Unchanged | Same transformation still needed |
| `find_sid_psid_columns()` | Unchanged | Same matching logic |
| `append_common_data()` | Unchanged | Works generically |
| `main()` | Modified | Two file path changes |
| `AppendStatistics` | Unchanged | Same structure |
