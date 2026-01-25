"""Tests for parms_processor module."""

import csv
import os
import tempfile
import pytest
from unittest.mock import MagicMock

from parms_processor import process_parms_file
from database import QuestionMapRecord
from parmedit import ParmeditMapper
from report import reset_collector


class TestProcessParmsFile:
    """Tests for process_parms_file function."""

    def setup_method(self):
        """Reset the report collector before each test."""
        reset_collector()

    def _create_parms_file(self, tmpdir: str, rows: list) -> str:
        """Helper to create a parms CSV file."""
        parms_path = os.path.join(tmpdir, "test_parms.csv")
        with open(parms_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return parms_path

    def _create_mock_mapper(self, mapping: dict, file_path: str = "test_parmedit.csv") -> ParmeditMapper:
        """Helper to create a ParmeditMapper with test data."""
        return ParmeditMapper(_mapping=mapping, file_path=file_path)

    def _create_mock_db(self, records: dict) -> MagicMock:
        """Helper to create a mock database client.

        Args:
            records: Dict mapping question_number to QuestionMapRecord or None
        """
        mock_db = MagicMock()

        def get_question_map(study_name, study_date, question_number):
            return records.get(question_number)

        mock_db.get_question_map.side_effect = get_question_map
        return mock_db

    def test_process_basic(self):
        """Basic processing with mocked DB returning valid records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parms file with 2 questions
            rows = [
                ['1', '3', 'What is your gender?', '', 'Male^Female^Other', 'S'],
                ['2', '5', 'What is your age?', '', 'Under 18^18-25^26-35^36-50^Over 50', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            # Create mapper: parms_question_number -> question_number
            mapper = self._create_mock_mapper({1: 101, 2: 102})

            # Create mock DB returning records
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='1^2^3'),
                102: QuestionMapRecord(question_id=1002, answer_value_map='1^2^3^4^5'),
            })

            # Process
            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            # Verify output file exists
            assert os.path.exists(output_path)
            assert output_path == f"{parms_path}.appended"

            # Read and verify output
            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 2
            # Row 1: original columns + question_id + answer_ids
            assert output_rows[0][:6] == rows[0]
            assert output_rows[0][6] == '1001'  # question_id
            assert output_rows[0][7] == '0^1^2'  # answer_ids (positions in answer_value_map)

            # Row 2
            assert output_rows[1][:6] == rows[1]
            assert output_rows[1][6] == '1002'
            assert output_rows[1][7] == '0^1^2^3^4'

    def test_process_db_returns_none(self, capsys):
        """Handle DB returning None for a question."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                ['1', '2', 'Question 1', '', 'Yes^No', 'S'],
                ['2', '2', 'Question 2', '', 'Yes^No', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101, 2: 102})

            # DB returns None for question 102
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='1^2'),
                102: None,  # Not found
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            # First row should have valid data
            assert output_rows[0][6] == '1001'
            assert output_rows[0][7] == '0^1'

            # Second row should have empty question_id and answer_ids
            assert output_rows[1][6] == ''
            assert output_rows[1][7] == ''

            # Warning should be logged
            captured = capsys.readouterr()
            assert 'WARNING' in captured.err
            assert 'No database record' in captured.err

    def test_process_empty_file(self):
        """Empty parms file produces empty output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty parms file
            parms_path = self._create_parms_file(tmpdir, [])

            mapper = self._create_mock_mapper({})
            mock_db = self._create_mock_db({})

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            assert os.path.exists(output_path)

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 0

    def test_process_type_s_question(self):
        """Single-choice question processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Type S = single-choice
            rows = [
                ['1', '4', 'Favorite color?', '', 'Red^Blue^Green^Yellow', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='2^1^4^3'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 1
            assert output_rows[0][5] == 'S'  # Type preserved
            assert output_rows[0][6] == '1001'
            # answer_value_map is '2^1^4^3'
            # For answer 1, find '1' in map -> index 1
            # For answer 2, find '2' in map -> index 0
            # For answer 3, find '3' in map -> index 3
            # For answer 4, find '4' in map -> index 2
            assert output_rows[0][7] == '1^0^3^2'

    def test_process_type_m_question(self):
        """Multiple-choice question processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Type M = multiple-choice
            rows = [
                ['1', '3', 'Select all that apply', '', 'Option A^Option B^Option C', 'M'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='3^2^1'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 1
            assert output_rows[0][5] == 'M'  # Type preserved
            assert output_rows[0][6] == '1001'
            # answer_value_map is '3^2^1'
            # Answer 1 -> position of '1' -> index 2
            # Answer 2 -> position of '2' -> index 1
            # Answer 3 -> position of '3' -> index 0
            assert output_rows[0][7] == '2^1^0'

    def test_process_type_f_question(self):
        """Free-form question processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Type F = free-form (no answers)
            rows = [
                ['1', '0', 'Please describe your experience', '', '', 'F'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map=''),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 1
            assert output_rows[0][5] == 'F'  # Type preserved
            assert output_rows[0][6] == '1001'
            assert output_rows[0][7] == ''  # Empty answer_ids for type F

    def test_process_malformed_row(self):
        """Row with fewer than expected columns should be handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Row with only 3 columns (fewer than 6 expected)
            rows = [
                ['1', '2', 'Incomplete row'],  # Missing columns
                ['2', '3', 'Complete row', '', 'A^B^C', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101, 2: 102})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='1^2'),
                102: QuestionMapRecord(question_id=1002, answer_value_map='1^2^3'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 2

            # Malformed row should have empty appended columns
            assert output_rows[0][:3] == ['1', '2', 'Incomplete row']
            assert output_rows[0][-2:] == ['', '']  # Empty question_id and answer_ids

            # Complete row should process normally
            assert output_rows[1][6] == '1002'
            assert output_rows[1][7] == '0^1^2'

    def test_process_non_numeric_parms_qn(self, capsys):
        """Non-numeric parms_question_number should be handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                ['abc', '2', 'Question with bad QN', '', 'Yes^No', 'S'],
                ['2', '2', 'Normal question', '', 'Yes^No', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({0: 100, 2: 102})  # 0 for non-numeric
            mock_db = self._create_mock_db({
                100: QuestionMapRecord(question_id=1000, answer_value_map='1^2'),
                102: QuestionMapRecord(question_id=1002, answer_value_map='1^2'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 2
            # Non-numeric parms_question_number (abc) becomes 0
            # If 0 is not in mapper, it will have empty columns
            # If 0 is in mapper (as we've set up), it will get data from question 100

            # Second row should process normally
            assert output_rows[1][6] == '1002'

    def test_output_file_created(self):
        """Verify .appended file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                ['1', '2', 'Test question', '', 'A^B', 'S'],
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({1: 101})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='1^2'),
            })

            # Verify output doesn't exist before
            expected_output = f"{parms_path}.appended"
            assert not os.path.exists(expected_output)

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            # Verify output exists after
            assert os.path.exists(output_path)
            assert output_path == expected_output

    def test_output_preserves_original_columns(self):
        """Original columns preserved in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Row with specific data in each column
            original_row = [
                '42',  # parms_question_number
                '5',   # total_answers
                'A question with "quoted" text',  # question_text
                'Column 4 data',  # column 4
                'Ans1^Ans2^Ans3^Ans4^Ans5',  # answers
                'M'    # type
            ]
            rows = [original_row]
            parms_path = self._create_parms_file(tmpdir, rows)

            mapper = self._create_mock_mapper({42: 101})
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=999, answer_value_map='1^2^3^4^5'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            assert len(output_rows) == 1
            output_row = output_rows[0]

            # All original columns should be preserved exactly
            assert output_row[0] == '42'
            assert output_row[1] == '5'
            assert output_row[2] == 'A question with "quoted" text'
            assert output_row[3] == 'Column 4 data'
            assert output_row[4] == 'Ans1^Ans2^Ans3^Ans4^Ans5'
            assert output_row[5] == 'M'

            # New columns appended
            assert output_row[6] == '999'  # question_id
            assert output_row[7] == '0^1^2^3^4'  # answer_ids

    def test_process_parms_qn_not_in_parmedit(self, capsys):
        """parms_question_number not found in parmedit mapper logs warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                ['1', '2', 'Question 1', '', 'Yes^No', 'S'],
                ['999', '2', 'Unknown question', '', 'Yes^No', 'S'],  # Not in mapper
            ]
            parms_path = self._create_parms_file(tmpdir, rows)

            # Only parms_qn=1 is in mapper, 999 is not
            mapper = self._create_mock_mapper({1: 101}, file_path='test_parmedit.csv')
            mock_db = self._create_mock_db({
                101: QuestionMapRecord(question_id=1001, answer_value_map='1^2'),
            })

            output_path = process_parms_file(
                parms_path=parms_path,
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                output_rows = list(reader)

            # First row should be processed normally
            assert output_rows[0][6] == '1001'

            # Second row should have empty columns
            assert output_rows[1][6] == ''
            assert output_rows[1][7] == ''

            # Warning should be logged
            captured = capsys.readouterr()
            assert 'WARNING' in captured.err
            assert '999' in captured.err
            assert 'not found in parmedit' in captured.err

    def test_process_file_not_found(self):
        """Non-existent parms file raises FileNotFoundError."""
        mapper = self._create_mock_mapper({})
        mock_db = self._create_mock_db({})

        with pytest.raises(FileNotFoundError):
            process_parms_file(
                parms_path='/nonexistent/parms.csv',
                study_name='TestStudy',
                study_date='2026-01-01',
                db_client=mock_db,
                parmedit_mapper=mapper
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
