"""CLI integration tests for combinewaves.py."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from combinewaves import main


class TestMainArgumentValidation:
    """Test command-line argument validation."""

    def test_no_arguments(self, capsys):
        """Returns 1 when no args provided."""
        result = main([])

        assert result == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.err

    def test_too_many_arguments(self, capsys):
        """Returns 1 when too many args provided."""
        result = main(["arg1", "arg2"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.err


class TestMainControlFileErrors:
    """Test control file error handling."""

    def test_control_file_not_found(self, capsys):
        """Returns 1 when control file doesn't exist."""
        result = main(["/nonexistent/path/control.txt"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Control file not found" in captured.err

    def test_control_file_invalid_format(self, capsys):
        """Returns 1 when control file has bad format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = os.path.join(tmpdir, "bad_control.txt")
            with open(control_path, 'w') as f:
                # Only 3 fields instead of required 6
                f.write("study,date,parms_only\n")

            result = main([control_path])

            assert result == 1
            captured = capsys.readouterr()
            assert "Invalid control file format" in captured.err

    def test_control_file_empty(self, capsys):
        """Returns 0 when control file is empty (warning only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = os.path.join(tmpdir, "empty_control.txt")
            with open(control_path, 'w') as f:
                f.write("")  # Empty file

            result = main([control_path])

            assert result == 0
            captured = capsys.readouterr()
            assert "Control file is empty" in captured.err


class TestMainWorkflow:
    """Test the main workflow with mocked dependencies."""

    @patch('combinewaves.generate_common_parms')
    @patch('combinewaves.generate_common_pip')
    @patch('combinewaves.generate_common_questions')
    @patch('combinewaves.process_parms_file')
    @patch('combinewaves.load_parmedit_appended')
    @patch('combinewaves.create_parmedit_appended')
    @patch('combinewaves.DatabaseClient')
    def test_successful_run_mocked(
        self,
        mock_db_client,
        mock_create_parmedit_appended,
        mock_load_parmedit_appended,
        mock_process_parms_file,
        mock_generate_common_questions,
        mock_generate_common_pip,
        mock_generate_common_parms,
        capsys
    ):
        """Full run with all external dependencies mocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create control file
            control_path = os.path.join(tmpdir, "test_control.txt")
            parms_file = os.path.join(tmpdir, "test_parms.csv")
            pip_file = os.path.join(tmpdir, "test_data.pip")
            parmedit_file = os.path.join(tmpdir, "test_parmedit.csv")
            upload_file = os.path.join(tmpdir, "test_UPLOAD.csv")
            appended_file = os.path.join(tmpdir, "test_parms.csv.appended")
            parmedit_appended_file = os.path.join(tmpdir, "test_parmedit_APPENDED.csv")
            common_questions_file = os.path.join(tmpdir, "CommonQuestions.csv")
            common_pip_file = os.path.join(tmpdir, "CommonData.pip")
            common_parms_file = os.path.join(tmpdir, "CommonParms.csv")

            with open(control_path, 'w') as f:
                f.write(f"TestStudy,2025-01,{parms_file},{pip_file},{parmedit_file},{upload_file}\n")

            # Create dummy input files
            with open(parms_file, 'w') as f:
                f.write("1,2,Question text,,ans1^ans2,S\n")
            with open(pip_file, 'w') as f:
                f.write("1|2|3\n")
            with open(parmedit_file, 'w') as f:
                f.write("1,,Question text\n")
            with open(upload_file, 'w') as f:
                f.write("question_number,col2,col3,question_text\n")
                f.write("1,x,y,Question text\n")

            # Setup mocks
            mock_db_instance = MagicMock()
            mock_db_client.return_value.__enter__ = MagicMock(return_value=mock_db_instance)
            mock_db_client.return_value.__exit__ = MagicMock(return_value=False)

            mock_create_parmedit_appended.return_value = parmedit_appended_file
            mock_load_parmedit_appended.return_value = MagicMock()
            mock_process_parms_file.return_value = appended_file

            # Create the appended file that process_parms_file would create
            with open(appended_file, 'w') as f:
                f.write("1,2,Question text,,ans1^ans2,S,100,1^2\n")

            # Mock generate_common_questions to create CommonQuestions.csv
            def create_common_questions(*args, **kwargs):
                with open(common_questions_file, 'w') as f:
                    f.write("common_question_id,master_question_text,common_answer_ids\n")
                    f.write("100,Question text,1^2\n")
                return common_questions_file

            mock_generate_common_questions.side_effect = create_common_questions

            # Mock generate_common_pip to create CommonData.pip
            def create_common_pip(*args, **kwargs):
                with open(common_pip_file, 'w') as f:
                    f.write("1|2\n")
                return common_pip_file

            mock_generate_common_pip.side_effect = create_common_pip

            # Mock generate_common_parms to create CommonParms.csv
            mock_generate_common_parms.return_value = common_parms_file

            # Change to tmpdir so output files are created there
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = main([control_path])
            finally:
                os.chdir(original_cwd)

            # Verify success
            assert result == 0

            # Verify mocks were called
            mock_create_parmedit_appended.assert_called_once_with(
                parmedit_file,
                upload_file
            )
            mock_load_parmedit_appended.assert_called_once_with(parmedit_appended_file)
            mock_process_parms_file.assert_called_once()
            mock_generate_common_questions.assert_called_once()
            mock_generate_common_pip.assert_called_once()
            mock_generate_common_parms.assert_called_once()

            # Verify output messages
            captured = capsys.readouterr()
            assert "Step 1:" in captured.out
            assert "Step 2:" in captured.out
            assert "Step 3:" in captured.out
            assert "Step 4:" in captured.out
