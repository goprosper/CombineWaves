# CombineWaves Implementation Plan

## Overview

This document outlines the implementation plan for CombineWaves, organized into phases with specific tasks, dependencies, and acceptance criteria.

## Phase 1: Project Setup

### Task 1.1: Create requirements.txt
**File:** `requirements.txt`

**Content:**
```
PyMySQL==1.1.2
```

**Acceptance Criteria:**
- [ ] File exists with correct PyMySQL version
- [ ] `pip install -r requirements.txt` succeeds

### Task 1.2: Create project structure
**Action:** Create empty module files

**Files to create:**
- `combinewaves.py`
- `control_file.py`
- `database.py`
- `answer_mapper.py`
- `parms_processor.py`

**Acceptance Criteria:**
- [ ] All module files exist
- [ ] Each file can be imported without errors

---

## Phase 2: Core Algorithm Implementation

### Task 2.1: Implement answer_mapper.py
**Dependencies:** None

**Implementation:**
```python
def compute_answer_ids(answer_value_map: str, answer_count: int) -> str:
    """
    Compute answer IDs by finding each answer number's position in the value map.
    """
    value_map = answer_value_map.split('^')

    answer_ids = []
    for answer_number in range(1, answer_count + 1):
        answer_number_str = str(answer_number)
        try:
            index = value_map.index(answer_number_str)
            answer_ids.append(str(index))
        except ValueError:
            answer_ids.append('')

    return '^'.join(answer_ids)
```

**Test Cases:**
| Input (map, count) | Expected Output |
|--------------------|-----------------|
| `("2^1", 2)` | `"1^0"` |
| `("3^2^?^1", 3)` | `"3^1^0"` |
| `("3^2^?^1^6^7^4^5", 7)` | `"3^1^0^6^7^4^5"` |
| `("1^3", 3)` | `"0^^1"` |
| `("", 0)` | `""` |

**Acceptance Criteria:**
- [ ] Function handles standard mappings correctly
- [ ] Function handles `?` placeholder in value map
- [ ] Function handles missing answer numbers gracefully
- [ ] Function handles empty inputs
- [ ] All test cases pass

---

## Phase 3: Data Layer Implementation

### Task 3.1: Implement control_file.py
**Dependencies:** None

**Data Structure:**
```python
from dataclasses import dataclass

@dataclass
class ControlEntry:
    study_name: str
    study_date: str
    parms_file_name: str
    pip_file_name: str
```

**Function:**
```python
def read_control_file(path: str) -> Iterator[ControlEntry]:
    # Open file, parse each line as CSV
    # Skip empty lines
    # Yield ControlEntry for valid lines
    # Raise ValueError for malformed lines
```

**Acceptance Criteria:**
- [ ] Parses valid control file lines correctly
- [ ] Skips empty lines
- [ ] Raises FileNotFoundError for missing files
- [ ] Raises ValueError for lines with wrong number of fields
- [ ] Handles lines with whitespace

### Task 3.2: Implement database.py
**Dependencies:** Task 1.1 (requirements.txt)

**Data Structure:**
```python
from dataclasses import dataclass

@dataclass
class QuestionMapRecord:
    question_id: int
    answer_value_map: str
```

**Class:**
```python
class DatabaseClient:
    DB_CONFIG = {
        'host': '50.17.224.19',
        'database': 'ptdb',
        'user': 'root',
        'password': 'L0w_L3v31',
        'charset': 'utf8mb4'
    }

    def __enter__(self) -> 'DatabaseClient':
        # Connect to MySQL using PyMySQL

    def __exit__(self, *args) -> None:
        # Close connection

    def get_question_map(
        self,
        study_name: str,
        study_date: str,
        question_number: int
    ) -> Optional[QuestionMapRecord]:
        # Execute query, return record or None
```

**SQL Query:**
```sql
SELECT question_id, answer_value_map
FROM br_question_map
WHERE study_name = %s
  AND study_date = %s
  AND question_number = %s
```

**Acceptance Criteria:**
- [ ] Context manager properly opens/closes connection
- [ ] Query returns QuestionMapRecord for existing records
- [ ] Query returns None for non-existent records
- [ ] Handles connection errors gracefully
- [ ] Uses parameterized queries (no SQL injection)

---

## Phase 4: Processing Logic Implementation

### Task 4.1: Implement parms_processor.py
**Dependencies:** Task 2.1, Task 3.2

**Function:**
```python
def process_parms_file(
    parms_path: str,
    study_name: str,
    study_date: str,
    db_client: DatabaseClient
) -> str:
    # 1. Read parms CSV file
    # 2. For each row:
    #    a. Extract question_number (col 1) and total_answers (col 2)
    #    b. Query database for question_id and answer_value_map
    #    c. Compute answer_ids using answer_mapper
    #    d. Append question_id and answer_ids to row
    # 3. Write all rows to output file
    # 4. Return output file path
```

