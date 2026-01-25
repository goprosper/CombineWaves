"""Tests for upload_matcher module."""

import os
import tempfile
import pytest

from upload_matcher import (
    UploadQuestion,
    load_upload_file,
    text_similarity,
    match_parmedit_to_upload,
    create_parmedit_appended,
)


class TestUploadQuestion:
    """Tests for UploadQuestion dataclass."""

    def test_create_upload_question(self):
        """Create UploadQuestion with valid data."""
        q = UploadQuestion(question_number=1, question_text="What is your name?")
        assert q.question_number == 1
        assert q.question_text == "What is your name?"


class TestLoadUploadFile:
    """Tests for load_upload_file function."""

    def test_load_basic(self):
        """Load UPLOAD file and verify questions extracted."""
        content = '''header,row,skipped,by,loader
1,X,"Q1","What is your gender?","Male^Female"
2,S,"Q2","What is your marital status?","Married^Single"
3,A,"Q3","Please tell us your age:","18-24^25-34"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)

            assert len(questions) == 3
            assert questions[0].question_number == 1
            assert questions[0].question_text == "What is your gender?"
            assert questions[1].question_number == 2
            assert questions[1].question_text == "What is your marital status?"
            assert questions[2].question_number == 3
            assert questions[2].question_text == "Please tell us your age:"
        finally:
            os.unlink(temp_path)

    def test_load_skips_header(self):
        """Row 1 (header) is skipped."""
        content = '''This,is,the,header,row
1,X,"Q1","First question","Answers"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)

            # Only one question should be loaded (header skipped)
            assert len(questions) == 1
            assert questions[0].question_number == 1
        finally:
            os.unlink(temp_path)

    def test_load_extracts_correct_columns(self):
        """Extracts question_number from col 1 and question_text from col 4."""
        content = '''h1,h2,h3,h4,h5
42,ignore,ignore,"The actual question text","more data"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)

            assert questions[0].question_number == 42
            assert questions[0].question_text == "The actual question text"
        finally:
            os.unlink(temp_path)

    def test_load_file_not_found(self):
        """Attempt to load non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_upload_file("/nonexistent/path/upload.csv")

    def test_load_preserves_order(self):
        """Questions are returned in file order."""
        content = '''header
100,X,"Q100","Question 100","A"
50,X,"Q50","Question 50","A"
200,X,"Q200","Question 200","A"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)

            assert len(questions) == 3
            assert questions[0].question_number == 100
            assert questions[1].question_number == 50
            assert questions[2].question_number == 200
        finally:
            os.unlink(temp_path)

    def test_load_empty_file(self):
        """Load empty UPLOAD file returns empty list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)
            assert questions == []
        finally:
            os.unlink(temp_path)

    def test_load_header_only(self):
        """Load UPLOAD file with only header returns empty list."""
        content = '''header,row,only
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            questions = load_upload_file(temp_path)
            assert questions == []
        finally:
            os.unlink(temp_path)


class TestTextSimilarity:
    """Tests for text_similarity function."""

    def test_exact_match(self):
        """Exact match returns 1.0."""
        assert text_similarity("Hello World", "Hello World") == 1.0

    def test_case_insensitive(self):
        """Case differences don't affect match."""
        assert text_similarity("HELLO WORLD", "hello world") == 1.0
        assert text_similarity("Hello World", "HELLO WORLD") == 1.0

    def test_partial_match(self):
        """Partial match returns expected ratio."""
        # These should have high similarity
        sim = text_similarity(
            "What is your gender?",
            "What is your gender"  # Missing question mark
        )
        assert sim > 0.9

    def test_similar_questions(self):
        """Similar questions have high similarity."""
        sim = text_similarity(
            "Men's Clothing (Shop at Most Often) [write-in]",
            "Men's Clothing (Shop at Most Often) [Retail Format]"
        )
        assert 0.8 < sim < 0.95  # Similar but not exact

    def test_different_questions(self):
        """Different questions have low similarity."""
        sim = text_similarity(
            "What is your gender?",
            "How old are you?"
        )
        assert sim < 0.5

    def test_empty_strings(self):
        """Empty strings comparison."""
        assert text_similarity("", "") == 1.0
        assert text_similarity("Hello", "") == 0.0
        assert text_similarity("", "World") == 0.0


