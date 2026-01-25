"""Tests for append_agile_brain.py"""

import csv
import os
import tempfile
import unittest

from append_agile_brain import (
    LayoutRow,
    AppendStatistics,
    load_layout_file,
    determine_question_type,
    load_agile_brain_index,
    find_sid_psid_columns,
    transform_agile_value,
    append_common_parms,
    append_common_data,
)


class TestLayoutRow(unittest.TestCase):
    """Tests for LayoutRow dataclass."""

    def test_create_layout_row(self):
        """Test creating a LayoutRow."""
        row = LayoutRow(
            field_number=1852,
            question_id="AgileBrainAlertLevel",
            question_text="Binary flag description",
            answer_code="Binary (0 or 1)"
        )
        self.assertEqual(row.field_number, 1852)
        self.assertEqual(row.question_id, "AgileBrainAlertLevel")
        self.assertEqual(row.question_text, "Binary flag description")
        self.assertEqual(row.answer_code, "Binary (0 or 1)")


class TestAppendStatistics(unittest.TestCase):
    """Tests for AppendStatistics dataclass."""

    def test_create_statistics(self):
        """Test creating AppendStatistics."""
        stats = AppendStatistics(
            parms_rows_appended=100,
            data_columns_appended=100,
            data_rows_matched=5000,
            data_rows_unmatched=1000,
            total_parms_rows=373,
            total_data_rows=5000
        )
        self.assertEqual(stats.parms_rows_appended, 100)
        self.assertEqual(stats.data_columns_appended, 100)
        self.assertEqual(stats.data_rows_matched, 5000)
        self.assertEqual(stats.data_rows_unmatched, 1000)


class TestLoadLayoutFile(unittest.TestCase):
    """Tests for load_layout_file function."""

    def test_load_layout_file_basic(self):
        """Test loading a basic layout file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Header1,Header2,Header3,Header4\n")
            f.write("Row2,Data,Data,Data\n")
            f.write("Row3,Data,Data,Data\n")
            f.write("1852,AgileBrainAlertLevel,Description,Binary (0 or 1)\n")
            f.write("1853,AgileBrainStateNumber,Description,Integer (1-10)\n")
            filepath = f.name

        try:
            rows = load_layout_file(filepath)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].field_number, 1852)
            self.assertEqual(rows[0].question_id, "AgileBrainAlertLevel")
            self.assertEqual(rows[1].field_number, 1853)
        finally:
            os.unlink(filepath)

    def test_load_layout_file_skips_first_three_rows(self):
        """Test that the first 3 rows are skipped."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Header1,Header2,Header3,Header4\n")
            f.write("Header2,Data,Data,Data\n")
            f.write("Header3,Data,Data,Data\n")
            f.write("1852,ID1,Text1,Code1\n")
            filepath = f.name

        try:
            rows = load_layout_file(filepath)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].field_number, 1852)
        finally:
            os.unlink(filepath)

    def test_load_layout_file_handles_utf8_bom(self):
        """Test loading file with UTF-8 BOM."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            # Write UTF-8 BOM
            f.write(b'\xef\xbb\xbf')
            f.write(b"Header1,Header2,Header3,Header4\n")
            f.write(b"Row2,Data,Data,Data\n")
            f.write(b"Row3,Data,Data,Data\n")
            f.write(b"1852,TestID,TestText,TestCode\n")
            filepath = f.name

        try:
            rows = load_layout_file(filepath)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].field_number, 1852)
        finally:
            os.unlink(filepath)

    def test_load_layout_file_stops_at_row_103(self):
        """Test that loading stops at row 103 (100 data rows max)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("H1,H2,H3,H4\n")
            f.write("H1,H2,H3,H4\n")
            f.write("H1,H2,H3,H4\n")
            # Write 105 data rows (rows 4-108)
            for i in range(105):
                f.write(f"{1852+i},ID{i},Text{i},Code{i}\n")
            filepath = f.name

        try:
            rows = load_layout_file(filepath)
            # Should only have 100 rows (rows 4-103)
            self.assertEqual(len(rows), 100)
            self.assertEqual(rows[-1].field_number, 1951)
        finally:
            os.unlink(filepath)


