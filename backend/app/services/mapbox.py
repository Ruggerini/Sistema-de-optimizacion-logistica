import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)


class MapboxService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://api.mapbox.com"

    @property
    def token(self) -> str:
        return self.settings.mapbox_token

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        encoded_address = quote(address)
        url = f"{self.base_url}/geocoding/v5/mapbox.places/{encoded_address}.json"
        params = {"access_token": self.token, "limit": 1}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error("Geocoding failed for %s: %s", address, response.text)
            return None
        data = response.json()
        features = data.get("features", [])
        if not features:
            logger.warning("No geocoding results for address: %s", address)
            return None
        lon, lat = features[0]["center"]
        return lat, lon

    def optimize_trip(
        self,
        coordinates: List[Tuple[float, float]],
        source: str = "first",
        destination: str = "last",
    ) -> Optional[Dict]:
        coord_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        url = f"{self.base_url}/optimized-trips/v1/mapbox/driving/{coord_str}"
        params = {
            "access_token": self.token,
            "overview": "full",
            "geometries": "geojson",
            "roundtrip": "false",
            "source": source,
            "destination": destination,
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            logger.error("Route optimization failed: %s", response.text)
            return None
        return response.json()
