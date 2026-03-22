import requests
import json
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
r = requests.post('https://api.platform.opentargets.org/api/v4/graphql', json={"query": q}, verify=False).json()
with open("ot_test_result.json", "w") as f:
    json.dump(r, f, indent=2)
