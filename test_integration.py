"""Integration tests for CombineWaves with parmedit support."""

import csv
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from control_file import ControlEntry
from parmedit import load_parmedit
from parms_processor import process_parms_file
from database import QuestionMapRecord


class TestParmsProcessorWithParmedit:
    """Integration tests for parms_processor with parmedit mapper."""

    def test_process_parms_with_parmedit_mapping(self):
        """Process parms file using parmedit mapping for question_number lookup."""
        # Create parmedit file:
        # Row 1: parms_qn=100 -> qn=1
        # Row 2: parms_qn=200 -> qn=2
        parmedit_content = """100,2,Question 1,,Yes^No,S
200,3,Question 2,,A^B^C,S
"""
        # Create parms file with parms_question_numbers 100 and 200
        parms_content = """100,2,Question 1,,Yes^No,S
200,3,Question 2,,A^B^C,S
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            parms_path = os.path.join(tmpdir, "parms.csv")

            with open(parmedit_path, 'w') as f:
                f.write(parmedit_content)
            with open(parms_path, 'w') as f:
                f.write(parms_content)

            # Load parmedit mapper
            parmedit_mapper = load_parmedit(parmedit_path)

            # Verify mapping
            assert parmedit_mapper.get_question_number(100) == 1
            assert parmedit_mapper.get_question_number(200) == 2

            # Mock database client
            mock_db = MagicMock()

            def mock_get_question_map(study_name, study_date, question_number):
                # Return records for question_number 1 and 2 (not 100 and 200)
                if question_number == 1:
                    return QuestionMapRecord(question_id=1001, answer_value_map="1^2")
                elif question_number == 2:
                    return QuestionMapRecord(question_id=1002, answer_value_map="1^2^3")
                return None

            mock_db.get_question_map.side_effect = mock_get_question_map

            # Process parms file
            output_path = process_parms_file(
                parms_path,
                "TestStudy",
                "2026-01-01",
                mock_db,
                parmedit_mapper
            )

            # Verify output file exists
            assert os.path.exists(output_path)

            # Read output and verify
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2

            # Row 1: parms_qn=100 -> qn=1 -> question_id=1001
            assert rows[0][6] == "1001"

            # Row 2: parms_qn=200 -> qn=2 -> question_id=1002
            assert rows[1][6] == "1002"

            # Verify database was called with question_number (1, 2), not parms_question_number (100, 200)
            calls = mock_db.get_question_map.call_args_list
            assert len(calls) == 2
            # First call should use question_number=1
            assert calls[0][0][2] == 1  # Third positional arg is question_number
            # Second call should use question_number=2
            assert calls[1][0][2] == 2

    def test_parms_question_number_not_in_parmedit(self):
        """Warning when parms_question_number not found in parmedit."""
        parmedit_content = """100,2,Question 1,,Yes^No,S
"""
        parms_content = """100,2,Question 1,,Yes^No,S
999,2,Unknown Question,,A^B,S
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            parms_path = os.path.join(tmpdir, "parms.csv")

            with open(parmedit_path, 'w') as f:
                f.write(parmedit_content)
            with open(parms_path, 'w') as f:
                f.write(parms_content)

            parmedit_mapper = load_parmedit(parmedit_path)

            mock_db = MagicMock()
            mock_db.get_question_map.return_value = QuestionMapRecord(
                question_id=1001, answer_value_map="1^2"
            )

            # Process parms file (should print warning for parms_qn=999)
            output_path = process_parms_file(
                parms_path,
                "TestStudy",
                "2026-01-01",
                mock_db,
                parmedit_mapper
            )

            # Read output
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Row 1 should have question_id
            assert rows[0][6] == "1001"

            # Row 2 (parms_qn=999 not in parmedit) should have empty question_id
            assert rows[1][6] == ""
            assert rows[1][7] == ""


class TestEndToEndWorkflow:
    """End-to-end tests for the complete workflow."""

    def test_full_workflow_with_mock_db(self):
        """Test complete workflow from control file to output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create control file
            control_path = os.path.join(tmpdir, "control.txt")
            parms_path = os.path.join(tmpdir, "parms.csv")
            parmedit_path = os.path.join(tmpdir, "parmedit.csv")
            pip_path = os.path.join(tmpdir, "data.pip")

            # Create parmedit file
            parmedit_content = """50,2,Gender,,Male^Female,S
51,3,Age,,Young^Middle^Old,S
"""
            with open(parmedit_path, 'w') as f:
                f.write(parmedit_content)

            # Create parms file
            parms_content = """50,2,What is your gender?,,Male^Female,S
