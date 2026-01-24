# CombineWaves Design Document

## 1. Architecture Overview

CombineWaves follows a simple sequential processing architecture with three main components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Control File   │────>│  Parms File     │────>│  Output File    │
│  Reader         │     │  Processor      │     │  Writer         │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 v
                        ┌─────────────────┐
                        │  Database       │
                        │  Client         │
                        └─────────────────┘
```

## 2. Module Structure

```
CombineWaves/
├── combinewaves.py          # Main entry point
├── control_file.py          # Control file parsing
├── parms_processor.py       # Parms file processing logic
├── database.py              # Database connection and queries
├── answer_mapper.py         # Answer ID mapping algorithm
├── requirements.txt         # Python dependencies
└── WaveFiles/               # Sample data files
```

## 3. Component Design

### 3.1 Main Entry Point (combinewaves.py)

**Responsibilities:**
- Parse command-line arguments
- Orchestrate the processing workflow
- Handle top-level error reporting

**Interface:**
```python
def main(argv: list[str]) -> int:
    """
    Main entry point.

    Args:
        argv: Command-line arguments (sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
```

### 3.2 Control File Reader (control_file.py)

**Responsibilities:**
- Read and parse the control file
- Validate control file format
- Yield control file entries for processing

**Data Structure:**
```python
@dataclass
class ControlEntry:
    study_name: str
    study_date: str
    parms_file_name: str
    pip_file_name: str
```

**Interface:**
```python
def read_control_file(path: str) -> Iterator[ControlEntry]:
    """
    Read and parse the control file.

    Args:
        path: Path to the control file

    Yields:
        ControlEntry for each valid line

    Raises:
        FileNotFoundError: If control file doesn't exist
        ValueError: If a line has invalid format
    """
```

### 3.3 Database Client (database.py)

**Responsibilities:**
- Manage MySQL database connection
- Execute queries against br_question_map table
- Handle connection pooling and error recovery

**Data Structure:**
```python
@dataclass
class QuestionMapRecord:
    question_id: int
    answer_value_map: str
```

**Configuration:**
```python
DB_CONFIG = {
    'host': '50.17.224.19',
    'database': 'ptdb',
    'user': 'root',
    'password': 'L0w_L3v31',
    'charset': 'utf8mb4'
}
```

**Interface:**
```python
class DatabaseClient:
    def __enter__(self) -> 'DatabaseClient':
        """Open database connection."""

    def __exit__(self, *args) -> None:
        """Close database connection."""

    def get_question_map(
        self,
        study_name: str,
        study_date: str,
        question_number: int
    ) -> Optional[QuestionMapRecord]:
        """
        Retrieve question mapping from database.

        Args:
            study_name: Name of the study
            study_date: Date of the study
            question_number: Question number from parms file

        Returns:
            QuestionMapRecord if found, None otherwise
        """
```

**SQL Query:**
```sql
SELECT question_id, answer_value_map
FROM br_question_map
WHERE study_name = %s
  AND study_date = %s
  AND question_number = %s
```

### 3.4 Answer Mapper (answer_mapper.py)

**Responsibilities:**
- Implement the answer ID mapping algorithm
- Handle edge cases (missing values, special characters)

**Algorithm:**
```
Input: answer_value_map = "3^2^?^1^6^7^4^5"
       answer_count = 7

For each answer_number from 1 to answer_count:
    1. Split answer_value_map by "^" into a list
    2. Find the index where answer_number appears (as string)
    3. That index is the answer_id for this answer

Output: answer_ids = "3^1^0^6^7^4^5"
```

**Interface:**
```python
def compute_answer_ids(answer_value_map: str, answer_count: int) -> str:
    """
    Compute answer IDs from the answer value map.

    Args:
        answer_value_map: ^-delimited string from database
        answer_count: Number of answers in the parms file

    Returns:
        ^-delimited string of answer IDs

    Example:
        >>> compute_answer_ids("3^2^?^1^6^7^4^5", 7)
        "3^1^0^6^7^4^5"
    """
```

**Detailed Algorithm Implementation:**
```python
def compute_answer_ids(answer_value_map: str, answer_count: int) -> str:
    # Parse the answer_value_map into a list
    value_map = answer_value_map.split('^')

    answer_ids = []
    for answer_number in range(1, answer_count + 1):
        # Find where this answer_number appears in the value_map
        answer_number_str = str(answer_number)
        try:
            index = value_map.index(answer_number_str)
            answer_ids.append(str(index))
        except ValueError:
            # Answer number not found in map - use empty or error marker
            answer_ids.append('')

    return '^'.join(answer_ids)
```

### 3.5 Parms Processor (parms_processor.py)

**Responsibilities:**
- Read and parse parms CSV files
- Coordinate database lookups for each question
- Generate appended output files

**Data Structure:**
```python
@dataclass
class ParmsRow:
    question_number: int
    total_answers: int
    question_text: str
    empty_field: str
    answers: str          # ^-delimited
    question_type: str    # S, M, or F
    question_id: Optional[int] = None
    answer_ids: Optional[str] = None
```

**Interface:**
```python
def process_parms_file(
    parms_path: str,
    study_name: str,
    study_date: str,
    db_client: DatabaseClient
) -> str:
    """
    Process a parms file and create appended output.

    Args:
        parms_path: Path to the input parms file
        study_name: Study name for database lookup
        study_date: Study date for database lookup
        db_client: Database client instance

    Returns:
        Path to the generated output file

    Raises:
        FileNotFoundError: If parms file doesn't exist
    """
```

## 4. Data Flow

### 4.1 Processing Sequence

```
1. User invokes: python combinewaves.py control_file.txt

2. Main reads control file:
   "StudyA,2026-01-15,WaveFiles/parms.csv,WaveFiles/data.pip"

3. For each control entry:
   a. Open database connection
   b. Read parms file row by row
   c. For each row:
      - Extract question_number from column 1
      - Query database for question_id and answer_value_map
      - Compute answer_ids using mapping algorithm
      - Append question_id and answer_ids to row
   d. Write all rows to output file
   e. Close database connection
```

### 4.2 Answer Mapping Example

```
Parms row:
  question_number = 5
  answers = "American Indian^Asian^Black/African American^East Indian^Hispanic^White^Other"
  (7 answers, numbered 1-7)

Database record:
  answer_value_map = "3^2^?^1^6^7^4^5"

Mapping process:
  Answer 1 -> Find "1" in map -> index 3 -> answer_id = 3
  Answer 2 -> Find "2" in map -> index 1 -> answer_id = 1
  Answer 3 -> Find "3" in map -> index 0 -> answer_id = 0
  Answer 4 -> Find "4" in map -> index 6 -> answer_id = 6
  Answer 5 -> Find "5" in map -> index 7 -> answer_id = 7
  Answer 6 -> Find "6" in map -> index 4 -> answer_id = 4
  Answer 7 -> Find "7" in map -> index 5 -> answer_id = 5

Result:
  answer_ids = "3^1^0^6^7^4^5"
```

## 5. Error Handling Strategy

| Error Condition | Handling Approach |
|-----------------|-------------------|
| Control file not found | Exit with error code 1, print message to stderr |
| Invalid control file line | Log warning, skip line, continue processing |
| Parms file not found | Log error, skip this entry, continue with next |
| Database connection failure | Exit with error code 2, print message to stderr |
| Question not found in database | Log warning, leave question_id and answer_ids empty |
| Answer number not in value_map | Use empty string for that answer_id |
| Output file write failure | Exit with error code 3, print message to stderr |

## 6. Dependencies

**requirements.txt:**
```
PyMySQL==1.1.2
```

## 7. Configuration

Database credentials and connection parameters are defined as constants in `database.py`. For future enhancement, these could be moved to environment variables or a configuration file.

## 8. Testing Strategy

### 8.1 Unit Tests
- `test_answer_mapper.py`: Test mapping algorithm with various inputs
- `test_control_file.py`: Test control file parsing
- `test_parms_processor.py`: Test CSV parsing and row processing

### 8.2 Integration Tests
- Test full workflow with mock database
- Test with sample data in WaveFiles/

### 8.3 Test Cases for Answer Mapping

| Test Case | answer_value_map | answer_count | Expected answer_ids |
|-----------|------------------|--------------|---------------------|
| Basic | "2^1" | 2 | "1^0" |
| With ? | "3^2^?^1" | 3 | "3^1^0" |
| Seven answers | "3^2^?^1^6^7^4^5" | 7 | "3^1^0^6^7^4^5" |
| Missing value | "1^3" | 3 | "0^^1" |

## 9. Future Enhancements

1. **Configuration file support**: Move database credentials to external config
2. **Parallel processing**: Process multiple control entries concurrently
3. **Progress reporting**: Add verbose mode with progress indicators
4. **Dry run mode**: Validate inputs without writing output files
5. **Pip file processing**: The pip_file_name is captured but not currently used
