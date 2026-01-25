"""Tests for intersection module."""

import csv
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from intersection import (
    read_appended_file,
    read_parmedit_appended_file,
    determine_majority_type,
    compute_intersection,
    generate_common_questions,
)


class TestReadAppendedFile:
    """Tests for read_appended_file function."""

    def test_read_basic(self):
        """Read file with valid data."""
        content = """1,2,Question Text 1,e,ans1^ans2,S,101,0^1^2
2,2,Question Text 2,e,ans1^ans2,M,102,0^1
3,2,Question Text 3,e,ans1^ans2,F,103,
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 3
            # Check structure: (answer_ids, parms_type, question_text, parms_qn)
            assert result[101][0] == {0, 1, 2}
            assert result[101][1] == 'S'
            assert result[101][2] == 'Question Text 1'
            assert result[101][3] == 1

            assert result[102][0] == {0, 1}
            assert result[102][1] == 'M'

            assert result[103][0] == set()
            assert result[103][1] == 'F'
        finally:
            os.unlink(temp_path)

    def test_read_skips_empty_question_id(self):
        """Rows without question_id are skipped."""
        content = """1,2,Q1,e,a^b,S,101,0^1
2,2,Q2,e,a^b,S,,0^1
3,2,Q3,e,a^b,S,102,0^1^2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 2
            assert 101 in result
            assert 102 in result
        finally:
            os.unlink(temp_path)

    def test_read_merges_duplicate_question_ids(self):
        """Same question_id on multiple rows has answer_ids merged."""
        content = """1,2,Q1,e,a^b,S,101,0^1
2,2,Q1,e,a^b,M,101,2^3
3,2,Q1,e,a^b,F,101,4
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 1
            assert result[101][0] == {0, 1, 2, 3, 4}
            # Should keep first occurrence's metadata
            assert result[101][1] == 'S'
        finally:
            os.unlink(temp_path)

    def test_read_handles_empty_answer_ids(self):
        """Rows with empty answer_ids are handled."""
        content = """1,2,Q1,e,a^b,F,101,
2,2,Q2,e,a^b,S,102,0^1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 2
            assert result[101][0] == set()
            assert result[102][0] == {0, 1}
        finally:
            os.unlink(temp_path)

    def test_read_file_not_found(self):
        """FileNotFoundError raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_appended_file("/nonexistent/path/file.csv")

    def test_read_skips_short_rows(self):
        """Rows with fewer than 8 columns are skipped."""
        content = """1,2,Q1,e,a^b,S,101,0^1
short,row
2,2,Q2,e,a^b,S,102,0^1^2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 2
            assert 101 in result
            assert 102 in result
        finally:
            os.unlink(temp_path)


class TestReadParmeditAppendedFile:
    """Tests for read_parmedit_appended_file function."""

    def test_read_basic(self):
        """Read parmedit_APPENDED file."""
        content = """1,2,Q1,e,a^b,X,extra,extra,extra,extra,extra,10
2,2,Q2,e,a^b,S,extra,extra,extra,extra,extra,11
3,2,Q3,e,a^b,A,extra,extra,extra,extra,extra,12
4,2,Q4,e,a^b,F,extra,extra,extra,extra,extra,13
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_parmedit_appended_file(temp_path)

            assert len(result) == 4
            assert result[1] == 'X'
            assert result[2] == 'S'
            assert result[3] == 'A'
            assert result[4] == 'F'
        finally:
            os.unlink(temp_path)

    def test_read_skips_invalid_parms_qn(self):
        """Rows with non-numeric parms_question_number are skipped."""
        content = """1,2,Q1,e,a^b,X,extra,extra,extra,extra,extra,10
