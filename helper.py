import json
from difflib import get_close_matches

with open("lines.json", "r") as f:
    lines = json.load(f)

def match_stop(stop: str):
    stop = stop.lower()
    matches = [line for line in lines if stop in line['name'].lower()]
    if not matches:
        close_matches = get_close_matches(stop, [line['name'].lower() for line in lines])
        if close_matches:
            matches = [line for line in lines if line['name'].lower() in close_matches]
    return matches[0] if matches else None

def get_line_id(stop, direction):
    for line in lines:
        if line['name'] == stop['name'] and line['direction'] == direction:
            return line['id']
    return None

def load_user_data():
    with open("userdata.json", "r") as f:
        return json.load(f)

def save_user_data(data):
    with open("userdata.json", "w") as f:
        json.dump(data, f)

if __name__ == "__main__":
    print(match_stop("drafwefweqwkinodq3iuq3ma"))