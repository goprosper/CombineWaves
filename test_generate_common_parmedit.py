"""Tests for generate_common_parmedit module."""

import csv
import os
import tempfile
from io import StringIO

import pytest

from generate_common_parmedit import (
    CommonParmsRow,
    ParmeditAppendedRow,
    CommonParmeditRow,
    load_common_parms,
    load_parmedit_appended_full,
    get_most_recent_parmedit_appended,
    translate_reference_answers,
    generate_common_parmedit,
    load_common_questions_answer_ids,
    load_appended_answer_ids,
)


class TestLoadCommonParms:
    """Tests for load_common_parms function."""

    def test_load_basic(self):
        """Load file with multiple rows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonParms.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'What is your gender?', '', 'Male^Female', 'S', 101])
                writer.writerow([2, 5, 'What is your age?', '', '18-24^25-34^35-44^45-54^55+', 'S', 102])
                writer.writerow([3, 0, 'Enter your zip code:', '', '', 'F', 103])

            result = load_common_parms(filepath)

            assert len(result) == 3

            assert result[0].question_number == 1
            assert result[0].total_answers == 2
            assert result[0].question_text == 'What is your gender?'
            assert result[0].answer_list == 'Male^Female'
            assert result[0].question_type == 'S'
            assert result[0].common_question_id == 101

            assert result[1].question_number == 2
            assert result[1].total_answers == 5
            assert result[1].question_text == 'What is your age?'
            assert result[1].common_question_id == 102

            assert result[2].question_number == 3
            assert result[2].total_answers == 0
            assert result[2].question_type == 'F'
            assert result[2].common_question_id == 103

    def test_load_includes_study_date_row(self):
        """Handle last Study Date row by including it with None common_question_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonParms.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'What is your gender?', '', 'Male^Female', 'S', 101])
                writer.writerow([2, 0, 'Study Date', '', '', 'F', ''])  # Study Date row

            result = load_common_parms(filepath)

            # Should have 2 rows - Study Date row included
            assert len(result) == 2
            assert result[0].question_text == 'What is your gender?'
            assert result[0].common_question_id == 101
            assert result[1].question_text == 'Study Date'
            assert result[1].common_question_id is None

    def test_load_handles_missing_columns(self):
        """Graceful handling of rows with fewer columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonParms.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Full row
                writer.writerow([1, 2, 'Full question', '', 'Yes^No', 'S', 101])
                # Row with only 6 columns (missing common_question_id)
                writer.writerow([2, 3, 'Short row', '', 'A^B^C', 'M'])
                # Row with too few columns (should be skipped)
                writer.writerow([3, 2, 'Too short', '', ''])

            result = load_common_parms(filepath)

            assert len(result) == 2

            # First row - full data
            assert result[0].question_number == 1
            assert result[0].common_question_id == 101

            # Second row - missing common_question_id
            assert result[1].question_number == 2
            assert result[1].question_text == 'Short row'
            assert result[1].common_question_id is None  # Missing, so None

    def test_load_file_not_found(self):
        """Verify FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_common_parms("/nonexistent/path/CommonParms.csv")