class TestDetermineQuestionType(unittest.TestCase):
    """Tests for determine_question_type function."""

    def test_binary_answer_code(self):
        """Test Binary (0 or 1) mapping."""
        result = determine_question_type("Binary (0 or 1)")
        self.assertEqual(result, ("Yes^No", 2, "S"))

    def test_integer_answer_code(self):
        """Test Integer (1-10) mapping."""
        result = determine_question_type("Integer (1-10)")
        self.assertEqual(result, ("1^2^3^4^5^6^7^8^9^10", 10, "S"))

    def test_numeric_answer_code(self):
        """Test Numeric (0-1) mapping (free-form)."""
        result = determine_question_type("Numeric (0-1)")
        self.assertEqual(result, ("", 1, "F"))

    def test_unknown_answer_code(self):
        """Test unknown answer code defaults to free-form."""
        result = determine_question_type("Some other code")
        self.assertEqual(result, ("", 1, "F"))


class TestLoadAgileBrainIndex(unittest.TestCase):
    """Tests for load_agile_brain_index function."""

    def test_load_basic_index(self):
        """Test loading a basic Agile Brain index."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Create a CSV with enough columns (need 1951 columns, 0-indexed 1950)
            # Column 1851 (0-indexed 1850) is ID, columns 1852-1951 are data
            header = ','.join([f"Col{i}" for i in range(1952)])
            f.write(header + '\n')

            # Data row with ID in column 1851
            row = [''] * 1952
            row[1850] = 'PROSPER_ID_1'
            row[1851] = 'val1'  # Column 1852
            row[1852] = 'val2'  # Column 1853
            row[1950] = 'val100'  # Column 1951
            f.write(','.join(row) + '\n')
            filepath = f.name

        try:
            index = load_agile_brain_index(filepath)
            self.assertIn('PROSPER_ID_1', index)
            self.assertEqual(len(index['PROSPER_ID_1']), 100)
            self.assertEqual(index['PROSPER_ID_1'][0], 'val1')
            self.assertEqual(index['PROSPER_ID_1'][1], 'val2')
            self.assertEqual(index['PROSPER_ID_1'][99], 'val100')
        finally:
            os.unlink(filepath)

    def test_load_multiple_ids(self):
        """Test loading multiple Prosper IDs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            header = ','.join([f"Col{i}" for i in range(1952)])
            f.write(header + '\n')

            for pid in ['ID_A', 'ID_B', 'ID_C']:
                row = [''] * 1952
                row[1850] = pid
                row[1851] = f'{pid}_data'
                f.write(','.join(row) + '\n')
            filepath = f.name

        try:
            index = load_agile_brain_index(filepath)
            self.assertEqual(len(index), 3)
            self.assertIn('ID_A', index)
            self.assertIn('ID_B', index)
            self.assertIn('ID_C', index)
        finally:
            os.unlink(filepath)

    def test_load_empty_file(self):
        """Test loading an empty file (header only)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            header = ','.join([f"Col{i}" for i in range(1952)])
            f.write(header + '\n')
            filepath = f.name

        try:
            index = load_agile_brain_index(filepath)
            self.assertEqual(len(index), 0)
        finally:
            os.unlink(filepath)


class TestFindSidPsidColumns(unittest.TestCase):
    """Tests for find_sid_psid_columns function."""

    def test_find_sid_psid_columns(self):
        """Test finding SID and psid column numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('1,0,Question1,,,F\n')
            f.write('250,0,SID,,,F\n')
            f.write('251,0,psid,,,F\n')
            f.write('252,0,Other,,,F\n')
            filepath = f.name

        try:
            sid_col, psid_col = find_sid_psid_columns(filepath)
            self.assertEqual(sid_col, 250)
            self.assertEqual(psid_col, 251)
        finally:
            os.unlink(filepath)

    def test_default_columns_when_not_found(self):
        """Test default column numbers when SID/psid not found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('1,0,Question1,,,F\n')
            f.write('2,0,Question2,,,F\n')
            filepath = f.name

        try:
            sid_col, psid_col = find_sid_psid_columns(filepath)
            self.assertEqual(sid_col, 250)
            self.assertEqual(psid_col, 251)
        finally:
            os.unlink(filepath)

    def test_only_sid_found(self):
        """Test when only SID is found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('100,0,SID,,,F\n')
            f.write('101,0,Other,,,F\n')
            filepath = f.name

        try:
            sid_col, psid_col = find_sid_psid_columns(filepath)
            self.assertEqual(sid_col, 100)
            self.assertEqual(psid_col, 251)
        finally:
            os.unlink(filepath)


