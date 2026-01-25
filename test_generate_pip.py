"""Tests for generate_pip module."""

import csv
import os
import tempfile
import unittest

from control_file import ControlEntry
from generate_pip import (
    AppendedRow,
    CommonQuestion,
    build_appended_index,
    generate_common_pip,
    load_common_questions,
    transform_answer_multiple,
    transform_answer_single,
)


class TestLoadCommonQuestions(unittest.TestCase):
    """Tests for load_common_questions function."""

    def test_load_basic(self):
        """Test loading a basic CommonQuestions.csv file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding='utf-8'
        ) as f:
            f.write("question_id,master_question_text,common_answer_ids\n")
            f.write('1,"What is your gender?","0^1"\n')
            f.write('3,"Age range?","0^1^2^3^4^5^6"\n')
            temp_path = f.name

        try:
            questions = load_common_questions(temp_path)

            self.assertEqual(len(questions), 2)

            self.assertEqual(questions[0].question_id, 1)
            self.assertEqual(questions[0].master_question_text, "What is your gender?")
            self.assertEqual(questions[0].common_answer_ids, [0, 1])

            self.assertEqual(questions[1].question_id, 3)
            self.assertEqual(questions[1].master_question_text, "Age range?")
            self.assertEqual(questions[1].common_answer_ids, [0, 1, 2, 3, 4, 5, 6])
        finally:
            os.unlink(temp_path)

    def test_load_empty_answer_ids(self):
        """Test loading with empty answer IDs (F-type questions)."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding='utf-8'
        ) as f:
            f.write("question_id,master_question_text,common_answer_ids\n")
            f.write('5,"Free form question",""\n')
            temp_path = f.name

        try:
            questions = load_common_questions(temp_path)

            self.assertEqual(len(questions), 1)
            self.assertEqual(questions[0].question_id, 5)
            self.assertEqual(questions[0].common_answer_ids, [])
        finally:
            os.unlink(temp_path)

    def test_load_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with self.assertRaises(FileNotFoundError):
            load_common_questions("/nonexistent/path.csv")


