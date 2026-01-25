# Design: Generate Common Parms (Step 4)

## Architecture

### Module Structure

```
generate_common_parms.py     # New module for Step 4 logic
database.py                  # Add get_question_master() method
combinewaves.py              # Add Step 4 invocation
test_generate_common_parms.py # Unit tests
```

## Database Changes

### New Method: DatabaseClient.get_question_master()

```python
@dataclass
class QuestionMasterRecord:
    """Represents a record from br_question_master table."""
    alternate_text: str
    answer_text: str

def get_question_master(
    self,
    study_name: str,
    question_id: int
) -> Optional[QuestionMasterRecord]:
    """
    Retrieve question master data for generating CommonParms.

    Args:
        study_name: Name of the study
        question_id: Question ID (common_question_id)

    Returns:
        QuestionMasterRecord with alternate_text and answer_text
    """
    sql = """
        SELECT alternate_text, answer_text
        FROM br_question_master
        WHERE study_name = %s
          AND question_id = %s
    """
```

## New Module: generate_common_parms.py

### Data Structures

```python
@dataclass
class CommonQuestion:
    """Parsed row from CommonQuestions.csv."""
    common_question_id: int
    master_question_text: str
    common_answer_ids: List[int]
    parms_question_type: str

@dataclass
class ParmsRow:
    """Row for CommonParms.csv output."""
    question_number: int
    total_answers: int
    question_text: str
    answer_text_list: str
    question_type: str
```

### Functions

#### load_common_questions_for_parms()
```python
def load_common_questions_for_parms(
    filepath: str
) -> List[CommonQuestion]:
    """
    Load CommonQuestions.csv for parms generation.

    Parses each row into CommonQuestion dataclass.
    Skips header row.
    """
```

#### transform_answer_ids_to_text()
```python
def transform_answer_ids_to_text(
    common_answer_ids: List[int],
    answer_text_map: str
) -> str:
    """
    Transform common_answer_ids to answer_text_list.

    Args:
        common_answer_ids: List of answer indices [0, 1, 2]
        answer_text_map: ^-delimited answer texts from DB

    Returns:
        ^-delimited answer_text_list

    Example:
        common_answer_ids = [0, 1]
        answer_text_map = "Male^Female"
        returns "Male^Female"

        common_answer_ids = [1, 0]
        answer_text_map = "Male^Female"
        returns "Female^Male"
    """
```

#### generate_common_parms()
```python
def generate_common_parms(
    common_questions_path: str,
    study_name: str,
    db: DatabaseClient,
    output_path: str = "CommonParms.csv"
) -> str:
    """
    Generate CommonParms.csv from CommonQuestions.csv.

    Args:
        common_questions_path: Path to CommonQuestions.csv
        study_name: Study name for database queries
        db: Database client instance
        output_path: Output file path

    Returns:
        Path to generated file

    Algorithm:
        1. Load CommonQuestions.csv
        2. For each row (question_number = 1, 2, 3...):
            a. Query br_question_master for alternate_text, answer_text
            b. Transform common_answer_ids using answer_text
            c. Build ParmsRow
        3. Write CSV output (no header)
    """
```

## Integration: combinewaves.py

### Step 4 Addition

```python
# Step 4: Generate common parms file
if os.path.exists("CommonQuestions.csv"):
    print("\nStep 4: Generating common parms...")
    try:
        parms_output = generate_common_parms(
            "CommonQuestions.csv",
            study_name,
            db,
            "CommonParms.csv"
        )
        print(f"Created: {parms_output}")
    except Exception as e:
        report.error("Step4Error", f"Error in Step 4: {e}")
        error_count += 1
```

## Output Format

### CommonParms.csv Example

```csv
1,0,Zip:,,,F
2,2,What is your gender?,,Male^Female,S
3,7,Please tell us which age range you are in:,,14-17^18-24^25-34^35-44^45-54^55-64^65+,S
```

## Error Handling

| Scenario | Action |
|----------|--------|
| question_id not in br_question_master | Log warning, use master_question_text as fallback, empty answer_text_list |
| Empty common_answer_ids | Set total_answers=0, answer_text_list="" |
| Database connection error | Propagate exception to caller |
| CommonQuestions.csv not found | Propagate FileNotFoundError |

## Testing Strategy

1. **Unit tests** for each function in generate_common_parms.py
2. **Mock database** for isolated testing
3. **Integration test** with real CommonQuestions.csv (mocked DB)
4. **Edge cases**: empty answers, missing DB records, type F questions