class TestTransformAgileValue(unittest.TestCase):
    """Tests for transform_agile_value function."""

    def test_transform_column_1852_value_0(self):
        """Test transforming value '0' in column 1852 (index 0)."""
        result = transform_agile_value("0", 0)
        self.assertEqual(result, "2")

    def test_transform_column_1852_value_1(self):
        """Test transforming value '1' in column 1852 (index 0)."""
        result = transform_agile_value("1", 0)
        self.assertEqual(result, "1")

    def test_no_transform_other_columns(self):
        """Test that other columns are not transformed."""
        result = transform_agile_value("0", 1)
        self.assertEqual(result, "0")

        result = transform_agile_value("0.75", 5)
        self.assertEqual(result, "0.75")


class TestAppendCommonParms(unittest.TestCase):
    """Tests for append_common_parms function."""

    def test_append_basic_rows(self):
        """Test appending basic rows to parms file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "output", "CommonParmsAppended.csv")

            # Create input file
            with open(parms_path, 'w') as f:
                f.write('1,2,Question1,,Yes^No,S\n')
                f.write('2,3,Question2,,A^B^C,S\n')

            # Create layout rows
            layout_rows = [
                LayoutRow(1852, "ID1", "Text1", "Binary (0 or 1)"),
                LayoutRow(1853, "ID2", "Text2", "Integer (1-10)"),
            ]

            count = append_common_parms(parms_path, layout_rows, output_path)
            self.assertEqual(count, 2)

            # Verify output
            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 4)
            self.assertIn("3,2,ID1: Text1,,Yes^No,S", lines[2])
            self.assertIn("4,10,ID2: Text2,,1^2^3^4^5^6^7^8^9^10,S", lines[3])

    def test_append_preserves_existing_rows(self):
        """Test that existing rows are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "output", "CommonParmsAppended.csv")

            with open(parms_path, 'w') as f:
                f.write('1,0,Zip:,,,F\n')
                f.write('2,2,Gender,,Male^Female,S\n')

            layout_rows = [
                LayoutRow(1852, "NewQ", "New Question", "Numeric (0-1)"),
            ]

            append_common_parms(parms_path, layout_rows, output_path)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 3)
            self.assertIn("Zip:", lines[0])
            self.assertIn("Gender", lines[1])

    def test_append_empty_layout(self):
        """Test appending with empty layout list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "output", "CommonParmsAppended.csv")

            with open(parms_path, 'w') as f:
                f.write('1,2,Q1,,A^B,S\n')

            count = append_common_parms(parms_path, [], output_path)
            self.assertEqual(count, 0)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)

    def test_append_sequential_numbering(self):
        """Test that question numbers are sequential starting from next."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "output", "CommonParmsAppended.csv")

            with open(parms_path, 'w') as f:
                for i in range(1, 274):
                    f.write(f'{i},0,Q{i},,,F\n')

            layout_rows = [
                LayoutRow(1852, "Q274", "Text", "Binary (0 or 1)"),
                LayoutRow(1853, "Q275", "Text", "Binary (0 or 1)"),
            ]

            append_common_parms(parms_path, layout_rows, output_path)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 275)
            self.assertTrue(lines[-2].startswith('274,'))
            self.assertTrue(lines[-1].startswith('275,'))

    def test_append_creates_output_directory(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "new", "nested", "dir", "output.csv")

            with open(parms_path, 'w') as f:
                f.write('1,0,Q1,,,F\n')

            layout_rows = [LayoutRow(1852, "Q", "T", "Binary (0 or 1)")]
            append_common_parms(parms_path, layout_rows, output_path)

            self.assertTrue(os.path.exists(output_path))

    def test_append_free_form_question(self):
        """Test appending a free-form question."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parms_path = os.path.join(tmpdir, "CommonParms.csv")
            output_path = os.path.join(tmpdir, "output", "CommonParmsAppended.csv")

            with open(parms_path, 'w') as f:
                f.write('1,0,Q1,,,F\n')

            layout_rows = [
                LayoutRow(1852, "NumericQ", "Score", "Numeric (0-1)"),
            ]

            append_common_parms(parms_path, layout_rows, output_path)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertIn("2,1,NumericQ: Score,,,F", lines[1])


class TestAppendCommonData(unittest.TestCase):
    """Tests for append_common_data function."""

    def test_append_matched_rows(self):
        """Test appending data to matched rows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "output", "CommonDataAppended.pip")

            # Create input data file with SID in column 2 (1-based)
            with open(data_path, 'w') as f:
                f.write('data1|ID_A|data3\n')
                f.write('data1|ID_B|data3\n')

            # Create index
            agile_index = {
                'ID_A': ['0', 'val2'],  # 0 should become 2
                'ID_B': ['1', 'val2'],  # 1 stays 1
            }

            matched, unmatched = append_common_data(
                data_path, agile_index, 2, 3, output_path
            )

            self.assertEqual(matched, 2)
            self.assertEqual(unmatched, 0)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)
            self.assertIn('|2|val2', lines[0])  # 0 transformed to 2
            self.assertIn('|1|val2', lines[1])  # 1 stays 1

    def test_unmatched_rows_omitted(self):
        """Test that unmatched rows are omitted from output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "output", "CommonDataAppended.pip")

            with open(data_path, 'w') as f:
                f.write('data1|ID_A|data3\n')
                f.write('data1|ID_UNKNOWN|data3\n')

            agile_index = {
                'ID_A': ['1', 'val2'],
            }

            matched, unmatched = append_common_data(
                data_path, agile_index, 2, 3, output_path
            )

            self.assertEqual(matched, 1)
            self.assertEqual(unmatched, 1)

            with open(output_path, 'r') as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)

    def test_match_by_psid(self):
        """Test matching by psid when SID doesn't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "output", "CommonDataAppended.pip")

            # Column 2 is SID (empty), column 3 is psid (has ID)
            with open(data_path, 'w') as f:
                f.write('data1||ID_A\n')

            agile_index = {
                'ID_A': ['1', 'val2'],
            }

            matched, unmatched = append_common_data(
                data_path, agile_index, 2, 3, output_path
            )

            self.assertEqual(matched, 1)
            self.assertEqual(unmatched, 0)

    def test_empty_data_file(self):
        """Test with empty input data file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "output", "CommonDataAppended.pip")

            with open(data_path, 'w') as f:
                pass  # Empty file

            agile_index = {'ID_A': ['1', 'val2']}

            matched, unmatched = append_common_data(
                data_path, agile_index, 2, 3, output_path
            )

            self.assertEqual(matched, 0)
            self.assertEqual(unmatched, 0)

    def test_creates_output_directory(self):
        """Test that output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "new", "nested", "output.pip")

            with open(data_path, 'w') as f:
                f.write('data1|ID_A|data3\n')

            agile_index = {'ID_A': ['1']}

            append_common_data(data_path, agile_index, 2, 3, output_path)

            self.assertTrue(os.path.exists(output_path))

    def test_preserves_existing_columns(self):
        """Test that existing columns are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = os.path.join(tmpdir, "CommonData.pip")
            output_path = os.path.join(tmpdir, "output", "CommonDataAppended.pip")

            with open(data_path, 'w') as f:
                f.write('col1|ID_A|col3|col4|col5\n')

            agile_index = {'ID_A': ['0', 'new2']}  # 0 will be transformed to 2

            append_common_data(data_path, agile_index, 2, 3, output_path)

            with open(output_path, 'r') as f:
                line = f.readline().strip()
            parts = line.split('|')
            self.assertEqual(parts[0], 'col1')
            self.assertEqual(parts[1], 'ID_A')
            self.assertEqual(parts[2], 'col3')
            self.assertEqual(parts[3], 'col4')
            self.assertEqual(parts[4], 'col5')
            self.assertEqual(parts[5], '2')  # 0 -> 2 transformation
            self.assertEqual(parts[6], 'new2')


class TestIntegration(unittest.TestCase):
    """Integration tests for the full workflow."""

    def test_full_workflow(self):
        """Test the full append workflow with realistic data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create layout file
            layout_path = os.path.join(tmpdir, "layout.csv")
            with open(layout_path, 'w') as f:
                f.write("H1,H2,H3,H4\n")
                f.write("H1,H2,H3,H4\n")
                f.write("H1,H2,H3,H4\n")
                f.write("1852,AlertLevel,At-risk flag,Binary (0 or 1)\n")
                f.write("1853,StateNum,Emotional state,Integer (1-10)\n")
                f.write("1854,Score,Activation score,Numeric (0-1)\n")

            # Load layout
            layout_rows = load_layout_file(layout_path)
            self.assertEqual(len(layout_rows), 3)

            # Create parms file
            parms_path = os.path.join(tmpdir, "parms.csv")
            with open(parms_path, 'w') as f:
                f.write('1,0,Zip,,,F\n')
                f.write('2,2,Gender,,Male^Female,S\n')

            # Append parms
            output_parms = os.path.join(tmpdir, "output", "parms_appended.csv")
            count = append_common_parms(parms_path, layout_rows, output_parms)
            self.assertEqual(count, 3)

            # Verify parms output
            with open(output_parms, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[2][0], '3')  # Sequential numbering
            self.assertEqual(rows[2][1], '2')  # Binary has 2 answers
            self.assertEqual(rows[3][1], '10')  # Integer has 10 answers
            self.assertEqual(rows[4][1], '1')  # Numeric is free-form (defaults to 1)

    def test_end_to_end_with_actual_files(self):
        """Test with actual project files if they exist."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        layout_path = os.path.join(base_dir, "AgileBrainsAppend", "Agile_Brain_Data_Layout.csv")

        if os.path.exists(layout_path):
            layout_rows = load_layout_file(layout_path)
            self.assertEqual(len(layout_rows), 100)
            self.assertEqual(layout_rows[0].field_number, 1852)
            self.assertEqual(layout_rows[0].question_id, "AgileBrainAlertLevel")
            self.assertEqual(layout_rows[-1].field_number, 1951)


class TestMain(unittest.TestCase):
    """Tests for main function."""

    def test_output_files_exist(self):
        """Test that output files exist after running main (if inputs exist)."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_parms = os.path.join(base_dir, "AgileBrainsAppend", "CommonParmsAppended.csv")
        output_data = os.path.join(base_dir, "AgileBrainsAppend", "CommonDataAppended.pip")

        # Only check if the program has been run
        if os.path.exists(output_parms):
            with open(output_parms, 'r') as f:
                lines = f.readlines()
            # 274 questions (273 + Study Date) + 100 Agile Brain = 374
            self.assertEqual(len(lines), 374)

        if os.path.exists(output_data):
            with open(output_data, 'r') as f:
                first_line = f.readline()
            columns = first_line.split('|')
            # 274 columns (273 + study_date) + 100 Agile Brain = 374
            self.assertEqual(len(columns), 374)

    def test_output_parms_structure(self):
        """Test the structure of output parms file."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_parms = os.path.join(base_dir, "AgileBrainsAppend", "CommonParmsAppended.csv")

        if os.path.exists(output_parms):
            with open(output_parms, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Row 274 (index 273) is the Study Date row
            row_274 = rows[273]
            self.assertEqual(row_274[0], '274')
            self.assertEqual(row_274[2], 'Study Date')
            self.assertEqual(row_274[5], 'F')

            # Row 275 (index 274) is the first Agile Brain row
            row_275 = rows[274]
            self.assertEqual(row_275[0], '275')
            self.assertEqual(row_275[1], '2')  # Binary has 2 answers
            self.assertIn("AgileBrainAlertLevel", row_275[2])
            self.assertEqual(row_275[4], 'Yes^No')
            self.assertEqual(row_275[5], 'S')


if __name__ == '__main__':
    unittest.main()
