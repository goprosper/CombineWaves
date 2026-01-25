# Implementation Plan: Generate Common Parms (Step 4)

## Task List

### Task 1: Add QuestionMasterRecord dataclass to database.py
- Add new dataclass `QuestionMasterRecord` with fields:
  - `alternate_text: str`
  - `answer_text: str`
- Location: `database.py` after `QuestionMapRecord`

### Task 2: Add get_question_master() method to DatabaseClient
- Add method to query br_question_master table
- Select `alternate_text` and `answer_text` columns
- Filter by `study_name` and `question_id`
- Return `QuestionMasterRecord` or `None`
- Location: `database.py` in `DatabaseClient` class

### Task 3: Create generate_common_parms.py module
- Create new file with:
  - `CommonQuestion` dataclass (parsed input row)
  - `ParmsRow` dataclass (output row)
  - `load_common_questions_for_parms()` function
  - `transform_answer_ids_to_text()` function
  - `generate_common_parms()` main function

### Task 4: Implement load_common_questions_for_parms()
- Read CommonQuestions.csv
- Skip header row
- Parse each row into CommonQuestion dataclass
- Handle empty common_answer_ids

### Task 5: Implement transform_answer_ids_to_text()
- Parse answer_text_map (^-delimited string)
- Map each common_answer_id to its answer text
- Return ^-delimited result
- Handle out-of-bounds indices gracefully

### Task 6: Implement generate_common_parms()
- Load common questions from CSV
- For each question:
  - Query database for alternate_text and answer_text
  - Transform answer IDs to text
  - Build output row
- Write CSV output (no header)
- Return output path

### Task 7: Create test_generate_common_parms.py
- Test load_common_questions_for_parms():
  - Basic loading
  - Empty answer_ids
  - File not found
- Test transform_answer_ids_to_text():
  - Basic transformation
  - Reordered IDs
  - Empty inputs
  - Out-of-bounds handling
- Test generate_common_parms():
  - Full workflow with mocked DB
  - Missing DB records
  - Type F questions (empty answers)

### Task 8: Integrate Step 4 into combinewaves.py
- Add import for generate_common_parms
- Add Step 4 section after Step 3
- Add error handling and reporting
- Update execution report

### Task 9: Update CLAUDE.md documentation
- Add Step 4 description to workflow
- Document CommonParms.csv format

## Dependencies

```
Task 1 ──┬── Task 2 ──┐
         │           │
Task 3 ──┼── Task 4 ─┼── Task 6 ── Task 8 ── Task 9
         │           │
         └── Task 5 ─┘
                     │
              Task 7 ┘
```

## Verification

After implementation:
1. Run `python3 -m pytest test_generate_common_parms.py -v`
2. Run `python3 -m pytest -v` (all tests)
3. Manually verify CommonParms.csv output format matches spec
