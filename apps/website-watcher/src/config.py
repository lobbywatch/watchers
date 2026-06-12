import tomllib

with open("config.toml", "rb") as f:
    data = tomllib.load(f)

def get_key(key: str)-> str:
    return data[key]
