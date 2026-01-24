"""Answer ID mapping algorithm for CombineWaves."""


def compute_answer_ids(answer_value_map: str, answer_count: int) -> str:
    """
    Compute answer IDs by finding each answer number's position in the value map.

    For each answer position (1-based), finds where that number appears in the
    answer_value_map and returns the index as the answer_id.

    Args:
        answer_value_map: ^-delimited string from database (e.g., "3^2^?^1^6^7^4^5")
        answer_count: Number of answers in the parms file

    Returns:
        ^-delimited string of answer IDs

    Example:
        >>> compute_answer_ids("3^2^?^1^6^7^4^5", 7)
        '3^1^0^6^7^4^5'
        >>> compute_answer_ids("2^1", 2)
        '1^0'
    """
    if not answer_value_map or answer_count == 0:
        return ''

    value_map = answer_value_map.split('^')

    answer_ids = []
    for answer_number in range(1, answer_count + 1):
        answer_number_str = str(answer_number)
        try:
            index = value_map.index(answer_number_str)
            answer_ids.append(str(index))
        except ValueError:
            # Answer number not found in map - use empty string
            answer_ids.append('')

    return '^'.join(answer_ids)
