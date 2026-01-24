# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CombineWaves is a Python command-line tool for processing survey data. It reads survey question/answer mappings from CSV files and appends database IDs by querying a MySQL database.

**Status**: Implemented.

## Workflow

### Step 1: Process Parms Files

1. Read a control file with format: `study_name,study_date,parms_file_name,pip_file_name,parmedit_file_name`
2. For each line:
   - Load the parmedit file to build a mapping from parms_question_number to question_number
   - Process the parms file:
     - For each row, look up the question_number via the parmedit mapping
     - Query MySQL table `br_question_map` using study_name, study_date, question_number
     - Retrieve question_id and answer_value_map
     - Compute answer_ids by mapping answer positions to database indices
   - Write output as `parms_file_name.appended`

### Step 2: Compute Intersection

1. Read all appended files generated in Step 1
2. Find question_ids common to ALL appended files
3. For each common question_id:
   - Compute the union of answer_ids across all files
   - Query `br_question_master` table for master_question_text
4. Write `CommonQuestions.csv` with columns: common_question_id, master_question_text, common_answer_ids

## Parmedit File Format (CSV)

The parmedit file maps parms_question_number to question_number:
- Column 1: parms_question_number
- Row number (1-based): the corresponding question_number for database queries

## Parms File Format (CSV)

| Column | Content |
|--------|---------|
| 1 | parms_question_number (mapped to question_number via parmedit file) |
| 2 | Total answers |
| 3 | Question text |
| 4 | Empty |
| 5 | ^-delimited list of answers |
| 6 | Question type (S=single, M=multiple, F=free-form) |
| 7 | question_id (appended) |
| 8 | answer_ids (appended) |

## Answer ID Mapping Logic

The answer_ids column maps each answer's position (1-based) to its index in the database's answer_value_map:

```
Parms answers:     American Indian^Asian^Black/African American^East Indian^Hispanic^White^Other
answer_value_map:  3^2^?^1^6^7^4^5
answer_ids:        3^1^0^6^7^4^5
```

For each answer position (1, 2, 3...), find where that number appears in answer_value_map; the index is the answer_id.

## CommonQuestions.csv Format

| Column | Content |
|--------|---------|
| 1 | common_question_id |
| 2 | master_question_text (from br_question_master table) |
| 3 | common_answer_ids (^-delimited, sorted, union of all files) |

## Technology Stack

- Python 3
- PyMySQL==1.1.2 (required for MySQL 5.1.44 compatibility)
- MySQL database on 50.17.224.19, database: ptdb
  - Table: br_question_map (Step 1)
  - Table: br_question_master (Step 2)

## Sample Data

- `WaveFiles/CJanuary2026_parms.csv` - Example parms file
- `WaveFiles/CJanuary2026_parmedit.csv` - Example parmedit file
- `WaveFiles/CJanuary2026_data.pip` - Example data file
- `WaveFiles/test_control.txt` - Example control file
