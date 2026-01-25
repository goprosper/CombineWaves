"""Unit tests for database.py."""

import pytest
from unittest.mock import patch, MagicMock

from database import QuestionMapRecord, QuestionMasterRecord, DatabaseClient


class TestQuestionMapRecord:
    """Tests for QuestionMapRecord dataclass."""

    def test_create_record(self):
        """Create with valid data."""
        record = QuestionMapRecord(question_id=123, answer_value_map='1^2^3')
        assert record.question_id == 123
        assert record.answer_value_map == '1^2^3'

    def test_create_record_empty_answer_map(self):
        """Create with empty answer_value_map."""
        record = QuestionMapRecord(question_id=456, answer_value_map='')
        assert record.question_id == 456
        assert record.answer_value_map == ''


class TestQuestionMasterRecord:
    """Tests for QuestionMasterRecord dataclass."""

    def test_create_record(self):
        """Create with valid data."""
        record = QuestionMasterRecord(
            alternate_text='What is your age?',
            answer_text='18-24^25-34^35-44'
        )
        assert record.alternate_text == 'What is your age?'
        assert record.answer_text == '18-24^25-34^35-44'

    def test_create_record_empty_fields(self):
        """Create with empty strings."""
        record = QuestionMasterRecord(alternate_text='', answer_text='')
        assert record.alternate_text == ''
        assert record.answer_text == ''


class TestDatabaseClientConnection:
    """Tests for DatabaseClient connection management."""

    @patch('database.pymysql.connect')
    def test_enter_opens_connection(self, mock_connect):
        """__enter__ calls pymysql.connect."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        client = DatabaseClient()
        result = client.__enter__()

        mock_connect.assert_called_once_with(**DatabaseClient.DB_CONFIG)
        assert result is client
        assert client._connection is mock_connection

    @patch('database.pymysql.connect')
    def test_exit_closes_connection(self, mock_connect):
        """__exit__ closes connection."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        client = DatabaseClient()
        client.__enter__()
        client.__exit__(None, None, None)

        mock_connection.close.assert_called_once()
        assert client._connection is None

    def test_exit_handles_none_connection(self):
        """__exit__ handles None connection gracefully."""
        client = DatabaseClient()
        # Should not raise any exception
        client.__exit__(None, None, None)
        assert client._connection is None


class TestGetQuestionMap:
    """Tests for DatabaseClient.get_question_map method."""

    @patch('database.pymysql.connect')
    def test_get_question_map_found(self, mock_connect):
        """Returns QuestionMapRecord when found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'question_id': 100,
            'answer_value_map': '3^2^1'
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_map('StudyA', '2025-01', 5)

        assert result is not None
        assert isinstance(result, QuestionMapRecord)
        assert result.question_id == 100
        assert result.answer_value_map == '3^2^1'
        mock_cursor.execute.assert_called_once()

    @patch('database.pymysql.connect')
    def test_get_question_map_not_found(self, mock_connect):
        """Returns None when not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_map('StudyA', '2025-01', 999)

        assert result is None

    @patch('database.pymysql.connect')
    def test_get_question_map_null_answer_map(self, mock_connect):
        """Handles NULL answer_value_map from DB."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'question_id': 200,
            'answer_value_map': None
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_map('StudyB', '2025-02', 10)

        assert result is not None
        assert result.question_id == 200
        assert result.answer_value_map == ''

    def test_get_question_map_no_connection(self):
        """Raises RuntimeError when not connected."""
        client = DatabaseClient()

        with pytest.raises(RuntimeError, match="Database connection not open"):
            client.get_question_map('StudyA', '2025-01', 1)


class TestGetQuestionText:
    """Tests for DatabaseClient.get_question_text method."""

    @patch('database.pymysql.connect')
    def test_get_question_text_found(self, mock_connect):
        """Returns text when found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'question_text': 'What is your favorite color?'
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_text('StudyA', 100)

        assert result == 'What is your favorite color?'
        mock_cursor.execute.assert_called_once()

    @patch('database.pymysql.connect')
    def test_get_question_text_not_found(self, mock_connect):
        """Returns None when not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_text('StudyA', 999)

        assert result is None

    def test_get_question_text_no_connection(self):
        """Raises RuntimeError when not connected."""
        client = DatabaseClient()

        with pytest.raises(RuntimeError, match="Database connection not open"):
            client.get_question_text('StudyA', 100)


class TestGetQuestionMaster:
    """Tests for DatabaseClient.get_question_master method."""

    @patch('database.pymysql.connect')
    def test_get_question_master_found(self, mock_connect):
        """Returns QuestionMasterRecord when found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'alternate_text': 'What is your gender?',
            'answer_text': 'Male^Female^Other'
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_master('StudyA', 50)

        assert result is not None
        assert isinstance(result, QuestionMasterRecord)
        assert result.alternate_text == 'What is your gender?'
        assert result.answer_text == 'Male^Female^Other'
        mock_cursor.execute.assert_called_once()

    @patch('database.pymysql.connect')
    def test_get_question_master_not_found(self, mock_connect):
        """Returns None when not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_master('StudyA', 999)

        assert result is None

    @patch('database.pymysql.connect')
    def test_get_question_master_null_fields(self, mock_connect):
        """Handles NULL fields from DB."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'alternate_text': None,
            'answer_text': None
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with DatabaseClient() as client:
            result = client.get_question_master('StudyB', 75)

        assert result is not None
        assert result.alternate_text == ''
        assert result.answer_text == ''

    def test_get_question_master_no_connection(self):
        """Raises RuntimeError when not connected."""
        client = DatabaseClient()

        with pytest.raises(RuntimeError, match="Database connection not open"):
            client.get_question_master('StudyA', 100)
