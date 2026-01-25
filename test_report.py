"""Tests for report module."""

import os
import tempfile
import pytest

from report import (
    Severity,
    ReportEntry,
    ReportCollector,
    get_collector,
    reset_collector,
)


class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Verify INFO, WARNING, ERROR values."""
        assert Severity.INFO.value == "INFO"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.ERROR.value == "ERROR"


class TestReportEntry:
    """Tests for ReportEntry dataclass."""

    def test_create_entry(self):
        """Create entry with all fields."""
        entry = ReportEntry(
            severity=Severity.WARNING,
            category="test_category",
            message="Test message",
            details={"key1": "value1", "key2": "value2"}
        )

        assert entry.severity == Severity.WARNING
        assert entry.category == "test_category"
        assert entry.message == "Test message"
        assert entry.details == {"key1": "value1", "key2": "value2"}

    def test_create_entry_without_context(self):
        """Create entry without context (details is None by default)."""
        entry = ReportEntry(
            severity=Severity.ERROR,
            category="error_category",
            message="Error message"
        )

        assert entry.severity == Severity.ERROR
        assert entry.category == "error_category"
        assert entry.message == "Error message"
        assert entry.details is None


class TestReportCollector:
    """Tests for ReportCollector class."""

    def test_add_entry(self):
        """Add entry directly."""
        collector = ReportCollector()
        collector.add(
            Severity.WARNING,
            "test_category",
            "Test message",
            {"detail": "value"},
            print_to_stderr=False
        )

        assert len(collector.entries) == 1
        entry = collector.entries[0]
        assert entry.severity == Severity.WARNING
        assert entry.category == "test_category"
        assert entry.message == "Test message"
        assert entry.details == {"detail": "value"}

    def test_info_method(self):
        """Add info-level entry."""
        collector = ReportCollector()
        collector.info("info_category", "Info message", {"info_key": "info_value"})

        assert len(collector.entries) == 1
        entry = collector.entries[0]
        assert entry.severity == Severity.INFO
        assert entry.category == "info_category"
        assert entry.message == "Info message"
        assert entry.details == {"info_key": "info_value"}

    def test_warning_method(self, capsys):
        """Add warning-level entry."""
        collector = ReportCollector()
        collector.warning("warning_category", "Warning message", {"warn_key": "warn_value"})

        assert len(collector.entries) == 1
        entry = collector.entries[0]
        assert entry.severity == Severity.WARNING
        assert entry.category == "warning_category"
        assert entry.message == "Warning message"
        assert entry.details == {"warn_key": "warn_value"}

        # Check stderr output
        captured = capsys.readouterr()
        assert "WARNING: Warning message" in captured.err

    def test_error_method(self, capsys):
        """Add error-level entry."""
        collector = ReportCollector()
        collector.error("error_category", "Error message", {"err_key": "err_value"})

        assert len(collector.entries) == 1
        entry = collector.entries[0]
        assert entry.severity == Severity.ERROR
        assert entry.category == "error_category"
        assert entry.message == "Error message"
        assert entry.details == {"err_key": "err_value"}

        # Check stderr output
        captured = capsys.readouterr()
        assert "ERROR: Error message" in captured.err

    def test_get_by_severity(self):
        """Filter entries by severity."""
        collector = ReportCollector()
        collector.info("cat1", "Info 1")
        collector.info("cat2", "Info 2")
        collector.warning("cat1", "Warning 1")
        collector.error("cat2", "Error 1")

        infos = collector.get_by_severity(Severity.INFO)
        warnings = collector.get_by_severity(Severity.WARNING)
        errors = collector.get_by_severity(Severity.ERROR)

        assert len(infos) == 2
        assert len(warnings) == 1
        assert len(errors) == 1
        assert infos[0].message == "Info 1"
        assert infos[1].message == "Info 2"
        assert warnings[0].message == "Warning 1"
        assert errors[0].message == "Error 1"

    def test_get_by_category(self):
        """Filter entries by category."""
        collector = ReportCollector()
        collector.info("category_a", "Info A1")
        collector.warning("category_b", "Warning B1")
        collector.info("category_a", "Info A2")
        collector.error("category_b", "Error B1")

        cat_a = collector.get_by_category("category_a")
        cat_b = collector.get_by_category("category_b")
        cat_c = collector.get_by_category("category_c")

        assert len(cat_a) == 2
        assert len(cat_b) == 2
        assert len(cat_c) == 0
        assert cat_a[0].message == "Info A1"
        assert cat_a[1].message == "Info A2"

    def test_count_by_severity(self):
        """Count entries by severity."""
        collector = ReportCollector()
        collector.info("cat", "Info 1")
        collector.info("cat", "Info 2")
        collector.info("cat", "Info 3")
        collector.warning("cat", "Warning 1")
        collector.warning("cat", "Warning 2")
        collector.error("cat", "Error 1")

        counts = collector.count_by_severity()

        assert counts[Severity.INFO] == 3
        assert counts[Severity.WARNING] == 2
        assert counts[Severity.ERROR] == 1

    def test_count_by_category(self):
        """Count entries by category."""
        collector = ReportCollector()
        collector.info("cat_x", "Info X1")
        collector.info("cat_x", "Info X2")
        collector.warning("cat_y", "Warning Y1")
        collector.warning("cat_y", "Warning Y2")
        collector.warning("cat_y", "Warning Y3")
        collector.error("cat_z", "Error Z1")

        counts = collector.count_by_category()

        assert counts["cat_x"] == 2
        assert counts["cat_y"] == 3
        assert counts["cat_z"] == 1

    def test_has_errors_true(self):
        """has_errors() returns True when errors exist."""
        collector = ReportCollector()
        collector.info("cat", "Info message")
        collector.warning("cat", "Warning message")
        collector.error("cat", "Error message")

        assert collector.has_errors() is True

    def test_has_errors_false(self):
        """has_errors() returns False when no errors."""
        collector = ReportCollector()
        collector.info("cat", "Info message")
        collector.warning("cat", "Warning message")

        assert collector.has_errors() is False

    def test_generate_report(self):
        """Report generation creates file with correct content."""
        collector = ReportCollector()
        collector.info("file_processing", "Processed file1.csv")
        collector.warning("match_warning", "Fuzzy match below threshold", {"score": 85})
        collector.error("database_error", "Connection failed", {"host": "localhost"})

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = os.path.join(tmpdir, "test_report.txt")

            result = collector.generate_report(
                output_path=report_path,
                control_file="test_control.txt",
                files_processed=4,
                common_questions=10,
                rows_processed=1000
            )

            assert result == report_path
            assert os.path.exists(report_path)

            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check header
            assert "COMBINEWAVES EXECUTION REPORT" in content

            # Check execution summary
            assert "Control File:      test_control.txt" in content
            assert "Files Processed:   4" in content
            assert "Common Questions:  10" in content
            assert "Rows Processed:    1000" in content

            # Check issue summary
            assert "Errors:            1" in content
            assert "Warnings:          1" in content
            assert "Info:              1" in content

            # Check issues by category
            assert "database_error: 1" in content
            assert "file_processing: 1" in content
            assert "match_warning: 1" in content

            # Check detailed errors section
            assert "ERRORS (1)" in content
            assert "[database_error] Connection failed" in content
            assert "host: localhost" in content

            # Check detailed warnings section
            assert "WARNINGS (1)" in content
            assert "Fuzzy match below threshold" in content
            assert "score: 85" in content

            # Check info section
            assert "INFO (1)" in content
            assert "[file_processing] Processed file1.csv" in content

            # Check footer
            assert "END OF REPORT" in content


class TestGlobalFunctions:
    """Tests for global collector functions."""

    def test_get_collector(self):
        """Returns singleton instance."""
        # Reset first to ensure clean state
        reset_collector()

        collector1 = get_collector()
        collector2 = get_collector()

        assert collector1 is collector2
        assert isinstance(collector1, ReportCollector)

    def test_reset_collector(self):
        """Resets to new instance."""
        # Get initial collector and add an entry
        collector1 = get_collector()
        collector1.info("test", "Test message")

        # Reset and get new collector
        collector2 = reset_collector()

        assert collector1 is not collector2
        assert len(collector2.entries) == 0
        assert isinstance(collector2, ReportCollector)

        # Verify get_collector now returns the new instance
        collector3 = get_collector()
        assert collector2 is collector3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