class TestBuildAppendedIndex(unittest.TestCase):
    """Tests for build_appended_index function."""

    def test_build_basic(self):
        """Test building index from basic appended file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.appended', delete=False, encoding='latin-1'
        ) as f:
            # Format: parms_qn,total_answers,question_text,empty,answers,type,question_id,answer_ids
            f.write('4,2,What is your gender?,,Male^Female,S,1,0^1\n')
            f.write('5,7,Age range?,,18-24^25-34^35-44^45-54^55-64^65+^Prefer not to say,S,3,0^1^2^3^4^5^6\n')
            temp_path = f.name

        try:
            index = build_appended_index(temp_path)

            self.assertEqual(len(index), 2)

            self.assertIn(1, index)
            self.assertEqual(index[1].parms_question_number, 4)
            self.assertEqual(index[1].question_type, 'S')
            self.assertEqual(index[1].answer_ids, [0, 1])

            self.assertIn(3, index)
            self.assertEqual(index[3].parms_question_number, 5)
            self.assertEqual(index[3].question_type, 'S')
            self.assertEqual(index[3].answer_ids, [0, 1, 2, 3, 4, 5, 6])
        finally:
            os.unlink(temp_path)

    def test_build_skips_empty_question_id(self):
        """Test that rows with empty question_id are skipped."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.appended', delete=False, encoding='latin-1'
        ) as f:
            f.write('4,2,What is your gender?,,Male^Female,S,1,0^1\n')
            f.write('5,2,No question id,,A^B,S,,\n')  # Empty question_id
            temp_path = f.name

        try:
            index = build_appended_index(temp_path)
            self.assertEqual(len(index), 1)
            self.assertIn(1, index)
        finally:
            os.unlink(temp_path)

    def test_build_handles_multiple_question_types(self):
        """Test handling F, S, and M question types."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.appended', delete=False, encoding='latin-1'
        ) as f:
            f.write('1,0,Free form?,,answer,F,10,\n')
            f.write('2,2,Single?,,A^B,S,20,0^1\n')
            f.write('3,3,Multiple?,,X^Y^Z,M,30,0^1^2\n')
            temp_path = f.name

        try:
            index = build_appended_index(temp_path)

            self.assertEqual(index[10].question_type, 'F')
            self.assertEqual(index[20].question_type, 'S')
            self.assertEqual(index[30].question_type, 'M')
        finally:
            os.unlink(temp_path)


class TestTransformAnswerSingle(unittest.TestCase):
    """Tests for transform_answer_single function."""

    def test_transform_basic(self):
        """Test basic single answer transformation."""
        # data_input=1, answer_ids=[10, 20], common=[10, 20, 30]
        # answer_id = answer_ids[0] = 10
        # position in common = 0 -> output = 1
        result = transform_answer_single("1", [10, 20], [10, 20, 30])
        self.assertEqual(result, "1")

    def test_transform_different_position(self):
        """Test transformation where positions differ."""
        # data_input=2, answer_ids=[20, 10], common=[10, 20, 30]
        # answer_id = answer_ids[1] = 10
        # position in common = 0 -> output = 1
        result = transform_answer_single("2", [20, 10], [10, 20, 30])
        self.assertEqual(result, "1")

    def test_transform_zero_unchanged(self):
        """Test that '0' is passed through unchanged."""
        result = transform_answer_single("0", [10, 20], [10, 20, 30])
        self.assertEqual(result, "0")

    def test_transform_empty_unchanged(self):
        """Test that empty string is passed through unchanged."""
        result = transform_answer_single("", [10, 20], [10, 20, 30])
        self.assertEqual(result, "")

    def test_transform_nonnumeric_unchanged(self):
        """Test that non-numeric values are passed through unchanged."""
        result = transform_answer_single("abc", [10, 20], [10, 20, 30])
        self.assertEqual(result, "abc")

    def test_transform_negative_unchanged(self):
        """Test that negative values are passed through unchanged."""
        result = transform_answer_single("-1", [10, 20], [10, 20, 30])
        self.assertEqual(result, "-1")

    def test_transform_out_of_bounds(self):
        """Test that out of bounds indices return original value."""
        result = transform_answer_single("5", [10, 20], [10, 20, 30])
        self.assertEqual(result, "5")

    def test_transform_answer_not_in_common(self):
        """Test that answer_id not in common list returns original."""
        # data_input=1, answer_ids=[99, 20], common=[10, 20, 30]
        # answer_id = 99 not in common
        result = transform_answer_single("1", [99, 20], [10, 20, 30])
        self.assertEqual(result, "1")


class TestTransformAnswerMultiple(unittest.TestCase):
    """Tests for transform_answer_multiple function."""

    def test_transform_basic(self):
        """Test basic multiple answer transformation."""
        # data_input="1^2", answer_ids=[10, 20, 30], common=[10, 20, 30]
        result = transform_answer_multiple("1^2", [10, 20, 30], [10, 20, 30])
        self.assertEqual(result, "1^2")

    def test_transform_reordered(self):
        """Test transformation with reordered common answers."""
        # data_input="1^2", answer_ids=[20, 10], common=[10, 20, 30]
        # answer_id[0]=20 -> position in common=1 -> output=2
        # answer_id[1]=10 -> position in common=0 -> output=1
        result = transform_answer_multiple("1^2", [20, 10], [10, 20, 30])
        self.assertEqual(result, "2^1")

    def test_transform_single_value(self):
        """Test transformation of single value in multiple format."""
        result = transform_answer_multiple("2", [10, 20], [10, 20, 30])
        self.assertEqual(result, "2")

    def test_transform_empty_unchanged(self):
        """Test that empty string is passed through unchanged."""
        result = transform_answer_multiple("", [10, 20], [10, 20, 30])
        self.assertEqual(result, "")

    def test_transform_invalid_format_unchanged(self):
        """Test that invalid format is passed through unchanged."""
        result = transform_answer_multiple("abc^def", [10, 20], [10, 20, 30])
        self.assertEqual(result, "abc^def")

    def test_transform_zero_in_list_unchanged(self):
        """Test that list containing 0 is passed through unchanged."""
        result = transform_answer_multiple("1^0^2", [10, 20, 30], [10, 20, 30])
        self.assertEqual(result, "1^0^2")

    def test_transform_negative_in_list_unchanged(self):
        """Test that list containing negative is passed through unchanged."""
        result = transform_answer_multiple("1^-1^2", [10, 20, 30], [10, 20, 30])
        self.assertEqual(result, "1^-1^2")

    def test_transform_mixed_valid_out_of_bounds(self):
        """Test with some values in bounds and some out of bounds."""
        # data_input="1^5", answer_ids=[10, 20], common=[10, 20, 30]
        # value 1 -> answer_id=10 -> position=0 -> output=1
        # value 5 -> out of bounds -> keep original "5"
        result = transform_answer_multiple("1^5", [10, 20], [10, 20, 30])
        self.assertEqual(result, "1^5")


class TestGenerateCommonPip(unittest.TestCase):
    """Tests for generate_common_pip function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.common_questions_path = os.path.join(self.temp_dir, "CommonQuestions.csv")
        self.output_path = os.path.join(self.temp_dir, "CommonData.pip")

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_common_questions(self, rows):
        """Helper to create CommonQuestions.csv."""
        with open(self.common_questions_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['question_id', 'master_question_text', 'common_answer_ids'])
            for row in rows:
                writer.writerow(row)

    def _create_appended_file(self, name, rows):
        """Helper to create appended file."""
        path = os.path.join(self.temp_dir, name)
        with open(path, 'w', encoding='latin-1', newline='') as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        return path

    def _create_pip_file(self, name, rows):
        """Helper to create pip file."""
        path = os.path.join(self.temp_dir, name)
        with open(path, 'w', encoding='latin-1') as f:
            for row in rows:
                f.write('|'.join(row) + '\n')
        return path

    def test_generate_basic(self):
        """Test basic pip generation with single file."""
        # Create CommonQuestions.csv
        self._create_common_questions([
            [1, "Gender?", "0^1"],
            [2, "Age?", "0^1^2"],
        ])

        # Create appended file
        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            # parms_qn, total, text, empty, answers, type, question_id, answer_ids
            [1, 2, "Gender?", "", "Male^Female", "S", 1, "0^1"],
            [2, 3, "Age?", "", "18-30^31-50^51+", "S", 2, "0^1^2"],
        ])

        # Create pip file
        pip_path = self._create_pip_file("test.pip", [
            ["1", "2"],  # Row 1: Gender=1, Age=2
            ["2", "1"],  # Row 2: Gender=2, Age=1
        ])

        # Create control entry
        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        # Generate
        result = generate_common_pip(self.common_questions_path, entries, self.output_path)

        self.assertEqual(result, self.output_path)
        self.assertTrue(os.path.exists(self.output_path))

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 2)
        # Last column is study_date
        self.assertEqual(lines[0].strip(), "1|2|2026-01-01")
        self.assertEqual(lines[1].strip(), "2|1|2026-01-01")

    def test_generate_type_f_passthrough(self):
        """Test that type F questions pass through unchanged."""
        self._create_common_questions([
            [1, "Free form question", ""],
        ])

        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            [1, 0, "Free form?", "", "", "F", 1, ""],
        ])

        pip_path = self._create_pip_file("test.pip", [
            ["any text value"],
            ["another value"],
        ])

        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        # Last column is study_date
        self.assertEqual(lines[0].strip(), "any text value|2026-01-01")
        self.assertEqual(lines[1].strip(), "another value|2026-01-01")

    def test_generate_type_s_transform(self):
        """Test that type S questions are transformed correctly."""
        self._create_common_questions([
            [1, "Question", "10^20^30"],  # common answer IDs
        ])

        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            # answer_ids are in different order than common
            [1, 3, "Question", "", "A^B^C", "S", 1, "20^10^30"],
        ])

        pip_path = self._create_pip_file("test.pip", [
            ["1"],  # Selects answer_ids[0]=20 -> position in common=1 -> output=2
            ["2"],  # Selects answer_ids[1]=10 -> position in common=0 -> output=1
            ["3"],  # Selects answer_ids[2]=30 -> position in common=2 -> output=3
        ])

        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        # Last column is study_date
        self.assertEqual(lines[0].strip(), "2|2026-01-01")
        self.assertEqual(lines[1].strip(), "1|2026-01-01")
        self.assertEqual(lines[2].strip(), "3|2026-01-01")

    def test_generate_type_m_transform(self):
        """Test that type M questions are transformed correctly."""
        self._create_common_questions([
            [1, "Multi question", "10^20^30"],
        ])

        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            [1, 3, "Multi?", "", "A^B^C", "M", 1, "20^10^30"],
        ])

        pip_path = self._create_pip_file("test.pip", [
            ["1^2"],  # Selects 20,10 -> positions 1,0 -> output 2^1
            ["2^3"],  # Selects 10,30 -> positions 0,2 -> output 1^3
        ])

        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        # Last column is study_date
        self.assertEqual(lines[0].strip(), "2^1|2026-01-01")
        self.assertEqual(lines[1].strip(), "1^3|2026-01-01")

    def test_generate_empty_common_questions(self):
        """Test with empty CommonQuestions.csv."""
        self._create_common_questions([])

        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            [1, 2, "Q?", "", "A^B", "S", 1, "0^1"],
        ])

        pip_path = self._create_pip_file("test.pip", [["1"]])

        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        # Output file should exist but be empty
        self.assertTrue(os.path.exists(self.output_path))
        with open(self.output_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "")

    def test_generate_question_not_in_appended(self):
        """Test handling when question_id is not in appended file."""
        self._create_common_questions([
            [1, "Question 1", "0^1"],
            [99, "Question 99", "0^1"],  # Not in appended
        ])

        parms_path = os.path.join(self.temp_dir, "test_parms")
        self._create_appended_file("test_parms.appended", [
            [1, 2, "Q1?", "", "A^B", "S", 1, "0^1"],
        ])

        pip_path = self._create_pip_file("test.pip", [["1"]])

        entries = [ControlEntry(
            study_name="test",
            study_date="2026-01-01",
            parms_file_name=parms_path,
            pip_file_name=pip_path,
            parmedit_file_name="",
            upload_file_name="",
        )]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        # Should have three columns: q1 value, empty q99, and study_date
        self.assertEqual(lines[0].strip(), "1||2026-01-01")

    def test_generate_multiple_pip_files(self):
        """Test generating from multiple pip files with different study_dates."""
        self._create_common_questions([
            [1, "Question", "0^1"],
        ])

        # First file
        parms_path1 = os.path.join(self.temp_dir, "parms1")
        self._create_appended_file("parms1.appended", [
            [1, 2, "Q?", "", "A^B", "S", 1, "0^1"],
        ])
        pip_path1 = self._create_pip_file("file1.pip", [["1"], ["2"]])

        # Second file
        parms_path2 = os.path.join(self.temp_dir, "parms2")
        self._create_appended_file("parms2.appended", [
            [1, 2, "Q?", "", "A^B", "S", 1, "0^1"],
        ])
        pip_path2 = self._create_pip_file("file2.pip", [["2"], ["1"]])

        entries = [
            ControlEntry(
                study_name="test",
                study_date="2025-01-01",
                parms_file_name=parms_path1,
                pip_file_name=pip_path1,
                parmedit_file_name="",
                upload_file_name="",
            ),
            ControlEntry(
                study_name="test",
                study_date="2025-04-01",
                parms_file_name=parms_path2,
                pip_file_name=pip_path2,
                parmedit_file_name="",
                upload_file_name="",
            ),
        ]

        generate_common_pip(self.common_questions_path, entries, self.output_path)

        with open(self.output_path, 'r') as f:
            lines = f.readlines()

        # Should have 4 rows total (2 from each file)
        self.assertEqual(len(lines), 4)

        # First 2 rows from file1 should have study_date 2025-01-01
        self.assertEqual(lines[0].strip(), "1|2025-01-01")
        self.assertEqual(lines[1].strip(), "2|2025-01-01")

        # Next 2 rows from file2 should have study_date 2025-04-01
        self.assertEqual(lines[2].strip(), "2|2025-04-01")
        self.assertEqual(lines[3].strip(), "1|2025-04-01")


if __name__ == '__main__':
    unittest.main()
