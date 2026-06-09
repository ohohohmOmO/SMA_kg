import requests
import json
from pathlib import Path
q = """
query {
  disease(efoId: "MONDO_0009669") {
    id
    name
    associatedTargets {
      rows { target { approvedSymbol } score }
    }
  }
}
"""
r = requests.post('https://api.platform.opentargets.org/api/v4/graphql', json={"query": q}, timeout=30).json()
output_file = Path("artifacts/test-results/ot_test_result.json")
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, "w") as f:
    json.dump(r, f, indent=2)
