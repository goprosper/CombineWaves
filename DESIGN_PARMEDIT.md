# CombineWaves Parmedit Modification - Design Document

## 1. Overview

This document describes the design changes required to add parmedit file support to CombineWaves. The modification introduces an intermediate lookup step that translates parms_question_number to question_number before querying the database.

## 2. Architecture Changes

### 2.1 Updated Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Control File   │────>│  Parmedit File  │────>│  Parms File     │
│  Reader         │     │  Loader         │     │  Processor      │
└─────────────────┘     └────────┬────────┘     └────────┬────────┘
                                 │                       │
                                 v                       v
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Question       │<────│  Database       │
                        │  Number Mapper  │     │  Client         │
                        └─────────────────┘     └─────────────────┘
                                                        │
                                                        v
                                                ┌─────────────────┐
                                                │  Output File    │
                                                │  Writer         │
                                                └─────────────────┘
```

### 2.2 New Component: Parmedit Loader

A new module `parmedit.py` will be added to handle parmedit file loading and lookups.

## 3. Module Changes

### 3.1 New Module: parmedit.py

**Responsibilities:**
- Load and parse the parmedit CSV file
- Build a mapping from parms_question_number to question_number
- Provide O(1) lookup for question_number given parms_question_number

**Data Structure:**
```python
@dataclass
class ParmeditMapper:
    """Maps parms_question_number to question_number."""
    _mapping: dict[int, int]  # parms_question_number -> question_number
```

**Interface:**
```python
def load_parmedit(path: str) -> ParmeditMapper:
    """
    Load parmedit file and create mapper.

    Args:
        path: Path to the parmedit CSV file

    Returns:
        ParmeditMapper instance for lookups

    Raises:
        FileNotFoundError: If parmedit file doesn't exist
        ValueError: If parmedit file format is invalid
    """

class ParmeditMapper:
    def get_question_number(self, parms_question_number: int) -> Optional[int]:
        """
        Look up question_number for a given parms_question_number.

        Args:
            parms_question_number: The question number from parms file column 1

        Returns:
            The question_number (row position in parmedit file), or None if not found
        """
```

**Implementation:**
```python
import csv
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParmeditMapper:
    _mapping: dict[int, int]

    def get_question_number(self, parms_question_number: int) -> Optional[int]:
        return self._mapping.get(parms_question_number)

def load_parmedit(path: str) -> ParmeditMapper:
    mapping = {}
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row_number, row in enumerate(reader, start=1):
            if row:  # Skip empty rows
                parms_question_number = int(row[0])
                mapping[parms_question_number] = row_number
    return ParmeditMapper(_mapping=mapping)
```

### 3.2 Modified Module: control_file.py

**Changes:**
- Update `ControlEntry` dataclass to include `parmedit_file_name`
- Update parsing logic to expect 5 columns

**Updated Data Structure:**
```python
@dataclass
class ControlEntry:
    study_name: str
    study_date: str
    parms_file_name: str
    pip_file_name: str
    parmedit_file_name: str  # NEW FIELD
```

**Updated Parsing:**
```python
def read_control_file(path: str) -> Iterator[ControlEntry]:
    with open(path, 'r') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 5:
                raise ValueError(
                    f"Line {line_num}: Expected 5 columns, got {len(parts)}"
                )
            yield ControlEntry(
                study_name=parts[0],
                study_date=parts[1],
                parms_file_name=parts[2],
                pip_file_name=parts[3],
                parmedit_file_name=parts[4]  # NEW
            )
```

### 3.3 Modified Module: parms_processor.py

**Changes:**
- Accept `ParmeditMapper` as a parameter
- Use mapper to translate parms_question_number to question_number
- Update field naming for clarity

**Updated Interface:**
```python
def process_parms_file(
    parms_path: str,
    study_name: str,
    study_date: str,
    db_client: DatabaseClient,
    parmedit_mapper: ParmeditMapper  # NEW PARAMETER
) -> str:
    """
    Process a parms file and create appended output.

    Args:
        parms_path: Path to the input parms file
        study_name: Study name for database lookup
        study_date: Study date for database lookup
        db_client: Database client instance
        parmedit_mapper: Mapper for parms_question_number to question_number

    Returns:
        Path to the generated output file
    """
```

**Updated Processing Logic:**
```python
def process_parms_file(..., parmedit_mapper: ParmeditMapper) -> str:
    # ... existing setup code ...

    for row in reader:
        parms_question_number = int(row[0])  # Column 1 is now parms_question_number

        # NEW: Look up question_number from parmedit mapper
        question_number = parmedit_mapper.get_question_number(parms_question_number)

        if question_number is None:
            print(f"Warning: parms_question_number {parms_question_number} not found in parmedit",
                  file=sys.stderr)
            question_id = ''
            answer_ids = ''
        else:
            # Query database using derived question_number
            record = db_client.get_question_map(study_name, study_date, question_number)
            # ... rest of existing logic ...
