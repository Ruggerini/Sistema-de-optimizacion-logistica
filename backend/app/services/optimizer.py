import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..schemas import (
    OptimizationRequest,
    OptimizationResponse,
    OptimizationSummary,
    StopDetail,
    StopInput,
    TruckInput,
    TruckRoute,
)
from .mapbox import MapboxService


@dataclass
class GeocodedLocation:
    address: str
    latitude: float
    longitude: float


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two lat/lon pairs."""
    radius = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


class OptimizationEngine:
    MAX_STOPS_PER_TRUCK = 9
    DEFAULT_CITY = "St Joseph, MO"

    def __init__(self, mapbox: Optional[MapboxService] = None) -> None:
        self.mapbox = mapbox or MapboxService()

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        if not request.trucks:
            raise ValueError("At least one truck must be provided.")
        if not request.stops:
            raise ValueError("At least one stop must be provided.")

        trucks = request.trucks
        stops = request.stops

        truck_locations = self._geocode_trucks(trucks)
        stop_locations, geocode_failures = self._geocode_stops(stops)

        unassigned_stops: List[StopDetail] = [StopDetail(address=addr) for addr in geocode_failures]

        if not stop_locations:
            return OptimizationResponse(
                summary=OptimizationSummary(
                    trucks_needed=0,
                    total_distance_km=0.0,
                    total_duration_minutes=0.0,
                    unassigned_stops=len(unassigned_stops),
                ),
                assignments=[],
                unassigned=unassigned_stops,
            )

        capacity = len(trucks) * self.MAX_STOPS_PER_TRUCK
        if len(stop_locations) > capacity:
            overflow = stop_locations[capacity:]
            stop_locations = stop_locations[:capacity]
            for item in overflow:
                unassigned_stops.append(StopDetail(address=item.address, latitude=item.latitude, longitude=item.longitude))

        clusters = self._cluster_stops(stop_locations, len(trucks))
        assignments = self._assign_clusters_to_trucks(clusters, trucks, truck_locations)

        optimized_routes: List[TruckRoute] = []
        total_distance_km = 0.0
        total_duration_minutes = 0.0

        for idx, truck in enumerate(trucks):
            cluster_key = assignments.get(idx)
            cluster_stops = clusters.get(cluster_key, []) if cluster_key is not None else []

            if not cluster_stops:
                start_detail = StopDetail(
                    address=truck_locations[truck.name]["start"].address,
                    latitude=truck_locations[truck.name]["start"].latitude,
                    longitude=truck_locations[truck.name]["start"].longitude,
                    eta_minutes=0.0,
                )
                end_detail = StopDetail(
                    address=truck_locations[truck.name]["end"].address,
                    latitude=truck_locations[truck.name]["end"].latitude,
                    longitude=truck_locations[truck.name]["end"].longitude,
                    eta_minutes=0.0,
                )
                route_stops = [start_detail, end_detail]
                optimized_routes.append(
                    TruckRoute(
                        truck_id=truck.id,
                        truck_name=truck.name,
                        zone_label=f"Zone {idx + 1}",
                        total_duration_minutes=0.0,
                        total_distance_km=0.0,
                        google_maps_link=self._build_google_maps_link(route_stops),
                        geometry=None,
                        assigned_stops=[],
                        stops=route_stops,
                    )
                )
                continue

            route = self._optimize_route_for_truck(
                truck, cluster_stops, truck_locations[truck.name], zone_label=f"Zone {idx + 1}"
            )

            optimized_routes.append(route)
            total_distance_km += route.total_distance_km
            total_duration_minutes += route.total_duration_minutes

        summary = OptimizationSummary(
            trucks_needed=sum(1 for route in optimized_routes if route.total_duration_minutes > 0),
            total_distance_km=round(total_distance_km, 2),
            total_duration_minutes=round(total_duration_minutes, 2),
            unassigned_stops=len(unassigned_stops),
        )

        return OptimizationResponse(summary=summary, assignments=optimized_routes, unassigned=unassigned_stops)

    def _geocode_trucks(self, trucks: List[TruckInput]) -> Dict[str, Dict[str, GeocodedLocation]]:
        info: Dict[str, Dict[str, GeocodedLocation]] = {}
        for truck in trucks:
            start_address = self._normalize_address(truck.start_address)
            end_address = self._normalize_address(truck.end_address)
            start = self.mapbox.geocode(start_address)
            end = self.mapbox.geocode(end_address)
            if not start or not end:
                raise ValueError(f"No se pudo geocodificar las direcciones para el camion {truck.name}.")
            info[truck.name] = {
                "start": GeocodedLocation(address=start_address, latitude=start[0], longitude=start[1]),
                "end": GeocodedLocation(address=end_address, latitude=end[0], longitude=end[1]),
            }
        return info

    def _geocode_stops(self, stops: List[StopInput]) -> Tuple[List[GeocodedLocation], List[str]]:
        geocoded: List[GeocodedLocation] = []
        failures: List[str] = []
        for stop in stops:
            address = self._normalize_address(stop.address)
            result = self.mapbox.geocode(address)
            if not result:
                failures.append(address)
                continue
            geocoded.append(GeocodedLocation(address=address, latitude=result[0], longitude=result[1]))
        return geocoded, failures

    def _cluster_stops(self, stops: List[GeocodedLocation], truck_count: int) -> Dict[int, List[GeocodedLocation]]:
        if truck_count <= 1 or len(stops) <= 1:
            return {0: stops}

        k = min(truck_count, len(stops))
        data = np.array([[s.latitude, s.longitude] for s in stops])

        # Initialize centroids with evenly spaced points
        centroids = data[np.linspace(0, len(data) - 1, k, dtype=int)]

        for _ in range(50):
            distances = np.linalg.norm(data[:, None, :] - centroids[None, :, :], axis=2)
            labels = np.argmin(distances, axis=1)

            new_centroids = np.array(
                [data[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i] for i in range(k)]
            )
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        clusters: Dict[int, List[GeocodedLocation]] = {i: [] for i in range(k)}
        for label, stop in zip(labels, stops):
            clusters[label].append(stop)

        # Re-balance clusters to respect capacity
        clusters = self._balance_clusters(clusters, self.MAX_STOPS_PER_TRUCK)
        return clusters

    def _balance_clusters(
        self, clusters: Dict[int, List[GeocodedLocation]], max_per_truck: int
    ) -> Dict[int, List[GeocodedLocation]]:
        overfull = [idx for idx, items in clusters.items() if len(items) > max_per_truck]
        underfull = [idx for idx, items in clusters.items() if len(items) < max_per_truck]

        while overfull and underfull:
            dst_idx = underfull[0]
            src_idx = overfull[0]

            if not clusters[src_idx]:
                overfull.pop(0)
                continue

            moved_stop = clusters[src_idx].pop()
            clusters[dst_idx].append(moved_stop)

            if len(clusters[src_idx]) <= max_per_truck:
                overfull.pop(0)
            if len(clusters[dst_idx]) >= max_per_truck:
                underfull.pop(0)

        return clusters

    def _assign_clusters_to_trucks(
        self,
        clusters: Dict[int, List[GeocodedLocation]],
        trucks: List[TruckInput],
        truck_locations: Dict[str, Dict[str, GeocodedLocation]],
    ) -> Dict[int, int]:
        truck_starts = [truck_locations[truck.name]["start"] for truck in trucks]
        cluster_centroids = {
            idx: GeocodedLocation(
                address=f"cluster-{idx}",
                latitude=sum(stop.latitude for stop in stops) / len(stops),
                longitude=sum(stop.longitude for stop in stops) / len(stops),
            )
            for idx, stops in clusters.items()
            if stops
        }

        assignments: Dict[int, int] = {}
        used_clusters: set[int] = set()

        for truck_idx, truck in enumerate(trucks):
            start_loc = truck_locations[truck.name]["start"]
            best_cluster = None
            best_distance = float("inf")
            for cluster_idx, centroid in cluster_centroids.items():
                if cluster_idx in used_clusters:
                    continue
                distance = haversine(
                    start_loc.latitude, start_loc.longitude, centroid.latitude, centroid.longitude
                )
                if distance < best_distance:
                    best_distance = distance
                    best_cluster = cluster_idx
            if best_cluster is not None:
                assignments[truck_idx] = best_cluster
                used_clusters.add(best_cluster)

        remaining_clusters = [idx for idx in clusters.keys() if idx not in used_clusters]
        remaining_trucks = [idx for idx in range(len(trucks)) if idx not in assignments]

        for truck_idx, cluster_idx in zip(remaining_trucks, remaining_clusters):
            assignments[truck_idx] = cluster_idx

        return assignments

    def _optimize_route_for_truck(
        self,
        truck: TruckInput,
        stops: List[GeocodedLocation],
        truck_locations: Dict[str, GeocodedLocation],
        zone_label: str,
    ) -> TruckRoute:
        coordinates = [truck_locations["start"]] + stops + [truck_locations["end"]]
        assigned_stop_details = [
            StopDetail(
                address=stop.address,
                latitude=stop.latitude,
                longitude=stop.longitude,
                eta_minutes=None,
            )
            for stop in stops
        ]

        coordinate_tuples = [(loc.latitude, loc.longitude) for loc in coordinates]
        optimization = self.mapbox.optimize_trip(coordinate_tuples)
        if not optimization or not optimization.get("trips"):
            raise ValueError(f"No se pudo optimizar la ruta para el camion {truck.name}.")

        trip = optimization["trips"][0]
        waypoint_order = trip.get("waypoint_order", [])

        ordered_indexes = [0] + [idx + 1 for idx in waypoint_order] + [len(coordinates) - 1]

        legs = trip.get("legs", [])
        cumulative_minutes = 0.0
        stop_details: List[StopDetail] = []
        total_distance_km = 0.0

        for seq, coord_idx in enumerate(ordered_indexes):
            location = coordinates[coord_idx]
            eta = cumulative_minutes
            stop_details.append(
                StopDetail(
                    address=location.address,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    eta_minutes=round(eta, 2),
                )
            )
            if seq < len(legs):
                leg = legs[seq]
                if leg is not None:
                    duration_minutes = (leg.get("duration", 0.0) or 0.0) / 60.0
                    distance_km = (leg.get("distance", 0.0) or 0.0) / 1000.0
                    cumulative_minutes += duration_minutes
                    total_distance_km += distance_km

        google_maps_link = self._build_google_maps_link(stop_details)
        ordered_assigned = stop_details[1:-1] if len(stop_details) > 2 else []
        if not ordered_assigned and stops:
            ordered_assigned = [
                StopDetail(
                    address=stop.address,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    eta_minutes=None,
                )
                for stop in stops
            ]

        return TruckRoute(
            truck_id=truck.id,
            truck_name=truck.name,
            zone_label=zone_label,
            total_duration_minutes=round(cumulative_minutes, 2),
            total_distance_km=round(total_distance_km, 2),
            google_maps_link=google_maps_link,
            mapbox_trip_id=trip.get("id"),
            geometry=trip.get("geometry"),
            assigned_stops=assigned_stop_details,
            stops=stop_details,
        )

    def _build_google_maps_link(self, stops: List[StopDetail]) -> str:
        if not stops:
            return ""

        origin = stops[0]
        destination = stops[-1]
        waypoints = stops[1:-1]

        def format_location(stop: StopDetail) -> str:
            if stop.address:
                return quote_plus(stop.address)
            if stop.latitude is not None and stop.longitude is not None:
                return f"{stop.latitude},{stop.longitude}"
            return ""

        waypoint_str = "|".join(
            loc
            for loc in (
                format_location(stop) for stop in waypoints[: self.MAX_STOPS_PER_TRUCK]
            )
            if loc
        )

        params = {
            "api": "1",
            "origin": format_location(origin),
            "destination": format_location(destination),
        }
        if waypoint_str:
            params["waypoints"] = waypoint_str

        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"https://www.google.com/maps/dir/?{query}"

    def _normalize_address(self, address: str) -> str:
        if not address:
            return self.DEFAULT_CITY

        normalized = address.strip().strip(",")
        lower_value = normalized.lower()
        if "st joseph" in lower_value:
            return normalized

        if normalized:
            return f"{normalized}, {self.DEFAULT_CITY}"
        return self.DEFAULT_CITY
