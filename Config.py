import json


d = {"key_id": "PKR4H9AURJ12NFU16YFT",
    "secret": "ov525A/An/sC5mR0fcoI4ZVClzyTTrOqg0CGQolH",
    "base_url": "https://paper-api.alpaca.markets"}


with open("paper.json", "w") as write_file:
    json.dump(d, write_file)
    print("HI")