# CombineWaves Step 2 - Compute Intersection: Design Document

## 1. Architecture Overview

Step 2 adds a new processing phase after the existing parms file processing. It reads all appended files, computes the intersection of question_ids, and generates a consolidated CommonQuestions.csv file.

### 1.1 Updated Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Step 1:        │────>│  Appended       │────>│  Step 2:        │
│  Process Parms  │     │  Files          │     │  Intersection   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         v
                                                ┌─────────────────┐
                                                │  CommonQuestions│
                                                │  .csv           │
                                                └─────────────────┘
```

### 1.2 Step 2 Internal Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Appended File  │────>│  Question ID    │────>│  Answer ID      │
│  Reader         │     │  Intersection   │     │  Union          │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │  Database       │<─────────────┘
                        │  (question_text)│
                        └────────┬────────┘
                                 │
                                 v
                        ┌─────────────────┐
                        │  CSV Writer     │
                        └─────────────────┘
```

## 2. Module Structure

### 2.1 New Module

```
CombineWaves/
├── ...existing files...
├── intersection.py          # NEW: Intersection computation logic
└── ...
```

### 2.2 Modified Modules

- **combinewaves.py**: Add Step 2 invocation after Step 1 completes
- **database.py**: Add method to query br_question_master for question_text

## 3. Component Design

### 3.1 Intersection Module (intersection.py)

**Responsibilities:**
- Read appended files and extract question_id/answer_ids
- Compute intersection of question_ids across all files
- Compute union of answer_ids for each common question
- Query database for master_question_text
- Write CommonQuestions.csv output

**Data Structures:**

```python
@dataclass
class QuestionAnswers:
    """Holds answer_ids for a question from a single file."""
    question_id: int
    answer_ids: set[int]

@dataclass
class CommonQuestion:
    """Represents a question common to all files."""
    question_id: int
    master_question_text: str
    common_answer_ids: list[int]  # sorted
```

**Interface:**

```python
def read_appended_file(path: str) -> dict[int, set[int]]:
    """
    Read an appended file and extract question_id -> answer_ids mapping.

    Args:
        path: Path to the appended file

    Returns:
        Dictionary mapping question_id to set of answer_ids
    """

def compute_intersection(
    file_data: list[dict[int, set[int]]]
) -> dict[int, set[int]]:
    """
    Compute intersection of question_ids and union of answer_ids.

    Args:
        file_data: List of question_id -> answer_ids mappings (one per file)

    Returns:
        Dictionary mapping common question_ids to union of answer_ids
    """

def generate_common_questions(
    appended_files: list[str],
    study_name: str,
    db_client: DatabaseClient,
    output_path: str
) -> str:
    """
    Generate CommonQuestions.csv from appended files.

    Args:
        appended_files: List of paths to appended files
        study_name: Study name for database lookup
        db_client: Database client instance
        output_path: Path for output file

    Returns:
        Path to generated file
    """
```

### 3.2 Database Client Extension (database.py)

**New Method:**

```python
def get_question_text(
    self,
    study_name: str,
    question_id: int
) -> Optional[str]:
    """
    Retrieve question text from br_question_master.

    Args:
        study_name: Name of the study
        question_id: Question ID

    Returns:
        Question text if found, None otherwise
    """
```

**SQL Query:**

```sql
SELECT question_text
FROM br_question_master
WHERE study_name = %s
  AND question_id = %s
```

### 3.3 Main Module Update (combinewaves.py)

**Changes:**
- After processing all control file entries, invoke Step 2
- Collect list of appended file paths
- Call `generate_common_questions()` with collected paths

```python
def main(argv: List[str]) -> int:
    # ... existing Step 1 code ...

    # Collect appended file paths
    appended_files = [f"{entry.parms_file_name}.appended" for entry in entries]

    # Step 2: Compute intersection
    if success_count > 0:
        study_name = entries[0].study_name  # Use first entry's study_name
        with DatabaseClient() as db:
            output_path = generate_common_questions(
                appended_files,
                study_name,
                db,
                "CommonQuestions.csv"
            )
            print(f"Created: {output_path}")

    return 0 if error_count == 0 else 1
```

## 4. Algorithm Details

### 4.1 Reading Appended Files

