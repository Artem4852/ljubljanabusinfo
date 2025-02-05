import json
from difflib import get_close_matches

with open("lines.json", "r") as f:
    lines = json.load(f)

def match_stop(stop: str) -> dict | None:
    """
    Finds and returns the first matching bus stop from a list of bus stops.
    The function performs a case-insensitive search for the provided stop name
    within a list of bus stops. If no exact matches are found, it attempts to
    find close matches using the `get_close_matches` function.
    Args:
        stop (str): The name of the bus stop to search for.
    Returns:
        dict or None: The first matching bus stop as a dictionary if found,
                      otherwise None.
    """
    stop = stop.lower()
    matches = [line for line in lines if stop in line['name'].lower()]
    if not matches:
        close_matches = get_close_matches(stop, [line['name'].lower() for line in lines])
        if close_matches:
            matches = [line for line in lines if line['name'].lower() in close_matches]
    return matches[0] if matches else None

def get_line_id(stop: str, direction: str) -> str | None:
    """
    Retrieve the line ID for a given stop and direction.
    Args:
        stop (str): The name of the bus stop.
        direction (str): The direction of the bus line.
    Returns:
        str | None: The ID of the bus line if found, otherwise None.
    """
    for line in lines:
        if line['name'] == stop['name'] and line['direction'] == direction:
            return line['id']
    return None

def load_user_data() -> dict:
    """
    Loads user data from a JSON file.
    Returns:
        dict: A dictionary containing the user data loaded from 'userdata.json'.
    """
    with open("userdata.json", "r") as f:
        return json.load(f)

def save_user_data(data) -> None:
    """
    Save user data to a JSON file.
    Args:
        data (dict): The user data to be saved.
    Returns:
        None
    """
    with open("userdata.json", "w") as f:
        json.dump(data, f)

if __name__ == "__main__":
    # print(match_stop("drafwefweqwkinodq3iuq3ma"))
    print(get_line_id({"name": "Astra"}, "to_center"))