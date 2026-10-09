def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "application": "ReconForge"}

def test_unauthorized(client):
    response = client.get("/api/projects")
    assert response.status_code == 401
    
def test_project_create_list(client):
    headers = {"Authorization": "Bearer test_token"}
    response = client.post("/api/projects", json={"name": "Test Proj", "authorized_ack": True}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Proj"
    
    response2 = client.get("/api/projects", headers=headers)
    assert response2.status_code == 200
    assert len(response2.json()) == 1
    assert response2.json()[0]["name"] == "Test Proj"
