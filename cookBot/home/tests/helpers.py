import json
from unittest.mock import MagicMock

# Sample data that mimics a real Spoonacular ingredient search response
MOCK_SEARCH_RESPONSE = {
    "results": [{"id": 9040, "name": "banana"}],
    "offset": 0,
    "number": 1,
    "totalResults": 1,
}

# Sample data that mimics a real Spoonacular nutrition response
MOCK_NUTRITION_RESPONSE = {
    "id": 9040,
    "name": "banana",
    "nutrition": {
        "nutrients": [
            {
                "name": "Calories",
                "amount": 89.0,
                "unit": "kcal",
                "percentOfDailyNeeds": 4.45,
            },
            {"name": "Fat", "amount": 0.33, "unit": "g", "percentOfDailyNeeds": 0.51},
            {
                "name": "Saturated Fat",
                "amount": 0.11,
                "unit": "g",
                "percentOfDailyNeeds": 0.69,
            },
            {
                "name": "Carbohydrates",
                "amount": 22.84,
                "unit": "g",
                "percentOfDailyNeeds": 7.61,
            },
            {"name": "Fiber", "amount": 2.6, "unit": "g", "percentOfDailyNeeds": 10.4},
            {
                "name": "Sugar",
                "amount": 12.23,
                "unit": "g",
                "percentOfDailyNeeds": 13.59,
            },
            {
                "name": "Protein",
                "amount": 1.09,
                "unit": "g",
                "percentOfDailyNeeds": 2.18,
            },
            {
                "name": "Sodium",
                "amount": 1.0,
                "unit": "mg",
                "percentOfDailyNeeds": 0.04,
            },
            {
                "name": "Potassium",
                "amount": 358.0,
                "unit": "mg",
                "percentOfDailyNeeds": 10.23,
            },
            {
                "name": "Vitamin C",
                "amount": 8.7,
                "unit": "mg",
                "percentOfDailyNeeds": 9.67,
            },
        ],
        "weightPerServing": {"amount": 100, "unit": "g"},
    },
}


def make_mock_response(json_data):
    """
    Creates a fake urllib response object that mimics what urlopen returns.
    urllib.request.urlopen is used as a context manager (with statement), so
    the mock needs __enter__ and __exit__ defined to behave the same way.
    read() returns the JSON data encoded as bytes, just like a real HTTP response.
    """
    mock = MagicMock()
    mock.read.return_value = json.dumps(json_data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock
