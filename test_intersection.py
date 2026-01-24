"""Tests for intersection module."""

import csv
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from intersection import (
    read_appended_file,
    compute_intersection,
    generate_common_questions,
)


class TestReadAppendedFile:
    """Tests for read_appended_file function."""

    def test_read_basic(self):
        """Read file with valid data."""
        content = """col1,col2,col3,col4,col5,col6,101,0^1^2
col1,col2,col3,col4,col5,col6,102,0^1
col1,col2,col3,col4,col5,col6,103,0^1^2^3
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 3
            assert result[101] == {0, 1, 2}
            assert result[102] == {0, 1}
            assert result[103] == {0, 1, 2, 3}
        finally:
            os.unlink(temp_path)

    def test_read_skips_empty_question_id(self):
        """Rows without question_id are skipped."""
        content = """col1,col2,col3,col4,col5,col6,101,0^1
col1,col2,col3,col4,col5,col6,,0^1
col1,col2,col3,col4,col5,col6,102,0^1^2
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
        content = """col1,col2,col3,col4,col5,col6,101,0^1
col1,col2,col3,col4,col5,col6,101,2^3
col1,col2,col3,col4,col5,col6,101,4
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 1
            assert result[101] == {0, 1, 2, 3, 4}
        finally:
            os.unlink(temp_path)

    def test_read_handles_empty_answer_ids(self):
        """Rows with empty answer_ids are handled."""
        content = """col1,col2,col3,col4,col5,col6,101,
col1,col2,col3,col4,col5,col6,102,0^1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_appended_file(temp_path)

            assert len(result) == 2
            assert result[101] == set()
            assert result[102] == {0, 1}
        finally:
            os.unlink(temp_path)

    def test_read_file_not_found(self):
        """FileNotFoundError raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_appended_file("/nonexistent/path/file.csv")

    def test_read_skips_short_rows(self):
        """Rows with fewer than 8 columns are skipped."""
        content = """col1,col2,col3,col4,col5,col6,101,0^1
short,row
col1,col2,col3,col4,col5,col6,102,0^1^2
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


class TestComputeIntersection:
    """Tests for compute_intersection function."""

    def test_intersection_basic(self):
        """Three files with overlapping questions."""
        file1 = {101: {0, 1, 2}, 102: {0, 1}, 103: {0, 1, 2, 3}}
        file2 = {101: {0, 1, 3}, 102: {0, 1, 2}, 104: {0, 1}}
        file3 = {101: {0, 2, 3}, 102: {0, 1}, 105: {0, 1}}

        result = compute_intersection([file1, file2, file3])

        assert len(result) == 2
        assert 101 in result
        assert 102 in result
        assert 103 not in result
        assert 104 not in result
        assert 105 not in result

    def test_intersection_all_common(self):
        """All files have same questions."""
        file1 = {101: {0, 1}, 102: {0, 1}}
        file2 = {101: {0, 2}, 102: {0, 2}}
        file3 = {101: {0, 3}, 102: {0, 3}}

        result = compute_intersection([file1, file2, file3])

        assert len(result) == 2
        assert 101 in result
        assert 102 in result

    def test_intersection_none_common(self):
        """No common questions."""
        file1 = {101: {0, 1}}
        file2 = {102: {0, 1}}
        file3 = {103: {0, 1}}

        result = compute_intersection([file1, file2, file3])

        assert len(result) == 0

    def test_intersection_single_file(self):
        """Only one file."""
        file1 = {101: {0, 1}, 102: {0, 1, 2}}

        result = compute_intersection([file1])

        assert len(result) == 2
        assert result[101] == {0, 1}
        assert result[102] == {0, 1, 2}

    def test_intersection_empty_list(self):
        """Empty file list."""
        result = compute_intersection([])

        assert len(result) == 0

    def test_answer_union(self):
        """Verify answer_ids are unioned correctly."""
        file1 = {101: {0, 1, 2}}
        file2 = {101: {0, 1, 3}}
        file3 = {101: {0, 2, 3}}

        result = compute_intersection([file1, file2, file3])

        assert result[101] == {0, 1, 2, 3}

    def test_answer_union_with_empty(self):
        """Union handles empty answer_ids sets."""
        file1 = {101: {0, 1, 2}}
        file2 = {101: set()}
        file3 = {101: {3, 4}}

        result = compute_intersection([file1, file2, file3])

        assert result[101] == {0, 1, 2, 3, 4}


class TestGenerateCommonQuestions:
    """Tests for generate_common_questions function."""

    def test_generate_basic(self):
        """End-to-end with mock database."""
        # Create temp appended files
        file1_content = """c1,c2,c3,c4,c5,c6,101,0^1
c1,c2,c3,c4,c5,c6,102,0^1^2
"""
        file2_content = """c1,c2,c3,c4,c5,c6,101,0^2
c1,c2,c3,c4,c5,c6,102,0^1
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            file2_path = os.path.join(tmpdir, "file2.appended")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)
            with open(file2_path, 'w') as f:
                f.write(file2_content)

            # Mock database client
            mock_db = MagicMock()

            def mock_get_question_text(study_name, question_id):
                texts = {101: "Question 101 text", 102: "Question 102 text"}
                return texts.get(question_id)

            mock_db.get_question_text.side_effect = mock_get_question_text

            # Generate
            result = generate_common_questions(
                [file1_path, file2_path],
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
            assert rows[0] == ['common_question_id', 'master_question_text', 'common_answer_ids']

            # Find rows by question_id
            data_rows = {int(row[0]): row for row in rows[1:]}

            assert data_rows[101][1] == "Question 101 text"
            assert data_rows[101][2] == "0^1^2"  # Union of {0,1} and {0,2}, sorted

            assert data_rows[102][1] == "Question 102 text"
            assert data_rows[102][2] == "0^1^2"  # Union of {0,1,2} and {0,1}, sorted

    def test_generate_empty_intersection(self):
        """Verify empty file created with header when no common questions."""
        file1_content = """c1,c2,c3,c4,c5,c6,101,0^1
"""
        file2_content = """c1,c2,c3,c4,c5,c6,102,0^1
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
                "TestStudy",
                mock_db,
                output_path
            )

            assert os.path.exists(output_path)

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 1  # Header only
            assert rows[0] == ['common_question_id', 'master_question_text', 'common_answer_ids']

    def test_generate_missing_question_text(self):
        """Warning logged, empty string used when question_text not found."""
        file1_content = """c1,c2,c3,c4,c5,c6,101,0^1
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)

            mock_db = MagicMock()
            mock_db.get_question_text.return_value = None

            result = generate_common_questions(
                [file1_path],
                "TestStudy",
                mock_db,
                output_path
            )

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert rows[1][1] == ""  # Empty question text

    def test_generate_answer_ids_sorted(self):
        """Answer IDs are sorted numerically in output."""
        file1_content = """c1,c2,c3,c4,c5,c6,101,5^2^10^1
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "file1.appended")
            output_path = os.path.join(tmpdir, "CommonQuestions.csv")

            with open(file1_path, 'w') as f:
                f.write(file1_content)

            mock_db = MagicMock()
            mock_db.get_question_text.return_value = "Test question"

            result = generate_common_questions(
                [file1_path],
                "TestStudy",
                mock_db,
                output_path
            )

            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert rows[1][2] == "1^2^5^10"  # Sorted numerically


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

        # All values should be sets of integers
        for aids in result.values():
            assert isinstance(aids, set)
            for aid in aids:
                assert isinstance(aid, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
