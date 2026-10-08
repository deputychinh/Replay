"""Print the OpenAPI document. `make gen-client` turns it into TypeScript for the web app."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2, sort_keys=True))