```python
def read_appended_file(path: str) -> dict[int, set[int]]:
    result = {}
    with open(path, 'r', encoding='latin-1', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 8:
                continue
            question_id_str = row[6]
            answer_ids_str = row[7]

            if not question_id_str:
                continue

            question_id = int(question_id_str)
            answer_ids = set()

            if answer_ids_str:
                for aid in answer_ids_str.split('^'):
                    if aid.strip().isdigit():
                        answer_ids.add(int(aid.strip()))

            if question_id in result:
                result[question_id].update(answer_ids)
            else:
                result[question_id] = answer_ids

    return result
```

### 4.2 Computing Intersection

```python
def compute_intersection(
    file_data: list[dict[int, set[int]]]
) -> dict[int, set[int]]:
    if not file_data:
        return {}

    # Get question_ids from each file
    question_id_sets = [set(fd.keys()) for fd in file_data]

    # Compute intersection of question_ids
    common_ids = question_id_sets[0]
    for qid_set in question_id_sets[1:]:
        common_ids = common_ids.intersection(qid_set)

    # For each common question_id, compute union of answer_ids
    result = {}
    for qid in common_ids:
        all_answers = set()
        for fd in file_data:
            all_answers.update(fd[qid])
        result[qid] = all_answers

    return result
```

### 4.3 Generating Output

```python
def generate_common_questions(
    appended_files: list[str],
    study_name: str,
    db_client: DatabaseClient,
    output_path: str
) -> str:
    # Read all appended files
    file_data = []
    for path in appended_files:
        file_data.append(read_appended_file(path))

    # Compute intersection
    common_questions = compute_intersection(file_data)

    if not common_questions:
        print("Warning: No common questions found across all files",
              file=sys.stderr)
        # Still create empty file
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
        return output_path

    # Build output rows
    rows = []
    for qid in sorted(common_questions.keys()):
        # Get master question text from database
        question_text = db_client.get_question_text(study_name, qid)
        if question_text is None:
            print(f"Warning: No question_text found for question_id {qid}",
                  file=sys.stderr)
            question_text = ''

        # Sort answer_ids and format
        sorted_aids = sorted(common_questions[qid])
        answer_ids_str = '^'.join(str(aid) for aid in sorted_aids)

        rows.append([qid, question_text, answer_ids_str])

    # Write output file
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
        writer.writerows(rows)

    return output_path
```

## 5. Error Handling

| Error Condition | Handling Approach |
|-----------------|-------------------|
| Appended file not found | Log error, skip file, continue with remaining files |
| No appended files available | Log error, skip Step 2 |
| Empty intersection | Log warning, create empty CommonQuestions.csv with header only |
| Question text not found | Log warning, use empty string |
| Invalid answer_id format | Skip that answer_id, continue processing |

## 6. Output File Format

### 6.1 CommonQuestions.csv

```csv
common_question_id,master_question_text,common_answer_ids
1,"What is your gender?","0^1"
3,"Please tell us which age range you are in:","0^1^2^3^4^5^6"
69,"What year were you born?","0^1^2^3^...^77"
```

### 6.2 Column Specifications

| Column | Type | Description |
|--------|------|-------------|
| common_question_id | Integer | Question ID common to all files |
| master_question_text | String | Question text from br_question_master (may be quoted if contains commas) |
| common_answer_ids | String | ^-delimited list of answer IDs, sorted numerically |

## 7. Testing Strategy

### 7.1 Unit Tests (test_intersection.py)

| Test Case | Description |
|-----------|-------------|
| test_read_appended_file | Read file and verify question_id/answer_ids extraction |
| test_read_appended_file_missing_qid | Verify rows with empty question_id are skipped |
| test_compute_intersection_basic | Three files with overlapping questions |
| test_compute_intersection_no_common | Files with no common questions |
| test_compute_intersection_empty | Empty file list |
| test_answer_id_union | Verify union of answer_ids computed correctly |
| test_answer_id_sorting | Verify answer_ids are sorted numerically |
| test_generate_common_questions | End-to-end test with mock database |

### 7.2 Integration Tests

| Test Case | Description |
|-----------|-------------|
| test_full_workflow | Run Step 1 and Step 2, verify CommonQuestions.csv |
| test_with_real_appended_files | Use actual appended files from WaveFiles/ |

## 8. Future Considerations

1. **Output location**: Currently hardcoded to `CommonQuestions.csv` in working directory; could be configurable
2. **Multiple study names**: Current design uses first entry's study_name; may need enhancement if studies differ
3. **Progress reporting**: Add verbose mode to report processing progress for large file sets
