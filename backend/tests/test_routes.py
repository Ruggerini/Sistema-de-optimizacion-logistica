from http import HTTPStatus

import pytest

from app.routers.routes import optimizer


@pytest.fixture(autouse=True)
def stub_mapbox():
    geocode_map = {
        "100 Main St, St Joseph, MO": (39.7701, -94.8501),
        "200 Main St, St Joseph, MO": (39.7711, -94.8521),
        "300 Main St, St Joseph, MO": (39.7721, -94.8531),
    }

    def fake_geocode(address: str):
        return geocode_map.get(address, (39.775, -94.84))

    def fake_optimize_trip(coordinates, source="first", destination="last"):
        coords_lonlat = [[lon, lat] for lat, lon in coordinates]
        legs = [{"duration": 900, "distance": 1200} for _ in range(len(coordinates) - 1)]
        waypoint_count = max(len(coordinates) - 2, 0)
        return {
            "trips": [
                {
                    "id": "trip-1",
                    "waypoint_order": list(range(waypoint_count)),
                    "legs": legs,
                    "geometry": {"type": "LineString", "coordinates": coords_lonlat},
                }
            ]
        }

    original_geocode = optimizer.mapbox.geocode
    original_optimize = optimizer.mapbox.optimize_trip
    optimizer.mapbox.geocode = fake_geocode
    optimizer.mapbox.optimize_trip = fake_optimize_trip
    yield
    optimizer.mapbox.geocode = original_geocode
    optimizer.mapbox.optimize_trip = original_optimize


def authenticate(client):
    register_payload = {
        "company_id": "WM-002",
        "company_name": "Waste Management Auth",
        "email": "routes@wm.com",
        "password": "strongpass123",
    }
    client.post("/api/auth/register", json=register_payload)
    response = client.post(
        "/api/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_optimize_and_history_flow(client):
    headers = authenticate(client)

    optimize_payload = {
        "execution_date": "2025-01-01",
        "trucks": [
            {
                "id": "truck-1",
                "name": "Camion Centro",
                "start_address": "100 Main St",
                "end_address": "200 Main St",
            }
        ],
        "stops": [{"id": "stop-1", "address": "300 Main St"}],
    }

    response = client.post("/api/routes/optimize", json=optimize_payload, headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["summary"]["trucks_needed"] == 1
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["google_maps_link"].startswith("https://www.google.com/maps/dir") and "via%3A" in data["assignments"][0]["google_maps_link"]
    assigned = data["assignments"][0]["assigned_stops"]
    assert len(assigned) == 1
    assert assigned[0]["address"].startswith("300 Main St")

    history_response = client.get("/api/routes/history", headers=headers)
    assert history_response.status_code == HTTPStatus.OK
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["truck_assignments"][0]["truck_name"] == "Camion Centro"
    assert len(history[0]["truck_assignments"][0]["assigned_stops"]) == 1