invalid,2,Q2,e,a^b,S,extra,extra,extra,extra,extra,11
3,2,Q3,e,a^b,A,extra,extra,extra,extra,extra,12
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_parmedit_appended_file(temp_path)

            assert len(result) == 2
            assert 1 in result
            assert 3 in result
        finally:
            os.unlink(temp_path)

    def test_read_file_not_found(self):
        """FileNotFoundError raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_parmedit_appended_file("/nonexistent/path/file.csv")


class TestDetermineMajorityType:
    """Tests for determine_majority_type function."""

    def test_unanimous(self):
        """All types agree."""
        majority, had_disagreement = determine_majority_type(['S', 'S', 'S'])
        assert majority == 'S'
        assert had_disagreement is False

    def test_disagreement(self):
        """Types disagree, majority wins."""
        majority, had_disagreement = determine_majority_type(['S', 'S', 'M'])
        assert majority == 'S'
        assert had_disagreement is True

    def test_empty_list(self):
        """Empty list returns empty string."""
        majority, had_disagreement = determine_majority_type([])
        assert majority == ''
        assert had_disagreement is False

    def test_all_empty_strings(self):
        """List of empty strings returns empty string."""
        majority, had_disagreement = determine_majority_type(['', '', ''])
        assert majority == ''
        assert had_disagreement is False

    def test_some_empty_strings(self):
        """Empty strings are filtered out."""
        majority, had_disagreement = determine_majority_type(['S', '', 'S'])
        assert majority == 'S'
        assert had_disagreement is False

    def test_tie_uses_first_most_common(self):
        """Tie uses first most common type."""
        majority, had_disagreement = determine_majority_type(['S', 'M'])
        assert majority in ('S', 'M')
        assert had_disagreement is True


class TestComputeIntersection:
    """Tests for compute_intersection function."""

    def test_intersection_basic(self):
        """Three files with overlapping questions."""
        file1 = {
            101: ({0, 1, 2}, 'S', 'Q1', 1),
            102: ({0, 1}, 'M', 'Q2', 2),
            103: ({0, 1, 2, 3}, 'F', 'Q3', 3)
        }
        file2 = {
            101: ({0, 1, 3}, 'S', 'Q1', 1),
            102: ({0, 1, 2}, 'M', 'Q2', 2),
            104: ({0, 1}, 'S', 'Q4', 4)
        }
        file3 = {
            101: ({0, 2, 3}, 'S', 'Q1', 1),
            102: ({0, 1}, 'M', 'Q2', 2),
            105: ({0, 1}, 'S', 'Q5', 5)
        }

        parmedit1 = {1: 'X', 2: 'M', 3: 'F'}
        parmedit2 = {1: 'X', 2: 'M', 4: 'S'}
        parmedit3 = {1: 'X', 2: 'M', 5: 'S'}

        order, result = compute_intersection(
            [file1, file2, file3],
            [parmedit1, parmedit2, parmedit3]
        )

        # Only 101 and 102 are common (103, 104, 105 are not in all files)
        assert len(result) == 2
        assert 101 in result
        assert 102 in result
        assert 103 not in result
        assert 104 not in result
        assert 105 not in result

    def test_intersection_preserves_order(self):
        """Processing order matches first file."""
        file1 = {
            102: ({0, 1}, 'S', 'Q2', 2),
            101: ({0, 1}, 'S', 'Q1', 1),
            103: ({0, 1}, 'S', 'Q3', 3)
        }
        file2 = {
            101: ({0, 1}, 'S', 'Q1', 1),
            102: ({0, 1}, 'S', 'Q2', 2),
            103: ({0, 1}, 'S', 'Q3', 3)
        }

        order, result = compute_intersection([file1, file2], [{}, {}])

        # Order should match file1's iteration order
        # Note: dict order is preserved in Python 3.7+
        assert order == [102, 101, 103]

    def test_filters_other_please_specify(self):
        """Filter F-type 'Other, please specify:' questions."""
        file1 = {
            101: ({0, 1}, 'S', 'Normal question', 1),
            102: ({}, 'F', 'Other, please specify:', 2),
            103: ({0, 1}, 'M', 'Another question', 3)
        }
        file2 = {
            101: ({0, 1}, 'S', 'Normal question', 1),
            102: ({}, 'F', 'Other, please specify:', 2),
            103: ({0, 1}, 'M', 'Another question', 3)
        }

        order, result = compute_intersection([file1, file2], [{}, {}])

        assert 101 in result
        assert 102 not in result  # Filtered out
        assert 103 in result

    def test_keeps_f_type_with_different_text(self):
        """Keep F-type questions that aren't 'Other, please specify:'."""
        file1 = {
            101: ({}, 'F', 'Zip:', 1),
            102: ({}, 'F', 'Other, please specify:', 2)
        }
        file2 = {
            101: ({}, 'F', 'Zip:', 1),
            102: ({}, 'F', 'Other, please specify:', 2)
        }

        order, result = compute_intersection([file1, file2], [{}, {}])

        assert 101 in result  # Kept
        assert 102 not in result  # Filtered

    def test_f_type_has_empty_answer_ids(self):
        """F-type questions have empty answer_ids in result."""
        file1 = {
            101: ({0, 1, 2}, 'S', 'Q1', 1),
            102: ({0, 1}, 'F', 'Free form', 2)  # Has answer_ids in input
        }
        file2 = {
            101: ({0, 2}, 'S', 'Q1', 1),
            102: ({2, 3}, 'F', 'Free form', 2)  # Has answer_ids in input
        }

        order, result = compute_intersection([file1, file2], [{}, {}])

        # S-type: union of answer_ids
        assert result[101][0] == {0, 1, 2}
        # F-type: empty set even though input had answer_ids
        assert result[102][0] == set()

    def test_collects_types_from_all_files(self):
        """Collects parms_types and parmedit_types from all files."""
        file1 = {101: ({0, 1}, 'S', 'Q1', 1)}
        file2 = {101: ({0, 1}, 'M', 'Q1', 1)}  # Different type
        file3 = {101: ({0, 1}, 'S', 'Q1', 1)}

        parmedit1 = {1: 'X'}
        parmedit2 = {1: 'A'}  # Different type
        parmedit3 = {1: 'X'}

        order, result = compute_intersection(
            [file1, file2, file3],
            [parmedit1, parmedit2, parmedit3]
        )

        # Should have collected all types
        assert result[101][1] == ['S', 'M', 'S']  # parms_types
        assert result[101][2] == ['X', 'A', 'X']  # parmedit_types

    def test_answer_union(self):
        """Verify answer_ids are unioned correctly."""
        file1 = {101: ({0, 1, 2}, 'S', 'Q1', 1)}
        file2 = {101: ({0, 1, 3}, 'S', 'Q1', 1)}
        file3 = {101: ({0, 2, 3}, 'S', 'Q1', 1)}

        order, result = compute_intersection([file1, file2, file3], [{}, {}, {}])

        assert result[101][0] == {0, 1, 2, 3}

    def test_empty_list(self):
        """Empty file list."""
        order, result = compute_intersection([], [])

        assert order == []
        assert result == {}


