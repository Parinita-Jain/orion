import json
from pathlib import Path

from .serializer import (
    serialize_state,
    deserialize_state,
)

WORKFLOW_DIR = Path("data/workflows")
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

def save_workflow( workflow_id: str,state,):

    data = serialize_state(state)

    path = WORKFLOW_DIR / f"{workflow_id}.json"

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
        )


def load_workflow(workflow_id):

    path = WORKFLOW_DIR / f"{workflow_id}.json"

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return deserialize_state(data)