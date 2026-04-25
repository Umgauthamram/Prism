import requests
import json

base_url = "http://localhost:8001"

def test():
    print("Testing /reset...")
    res = requests.post(f"{base_url}/reset", json={"seed": 42})
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
        return
    
    data = res.json()
    eid = data["observation"]["episode_id"]
    print(f"Episode ID: {eid}")
    
    print("Testing /step...")
    res = requests.post(f"{base_url}/step", json={
        "action": {"tool": "checkpoint", "args": {}},
        "episode_id": eid
    })
    print(f"Status: {res.status_code}")
    print(res.text)

if __name__ == "__main__":
    test()