class TestLoadParmeditAppendedFull:
    """Tests for load_parmedit_appended_full function."""

    def test_load_basic(self):
        """Load with all 13 columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # 13 columns: parms_qn, total_ans, qtext, empty, answer_list, qtype,
                #             special_code, special_values, reserved, ref_parms_qn,
                #             ref_answers, question_number, question_id
                writer.writerow([1, 2, 'Gender question', '', 'Male^Female', 'S',
                               '', '', '', '', '', 101, 1001])
                writer.writerow([2, 5, 'Age question', '', '18-24^25-34^35-44^45-54^55+', 'S',
                               '', '', '', '', '', 102, 1002])

            result = load_parmedit_appended_full(filepath)

            assert len(result) == 2

            assert result[0].parms_question_number == 1
            assert result[0].total_answers == 2
            assert result[0].question_text == 'Gender question'
            assert result[0].answer_list == 'Male^Female'
            assert result[0].question_type == 'S'
            assert result[0].question_number == 101
            assert result[0].question_id == 1001

            assert result[1].parms_question_number == 2
            assert result[1].question_id == 1002

    def test_load_variable_columns(self):
        """Handle rows with fewer columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # Full 13 columns
                writer.writerow([1, 2, 'Full row', '', 'Yes^No', 'S',
                               '', '', '', '', '', 101, 1001])
                # Shorter row - only 8 columns (no reference or appended IDs)
                writer.writerow([2, 3, 'Short row', '', 'A^B^C', 'M', '', '', 102, 1002])

            result = load_parmedit_appended_full(filepath)

            assert len(result) == 2

            # First row
            assert result[0].parms_question_number == 1
            assert result[0].question_id == 1001

            # Second row - shorter, should still parse
            assert result[1].parms_question_number == 2
            assert result[1].question_text == 'Short row'
            # Last two columns should be question_number and question_id
            assert result[1].question_number == 102
            assert result[1].question_id == 1002

    def test_load_with_references(self):
        """Rows with column 10-11 populated (references)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # Row with references in columns 10 and 11
                writer.writerow([5, 4, 'Reference question', '', 'A^B^C^D', 'X',
                               'AVG', '1,4', '', 3, '1,2,3', 105, 1005])

            result = load_parmedit_appended_full(filepath)

            assert len(result) == 1

            row = result[0]
            assert row.parms_question_number == 5
            assert row.question_type == 'X'
            assert row.special_code == 'AVG'
            assert row.special_values == '1,4'
            assert row.reference_parms_qn == 3  # Column 10
            assert row.reference_answers == '1,2,3'  # Column 11
            assert row.question_number == 105
            assert row.question_id == 1005

    def test_load_skips_invalid_rows(self):
        """Skip rows with invalid parms_question_number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # Valid row
                writer.writerow([1, 2, 'Valid', '', 'Yes^No', 'S', '', '', '', '', '', 101, 1001])
                # Invalid - non-numeric first column
                writer.writerow(['abc', 2, 'Invalid', '', 'Yes^No', 'S', '', '', '', '', '', 102, 1002])
                # Another valid row
                writer.writerow([3, 2, 'Valid2', '', 'Yes^No', 'S', '', '', '', '', '', 103, 1003])

            result = load_parmedit_appended_full(filepath)

            # Should only have 2 valid rows
            assert len(result) == 2
            assert result[0].parms_question_number == 1
            assert result[1].parms_question_number == 3

    def test_load_file_not_found(self):
        """Verify FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_parmedit_appended_full("/nonexistent/path/parmedit_APPENDED.csv")


class TestGetMostRecentParmeditAppended:
    """Tests for get_most_recent_parmedit_appended function."""

    def test_basic(self):
        """Correct date sorting - returns most recent entry's parmedit_APPENDED path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = os.path.join(tmpdir, "control.txt")
            with open(control_path, 'w', encoding='utf-8') as f:
                # Entries not in date order
                f.write("Study1,2025-01-15,parms1.csv,data1.pip,WaveFiles/parmedit1.csv,upload1.csv\n")
                f.write("Study2,2025-07-20,parms2.csv,data2.pip,WaveFiles/parmedit2.csv,upload2.csv\n")
                f.write("Study3,2025-04-10,parms3.csv,data3.pip,WaveFiles/parmedit3.csv,upload3.csv\n")

            result = get_most_recent_parmedit_appended(control_path)

            # Should return path for 2025-07-20 (most recent)
            assert result == "WaveFiles/parmedit2_APPENDED.csv"

    def test_empty_control_file(self):
        """Raises ValueError for empty control file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = os.path.join(tmpdir, "control.txt")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write("")  # Empty file

            with pytest.raises(ValueError, match="Control file is empty"):
                get_most_recent_parmedit_appended(control_path)

    def test_single_entry(self):
        """Handle control file with single entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = os.path.join(tmpdir, "control.txt")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write("Study1,2025-03-15,parms.csv,data.pip,parmedit.csv,upload.csv\n")

            result = get_most_recent_parmedit_appended(control_path)

            assert result == "parmedit_APPENDED.csv"

    def test_file_not_found(self):
        """Raises FileNotFoundError for missing control file."""
        with pytest.raises(FileNotFoundError):
            get_most_recent_parmedit_appended("/nonexistent/control.txt")


