# CombineWaves Parmedit Modification - Requirements Document

## 1. Overview

This document specifies the requirements for adding parmedit file support to CombineWaves. The parmedit file provides a mapping between parms_question_number (as found in the parms file) and question_number (as used in database queries).

### 1.1 Background

Currently, CombineWaves uses column 1 of the parms file directly as the question_number for database lookups. However, the parms file may use a different numbering scheme (parms_question_number) that does not match the survey's actual question_number. The parmedit file provides the mapping between these two numbering schemes.

### 1.2 Terminology

| Term | Definition |
|------|------------|
| parms_question_number | The question identifier in column 1 of the parms file (e.g., 4, 373, 5, 374...) |
| question_number | The actual survey question number used for database queries (derived from row position in parmedit file) |
| parmedit file | A CSV file that maps parms_question_number to question_number via row position |

## 2. Functional Requirements

### 2.1 Control File Format Changes

| ID | Requirement |
|----|-------------|
| FR-PE-001 | The control file format shall be extended to include a fifth column: `parmedit_file_name` |
| FR-PE-002 | The new control file format shall be: `study_name,study_date,parms_file_name,pip_file_name,parmedit_file_name` |
| FR-PE-003 | The application shall validate that the parmedit file exists before processing |

### 2.2 Parmedit File Processing

| ID | Requirement |
|----|-------------|
| FR-PE-010 | The application shall read the parmedit file specified in the control file |
| FR-PE-011 | The parmedit file shall be parsed as CSV format |
| FR-PE-012 | Only column 1 (parms_question_number) of the parmedit file shall be used |
| FR-PE-013 | The row number (1-based) in the parmedit file represents the corresponding question_number |
| FR-PE-014 | The entire parmedit file shall be loaded into memory for efficient lookups |
| FR-PE-015 | The parmedit file shall be loaded once per control file entry and reused for all parms rows |

### 2.3 Parms File Interpretation Changes

| ID | Requirement |
|----|-------------|
| FR-PE-020 | Column 1 of the parms file shall be interpreted as parms_question_number (not question_number) |
| FR-PE-021 | The application shall look up the question_number by finding the row in the parmedit file where column 1 matches the parms_question_number |
| FR-PE-022 | The question_number shall be the 1-based row number of the matching parmedit row |

### 2.4 Database Query Changes

| ID | Requirement |
|----|-------------|
| FR-PE-030 | The database query shall use the derived question_number (from parmedit lookup) instead of the parms_question_number |
| FR-PE-031 | All other database query parameters (study_name, study_date) shall remain unchanged |

### 2.5 Error Handling

| ID | Requirement |
|----|-------------|
| FR-PE-040 | The application shall report an error if the parmedit file does not exist |
| FR-PE-041 | The application shall report a warning if a parms_question_number is not found in the parmedit file |
| FR-PE-042 | If a parms_question_number is not found in parmedit, the row shall be processed with empty question_id and answer_ids |

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-PE-001 | The parmedit file shall be loaded once per control file entry (not per parms row) |
| NFR-PE-002 | Lookups in the parmedit mapping shall be O(1) using a dictionary/hash map |

### 3.2 Compatibility

| ID | Requirement |
|----|-------------|
| NFR-PE-010 | Existing control files with 4 columns shall no longer be supported (breaking change) |
| NFR-PE-011 | The modification shall not change any existing database access patterns |

## 4. Data Flow Example

### 4.1 Sample Files

**Control file entry:**
```
StudyA,2026-01-15,WaveFiles/CJanuary2026_parms.csv,WaveFiles/CJanuary2026_data.pip,WaveFiles/CJanuary2026_parmedit.csv
```

**Parmedit file (CJanuary2026_parmedit.csv):**
```
4,2,What is your gender?,,Male^Female,X,,,,,
373,5,What is your marital status?,...
5,7,Please tell us which age range you are in:,...
374,7,What is the highest level of formal education...
170,12,Which one of the following categories...
```

**Parms file (CJanuary2026_parms.csv) row:**
```
170,12,Which one of the following categories best describes your current occupation?,...
```

### 4.2 Lookup Process

1. Read parms row with column 1 = `170` (parms_question_number)
2. Search parmedit file for row where column 1 = `170`
3. Found at row 5 (1-based)
4. Use question_number = `5` for database query
5. Query: `SELECT question_id, answer_value_map FROM br_question_map WHERE study_name='StudyA' AND study_date='2026-01-15' AND question_number=5`

## 5. Mapping Logic Summary

```
Parmedit file:
  Row 1: parms_question_number = 4   -> question_number = 1
  Row 2: parms_question_number = 373 -> question_number = 2
  Row 3: parms_question_number = 5   -> question_number = 3
  Row 4: parms_question_number = 374 -> question_number = 4
  Row 5: parms_question_number = 170 -> question_number = 5

When processing parms file:
  Parms column 1 = 170
  Lookup: find parmedit row with column 1 = 170
  Result: row 5
  Use question_number = 5 for database query
```

## 6. Assumptions

- The parmedit file is well-formed CSV
- Each parms_question_number appears at most once in the parmedit file
- The parmedit file is small enough to fit in memory
- All control file entries will have 5 columns (no backwards compatibility with 4-column format)
