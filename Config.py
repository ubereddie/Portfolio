import json


d = {"key_id": "AK6MLMQ67NQU1E0IVW1X",
    "secret": "ORmHymf5Rb9zD5MzBsyHnLj0z2cE01OnCOU54r1s",
    "base_url": "https://api.alpaca.markets"}


with open("live.json", "w") as write_file:
    json.dump(d, write_file)

