# CombineWaves Requirements Document

## 1. Overview

CombineWaves is a Python command-line tool that processes survey parameter files by enriching them with database identifiers. The tool reads question/answer mappings from CSV files and appends corresponding question IDs and answer IDs by querying a MySQL database.

## 2. Functional Requirements

### 2.1 Command-Line Interface

| ID | Requirement |
|----|-------------|
| FR-001 | The application shall accept a single command-line argument specifying the path to a control file |
| FR-002 | The application shall display an error message and exit if no control file path is provided |
| FR-003 | The application shall display an error message and exit if the control file does not exist |

### 2.2 Control File Processing

| ID | Requirement |
|----|-------------|
| FR-010 | The application shall read a text control file containing one or more lines |
| FR-011 | Each control file line shall be parsed as comma-separated values in the format: `study_name,study_date,parms_file_name,pip_file_name` |
| FR-012 | The application shall process each line in the control file sequentially |
| FR-013 | The application shall skip empty lines in the control file |
| FR-014 | The application shall report errors for malformed control file lines and continue processing remaining lines |

### 2.3 Parms File Processing

| ID | Requirement |
|----|-------------|
| FR-020 | The application shall read each parms file specified in the control file |
| FR-021 | The application shall parse the parms file as CSV with the following column layout: |
|        | - Column 1: Question number |
|        | - Column 2: Total answers |
|        | - Column 3: Question text |
|        | - Column 4: Empty |
|        | - Column 5: ^-delimited list of answers |
|        | - Column 6: Question type (S=single, M=multiple, F=free-form) |
| FR-022 | The application shall process each row in the parms file |
| FR-023 | The application shall handle quoted fields containing commas in the CSV |

### 2.4 Database Query Requirements

| ID | Requirement |
|----|-------------|
| FR-030 | The application shall connect to the MySQL database at 50.17.224.19, database `ptdb` |
| FR-031 | For each question in the parms file, the application shall query the `br_question_map` table using study_name, study_date, and question_number |
| FR-032 | The application shall retrieve the `question_id` and `answer_value_map` fields from the query result |
| FR-033 | The application shall handle cases where no matching database record is found |

### 2.5 Answer ID Mapping

| ID | Requirement |
|----|-------------|
| FR-040 | The application shall compute answer_ids by mapping answer positions to database indices |
| FR-041 | Each answer in the parms file answer list shall be assigned a 1-based position number (answer_number) |
| FR-042 | For each answer_number, the application shall find its position (0-based index) in the answer_value_map |
| FR-043 | The resulting answer_ids shall be formatted as a ^-delimited list |
| FR-044 | The application shall handle the special character `?` in answer_value_map (representing position 0) |

### 2.6 Output File Generation

| ID | Requirement |
|----|-------------|
| FR-050 | The application shall create an output file named `{parms_file_name}.appended` |
| FR-051 | The output file shall contain all original columns from the parms file |
| FR-052 | Column 7 shall contain the question_id from the database |
| FR-053 | Column 8 shall contain the computed answer_ids |
| FR-054 | The output file shall maintain CSV format with proper quoting |

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-001 | The application shall process parms files with up to 500 questions |
| NFR-002 | Database connections shall be reused across queries within a single control file line |

### 3.2 Reliability

| ID | Requirement |
|----|-------------|
| NFR-010 | The application shall gracefully handle database connection failures |
| NFR-011 | The application shall not create partial output files on error |
| NFR-012 | The application shall log errors to stderr |

### 3.3 Compatibility

| ID | Requirement |
|----|-------------|
| NFR-020 | The application shall run on Python 3.8 or higher |
| NFR-021 | The application shall use PyMySQL version 1.1.2 for MySQL 5.1.44 compatibility |

## 4. Constraints

- The MySQL database runs version 5.1.44, requiring specific driver compatibility
- The parms file uses `^` as a delimiter within the answers field (column 5)
- The answer_value_map in the database also uses `^` as a delimiter

## 5. Assumptions

- The control file, parms files, and pip files are accessible from the local filesystem
- Database credentials are static and can be embedded in the application
- The br_question_map table contains valid data for all questions in the parms files
- Study names and dates in the control file match entries in the database

## 6. Example Data Flow

**Input (parms file row):**
```
4,2,What is your gender?,,Male^Female,S
```

**Database query result:**
```
question_id: 1234
answer_value_map: 2^1
```

**Output (appended row):**
```
4,2,What is your gender?,,Male^Female,S,1234,2^1
```

**Mapping explanation:**
- Answer 1 (Male) -> Find "1" in answer_value_map -> Index 1 -> answer_id = 1
- Answer 2 (Female) -> Find "2" in answer_value_map -> Index 0 -> answer_id = 0
- Result: answer_ids = "1^0"