class TestGenerateCommonQuestions:
    """Tests for generate_common_questions function."""

    def test_generate_basic(self):
        """End-to-end with mock database."""
        # Create temp appended files
        file1_content = """1,2,Q1,e,a^b,S,101,0^1
2,2,Q2,e,a^b,M,102,0^1^2
"""
        file2_content = """1,2,Q1,e,a^b,S,101,0^2
2,2,Q2,e,a^b,M,102,0^1
"""
        # Create temp parmedit_APPENDED files
        parmedit1_content = """1,2,Q1,e,a^b,X,e,e,e,e,e,10
2,2,Q2,e,a^b,M,e,e,e,e,e,11
"""
        parmedit2_content = """1,2,Q1,e,a^b,X,e,e,e,e,e,10
2,2,Q2,e,a^b,M,e,e,e,e,e,11
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            file2_path = os.path.join(tmpdir, "file2.appended")
            parmedit1_path = os.path.join(tmpdir, "parmedit1_APPENDED.csv")
            parmedit2_path = os.path.join(tmpdir, "parmedit2_APPENDED.csv")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(file2_path, 'w') as f:
                f.write(file2_content)
            with open(parmedit1_path, 'w') as f:
                f.write(parmedit1_content)
            with open(parmedit2_path, 'w') as f:
                f.write(parmedit2_content)

            # Mock database client
            mock_db = MagicMock()

            def mock_get_question_text(study_name, question_id):
                texts = {101: "Question 101 text", 102: "Question 102 text"}
                return texts.get(question_id)

            mock_db.get_question_text.side_effect = mock_get_question_text

            # Generate
            result = generate_common_questions(
                [file1_path, file2_path],
                [parmedit1_path, parmedit2_path],
                "TestStudy",
                mock_db,
                output_path
            )

            assert result == output_path
            assert os.path.exists(output_path)

            # Verify output
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 3  # Header + 2 data rows
            assert rows[0] == [
                'common_question_id',
                'master_question_text',
                'common_answer_ids',
                'ParmsQuestionType',
                'ParmeditQuestionType'
            ]

            # Find rows by question_id
            data_rows = {int(row[0]): row for row in rows[1:]}

            assert data_rows[101][1] == "Question 101 text"
            assert data_rows[101][2] == "0^1^2"  # Union of {0,1} and {0,2}, sorted
            assert data_rows[101][3] == "S"
            assert data_rows[101][4] == "X"

            assert data_rows[102][1] == "Question 102 text"
            assert data_rows[102][2] == "0^1^2"  # Union of {0,1,2} and {0,1}, sorted
            assert data_rows[102][3] == "M"
            assert data_rows[102][4] == "M"

    def test_generate_f_type_empty_answers(self):
        """F-type questions have empty answer_ids in output."""
        file1_content = """1,2,Q1,e,a^b,S,101,0^1
2,2,Zip:,e,,F,102,
"""
        parmedit1_content = """1,2,Q1,e,a^b,X,e,e,e,e,e,10