51,3,What is your age range?,,Young^Middle^Old,S
"""
            with open(parms_path, 'w') as f:
                f.write(parms_content)

            # Create empty pip file (not used but referenced)
            with open(pip_path, 'w') as f:
                f.write("")

            # Create control file
            control_content = f"TestStudy,2026-01-01,{parms_path},{pip_path},{parmedit_path}\n"
            with open(control_path, 'w') as f:
                f.write(control_content)

            # Load parmedit
            parmedit_mapper = load_parmedit(parmedit_path)

            # Verify parmedit mapping:
            # parms_qn=50 -> qn=1
            # parms_qn=51 -> qn=2
            assert parmedit_mapper.get_question_number(50) == 1
            assert parmedit_mapper.get_question_number(51) == 2

            # Mock database
            mock_db = MagicMock()

            def mock_get_question_map(study_name, study_date, question_number):
                if question_number == 1:
                    return QuestionMapRecord(question_id=101, answer_value_map="2^1")
                elif question_number == 2:
                    return QuestionMapRecord(question_id=102, answer_value_map="3^1^2")
                return None

            mock_db.get_question_map = mock_get_question_map

            # Process
            output_path = process_parms_file(
                parms_path,
                "TestStudy",
                "2026-01-01",
                mock_db,
                parmedit_mapper
            )

            # Verify output
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2

            # Row 1: question_id=101, answer_ids computed from "2^1" with 2 answers
            # Answer 1 -> find "1" in "2^1" -> index 1
            # Answer 2 -> find "2" in "2^1" -> index 0
            # answer_ids = "1^0"
            assert rows[0][6] == "101"
            assert rows[0][7] == "1^0"

            # Row 2: question_id=102, answer_ids computed from "3^1^2" with 3 answers
            # Answer 1 -> find "1" in "3^1^2" -> index 1
            # Answer 2 -> find "2" in "3^1^2" -> index 2
            # Answer 3 -> find "3" in "3^1^2" -> index 0
            # answer_ids = "1^2^0"
            assert rows[1][6] == "102"
            assert rows[1][7] == "1^2^0"


class TestGenerateCommonParmsIntegration:
    """Integration tests for Step 4: Generate Common Parms."""

    def test_step4_workflow_with_mock_db(self):
        """Test Step 4 workflow: CommonQuestions.csv -> CommonParms.csv."""
        from generate_common_parms import generate_common_parms
        from database import QuestionMasterRecord

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CommonQuestions.csv (output of Step 2)
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType', 'ParmeditQuestionType'])
                writer.writerow([288, 'Zip:', '', 'F', 'Z'])
                writer.writerow([1, 'What is your gender?', '0^1', 'S', 'X'])
                writer.writerow([3, 'Please tell us which age range you are in:', '0^1^2^3^4^5^6', 'S', 'A'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            # Mock database
            mock_db = MagicMock()

            def mock_get_question_master(study_name, question_id):
                records = {
                    288: QuestionMasterRecord(alternate_text="Zip Code", answer_text=""),
                    1: QuestionMasterRecord(alternate_text="Gender", answer_text="Male^Female"),
                    3: QuestionMasterRecord(alternate_text="Age Range", answer_text="14-17^18-24^25-34^35-44^45-54^55-64^65+"),
                }
                return records.get(question_id)

            mock_db.get_question_master.side_effect = mock_get_question_master

            # Run Step 4
            result = generate_common_parms(
                common_questions_path,
                "CIA",
                mock_db,
                output_path
            )

            assert result == output_path
            assert os.path.exists(output_path)

            # Verify output matches expected parms format
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 3

            # Row 1: Zip (type F, no answers)
            assert rows[0][0] == '1'  # question_number
            assert rows[0][1] == '0'  # total_answers
            assert rows[0][2] == 'Zip Code'  # question_text
            assert rows[0][3] == ''  # empty
            assert rows[0][4] == ''  # answer_text_list (empty for F)
            assert rows[0][5] == 'F'  # question_type

            # Row 2: Gender (type S, 2 answers)
            assert rows[1][0] == '2'
            assert rows[1][1] == '2'
            assert rows[1][2] == 'Gender'
            assert rows[1][4] == 'Male^Female'
            assert rows[1][5] == 'S'

            # Row 3: Age Range (type S, 7 answers)
            assert rows[2][0] == '3'
            assert rows[2][1] == '7'
            assert rows[2][2] == 'Age Range'
            assert rows[2][4] == '14-17^18-24^25-34^35-44^45-54^55-64^65+'
            assert rows[2][5] == 'S'

    def test_step4_database_called_correctly(self):
        """Verify database is called with correct parameters."""
        from generate_common_parms import generate_common_parms

        with tempfile.TemporaryDirectory() as tmpdir:
            common_questions_path = os.path.join(tmpdir, "CommonQuestions.csv")
            with open(common_questions_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['common_question_id', 'master_question_text', 'common_answer_ids', 'ParmsQuestionType'])
                writer.writerow([101, 'Question 1', '0^1', 'S'])
                writer.writerow([202, 'Question 2', '0^1^2', 'S'])
                writer.writerow([303, 'Question 3', '', 'F'])

            output_path = os.path.join(tmpdir, "CommonParms.csv")

            mock_db = MagicMock()
            mock_record = MagicMock()
            mock_record.alternate_text = "Test"
            mock_record.answer_text = "A^B^C"
            mock_db.get_question_master.return_value = mock_record

            generate_common_parms(common_questions_path, "TestStudy", mock_db, output_path)

            # Verify database calls
            calls = mock_db.get_question_master.call_args_list
            assert len(calls) == 3

            # Check each call used correct study_name and question_id
            assert calls[0][0] == ("TestStudy", 101)
            assert calls[1][0] == ("TestStudy", 202)
            assert calls[2][0] == ("TestStudy", 303)


class TestQuestionMasterRecord:
    """Tests for QuestionMasterRecord dataclass."""

    def test_create_question_master_record(self):
        """Create a QuestionMasterRecord instance."""
        from database import QuestionMasterRecord

        record = QuestionMasterRecord(
            alternate_text="What is your gender?",
            answer_text="Male^Female"
        )

        assert record.alternate_text == "What is your gender?"
        assert record.answer_text == "Male^Female"

    def test_question_master_record_empty_values(self):
        """Create a QuestionMasterRecord with empty values."""
        from database import QuestionMasterRecord

        record = QuestionMasterRecord(alternate_text="", answer_text="")

        assert record.alternate_text == ""
        assert record.answer_text == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
