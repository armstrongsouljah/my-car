from typing import Dict


def create(text: str, key=None) -> Dict:
    """
    :param text:  Message to return in response body.
    :param key: Dict identifier
    :return: Dict of details
    """
    if key is None:
        key = "detail"

    data = dict()
    data[key] = text
    return data
