"""Tests for control_file module."""

import os
import tempfile
import pytest

from control_file import ControlEntry, read_control_file


class TestControlEntry:
    """Tests for ControlEntry dataclass."""

    def test_create_entry(self):
        """Create a ControlEntry with all fields."""
        entry = ControlEntry(
            study_name="StudyA",
            study_date="2026-01-15",
            parms_file_name="parms.csv",
            pip_file_name="data.pip",
            parmedit_file_name="parmedit.csv",
            upload_file_name="upload.csv"
        )

        assert entry.study_name == "StudyA"
        assert entry.study_date == "2026-01-15"
        assert entry.parms_file_name == "parms.csv"
        assert entry.pip_file_name == "data.pip"
        assert entry.parmedit_file_name == "parmedit.csv"
        assert entry.upload_file_name == "upload.csv"


class TestReadControlFile:
    """Tests for read_control_file function."""

    def test_read_single_line(self):
        """Read control file with single line."""
        content = "StudyA,2026-01-15,parms.csv,data.pip,parmedit.csv,upload.csv\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries = list(read_control_file(temp_path))

            assert len(entries) == 1
            assert entries[0].study_name == "StudyA"
            assert entries[0].study_date == "2026-01-15"
            assert entries[0].parms_file_name == "parms.csv"
            assert entries[0].pip_file_name == "data.pip"
            assert entries[0].parmedit_file_name == "parmedit.csv"
            assert entries[0].upload_file_name == "upload.csv"
        finally:
            os.unlink(temp_path)

    def test_read_multiple_lines(self):
        """Read control file with multiple lines."""
        content = """StudyA,2026-01-15,parms1.csv,data1.pip,parmedit1.csv,upload1.csv
StudyB,2026-02-20,parms2.csv,data2.pip,parmedit2.csv,upload2.csv
StudyC,2026-03-25,parms3.csv,data3.pip,parmedit3.csv,upload3.csv
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries = list(read_control_file(temp_path))

            assert len(entries) == 3
            assert entries[0].study_name == "StudyA"
            assert entries[1].study_name == "StudyB"
            assert entries[2].study_name == "StudyC"
            assert entries[0].parmedit_file_name == "parmedit1.csv"
            assert entries[1].parmedit_file_name == "parmedit2.csv"
            assert entries[2].parmedit_file_name == "parmedit3.csv"
            assert entries[0].upload_file_name == "upload1.csv"
            assert entries[1].upload_file_name == "upload2.csv"
            assert entries[2].upload_file_name == "upload3.csv"
        finally:
            os.unlink(temp_path)

    def test_skip_empty_lines(self):
        """Empty lines in control file are skipped."""
        content = """StudyA,2026-01-15,parms1.csv,data1.pip,parmedit1.csv,upload1.csv

StudyB,2026-02-20,parms2.csv,data2.pip,parmedit2.csv,upload2.csv
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries = list(read_control_file(temp_path))

            assert len(entries) == 2
            assert entries[0].study_name == "StudyA"
            assert entries[1].study_name == "StudyB"
        finally:
            os.unlink(temp_path)

    def test_strip_whitespace(self):
        """Whitespace around fields is stripped."""
        content = "  StudyA  ,  2026-01-15  ,  parms.csv  ,  data.pip  ,  parmedit.csv  ,  upload.csv  \n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entries = list(read_control_file(temp_path))

            assert len(entries) == 1
            assert entries[0].study_name == "StudyA"
            assert entries[0].study_date == "2026-01-15"
            assert entries[0].parms_file_name == "parms.csv"
            assert entries[0].pip_file_name == "data.pip"
            assert entries[0].parmedit_file_name == "parmedit.csv"
            assert entries[0].upload_file_name == "upload.csv"
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Non-existent control file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            list(read_control_file("/nonexistent/control.txt"))

    def test_invalid_format_too_few_fields(self):
        """Line with fewer than 6 fields raises ValueError."""
        content = "StudyA,2026-01-15,parms.csv,data.pip,parmedit.csv\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                list(read_control_file(temp_path))
            assert "Expected 6 fields" in str(exc_info.value)
            assert "got 5" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_invalid_format_too_many_fields(self):
        """Line with more than 6 fields raises ValueError."""
        content = "StudyA,2026-01-15,parms.csv,data.pip,parmedit.csv,upload.csv,extra\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                list(read_control_file(temp_path))
            assert "Expected 6 fields" in str(exc_info.value)
            assert "got 7" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Empty control file returns no entries."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            entries = list(read_control_file(temp_path))
            assert len(entries) == 0
        finally:
            os.unlink(temp_path)


class TestControlFileWithRealFile:
    """Tests using actual control file from WaveFiles directory."""

    def test_read_test_control(self):
        """Read the actual test_control.txt file."""
        control_path = "WaveFiles/test_control.txt"

        if not os.path.exists(control_path):
            pytest.skip("test_control.txt not found")

        entries = list(read_control_file(control_path))

        assert len(entries) >= 1
        # Verify the first entry has all required fields
        entry = entries[0]
        assert entry.study_name
        assert entry.study_date
        assert entry.parms_file_name
        assert entry.pip_file_name
        assert entry.parmedit_file_name
        assert entry.upload_file_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
