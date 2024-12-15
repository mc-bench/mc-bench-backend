import json
import os


HERE = os.path.dirname(os.path.abspath(__file__))


BLOCKS_FILE = os.path.join(HERE, "blocks.json")


blocks = json.load(open(BLOCKS_FILE))
