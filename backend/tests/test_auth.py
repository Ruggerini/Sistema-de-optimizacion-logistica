from http import HTTPStatus


def test_register_and_login(client):
    register_payload = {
        "company_id": "WM-001",
        "company_name": "Waste Management Test",
        "email": "test@wm.com",
        "password": "password123",
    }

    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["email"] == register_payload["email"]
    assert data["company_id"] == register_payload["company_id"]

    login_payload = {"email": register_payload["email"], "password": register_payload["password"]}
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == HTTPStatus.OK
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