class TestTranslateReferenceAnswers:
    """Tests for translate_reference_answers function."""

    def test_basic_translation(self):
        """Simple 1:1 mapping - parmedit and common have same order."""
        # parmedit_answer_ids: [10, 20, 30] (positions 1, 2, 3)
        # common_answer_ids: [10, 20, 30] (positions 1, 2, 3)
        # reference_answers: "1,2" -> positions 1 and 2 in parmedit
        # Expected: "1,2" (same positions in common)
        result = translate_reference_answers(
            "1,2",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        assert result == "1,2"

    def test_empty_input(self):
        """Returns empty string for empty input."""
        result = translate_reference_answers(
            "",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        assert result == ""

        # Also test whitespace-only
        result = translate_reference_answers(
            "   ",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        assert result == ""

    def test_reordered_mapping(self):
        """Handles different orderings between parmedit and common."""
        # parmedit_answer_ids: [10, 20, 30] (answer_id 10 at pos 1, 20 at pos 2, 30 at pos 3)
        # common_answer_ids: [30, 10, 20] (answer_id 30 at pos 1, 10 at pos 2, 20 at pos 3)
        # reference_answers: "1,3" -> parmedit positions 1 and 3 -> answer_ids 10 and 30
        # In common: answer_id 10 is at pos 2, answer_id 30 is at pos 1
        # Expected: "2,1"
        result = translate_reference_answers(
            "1,3",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[30, 10, 20]
        )
        assert result == "2,1"

    def test_missing_answer_id(self):
        """Keeps original if answer_id not found in common."""
        # parmedit_answer_ids: [10, 20, 30]
        # common_answer_ids: [10, 30] (missing 20)
        # reference_answers: "1,2,3" -> answer_ids 10, 20, 30
        # In common: 10 at pos 1, 20 not found (keep "2"), 30 at pos 2
        # Expected: "1,2,2"
        result = translate_reference_answers(
            "1,2,3",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 30]
        )
        assert result == "1,2,2"

    def test_empty_parmedit_answer_ids(self):
        """Returns original when parmedit_answer_ids is empty."""
        result = translate_reference_answers(
            "1,2",
            parmedit_answer_ids=[],
            common_answer_ids=[10, 20]
        )
        assert result == "1,2"

    def test_empty_common_answer_ids(self):
        """Returns original when common_answer_ids is empty."""
        result = translate_reference_answers(
            "1,2",
            parmedit_answer_ids=[10, 20],
            common_answer_ids=[]
        )
        assert result == "1,2"

    def test_out_of_bounds_position(self):
        """Keeps original for out-of-bounds positions."""
        # parmedit has 3 elements, but reference asks for position 5
        result = translate_reference_answers(
            "1,5",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        # Position 1 translates to 1, position 5 is out of bounds (keep "5")
        assert result == "1,5"

    def test_non_numeric_position(self):
        """Keeps original for non-numeric positions."""
        result = translate_reference_answers(
            "1,abc,3",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        # "1" and "3" translate, "abc" is kept as-is
        assert result == "1,abc,3"

    def test_whitespace_handling(self):
        """Handles whitespace around positions."""
        result = translate_reference_answers(
            "  1 , 2 , 3  ",
            parmedit_answer_ids=[10, 20, 30],
            common_answer_ids=[10, 20, 30]
        )
        assert result == "1,2,3"


class TestGenerateCommonParmedit:
    """Tests for generate_common_parmedit function."""

    def test_basic_generation(self):
        """Full workflow with mock files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonParms.csv
            common_parms_path = os.path.join(tmpdir, "CommonParms.csv")
            with open(common_parms_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'Gender question', '', 'Male^Female', 'S', 1001])
                writer.writerow([2, 5, 'Age question', '', '18-24^25-34^35-44^45-54^55+', 'S', 1002])

            # Create control file
            control_path = os.path.join(tmpdir, "control.txt")
            parms_path = os.path.join(tmpdir, "parms.csv")
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write(f"Study1,2025-07-20,{parms_path},data.pip,{parmedit_path},upload.csv\n")

            # Create parmedit_APPENDED.csv
            parmedit_appended_path = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(parmedit_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # Match by question_id (last column)
                writer.writerow([1, 2, 'Gender q', '', 'M^F', 'S', '', '', '', '', '', 101, 1001])
                writer.writerow([2, 5, 'Age q', '', 'A^B^C^D^E', 'S', '', '', '', '', '', 102, 1002])

            # Create CommonQuestions.csv
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                writer.writerow([1001, 'Gender', '0^1'])
                writer.writerow([1002, 'Age', '0^1^2^3^4'])

            # Create parms.appended file (for answer_ids lookup)
            parms_appended_path = parms_path + '.appended'
            with open(parms_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'Gender', '', 'M^F', 'S', 1001, '0^1'])
                writer.writerow([2, 5, 'Age', '', 'A^B^C^D^E', 'S', 1002, '0^1^2^3^4'])

            output_path = os.path.join(tmpdir, "CommonParmedit.csv")

            result = generate_common_parmedit(
                common_parms_path,
                control_path,
                output_path,
                common_questions_path
            )

            assert result == output_path
            assert os.path.exists(output_path)

            # Read and verify output
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2

            # Row 1: Gender question
            assert rows[0][0] == '1'  # question_number
            assert rows[0][1] == '2'  # total_answers
            assert rows[0][2] == 'Gender question'  # question_text from CommonParms
            assert rows[0][4] == 'Male^Female'  # answer_list from CommonParms
            assert rows[0][5] == 'S'  # question_type from parmedit

            # Row 2: Age question
            assert rows[1][0] == '2'
            assert rows[1][5] == 'S'

    def test_unmatched_question(self, capsys):
        """Warning for missing parmedit match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonParms.csv with question_id not in parmedit
            common_parms_path = os.path.join(tmpdir, "CommonParms.csv")
            with open(common_parms_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'Unmatched question', '', 'Yes^No', 'S', 9999])

            # Create control file
            control_path = os.path.join(tmpdir, "control.txt")
            parms_path = os.path.join(tmpdir, "parms.csv")
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write(f"Study1,2025-07-20,{parms_path},data.pip,{parmedit_path},upload.csv\n")

            # Create parmedit_APPENDED.csv without question_id 9999
            parmedit_appended_path = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(parmedit_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'Other q', '', 'A^B', 'S', '', '', '', '', '', 101, 1001])

            # Create CommonQuestions.csv
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                writer.writerow([9999, 'Unmatched', '0^1'])

            # Create parms.appended file
            parms_appended_path = parms_path + '.appended'
            with open(parms_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 2, 'Other', '', 'A^B', 'S', 1001, '0^1'])

            output_path = os.path.join(tmpdir, "CommonParmedit.csv")

            generate_common_parmedit(
                common_parms_path,
                control_path,
                output_path,
                common_questions_path
            )

            # Check warning was printed to stderr
            captured = capsys.readouterr()
            assert "Warning" in captured.err
            assert "9999" in captured.err
            assert "not found in parmedit_APPENDED" in captured.err

            # Verify output still generated with fallback values
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 1
            # Should use CommonParms values as fallback
            assert rows[0][2] == 'Unmatched question'
            assert rows[0][5] == 'S'  # Falls back to CommonParms question_type

    def test_with_special_columns(self):
        """AVG columns copied from parmedit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonParms.csv
            common_parms_path = os.path.join(tmpdir, "CommonParms.csv")
            with open(common_parms_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 4, 'AVG question', '', 'A^B^C^D', 'X', 1001])

            # Create control file
            control_path = os.path.join(tmpdir, "control.txt")
            parms_path = os.path.join(tmpdir, "parms.csv")
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write(f"Study1,2025-07-20,{parms_path},data.pip,{parmedit_path},upload.csv\n")

            # Create parmedit_APPENDED.csv with AVG special columns
            parmedit_appended_path = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(parmedit_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # With AVG in column 7, values in column 8
                writer.writerow([1, 4, 'AVG q', '', 'A^B^C^D', 'X', 'AVG', '1,4', 'reserved_val', '', '', 101, 1001])

            # Create CommonQuestions.csv
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                writer.writerow([1001, 'AVG Master', '0^1^2^3'])

            # Create parms.appended file
            parms_appended_path = parms_path + '.appended'
            with open(parms_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 4, 'AVG', '', 'A^B^C^D', 'X', 1001, '0^1^2^3'])

            output_path = os.path.join(tmpdir, "CommonParmedit.csv")

            generate_common_parmedit(
                common_parms_path,
                control_path,
                output_path,
                common_questions_path
            )

            # Read and verify output
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 1

            # Verify special columns copied from parmedit
            assert rows[0][5] == 'X'  # question_type
            assert rows[0][6] == 'AVG'  # special_code
            assert rows[0][7] == '1,4'  # special_values
            assert rows[0][8] == 'reserved_val'  # reserved

    def test_with_references(self):
        """Reference translation works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonParms.csv - 2 questions, second references first
            common_parms_path = os.path.join(tmpdir, "CommonParms.csv")
            with open(common_parms_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # question_number 1 -> question_id 1001
                writer.writerow([1, 3, 'Base question', '', 'A^B^C', 'S', 1001])
                # question_number 2 -> question_id 1002, references 1001
                writer.writerow([2, 4, 'Ref question', '', 'W^X^Y^Z', 'X', 1002])

            # Create control file
            control_path = os.path.join(tmpdir, "control.txt")
            parms_path = os.path.join(tmpdir, "parms.csv")
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            with open(control_path, 'w', encoding='utf-8') as f:
                f.write(f"Study1,2025-07-20,{parms_path},data.pip,{parmedit_path},upload.csv\n")

            # Create parmedit_APPENDED.csv
            parmedit_appended_path = os.path.join(tmpdir, "parmedit_APPENDED.csv")
            with open(parmedit_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # parms_qn 10 -> question_id 1001
                writer.writerow([10, 3, 'Base q', '', 'A^B^C', 'S', '', '', '', '', '', 101, 1001])
                # parms_qn 20 -> question_id 1002, references parms_qn 10, answers 1,2
                writer.writerow([20, 4, 'Ref q', '', 'W^X^Y^Z', 'X', 'AVG', '', '', 10, '1,2', 102, 1002])

            # Create CommonQuestions.csv
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                # Same order for simplicity
                writer.writerow([1001, 'Base Master', '10^20^30'])
                writer.writerow([1002, 'Ref Master', '40^50^60^70'])

            # Create parms.appended file
            parms_appended_path = parms_path + '.appended'
            with open(parms_appended_path, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # question_id 1001 has answer_ids 10^20^30
                writer.writerow([10, 3, 'Base', '', 'A^B^C', 'S', 1001, '10^20^30'])
                writer.writerow([20, 4, 'Ref', '', 'W^X^Y^Z', 'X', 1002, '40^50^60^70'])

            output_path = os.path.join(tmpdir, "CommonParmedit.csv")

            generate_common_parmedit(
                common_parms_path,
                control_path,
                output_path,
                common_questions_path
            )

            # Read and verify output
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2

            # Row 2 (ref question) should have translated references
            # reference_common_qn should be "1" (CommonParms question_number for qid 1001)
            assert rows[1][9] == '1'  # reference_common_qn

            # reference_common_answers: "1,2" -> parmedit positions 1,2 -> answer_ids 10,20
            # In common, answer_ids [10,20,30], so 10 at pos 1, 20 at pos 2
            # Expected: "1,2"
            assert rows[1][10] == '1,2'  # reference_common_answers


class TestLoadCommonQuestionsAnswerIds:
    """Tests for load_common_questions_answer_ids function."""

    def test_basic_load(self):
        """Load answer_ids for each question."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                writer.writerow([1001, 'Question 1', '10^20^30'])
                writer.writerow([1002, 'Question 2', '5^15^25^35'])

            result = load_common_questions_answer_ids(filepath)

            assert result[1001] == [10, 20, 30]
            assert result[1002] == [5, 15, 25, 35]

    def test_empty_answer_ids(self):
        """Handle empty answer_ids (type F questions)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids'])
                writer.writerow([1001, 'Free form', ''])

            result = load_common_questions_answer_ids(filepath)

            assert result[1001] == []


class TestLoadAppendedAnswerIds:
    """Tests for load_appended_answer_ids function."""

    def test_basic_load(self):
        """Load answer_ids from appended file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parms.csv.appended")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                # Columns: 1-6 parms data, 7=question_id, 8=answer_ids
                writer.writerow([1, 3, 'Q1', '', 'A^B^C', 'S', 1001, '10^20^30'])
                writer.writerow([2, 2, 'Q2', '', 'X^Y', 'S', 1002, '5^15'])

            result = load_appended_answer_ids(filepath)

            assert result[1001] == [10, 20, 30]
            assert result[1002] == [5, 15]

    def test_empty_answer_ids(self):
        """Handle rows without answer_ids."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "parms.csv.appended")
            with open(filepath, 'w', encoding='latin-1', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([1, 0, 'Free', '', '', 'F', 1001, ''])

            result = load_appended_answer_ids(filepath)

            assert result[1001] == []


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_parmedit_appended_row(self):
        """Verify ParmeditAppendedRow structure."""
        row = ParmeditAppendedRow(
            parms_question_number=1,
            total_answers=2,
            question_text='Test',
            empty='',
            answer_list='A^B',
            question_type='S',
            special_code='AVG',
            special_values='1,2',
            reserved='res',
            reference_parms_qn=5,
            reference_answers='1,2,3',
            question_number=101,
            question_id=1001
        )
        assert row.parms_question_number == 1
        assert row.question_type == 'S'
        assert row.reference_parms_qn == 5

    def test_common_parms_row(self):
        """Verify CommonParmsRow structure."""
        row = CommonParmsRow(
            question_number=1,
            total_answers=2,
            question_text='Test',
            empty='',
            answer_list='A^B',
            question_type='S',
            common_question_id=1001
        )
        assert row.question_number == 1
        assert row.common_question_id == 1001

    def test_common_parmedit_row(self):
        """Verify CommonParmeditRow structure."""
        row = CommonParmeditRow(
            question_number=1,
            total_answers=2,
            question_text='Test',
            empty='',
            answer_list='A^B',
            question_type='X',
            special_code='AVG',
            special_values='1,4',
            reserved='res',
            reference_common_qn='5',
            reference_common_answers='1,2'
        )
        assert row.question_number == 1
        assert row.question_type == 'X'
        assert row.reference_common_qn == '5'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
