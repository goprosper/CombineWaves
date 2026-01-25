"""Tests for generate_common_parms module."""

import csv
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from generate_common_parms import (
    CommonQuestion,
    load_common_questions_for_parms,
    transform_answer_ids_to_text,
    generate_common_parms,
)


class TestLoadCommonQuestionsForParms:
    """Tests for load_common_questions_for_parms function."""

    def test_load_basic(self):
        """Load a simple CSV with 2-3 questions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([1, 'What is your gender?', '0^1', 'S'])
                writer.writerow([2, 'What is your age range?', '0^1^2^3^4', 'S'])
                writer.writerow([3, 'Select all that apply', '0^1^2', 'M'])

            result = load_common_questions_for_parms(filepath)

            assert len(result) == 3

            assert result[0].common_question_id == 1
            assert result[0].master_question_text == 'What is your gender?'
            assert result[0].common_answer_ids == [0, 1]
            assert result[0].parms_question_type == 'S'

            assert result[1].common_question_id == 2
            assert result[1].master_question_text == 'What is your age range?'
            assert result[1].common_answer_ids == [0, 1, 2, 3, 4]
            assert result[1].parms_question_type == 'S'

            assert result[2].common_question_id == 3
            assert result[2].master_question_text == 'Select all that apply'
            assert result[2].common_answer_ids == [0, 1, 2]
            assert result[2].parms_question_type == 'M'

    def test_load_empty_answer_ids(self):
        """Handle rows with empty common_answer_ids (like type F questions)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([1, 'Enter your zip code:', '', 'F'])
                writer.writerow([2, 'What is your gender?', '0^1', 'S'])

            result = load_common_questions_for_parms(filepath)

            assert len(result) == 2

            assert result[0].common_question_id == 1
            assert result[0].master_question_text == 'Enter your zip code:'
            assert result[0].common_answer_ids == []
            assert result[0].parms_question_type == 'F'

            assert result[1].common_answer_ids == [0, 1]

    def test_load_file_not_found(self):
        """Verify FileNotFoundError is raised."""
        with pytest.raises(FileNotFoundError):
            load_common_questions_for_parms("/nonexistent/path/CommonQuestions.csv")

    def test_load_skips_header(self):
        """Verify header row is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([1, 'First real question', '0^1', 'S'])

            result = load_common_questions_for_parms(filepath)

            # Should only have 1 data row, header should be skipped
            assert len(result) == 1
            assert result[0].common_question_id == 1
            assert result[0].master_question_text == 'First real question'


class TestTransformAnswerIdsToText:
    """Tests for transform_answer_ids_to_text function."""

    def test_transform_basic(self):
        """[0, 1] with 'Male^Female' -> 'Male^Female'."""
        result = transform_answer_ids_to_text([0, 1], "Male^Female")
        assert result == "Male^Female"

    def test_transform_reordered(self):
        """[1, 0] with 'Male^Female' -> 'Female^Male'."""
        result = transform_answer_ids_to_text([1, 0], "Male^Female")
        assert result == "Female^Male"

    def test_transform_subset(self):
        """[0, 2] with 'A^B^C^D' -> 'A^C'."""
        result = transform_answer_ids_to_text([0, 2], "A^B^C^D")
        assert result == "A^C"

    def test_transform_empty_ids(self):
        """[] -> ''."""
        result = transform_answer_ids_to_text([], "Male^Female")
        assert result == ""

    def test_transform_empty_map(self):
        """with empty answer_text_map -> ''."""
        result = transform_answer_ids_to_text([0, 1], "")
        assert result == ""

    def test_transform_out_of_bounds(self):
        """handle indices beyond list length."""
        # Only index 0 is valid, index 5 and 10 are out of bounds
        result = transform_answer_ids_to_text([0, 5, 10], "A^B")
        # Out-of-bounds indices are skipped, so only index 0 ('A') is included
        assert result == "A"


class TestGenerateCommonParms:
    """Tests for generate_common_parms function."""

    def test_generate_basic(self):
        """Full workflow with mocked database returning records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonQuestions.csv
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'What is your gender?', '0^1', 'S'])
                writer.writerow([102, 'What is your age?', '0^1^2^3^4', 'S'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            # Mock database client
            mock_db = MagicMock()

            # Create mock record objects
            mock_record_101 = MagicMock()
            mock_record_101.alternate_text = "Gender"
            mock_record_101.answer_text = "Male^Female"

            mock_record_102 = MagicMock()
            mock_record_102.alternate_text = "Age Range"
            mock_record_102.answer_text = "18-24^25-34^35-44^45-54^55+"

            def mock_get_question_master(study_name, question_id):
                records = {101: mock_record_101, 102: mock_record_102}
                return records.get(question_id)

            mock_db.get_question_master.side_effect = mock_get_question_master

            # Generate
            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            assert result == output_path
            assert os.path.exists(output_path)

            # Verify output
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Should have 3 rows: 2 question rows + 1 study_date row (no header)
            assert len(rows) == 3

            # Row 1: question_number=1, total_answers=2, question_text=Gender
            assert rows[0][0] == '1'  # question_number
            assert rows[0][1] == '2'  # total_answers
            assert rows[0][2] == 'Gender'  # question_text (alternate_text)
            assert rows[0][3] == ''  # empty column 4
            assert rows[0][4] == 'Male^Female'  # answer_text_list
            assert rows[0][5] == 'S'  # question_type

            # Row 2: question_number=2, total_answers=5, question_text=Age Range
            assert rows[1][0] == '2'
            assert rows[1][1] == '5'
            assert rows[1][2] == 'Age Range'
            assert rows[1][4] == '18-24^25-34^35-44^45-54^55+'
            assert rows[1][5] == 'S'

            # Row 3: Study Date metadata row
            assert rows[2][0] == '3'  # question_number (next sequential)
            assert rows[2][1] == '0'  # total_answers
            assert rows[2][2] == 'Study Date'  # question_text
            assert rows[2][3] == ''  # empty column 4
            assert rows[2][4] == ''  # empty answer_text_list
            assert rows[2][5] == 'F'  # question_type

    def test_generate_missing_db_record(self):
        """Verify fallback to master_question_text when DB returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Fallback question text', '0^1^2', 'S'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            # Mock database returning None
            mock_db = MagicMock()
            mock_db.get_question_master.return_value = None

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            # Should use master_question_text as fallback
            assert rows[0][2] == 'Fallback question text'
            # answer_text_list should be empty when DB returns None
            assert rows[0][4] == ''

            # Verify study_date row
            assert rows[1][0] == '2'
            assert rows[1][2] == 'Study Date'
            assert rows[1][5] == 'F'

    def test_generate_type_f_empty_answers(self):
        """Verify type F questions have 0 answers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Enter your zip code:', '', 'F'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Zip Code"
            mock_record.answer_text = ""
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            # total_answers should be 0 for type F
            assert rows[0][1] == '0'
            # answer_text_list should be empty
            assert rows[0][4] == ''
            # question_type should be F
            assert rows[0][5] == 'F'

            # Verify study_date row
            assert rows[1][0] == '2'
            assert rows[1][2] == 'Study Date'

    def test_generate_output_format(self):
        """Verify CSV has correct columns and no header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Question 1', '0^1', 'S'])
                writer.writerow([102, 'Question 2', '0^1^2', 'M'])
                writer.writerow([103, 'Question 3', '', 'F'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Test Question"
            mock_record.answer_text = "A^B^C"
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Should have 4 rows: 3 question rows + 1 study_date row (no header)
            assert len(rows) == 4

            # Verify column format for each row
            for i, row in enumerate(rows, start=1):
                assert len(row) == 6  # 6 columns
                assert row[0] == str(i)  # question_number is sequential
                assert row[3] == ''  # column 4 is always empty

            # Verify question numbers are sequential
            assert rows[0][0] == '1'
            assert rows[1][0] == '2'
            assert rows[2][0] == '3'
            assert rows[3][0] == '4'  # Study Date row

            # Verify last row is Study Date
            assert rows[3][2] == 'Study Date'
            assert rows[3][5] == 'F'


class TestGenerateCommonParmsEdgeCases:
    """Additional edge case tests for generate_common_parms."""

    def test_generate_empty_alternate_text_fallback(self):
        """Verify fallback to master_question_text when alternate_text is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Master question text', '0^1', 'S'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            # Mock database returning record with empty alternate_text
            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = ""  # Empty - should fallback
            mock_record.answer_text = "Yes^No"
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            # Should use master_question_text as fallback
            assert rows[0][2] == 'Master question text'
            # But answer_text_list should still be populated from DB
            assert rows[0][4] == 'Yes^No'

            # Verify study_date row
            assert rows[1][2] == 'Study Date'

    def test_generate_type_m_multiple_answers(self):
        """Verify type M (multiple choice) questions work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Select all that apply', '0^1^2^3^4', 'M'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Multi-select question"
            mock_record.answer_text = "Option A^Option B^Option C^Option D^Option E"
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            assert rows[0][1] == '5'  # total_answers
            assert rows[0][4] == 'Option A^Option B^Option C^Option D^Option E'
            assert rows[0][5] == 'M'

            # Verify study_date row
            assert rows[1][2] == 'Study Date'

    def test_generate_single_answer_question(self):
        """Verify single answer question works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Yes or no?', '0', 'S'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Single option question"
            mock_record.answer_text = "Yes"
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            assert rows[0][1] == '1'  # total_answers = 1
            assert rows[0][4] == 'Yes'

            # Verify study_date row
            assert rows[1][2] == 'Study Date'

    def test_generate_reordered_answer_ids(self):
        """Verify answer_ids that are not in sequential order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                # Answer IDs are [2, 0, 3] - not sequential
                writer.writerow([101, 'Reordered answers', '2^0^3', 'S'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Reordered question"
            mock_record.answer_text = "A^B^C^D"  # Indices 0,1,2,3
            mock_db.get_question_master.return_value = mock_record

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 1 question row + 1 study_date row
            assert len(rows) == 2
            # Answer IDs [2, 0, 3] -> C, A, D
            assert rows[0][4] == 'C^A^D'

            # Verify study_date row
            assert rows[1][2] == 'Study Date'

    def test_generate_empty_common_questions(self):
        """Verify behavior with empty CommonQuestions.csv (header only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                # No data rows

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()

            result = generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Should have 1 row: just the study_date row (no questions)
            assert len(rows) == 1
            # DB should not have been called
            mock_db.get_question_master.assert_not_called()

            # Verify it's the study_date row
            assert rows[0][0] == '1'  # First row, so question_number=1
            assert rows[0][2] == 'Study Date'
            assert rows[0][5] == 'F'


class TestWithRealCommonQuestionsFile:
    """Tests using real CommonQuestions.csv if available."""

    def test_load_real_common_questions_file(self):
        """Load the real CommonQuestions.csv file if it exists."""
        filepath = "CommonQuestions.csv"
        if not os.path.exists(filepath):
            pytest.skip("CommonQuestions.csv not found")

        result = load_common_questions_for_parms(filepath)

        # Verify we loaded some questions
        assert len(result) > 0

        # Verify first question has expected structure
        first = result[0]
        assert isinstance(first.common_question_id, int)
        assert isinstance(first.master_question_text, str)
        assert isinstance(first.common_answer_ids, list)
        assert first.parms_question_type in ('S', 'M', 'F')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
