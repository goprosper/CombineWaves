"""Database client for CombineWaves."""

from dataclasses import dataclass
from typing import Optional

import pymysql
import pymysql.cursors


@dataclass
class QuestionMapRecord:
    """Represents a record from the br_question_map table."""
    question_id: int
    answer_value_map: str


@dataclass
class QuestionMasterRecord:
    """Represents a record from the br_question_master table."""
    alternate_text: str
    answer_text: str


class DatabaseClient:
    """MySQL database client for querying question mappings."""

    DB_CONFIG = {
        'host': '50.17.224.19',
        'database': 'ptdb',
        'user': 'root',
        'password': 'L0w_L3v31',
        'charset': 'utf8',
        'cursorclass': pymysql.cursors.DictCursor
    }

    def __init__(self):
        self._connection = None

    def __enter__(self) -> 'DatabaseClient':
        """Open database connection."""
        self._connection = pymysql.connect(**self.DB_CONFIG)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_question_map(
        self,
        study_name: str,
        study_date: str,
        question_number: int
    ) -> Optional[QuestionMapRecord]:
        """
        Retrieve question mapping from database.

        Args:
            study_name: Name of the study
            study_date: Date of the study
            question_number: Question number from parms file

        Returns:
            QuestionMapRecord if found, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Database connection not open. Use 'with' statement.")

        sql = """
            SELECT question_id, answer_value_map
            FROM br_question_map
            WHERE study_name = %s
              AND study_date = %s
              AND question_number = %s
        """

        with self._connection.cursor() as cursor:
            cursor.execute(sql, (study_name, study_date, question_number))
            row = cursor.fetchone()

            if row:
                return QuestionMapRecord(
                    question_id=row['question_id'],
                    answer_value_map=row['answer_value_map'] or ''
                )

            return None

    def get_question_text(
        self,
        study_name: str,
        question_id: int
    ) -> Optional[str]:
        """
        Retrieve question text from br_question_master.

        Args:
            study_name: Name of the study
            question_id: Question ID

        Returns:
            Question text if found, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Database connection not open. Use 'with' statement.")

        sql = """
            SELECT question_text
            FROM br_question_master
            WHERE study_name = %s
              AND question_id = %s
        """

        with self._connection.cursor() as cursor:
            cursor.execute(sql, (study_name, question_id))
            row = cursor.fetchone()

            if row:
                return row['question_text'] or ''

            return None

    def get_question_master(
        self,
        study_name: str,
        question_id: int
    ) -> Optional[QuestionMasterRecord]:
        """
        Retrieve question master record from br_question_master.

        Args:
            study_name: Name of the study
            question_id: Question ID

        Returns:
            QuestionMasterRecord if found, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Database connection not open. Use 'with' statement.")

        sql = """
            SELECT alternate_text, answer_text
            FROM br_question_master
            WHERE study_name = %s
              AND question_id = %s
        """

        with self._connection.cursor() as cursor:
            cursor.execute(sql, (study_name, question_id))
            row = cursor.fetchone()

            if row:
                return QuestionMasterRecord(
                    alternate_text=row['alternate_text'] or '',
                    answer_text=row['answer_text'] or ''
                )

            return None
