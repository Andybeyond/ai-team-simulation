import requests
import json

def test_github_init():
    url = 'http://localhost:5000/github/init'
    headers = {'Content-Type': 'application/json'}
    data = {
        'repo_name': 'ai-team-simulation-test',
        'description': 'Test repository for AI Team Simulation'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        print('Response:', result)
        return result
    except Exception as e:
        print('Error:', str(e))
        return None

if __name__ == '__main__':
    test_github_init()
