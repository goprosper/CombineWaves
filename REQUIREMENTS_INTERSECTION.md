# CombineWaves Step 2 - Compute Intersection: Requirements Document

## 1. Overview

This document specifies the requirements for Step 2 of CombineWaves: computing the intersection of questions across multiple appended parms files and generating a CommonQuestions output file.

### 1.1 Purpose

After Step 1 generates multiple `.appended` files (one per control file entry), Step 2 identifies questions that are common to all appended files and consolidates their answer IDs into a single output file.

### 1.2 Terminology

| Term | Definition |
|------|------------|
| common_question_id | A question_id that appears in ALL appended files |
| master_question_text | The question text from br_question_master table |
| common_answer_ids | Superset of all answer_ids for a question across all appended files |
| appended file | Output from Step 1 with format `{parms_file}.appended` |

## 2. Functional Requirements

### 2.1 Input Processing

| ID | Requirement |
|----|-------------|
| FR-INT-001 | The application shall read all `.appended` files generated from the control file entries |
| FR-INT-002 | For each appended file, the application shall extract question_id (column 7) and answer_ids (column 8) from each row |
| FR-INT-003 | The application shall skip rows where question_id is empty |

### 2.2 Intersection Computation

| ID | Requirement |
|----|-------------|
| FR-INT-010 | The application shall compute the set of question_ids present in each appended file |
| FR-INT-011 | The application shall compute the intersection of all question_id sets (only question_ids present in ALL files) |
| FR-INT-012 | For each common question_id, the application shall collect all answer_ids from all appended files |
| FR-INT-013 | The application shall compute the union (superset) of answer_ids for each common question_id |
| FR-INT-014 | The common_answer_ids shall be sorted in numeric order |
| FR-INT-015 | The common_answer_ids shall be formatted as a ^-delimited list |

### 2.3 Database Query

| ID | Requirement |
|----|-------------|
| FR-INT-020 | For each common question_id, the application shall query the br_question_master table |
| FR-INT-021 | The query shall use study_name (from control file) and question_id to retrieve question_text |
| FR-INT-022 | The retrieved question_text shall be used as master_question_text in the output |
| FR-INT-023 | If question_text is not found, an empty string shall be used |

### 2.4 Output File Generation

| ID | Requirement |
|----|-------------|
| FR-INT-030 | The application shall generate a file named `CommonQuestions.csv` |
| FR-INT-031 | The output file shall be in CSV format |
| FR-INT-032 | The output file shall have three columns: common_question_id, master_question_text, common_answer_ids |
| FR-INT-033 | The output file shall contain one row per common question_id |
| FR-INT-034 | The rows shall be ordered by common_question_id |

### 2.5 Error Handling

| ID | Requirement |
|----|-------------|
| FR-INT-040 | The application shall report an error if no appended files exist |
| FR-INT-041 | The application shall report a warning if the intersection is empty (no common questions) |
| FR-INT-042 | The application shall report a warning if master_question_text cannot be retrieved for a question_id |

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-INT-001 | The application shall process appended files efficiently using set operations |
| NFR-INT-002 | Database queries for master_question_text shall be batched or cached where possible |

### 3.2 Compatibility

| ID | Requirement |
|----|-------------|
| NFR-INT-010 | Step 2 shall use the same database connection configuration as Step 1 |
| NFR-INT-011 | Step 2 shall be invoked after Step 1 completes successfully |

## 4. Data Flow Example

### 4.1 Input: Three Appended Files

**File1.appended:**
```
...,S,101,0^1^2
...,S,102,0^1
...,S,103,0^1^2^3
```

**File2.appended:**
```
...,S,101,0^1^3
...,S,102,0^1^2
...,S,104,0^1
```

**File3.appended:**
```
...,S,101,0^2^3
...,S,102,0^1
...,S,105,0^1
```

### 4.2 Intersection Computation

- File1 question_ids: {101, 102, 103}
- File2 question_ids: {101, 102, 104}
- File3 question_ids: {101, 102, 105}
- **Intersection: {101, 102}**

### 4.3 Answer ID Union

- question_id 101: {0,1,2} ∪ {0,1,3} ∪ {0,2,3} = {0,1,2,3} → "0^1^2^3"
- question_id 102: {0,1} ∪ {0,1,2} ∪ {0,1} = {0,1,2} → "0^1^2"

### 4.4 Output: CommonQuestions.csv

```
common_question_id,master_question_text,common_answer_ids
101,"What is your gender?","0^1^2^3"
102,"What is your age?","0^1^2"
```

## 5. Database Schema

### 5.1 br_question_master Table

| Column | Type | Description |
|--------|------|-------------|
| study_name | VARCHAR | Name of the study |
| question_id | INT | Unique question identifier |
| question_text | TEXT | The master question text |

### 5.2 Query

```sql
SELECT question_text
FROM br_question_master
WHERE study_name = %s
  AND question_id = %s
```

## 6. Assumptions

- All appended files from Step 1 are available and readable
- The study_name is consistent across all control file entries (use first entry's study_name for master_question_text lookup)
- The br_question_master table contains entries for all common question_ids
- Answer IDs are numeric strings that can be sorted numerically