```

### 3.4 Modified Module: combinewaves.py

**Changes:**
- Load parmedit file before processing parms file
- Pass parmedit mapper to parms processor

**Updated Main Logic:**
```python
from parmedit import load_parmedit

def main(argv: list[str]) -> int:
    # ... existing argument parsing ...

    for entry in read_control_file(control_path):
        # NEW: Load parmedit file
        parmedit_mapper = load_parmedit(entry.parmedit_file_name)

        with DatabaseClient() as db:
            output_path = process_parms_file(
                entry.parms_file_name,
                entry.study_name,
                entry.study_date,
                db,
                parmedit_mapper  # NEW ARGUMENT
            )
        print(f"Created: {output_path}")

    return 0
```

## 4. Updated Module Structure

```
CombineWaves/
├── combinewaves.py          # Main entry point (modified)
├── control_file.py          # Control file parsing (modified)
├── parmedit.py              # NEW: Parmedit file loading and mapping
├── parms_processor.py       # Parms file processing (modified)
├── database.py              # Database connection (unchanged)
├── answer_mapper.py         # Answer ID mapping (unchanged)
├── requirements.txt         # Python dependencies (unchanged)
└── WaveFiles/               # Sample data files
```

## 5. Data Flow Example

### 5.1 Processing Sequence

```
1. User invokes: python combinewaves.py control_file.txt

2. Main reads control file:
   "StudyA,2026-01-15,WaveFiles/parms.csv,WaveFiles/data.pip,WaveFiles/parmedit.csv"

3. For each control entry:
   a. Load parmedit file into memory as ParmeditMapper
      - Row 1: parms_qn=4   -> qn=1
      - Row 2: parms_qn=373 -> qn=2
      - Row 3: parms_qn=5   -> qn=3
      - ...

   b. Open database connection

   c. Read parms file row by row:
      - Extract parms_question_number from column 1
      - Look up question_number via ParmeditMapper
      - Query database using question_number (not parms_question_number)
      - Compute answer_ids using mapping algorithm
      - Append question_id and answer_ids to row

   d. Write all rows to output file
   e. Close database connection
```

### 5.2 Concrete Example

**Input parms row:**
```
170,12,"Which one of the following categories best describes your current occupation?",...
```

**Parmedit lookup:**
```
parms_question_number = 170
Find in parmedit: row where column 1 = 170
Result: row 5
question_number = 5
```

**Database query:**
```sql
SELECT question_id, answer_value_map
FROM br_question_map
WHERE study_name = 'StudyA'
  AND study_date = '2026-01-15'
  AND question_number = 5
```

## 6. Error Handling

| Error Condition | Handling Approach |
|-----------------|-------------------|
| Parmedit file not found | Exit with error code, print message to stderr |
| Invalid parmedit CSV format | Exit with error code, print message to stderr |
| parms_question_number not in parmedit | Log warning, write empty question_id and answer_ids |
| Non-integer in parmedit column 1 | Skip row with warning, continue processing |

## 7. Testing Strategy

### 7.1 New Unit Tests: test_parmedit.py

| Test Case | Description |
|-----------|-------------|
| test_load_basic | Load parmedit file and verify mapping created |
| test_lookup_found | Look up existing parms_question_number, verify correct question_number |
| test_lookup_not_found | Look up missing parms_question_number, verify None returned |
| test_empty_file | Load empty parmedit file, verify empty mapping |
| test_file_not_found | Attempt to load non-existent file, verify FileNotFoundError |

### 7.2 Updated Integration Tests

| Test Case | Description |
|-----------|-------------|
| test_full_workflow_with_parmedit | Process control file with parmedit, verify correct question_numbers used |
| test_parmedit_mapping_correct | Verify database receives question_number (not parms_question_number) |

### 7.3 Test Data

**test_parmedit.csv:**
```
4,2,What is your gender?,,Male^Female,X
373,5,What is your marital status?,...
5,7,Please tell us which age range you are in:,...
```

**Expected mapping:**
- `4 -> 1`
- `373 -> 2`
- `5 -> 3`

## 8. Migration Notes

### 8.1 Breaking Changes

- Control files must now have 5 columns (previously 4)
- Column 1 of parms file is now interpreted as parms_question_number

### 8.2 Required Actions

1. Update all existing control files to add parmedit_file_name column
2. Ensure parmedit files exist for all studies
3. Verify parmedit files correctly map parms_question_number to question_number