**Key Implementation Details:**
- Use Python's `csv` module for proper CSV parsing
- Handle quoted fields containing commas
- Write to temporary file first, then rename (atomic write)
- Output filename: `{parms_path}.appended`

**Acceptance Criteria:**
- [ ] Reads CSV files correctly including quoted fields
- [ ] Appends question_id as column 7
- [ ] Appends answer_ids as column 8
- [ ] Preserves original data exactly
- [ ] Creates output file with `.appended` suffix
- [ ] Handles missing database records (empty columns 7-8)
- [ ] Does not create partial files on error

---

## Phase 5: Main Entry Point Implementation

### Task 5.1: Implement combinewaves.py
**Dependencies:** Task 3.1, Task 3.2, Task 4.1

**Structure:**
```python
import sys
from control_file import read_control_file
from database import DatabaseClient
from parms_processor import process_parms_file

def main(argv: list[str]) -> int:
    # 1. Validate command-line arguments
    if len(argv) != 1:
        print("Usage: python combinewaves.py <control_file>", file=sys.stderr)
        return 1

    control_path = argv[0]

    # 2. Read control file
    try:
        entries = list(read_control_file(control_path))
    except FileNotFoundError:
        print(f"Error: Control file not found: {control_path}", file=sys.stderr)
        return 1

    # 3. Process each entry
    for entry in entries:
        try:
            with DatabaseClient() as db:
                output_path = process_parms_file(
                    entry.parms_file_name,
                    entry.study_name,
                    entry.study_date,
                    db
                )
                print(f"Created: {output_path}")
        except Exception as e:
            print(f"Error processing {entry.parms_file_name}: {e}", file=sys.stderr)
            continue

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

**Acceptance Criteria:**
- [ ] Accepts control file path as command-line argument
- [ ] Prints usage message when no argument provided
- [ ] Exits with code 1 for missing control file
- [ ] Processes all entries in control file
- [ ] Continues processing after individual entry errors
- [ ] Prints created output file paths to stdout
- [ ] Prints errors to stderr
- [ ] Returns 0 on success

---

## Phase 6: Testing

### Task 6.1: Create test control file
**File:** `WaveFiles/test_control.txt`

**Content:**
```
TestStudy,2026-01-15,WaveFiles/CJanuary2026_parms.csv,WaveFiles/CJanuary2026_data.pip
```

### Task 6.2: Manual integration test
**Steps:**
1. Ensure database is accessible
2. Run: `python combinewaves.py WaveFiles/test_control.txt`
3. Verify `WaveFiles/CJanuary2026_parms.csv.appended` is created
4. Verify output has 8 columns
5. Verify question_ids and answer_ids are populated

### Task 6.3: Unit tests (optional)
**Files:**
- `tests/test_answer_mapper.py`
- `tests/test_control_file.py`

---

## Implementation Order

```
Phase 1: Project Setup
    └── Task 1.1: requirements.txt
    └── Task 1.2: Project structure

Phase 2: Core Algorithm
    └── Task 2.1: answer_mapper.py

Phase 3: Data Layer (can be parallel)
    ├── Task 3.1: control_file.py
    └── Task 3.2: database.py

Phase 4: Processing Logic
    └── Task 4.1: parms_processor.py
        (depends on 2.1, 3.2)

Phase 5: Main Entry Point
    └── Task 5.1: combinewaves.py
        (depends on 3.1, 3.2, 4.1)

Phase 6: Testing
    └── Task 6.1-6.3: Testing
        (depends on 5.1)
```

---

## Dependency Graph

```
requirements.txt (1.1)
        │
        v
database.py (3.2) ◄──────────────────┐
        │                            │
        v                            │
answer_mapper.py (2.1)               │
        │                            │
        v                            │
parms_processor.py (4.1) ────────────┤
        │                            │
        v                            │
control_file.py (3.1) ───────────────┤
        │                            │
        v                            │
combinewaves.py (5.1) ◄──────────────┘
        │
        v
    Testing (6.x)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Database connectivity issues | Test connection early in Phase 3; have fallback test data |
| CSV parsing edge cases | Use Python's csv module; test with actual parms file |
| Answer mapping logic errors | Implement comprehensive unit tests in Phase 2 |
| MySQL version compatibility | Verify PyMySQL 1.1.2 works with MySQL 5.1.44 early |

---

## Definition of Done

The implementation is complete when:
1. All module files are implemented per design specifications
2. `python combinewaves.py <control_file>` runs without errors
3. Output files are generated with correct format
4. Question IDs and answer IDs are correctly populated
5. Error conditions are handled gracefully
6. Code follows Python best practices (type hints, docstrings)
