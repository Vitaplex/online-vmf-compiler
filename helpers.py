import json

def get_configured_directories():
    with open("./static/config.json", "r") as config_file:
        content = config_file.read()
        config = json.loads(content)
        return config