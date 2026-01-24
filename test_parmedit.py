"""Tests for parmedit module."""

import os
import tempfile
import pytest

from parmedit import ParmeditMapper, load_parmedit


class TestParmeditMapper:
    """Tests for ParmeditMapper class."""

    def test_get_question_number_found(self):
        """Look up existing parms_question_number returns correct question_number."""
        mapper = ParmeditMapper(_mapping={4: 1, 373: 2, 5: 3, 170: 5}, file_path="test.csv")

        assert mapper.get_question_number(4) == 1
        assert mapper.get_question_number(373) == 2
        assert mapper.get_question_number(5) == 3
        assert mapper.get_question_number(170) == 5

    def test_get_question_number_not_found(self):
        """Look up missing parms_question_number returns None."""
        mapper = ParmeditMapper(_mapping={4: 1, 373: 2}, file_path="test.csv")

        assert mapper.get_question_number(999) is None
        assert mapper.get_question_number(0) is None

    def test_empty_mapping(self):
        """Empty mapper returns None for any lookup."""
        mapper = ParmeditMapper(_mapping={}, file_path="test.csv")

        assert mapper.get_question_number(1) is None
        assert mapper.get_question_number(100) is None


class TestLoadParmedit:
    """Tests for load_parmedit function."""

    def test_load_basic(self):
        """Load parmedit file and verify mapping created correctly."""
        content = """4,2,What is your gender?,,Male^Female,X
373,5,What is your marital status?,,Answer1^Answer2,S
5,7,Please tell us which age range you are in:,,14-17^18-24,A
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            mapper = load_parmedit(temp_path)

            # Row 1 has parms_question_number=4, so 4 -> 1
            assert mapper.get_question_number(4) == 1
            # Row 2 has parms_question_number=373, so 373 -> 2
            assert mapper.get_question_number(373) == 2
            # Row 3 has parms_question_number=5, so 5 -> 3
            assert mapper.get_question_number(5) == 3
        finally:
            os.unlink(temp_path)

    def test_load_with_quoted_fields(self):
        """Load parmedit file with quoted CSV fields."""
        content = '''4,2,"What is your gender?",,Male^Female,X
373,5,"What is your marital status, really?",,"Answer1,Answer2",S
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            mapper = load_parmedit(temp_path)

            assert mapper.get_question_number(4) == 1
            assert mapper.get_question_number(373) == 2
        finally:
            os.unlink(temp_path)

    def test_load_empty_file(self):
        """Load empty parmedit file creates empty mapping."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            mapper = load_parmedit(temp_path)
            assert mapper.get_question_number(1) is None
        finally:
            os.unlink(temp_path)

    def test_load_file_not_found(self):
        """Attempt to load non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_parmedit("/nonexistent/path/parmedit.csv")

    def test_load_invalid_parms_question_number(self):
        """Non-integer in column 1 raises ValueError."""
        content = """4,2,Question 1,,Answer,S
abc,5,Question 2,,Answer,S
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                load_parmedit(temp_path)
            assert "row 2" in str(exc_info.value)
            assert "abc" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_load_skips_empty_rows(self):
        """Empty rows in parmedit file are skipped."""
        content = """4,2,Question 1,,Answer,S

373,5,Question 2,,Answer,S
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            mapper = load_parmedit(temp_path)
            # Row 1: 4 -> 1
            assert mapper.get_question_number(4) == 1
            # Row 2 is empty, skipped
            # Row 3: 373 -> 3 (row number still increments)
            assert mapper.get_question_number(373) == 3
        finally:
            os.unlink(temp_path)

    def test_load_large_question_numbers(self):
        """Handle large parms_question_numbers."""
        content = """99999,2,Question,,Answer,S
12345,5,Question,,Answer,S
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            mapper = load_parmedit(temp_path)
            assert mapper.get_question_number(99999) == 1
            assert mapper.get_question_number(12345) == 2
        finally:
            os.unlink(temp_path)


class TestParmeditWithRealFile:
    """Tests using actual parmedit files from WaveFiles directory."""

    def test_load_cjanuary2026_parmedit(self):
        """Load the actual CJanuary2026_parmedit.csv file."""
        parmedit_path = "WaveFiles/CJanuary2026_parmedit.csv"

        if not os.path.exists(parmedit_path):
            pytest.skip("CJanuary2026_parmedit.csv not found")

        mapper = load_parmedit(parmedit_path)

        # Based on the file content we saw earlier:
        # Row 1: parms_question_number=4 -> question_number=1
        # Row 2: parms_question_number=373 -> question_number=2
        # Row 3: parms_question_number=5 -> question_number=3
        # Row 5: parms_question_number=170 -> question_number=5
        assert mapper.get_question_number(4) == 1
        assert mapper.get_question_number(373) == 2
        assert mapper.get_question_number(5) == 3
        assert mapper.get_question_number(170) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
