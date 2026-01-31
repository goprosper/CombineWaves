"""Tests for answer_mapper module."""

import pytest

from answer_mapper import compute_answer_ids


class TestComputeAnswerIds:
    """Tests for compute_answer_ids function."""

    def test_basic_mapping(self):
        """Basic case where answer positions map correctly."""
        # From the docstring example:
        # answer_value_map: "3^2^?^1^6^7^4^5"
        # answer_count: 7
        # For answer 1, find "1" in map -> index 3
        # For answer 2, find "2" in map -> index 1
        # For answer 3, find "3" in map -> index 0
        # For answer 4, find "4" in map -> index 6
        # For answer 5, find "5" in map -> index 7
        # For answer 6, find "6" in map -> index 4
        # For answer 7, find "7" in map -> index 5
        result, count = compute_answer_ids("3^2^?^1^6^7^4^5", 7)
        assert result == "3^1^0^6^7^4^5"
        assert count == 7

    def test_sequential_mapping(self):
        """When answer_value_map is "1^2^3" (sequential)."""
        # For answer 1, find "1" -> index 0
        # For answer 2, find "2" -> index 1
        # For answer 3, find "3" -> index 2
        result, count = compute_answer_ids("1^2^3", 3)
        assert result == "0^1^2"
        assert count == 3

    def test_reordered_mapping(self):
        """When answer_value_map has different order like "2^1^3"."""
        # From the docstring example:
        # For answer 1, find "1" -> index 1
        # For answer 2, find "2" -> index 0
        result, count = compute_answer_ids("2^1", 2)
        assert result == "1^0"
        assert count == 2

        # Another reordered case
        # For answer 1, find "1" -> index 1
        # For answer 2, find "2" -> index 0
        # For answer 3, find "3" -> index 2
        result, count = compute_answer_ids("2^1^3", 3)
        assert result == "1^0^2"
        assert count == 3

    def test_empty_answer_value_map(self):
        """Empty string for answer_value_map returns empty string."""
        result, count = compute_answer_ids("", 5)
        assert result == ""
        assert count == 0

    def test_zero_answer_count(self):
        """answer_count of 0 returns empty string."""
        result, count = compute_answer_ids("1^2^3", 0)
        assert result == ""
        assert count == 0

    def test_answer_not_found(self):
        """Answer number not found in map is dropped and count reduced."""
        # answer_value_map has only 1 and 2, but answer_count is 3
        # For answer 1, find "1" -> index 0
        # For answer 2, find "2" -> index 1
        # For answer 3, find "3" -> not found -> skipped
        result, count = compute_answer_ids("1^2", 3)
        assert result == "0^1"
        assert count == 2

    def test_large_answer_count(self):
        """Many answers (10+) mapped correctly."""
        # Create a map with 12 answers in scrambled order
        answer_value_map = "3^1^4^2^6^5^8^7^10^9^12^11"
        # For answer 1, find "1" -> index 1
        # For answer 2, find "2" -> index 3
        # For answer 3, find "3" -> index 0
        # For answer 4, find "4" -> index 2
        # For answer 5, find "5" -> index 5
        # For answer 6, find "6" -> index 4
        # For answer 7, find "7" -> index 7
        # For answer 8, find "8" -> index 6
        # For answer 9, find "9" -> index 9
        # For answer 10, find "10" -> index 8
        # For answer 11, find "11" -> index 11
        # For answer 12, find "12" -> index 10
        result, count = compute_answer_ids(answer_value_map, 12)
        assert result == "1^3^0^2^5^4^7^6^9^8^11^10"
        assert count == 12

    def test_single_answer(self):
        """Only one answer maps correctly."""
        result, count = compute_answer_ids("1", 1)
        assert result == "0"
        assert count == 1

    def test_map_with_non_numeric_values(self):
        """Map containing non-numeric values like '?' are handled correctly."""
        # The "?" in the map should be skipped when searching for numeric answers
        # answer_value_map: "?^1^2"
        # For answer 1, find "1" -> index 1
        # For answer 2, find "2" -> index 2
        result, count = compute_answer_ids("?^1^2", 2)
        assert result == "1^2"
        assert count == 2

    def test_partial_missing_answers(self):
        """Some answers found, some not found - missing ones are dropped."""
        # Map has 1, 3 but not 2
        # For answer 1, find "1" -> index 0
        # For answer 2, find "2" -> not found -> skipped
        # For answer 3, find "3" -> index 1
        result, count = compute_answer_ids("1^3", 3)
        assert result == "0^1"
        assert count == 2

    def test_none_answer_value_map(self):
        """None value for answer_value_map returns empty string."""
        # The function checks "if not answer_value_map" which handles None
        result, count = compute_answer_ids(None, 5)
        assert result == ""
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