2,2,Zip:,e,,F,e,e,e,e,e,11
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            parmedit1_path = os.path.join(tmpdir, "parmedit1_APPENDED.csv")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(parmedit1_path, 'w') as f:
                f.write(parmedit1_content)

            mock_db = MagicMock()
            mock_db.get_question_text.return_value = "Test question"

            result = generate_common_questions(
                [file1_path],
                [parmedit1_path],
                "TestStudy",
                mock_db,
                output_path
            )

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Find F-type row
            f_row = [r for r in rows[1:] if r[3] == 'F'][0]
            assert f_row[2] == ''  # Empty answer_ids for F-type

    def test_generate_filters_other_please_specify(self):
        """'Other, please specify:' F-type questions are filtered."""
        file1_content = """1,2,Q1,e,a^b,S,101,0^1
2,2,"Other, please specify:",e,,F,102,
3,2,Q3,e,a^b,M,103,0^1
"""
        parmedit1_content = """1,2,Q1,e,a^b,X,e,e,e,e,e,10
2,2,"Other, please specify:",e,,F,e,e,e,e,e,11
3,2,Q3,e,a^b,M,e,e,e,e,e,12
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            parmedit1_path = os.path.join(tmpdir, "parmedit1_APPENDED.csv")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(parmedit1_path, 'w') as f:
                f.write(parmedit1_content)

            mock_db = MagicMock()
            mock_db.get_question_text.return_value = "Test question"

            result = generate_common_questions(
                [file1_path],
                [parmedit1_path],
                "TestStudy",
                mock_db,
                output_path
            )

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Should have header + 2 rows (101 and 103, not 102)
            assert len(rows) == 3
            question_ids = [int(r[0]) for r in rows[1:]]
            assert 101 in question_ids
            assert 102 not in question_ids  # Filtered
            assert 103 in question_ids

    def test_generate_empty_intersection(self):
        """Verify empty file created with header when no common questions."""
        file1_content = """1,2,Q1,e,a^b,S,101,0^1
"""
        file2_content = """1,2,Q2,e,a^b,S,102,0^1
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            file2_path = os.path.join(tmpdir, "file2.appended")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(file2_path, 'w') as f:
                f.write(file2_content)

            mock_db = MagicMock()

            result = generate_common_questions(
                [file1_path, file2_path],
                [],
                "TestStudy",
                mock_db,
                output_path
            )

            assert os.path.exists(output_path)

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 1  # Header only
            assert rows[0] == [
                'common_question_id',
                'master_question_text',
                'common_answer_ids',
                'ParmsQuestionType',
                'ParmeditQuestionType'
            ]

    def test_generate_preserves_processing_order(self):
        """Output is in processing order, not sorted by question_id."""
        # Create file with non-sorted question_ids
        file1_content = """3,2,Q3,e,a^b,S,300,0^1
1,2,Q1,e,a^b,S,100,0^1
2,2,Q2,e,a^b,S,200,0^1
"""
        parmedit1_content = """3,2,Q3,e,a^b,X,e,e,e,e,e,10
1,2,Q1,e,a^b,X,e,e,e,e,e,11
2,2,Q2,e,a^b,X,e,e,e,e,e,12
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            parmedit1_path = os.path.join(tmpdir, "parmedit1_APPENDED.csv")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(parmedit1_path, 'w') as f:
                f.write(parmedit1_content)

            mock_db = MagicMock()
            mock_db.get_question_text.return_value = "Test"

            result = generate_common_questions(
                [file1_path],
                [parmedit1_path],
                "TestStudy",
                mock_db,
                output_path
            )

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Order should match file order: 300, 100, 200 (not sorted: 100, 200, 300)
            question_ids = [int(r[0]) for r in rows[1:]]
            assert question_ids == [300, 100, 200]


class TestWithRealAppendedFiles:
    """Tests using actual appended files from WaveFiles directory."""

    def test_read_real_appended_file(self):
        """Read the actual CJanuary2026_parms.csv.appended file."""
        appended_path = "WaveFiles/CJanuary2026_parms.csv.appended"

        if not os.path.exists(appended_path):
            pytest.skip("Appended file not found")

        result = read_appended_file(appended_path)

        # Should have many question_ids
        assert len(result) > 0

        # All keys should be integers
        for qid in result.keys():
            assert isinstance(qid, int)

        # All values should be tuples with correct structure
        for data in result.values():
            assert isinstance(data, tuple)
            assert len(data) == 4
            assert isinstance(data[0], set)  # answer_ids
            assert isinstance(data[1], str)  # parms_type
            assert isinstance(data[2], str)  # question_text
            assert isinstance(data[3], int)  # parms_question_number


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