class TestMatchParmeditToUpload:
    """Tests for match_parmedit_to_upload function."""

    def test_exact_alignment(self):
        """All rows match in order."""
        parmedit_content = '''1,2,What is your gender?,,Male^Female,S
2,3,What is your age?,,18-24^25-34,S
3,4,What is your income?,,Low^Medium^High,S
'''
        upload_questions = [
            UploadQuestion(101, "What is your gender?"),
            UploadQuestion(102, "What is your age?"),
            UploadQuestion(103, "What is your income?"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            temp_path = f.name

        try:
            matched, unmatched_p, skipped_u = match_parmedit_to_upload(
                temp_path, upload_questions
            )

            assert len(matched) == 3
            assert matched[0][1] == 101  # parmedit row 1 -> UPLOAD Q101
            assert matched[1][1] == 102  # parmedit row 2 -> UPLOAD Q102
            assert matched[2][1] == 103  # parmedit row 3 -> UPLOAD Q103
            assert unmatched_p == []
            assert skipped_u == []
        finally:
            os.unlink(temp_path)

    def test_with_upload_skips(self):
        """UPLOAD has extra rows that get skipped."""
        parmedit_content = '''1,2,What is your gender?,,Male^Female,S
2,3,What is your age?,,18-24^25-34,S
'''
        # UPLOAD has an extra question between the two
        upload_questions = [
            UploadQuestion(101, "What is your gender?"),
            UploadQuestion(102, "Extra question not in parmedit"),
            UploadQuestion(103, "What is your age?"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            temp_path = f.name

        try:
            matched, unmatched_p, skipped_u = match_parmedit_to_upload(
                temp_path, upload_questions
            )

            assert len(matched) == 2
            assert matched[0][1] == 101
            assert matched[1][1] == 103
            assert unmatched_p == []
            assert skipped_u == [102]  # Q102 was skipped
        finally:
            os.unlink(temp_path)

    def test_unmatched_parmedit(self):
        """Parmedit row with no match in UPLOAD."""
        parmedit_content = '''1,2,What is your gender?,,Male^Female,S
2,3,This question has no match,,Answers,S
3,4,What is your age?,,18-24^25-34,S
'''
        upload_questions = [
            UploadQuestion(101, "What is your gender?"),
            UploadQuestion(102, "What is your age?"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            temp_path = f.name

        try:
            matched, unmatched_p, skipped_u = match_parmedit_to_upload(
                temp_path, upload_questions
            )

            assert len(matched) == 3
            assert matched[0][1] == 101
            assert matched[1][1] is None  # Row 2 unmatched
            assert matched[2][1] == 102
            assert unmatched_p == [2]  # Row 2 couldn't match
        finally:
            os.unlink(temp_path)

    def test_lookahead_finds_match(self):
        """Match found within lookahead distance."""
        parmedit_content = '''1,2,Target question,,Answers,S
'''
        # Target question is 5 positions ahead
        upload_questions = [
            UploadQuestion(1, "Skip 1"),
            UploadQuestion(2, "Skip 2"),
            UploadQuestion(3, "Skip 3"),
            UploadQuestion(4, "Skip 4"),
            UploadQuestion(5, "Skip 5"),
            UploadQuestion(6, "Target question"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            temp_path = f.name

        try:
            matched, unmatched_p, skipped_u = match_parmedit_to_upload(
                temp_path, upload_questions, lookahead=10
            )

            assert len(matched) == 1
            assert matched[0][1] == 6  # Found at position 6
            assert skipped_u == [1, 2, 3, 4, 5]  # Skipped Q1-Q5
        finally:
            os.unlink(temp_path)

    def test_similarity_threshold(self):
        """Matches above/below threshold."""
        parmedit_content = '''1,2,What is your annual household income?,,Answers,S
'''
        upload_questions = [
            # This should NOT match at 90% threshold (completely different topic)
            UploadQuestion(1, "What is your favorite color?"),
            # This should match (same text)
            UploadQuestion(2, "What is your annual household income?"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            temp_path = f.name

        try:
            matched, unmatched_p, skipped_u = match_parmedit_to_upload(
                temp_path, upload_questions, similarity_threshold=0.90
            )

            assert matched[0][1] == 2  # Matched to Q2, not Q1
            assert skipped_u == [1]  # Q1 was skipped
        finally:
            os.unlink(temp_path)


class TestCreateParmeditAppended:
    """Tests for create_parmedit_appended function."""

    def test_creates_file(self):
        """Output file is created."""
        parmedit_content = '''1,2,What is your gender?,,Male^Female,S
2,3,What is your age?,,18-24,S
'''
        upload_content = '''header
1,X,"Q1","What is your gender?","A"
2,X,"Q2","What is your age?","A"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            parmedit_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(upload_content)
            upload_path = f.name

        output_path = parmedit_path.replace('.csv', '_APPENDED.csv')

        try:
            result = create_parmedit_appended(parmedit_path, upload_path)
            assert os.path.exists(result)
            assert result == output_path
        finally:
            os.unlink(parmedit_path)
            os.unlink(upload_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_appends_question_number(self):
        """Last column has question_number from UPLOAD."""
        parmedit_content = '''1,2,What is your gender?,,Male^Female,S
2,3,What is your age?,,18-24,S
'''
        upload_content = '''header
101,X,"Q101","What is your gender?","A"
102,X,"Q102","What is your age?","A"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            parmedit_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(upload_content)
            upload_path = f.name

        output_path = parmedit_path.replace('.csv', '_APPENDED.csv')

        try:
            create_parmedit_appended(parmedit_path, upload_path)

            # Read output and verify last column
            import csv
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert rows[0][-1] == '101'  # First row has Q101
            assert rows[1][-1] == '102'  # Second row has Q102
        finally:
            os.unlink(parmedit_path)
            os.unlink(upload_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_preserves_original_columns(self):
        """Original parmedit data is unchanged."""
        parmedit_content = '''1,2,Question Text,col4,Male^Female,S
'''
        upload_content = '''header
101,X,"Q101","Question Text","A"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            parmedit_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(upload_content)
            upload_path = f.name

        output_path = parmedit_path.replace('.csv', '_APPENDED.csv')

        try:
            create_parmedit_appended(parmedit_path, upload_path)

            import csv
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                row = next(reader)

            # Original columns preserved
            assert row[0] == '1'
            assert row[1] == '2'
            assert row[2] == 'Question Text'
            assert row[3] == 'col4'
            assert row[4] == 'Male^Female'
            assert row[5] == 'S'
            # Appended column
            assert row[6] == '101'
        finally:
            os.unlink(parmedit_path)
            os.unlink(upload_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_raises_on_unmatched_parmedit(self):
        """ValueError raised when parmedit row cannot be matched."""
        parmedit_content = '''1,2,This question has no match,,Answers,S
'''
        upload_content = '''header
1,X,"Q1","Completely different question","A"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(parmedit_content)
            parmedit_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(upload_content)
            upload_path = f.name

        output_path = parmedit_path.replace('.csv', '_APPENDED.csv')

        try:
            with pytest.raises(ValueError) as exc_info:
                create_parmedit_appended(parmedit_path, upload_path)
            assert "could not be matched" in str(exc_info.value)
        finally:
            os.unlink(parmedit_path)
            os.unlink(upload_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestWithRealFiles:
    """Tests using actual files from WaveFiles directory."""

    def test_load_coctober2025_upload(self):
        """Load the actual COctober2025_UPLOAD.csv file."""
        upload_path = "WaveFiles/COctober2025_UPLOAD.csv"

        if not os.path.exists(upload_path):
            pytest.skip("COctober2025_UPLOAD.csv not found")

        questions = load_upload_file(upload_path)

        # Should have many questions
        assert len(questions) > 100

        # First question should be Q1
        assert questions[0].question_number == 1
        assert "gender" in questions[0].question_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
