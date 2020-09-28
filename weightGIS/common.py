import json


def load_json(path):
    """
    Load a json file at a given path
    """
    with open(path) as j:
        return json.load(j)


def write_json(write_path, write_data):
    """
    Write the Json data
    """
    with open(f"{write_path}.txt", "w", encoding="utf-8") as json_saver:
        json.dump(write_data, json_saver, ensure_ascii=False, indent=4, sort_keys=True)
