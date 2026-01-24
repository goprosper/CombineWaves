# CombineWaves Step 2 - Compute Intersection: Implementation Plan

## Overview

This document provides a step-by-step implementation plan for adding the intersection computation feature to CombineWaves.

## Prerequisites

- Step 1 (parms processing with parmedit support) is complete and tested
- All existing tests pass
- Appended files are being generated correctly

## Implementation Steps

### Step 1: Extend DatabaseClient

**File:** `database.py`

**Task:** Add a new method to query br_question_master for question_text.

**Changes:**
1. Add new method `get_question_text(study_name, question_id)` to DatabaseClient class
2. Method should return Optional[str] - the question_text or None if not found

**SQL Query:**
```sql
SELECT question_text
FROM br_question_master
WHERE study_name = %s
  AND question_id = %s
```

---

### Step 2: Create Intersection Module

**File:** `intersection.py` (new file)

**Task:** Create the core intersection computation module.

**Functions to implement:**

1. `read_appended_file(path: str) -> dict[int, set[int]]`
   - Read CSV file
   - Extract question_id from column 7 (index 6)
   - Extract answer_ids from column 8 (index 7)
   - Parse answer_ids string into set of integers
   - Skip rows with empty question_id
   - Handle duplicate question_ids by merging answer_ids
   - Use latin-1 encoding (consistent with other file reading)

2. `compute_intersection(file_data: list[dict[int, set[int]]]) -> dict[int, set[int]]`
   - Compute set intersection of all question_id keys
   - For each common question_id, compute union of answer_ids
   - Return mapping of common question_ids to their answer_id unions

3. `generate_common_questions(appended_files, study_name, db_client, output_path) -> str`
   - Read all appended files using `read_appended_file()`
   - Compute intersection using `compute_intersection()`
   - For each common question_id:
     - Query database for master_question_text
     - Sort answer_ids numerically
     - Format as ^-delimited string
   - Write CommonQuestions.csv with header row
   - Return output path

**Error handling:**
- Log warning if appended file not found, continue with remaining files
- Log warning if intersection is empty
- Log warning if question_text not found for a question_id

---

### Step 3: Update Main Module

**File:** `combinewaves.py`

**Task:** Integrate Step 2 after Step 1 completes.

**Changes:**
1. Add import for `generate_common_questions` from intersection module
2. After Step 1 loop completes:
   - Collect list of successfully created appended file paths
   - If at least one appended file was created:
     - Use study_name from first control entry
     - Open database connection
     - Call `generate_common_questions()`
     - Print success message with output path
3. Include file names in any error/warning messages

---

### Step 4: Create Unit Tests

**File:** `test_intersection.py` (new file)

**Test cases to implement:**

1. **TestReadAppendedFile**
   - `test_read_basic`: Read file with valid data
   - `test_read_skips_empty_question_id`: Rows without question_id are skipped
   - `test_read_merges_duplicate_question_ids`: Same question_id on multiple rows
   - `test_read_handles_empty_answer_ids`: Rows with empty answer_ids
   - `test_read_file_not_found`: FileNotFoundError raised

2. **TestComputeIntersection**
   - `test_intersection_basic`: Three files with overlapping questions
   - `test_intersection_all_common`: All files have same questions
   - `test_intersection_none_common`: No common questions
   - `test_intersection_single_file`: Only one file
   - `test_intersection_empty_list`: Empty file list
   - `test_answer_union`: Verify answer_ids are unioned correctly
   - `test_answer_sorting`: Verify sorted output

3. **TestGenerateCommonQuestions**
   - `test_generate_basic`: End-to-end with mock database
   - `test_generate_empty_intersection`: Verify empty file created with header
   - `test_generate_missing_question_text`: Warning logged, empty string used

---

### Step 5: Create Integration Tests

**File:** `test_intersection.py` (add to existing)

**Test cases:**

1. `test_with_real_appended_files`: Use actual files from WaveFiles/ directory
2. `test_full_workflow`: Run both Step 1 and Step 2

---

### Step 6: Update Documentation

**Files to update:**

1. **CLAUDE.md**: Add Step 2 description to workflow section
2. **README** (if exists): Document new CommonQuestions.csv output

---

### Step 7: Run All Tests

**Command:** `python3 -m pytest -v`

**Expected:** All existing tests pass + new intersection tests pass

---

### Step 8: Manual Testing

1. Run full workflow with test_control.txt:
   ```
   python3 combinewaves.py WaveFiles/test_control.txt
   ```

2. Verify CommonQuestions.csv is created

3. Check CommonQuestions.csv contents:
   - Has header row
   - Contains only question_ids common to all appended files
   - answer_ids are sorted and ^-delimited
   - master_question_text is populated from database

---

### Step 9: Commit Changes

**Files to commit:**
- database.py (modified)
- intersection.py (new)
- combinewaves.py (modified)
- test_intersection.py (new)
- CLAUDE.md (modified)
- REQUIREMENTS_INTERSECTION.md (new)
- DESIGN_INTERSECTION.md (new)
- IMPLEMENTATION_PLAN_INTERSECTION.md (new)

---

## Verification Checklist

- [ ] DatabaseClient.get_question_text() works correctly
- [ ] read_appended_file() correctly parses appended files
- [ ] compute_intersection() correctly computes common question_ids
- [ ] compute_intersection() correctly unions answer_ids
- [ ] answer_ids are sorted numerically in output
- [ ] CommonQuestions.csv has correct format
- [ ] Warning messages include relevant file names
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual test with test_control.txt succeeds
- [ ] Code is committed

## Estimated File Changes

| File | Change Type | Lines (approx) |
|------|-------------|----------------|
| database.py | Modify | +20 |
| intersection.py | New | ~120 |
| combinewaves.py | Modify | +15 |
| test_intersection.py | New | ~200 |
| CLAUDE.md | Modify | +10 |
| Total | | ~365 |
