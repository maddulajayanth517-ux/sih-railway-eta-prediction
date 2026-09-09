"""
Telemetry Feed & Data Integration Module
Member 4: Station Master Command Center (Python)

Provides real-time GPS telemetry, ML ETA predictions, XAI delay attributions,
and corridor geometry. Integrates with Member 3's backend-api (REST/WebSocket)
with automatic fallback to a high-fidelity Indian Railways simulator.
"""

from __future__ import annotations
import math
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# =====================================================================
# 1. INDIAN RAILWAYS STATIONS & CORRIDOR TOPOLOGY
# =====================================================================

STATIONS: Dict[str, Dict[str, Any]] = {
    # Delhi - Howrah Main Trunk Corridor
    "NDLS": {"name": "New Delhi", "lat": 28.6427, "lon": 77.2195, "platforms": 16, "division": "Delhi", "zone": "NR"},
    "ALJN": {"name": "Aligarh Jn", "lat": 27.8967, "lon": 78.0833, "platforms": 7, "division": "Prayagraj", "zone": "NCR"},
    "TDL":  {"name": "Tundla Jn", "lat": 27.2081, "lon": 78.2431, "platforms": 5, "division": "Prayagraj", "zone": "NCR"},
    "CNB":  {"name": "Kanpur Central", "lat": 26.4547, "lon": 80.3507, "platforms": 10, "division": "Prayagraj", "zone": "NCR"},
    "FTP":  {"name": "Fatehpur", "lat": 25.9284, "lon": 80.8128, "platforms": 4, "division": "Prayagraj", "zone": "NCR"},
    "PRYJ": {"name": "Prayagraj Jn", "lat": 25.4497, "lon": 81.8282, "platforms": 10, "division": "Prayagraj", "zone": "NCR"},
    "MZP":  {"name": "Mirzapur", "lat": 25.1337, "lon": 82.5644, "platforms": 3, "division": "Danapur", "zone": "ECR"},
    "DDU":  {"name": "Pt. Deen Dayal Upadhyaya Jn", "lat": 25.2817, "lon": 83.1189, "platforms": 8, "division": "DDU", "zone": "ECR"},
    "BXR":  {"name": "Buxar", "lat": 25.5684, "lon": 83.9777, "platforms": 3, "division": "Danapur", "zone": "ECR"},
    "ARA":  {"name": "Ara Jn", "lat": 25.5562, "lon": 84.6603, "platforms": 4, "division": "Danapur", "zone": "ECR"},
    "PNBE": {"name": "Patna Jn", "lat": 25.6022, "lon": 85.1376, "platforms": 10, "division": "Danapur", "zone": "ECR"},
    "MKA":  {"name": "Mokama", "lat": 25.3980, "lon": 85.9189, "platforms": 4, "division": "Danapur", "zone": "ECR"},
    "KIUL": {"name": "Kiul Jn", "lat": 25.1764, "lon": 86.0963, "platforms": 5, "division": "Danapur", "zone": "ECR"},
    "JAJ":  {"name": "Jhajha", "lat": 24.7733, "lon": 86.3776, "platforms": 4, "division": "Asansol", "zone": "ER"},
    "JSME": {"name": "Jasidih Jn", "lat": 24.5165, "lon": 86.6467, "platforms": 5, "division": "Asansol", "zone": "ER"},
    "MDP":  {"name": "Madhupur Jn", "lat": 24.2589, "lon": 86.6492, "platforms": 4, "division": "Asansol", "zone": "ER"},
    "CRJ":  {"name": "Chittaranjan", "lat": 23.8647, "lon": 86.8719, "platforms": 3, "division": "Asansol", "zone": "ER"},
    "ASN":  {"name": "Asansol Jn", "lat": 23.6871, "lon": 86.9746, "platforms": 8, "division": "Asansol", "zone": "ER"},
    "DGR":  {"name": "Durgapur", "lat": 23.4983, "lon": 87.3119, "platforms": 5, "division": "Asansol", "zone": "ER"},
    "BWN":  {"name": "Barddhaman Jn", "lat": 23.2324, "lon": 87.8615, "platforms": 8, "division": "Howrah", "zone": "ER"},
    "HWH":  {"name": "Howrah Jn", "lat": 22.5850, "lon": 88.3426, "platforms": 23, "division": "Howrah", "zone": "ER"},

    # Delhi - Mumbai Trunk Corridor Additions
    "MMCT": {"name": "Mumbai Central", "lat": 18.9696, "lon": 72.8193, "platforms": 9, "division": "Mumbai", "zone": "WR"},
    "ST":   {"name": "Surat", "lat": 21.2049, "lon": 72.8406, "platforms": 6, "division": "Mumbai", "zone": "WR"},
    "BRC":  {"name": "Vadodara Jn", "lat": 22.3107, "lon": 73.1812, "platforms": 7, "division": "Vadodara", "zone": "WR"},
    "RTM":  {"name": "Ratlam Jn", "lat": 23.3441, "lon": 75.0375, "platforms": 7, "division": "Ratlam", "zone": "WR"},
    "KOTA": {"name": "Kota Jn", "lat": 25.2138, "lon": 75.8648, "platforms": 6, "division": "Kota", "zone": "WCR"},
    "SWM":  {"name": "Sawai Madhopur", "lat": 25.9928, "lon": 76.3571, "platforms": 4, "division": "Kota", "zone": "WCR"},
    "MTJ":  {"name": "Mathura Jn", "lat": 27.4924, "lon": 77.6737, "platforms": 10, "division": "Agra", "zone": "NCR"},
    "NZM":  {"name": "Hazrat Nizamuddin", "lat": 28.5889, "lon": 77.2534, "platforms": 9, "division": "Delhi", "zone": "NR"},
}

CORRIDOR_DELHI_HOWRAH = [
    "NDLS", "ALJN", "TDL", "CNB", "FTP", "PRYJ", "MZP", "DDU",
    "BXR", "ARA", "PNBE", "MKA", "KIUL", "JAJ", "JSME", "MDP",
    "CRJ", "ASN", "DGR", "BWN", "HWH"
]

CORRIDOR_DELHI_MUMBAI = [
    "MMCT", "ST", "BRC", "RTM", "KOTA", "SWM", "MTJ", "NZM", "NDLS"
]

# Track Sections with Block Capacity
TRACK_SECTIONS: List[Dict[str, Any]] = [
    {"section_id": "SEC-NDLS-ALJN", "from": "NDLS", "to": "ALJN", "tracks": "Double Quadruple", "max_speed": 130, "distance_km": 131},
    {"section_id": "SEC-ALJN-CNB",  "from": "ALJN", "to": "CNB",  "tracks": "Double Auto-Signaled", "max_speed": 130, "distance_km": 303},
    {"section_id": "SEC-CNB-PRYJ",  "from": "CNB",  "to": "PRYJ", "tracks": "Triple Auto-Signaled", "max_speed": 130, "distance_km": 194},
    {"section_id": "SEC-PRYJ-DDU",  "from": "PRYJ", "to": "DDU",  "tracks": "Triple Dedicated", "max_speed": 130, "distance_km": 153},
    {"section_id": "SEC-DDU-PNBE",  "from": "DDU",  "to": "PNBE", "tracks": "Double Electrified", "max_speed": 110, "distance_km": 214},
    {"section_id": "SEC-PNBE-ASN",  "from": "PNBE", "to": "ASN",  "tracks": "Double Electrified", "max_speed": 110, "distance_km": 331},
    {"section_id": "SEC-ASN-HWH",   "from": "ASN",  "to": "HWH",   "tracks": "Quadruple Suburban", "max_speed": 130, "distance_km": 200},
    {"section_id": "SEC-NZM-KOTA",  "from": "NZM",  "to": "KOTA",  "tracks": "Double High Speed", "max_speed": 130, "distance_km": 458},
    {"section_id": "SEC-KOTA-BRC",  "from": "KOTA", "to": "BRC",   "tracks": "Double High Speed", "max_speed": 130, "distance_km": 528},
    {"section_id": "SEC-BRC-MMCT",  "from": "BRC",  "to": "MMCT",  "tracks": "Double Suburban-Auto", "max_speed": 120, "distance_km": 392},
]

# =====================================================================
# 2. ROSTER OF REAL INDIAN RAILWAYS EXPRESS FLEET
# =====================================================================

INITIAL_TRAINS_ROSTER: List[Dict[str, Any]] = [
    {
        "train_id": "12301",
        "train_name": "Howrah Rajdhani Express",
        "type": "Rajdhani Express",
        "corridor": "NDLS-HWH",
        "origin": "HWH",
        "destination": "NDLS",
        "direction": "UP",
        "progress_pct": 0.62,
        "base_speed": 118,
        "assigned_platform": 4,
        "scheduled_arrival": "10:05",
        "priority": 1,
        "crew_id": "LP-DEL-4019",
        "rake_id": "LHB-RAJ-01",
    },
    {
        "train_id": "12302",
        "train_name": "Kolkata Rajdhani Express",
        "type": "Rajdhani Express",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "HWH",
        "direction": "DOWN",
        "progress_pct": 0.38,
        "base_speed": 112,
        "assigned_platform": 8,
        "scheduled_arrival": "18:40",
        "priority": 1,
        "crew_id": "LP-HWH-1102",
        "rake_id": "LHB-RAJ-02",
    },
    {
        "train_id": "22436",
        "train_name": "Vande Bharat Express",
        "type": "Vande Bharat",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "BSB",
        "direction": "DOWN",
        "progress_pct": 0.28,
        "base_speed": 128,
        "assigned_platform": 1,
        "scheduled_arrival": "14:00",
        "priority": 1,
        "crew_id": "LP-CNB-8831",
        "rake_id": "VB-T18-09",
    },
    {
        "train_id": "12423",
        "train_name": "Dibrugarh Rajdhani",
        "type": "Rajdhani Express",
        "corridor": "NDLS-HWH",
        "origin": "DBRG",
        "destination": "NDLS",
        "direction": "UP",
        "progress_pct": 0.58,
        "base_speed": 105,
        "assigned_platform": 4,  # Intentional initial platform conflict with 12301
        "scheduled_arrival": "10:20",
        "priority": 1,
        "crew_id": "LP-DDU-5021",
        "rake_id": "LHB-RAJ-08",
    },
    {
        "train_id": "12004",
        "train_name": "Lucknow Swarna Shatabdi",
        "type": "Shatabdi Express",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "LKO",
        "direction": "DOWN",
        "progress_pct": 0.16,
        "base_speed": 110,
        "assigned_platform": 2,
        "scheduled_arrival": "12:35",
        "priority": 2,
        "crew_id": "LP-LKO-3012",
        "rake_id": "LHB-SHT-03",
    },
    {
        "train_id": "12802",
        "train_name": "Purushottam Express",
        "type": "Superfast Express",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "PURI",
        "direction": "DOWN",
        "progress_pct": 0.44,
        "base_speed": 88,
        "assigned_platform": 5,
        "scheduled_arrival": "21:15",
        "priority": 3,
        "crew_id": "LP-PRYJ-7724",
        "rake_id": "ICF-SF-44",
    },
    {
        "train_id": "12382",
        "train_name": "Poorva Express",
        "type": "Superfast Express",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "HWH",
        "direction": "DOWN",
        "progress_pct": 0.52,
        "base_speed": 45,  # Slow speed caution
        "assigned_platform": 6,
        "scheduled_arrival": "16:55",
        "priority": 3,
        "crew_id": "LP-DDU-9031",
        "rake_id": "LHB-SF-19",
    },
    {
        "train_id": "12554",
        "train_name": "Vaishali Express",
        "type": "Superfast Express",
        "corridor": "NDLS-HWH",
        "origin": "NDLS",
        "destination": "SHC",
        "direction": "DOWN",
        "progress_pct": 0.22,
        "base_speed": 82,
        "assigned_platform": 7,
        "scheduled_arrival": "19:20",
        "priority": 3,
        "crew_id": "LP-DEL-6621",
        "rake_id": "ICF-SF-88",
    },
    {
        "train_id": "12259",
        "train_name": "Sealdah Bikaner Duronto",
        "type": "Duronto Express",
        "corridor": "NDLS-HWH",
        "origin": "SDAH",
        "destination": "BKN",
        "direction": "UP",
        "progress_pct": 0.74,
        "base_speed": 115,
        "assigned_platform": 3,
        "scheduled_arrival": "11:10",
        "priority": 2,
        "crew_id": "LP-ASN-4120",
        "rake_id": "LHB-DUR-05",
    },
    {
        "train_id": "12417",
        "train_name": "Prayagraj Express",
        "type": "Superfast Express",
        "corridor": "NDLS-HWH",
        "origin": "PRYJ",
        "destination": "NDLS",
        "direction": "UP",
        "progress_pct": 0.85,
        "base_speed": 6,  # Halted / Outer Signal Hold
        "assigned_platform": 14,
        "scheduled_arrival": "07:00",
        "priority": 2,
        "crew_id": "LP-PRYJ-2201",
        "rake_id": "LHB-SF-12",
    },
    {
        "train_id": "12393",
        "train_name": "Sampoorna Kranti Express",
        "type": "Superfast Express",
        "corridor": "NDLS-HWH",
        "origin": "RJPB",
        "destination": "NDLS",
        "direction": "UP",
        "progress_pct": 0.69,
        "base_speed": 102,
        "assigned_platform": 16,
        "scheduled_arrival": "07:55",
        "priority": 2,
        "crew_id": "LP-PNBE-8172",
        "rake_id": "LHB-SF-31",
    },
    {
        "train_id": "12951",
        "train_name": "Mumbai Tejas Rajdhani",
        "type": "Rajdhani Express",
        "corridor": "NDLS-MMCT",
        "origin": "MMCT",
        "destination": "NDLS",
        "direction": "UP",
        "progress_pct": 0.45,
        "base_speed": 122,
        "assigned_platform": 1,
        "scheduled_arrival": "08:32",
        "priority": 1,
        "crew_id": "LP-BRC-3392",
        "rake_id": "TEJAS-01",
    },
    {
        "train_id": "12952",
        "train_name": "Mumbai Tejas Rajdhani (Down)",
        "type": "Rajdhani Express",
        "corridor": "NDLS-MMCT",
        "origin": "NDLS",
        "destination": "MMCT",
        "direction": "DOWN",
        "progress_pct": 0.71,
        "base_speed": 125,
        "assigned_platform": 1,
        "scheduled_arrival": "08:35",
        "priority": 1,
        "crew_id": "LP-KOTA-5541",
        "rake_id": "TEJAS-02",
    },
    {
        "train_id": "12953",
        "train_name": "August Kranti Tejas Rajdhani",
        "type": "Rajdhani Express",
        "corridor": "NDLS-MMCT",
        "origin": "MMCT",
        "destination": "NZM",
        "direction": "UP",
        "progress_pct": 0.81,
        "base_speed": 115,
        "assigned_platform": 3,
        "scheduled_arrival": "10:55",
        "priority": 1,
        "crew_id": "LP-RTM-1194",
        "rake_id": "TEJAS-04",
    },
    {
        "train_id": "12009",
        "train_name": "Mumbai Ahmedabad Shatabdi",
        "type": "Shatabdi Express",
        "corridor": "NDLS-MMCT",
        "origin": "MMCT",
        "destination": "ADI",
        "direction": "DOWN",
        "progress_pct": 0.32,
        "base_speed": 105,
        "assigned_platform": 5,
        "scheduled_arrival": "12:45",
        "priority": 2,
        "crew_id": "LP-ST-7731",
        "rake_id": "LHB-SHT-08",
    },
]

# =====================================================================
# 3. INTERPOLATION & SPEED BAND HELPER UTILITIES
# =====================================================================

def get_speed_band(speed: float) -> str:
    """Classify train speed into Green (Normal), Yellow (Slow), Red (Halted)."""
    if speed >= 60.0:
        return "Normal"
    elif speed >= 10.0:
        return "Slow"
    return "Halted"

def get_speed_color(speed: float) -> str:
    """Return hex color code corresponding to speed profile."""
    if speed >= 60.0:
        return "#10b981"  # Emerald Green
    elif speed >= 10.0:
        return "#f59e0b"  # Amber Yellow
    return "#ef4444"      # Crimson Red

def interpolate_coordinates(
    corridor_stations: List[str], progress: float, direction: str = "DOWN"
) -> Tuple[float, float, str, str]:
    """
    Interpolates GPS coordinates along a sequence of stations based on journey progress (0.0 to 1.0).
    Returns (lat, lon, last_station_code, next_station_code).
    """
    stations_list = list(corridor_stations)
    if direction == "UP":
        stations_list.reverse()

    n = len(stations_list)
    if n < 2:
        st = STATIONS[stations_list[0]]
        return st["lat"], st["lon"], stations_list[0], stations_list[0]

    clamped_prog = max(0.0, min(1.0, progress))
    segment_float = clamped_prog * (n - 1)
    idx = int(math.floor(segment_float))
    idx = min(idx, n - 2)
    local_ratio = segment_float - idx

    s1_code = stations_list[idx]
    s2_code = stations_list[idx + 1]

    s1 = STATIONS[s1_code]
    s2 = STATIONS[s2_code]

    lat = s1["lat"] + (s2["lat"] - s1["lat"]) * local_ratio
    lon = s1["lon"] + (s2["lon"] - s1["lon"]) * local_ratio

    return lat, lon, s1_code, s2_code

# =====================================================================
# 4. TELEMETRY STATE MANAGER CLASS
# =====================================================================

class TelemetryFeed:
    """
    Central data provider for Member 4 Command Center.
    Handles dynamic live telemetry updates, ETA prediction calculations,
    platform conflict tracking, and operational overrides.
    """

    def __init__(self):
        self.trains_state: Dict[str, Dict[str, Any]] = {}
        self.maintenance_blocks: List[Dict[str, Any]] = []
        self.caution_orders: List[Dict[str, Any]] = []
        self.last_tick: float = time.time()
        self.backend_url: str = "http://localhost:8000"
        self.ws_url: str = "ws://localhost:8000/ws/train-stream"
        self.is_connected_backend: bool = False
        self._initialize_trains()

    def _initialize_trains(self):
        """Builds initial state dictionary with complete telemetry & XAI predictions."""
        for t in INITIAL_TRAINS_ROSTER:
            train_id = t["train_id"]
            corridor = CORRIDOR_DELHI_HOWRAH if t["corridor"] == "NDLS-HWH" else CORRIDOR_DELHI_MUMBAI
            lat, lon, last_st, next_st = interpolate_coordinates(corridor, t["progress_pct"], t["direction"])

            # Compute initial realistic delay and ETA
            speed = t["base_speed"]
            delay_minutes = 0
            reasons = []

            if speed < 10:
                delay_minutes = random.randint(35, 65)
                reasons = ["Signal clearance hold at station approach", "Downstream track block occupation"]
            elif speed < 60:
                delay_minutes = random.randint(12, 28)
                reasons = ["Caution order (30 km/h) due to track tamping", "Winter dense fog speed restriction"]
            else:
                delay_minutes = random.choice([0, 2, 5])
                reasons = ["Normal sectional running", "No active track restrictions"]

            # Calculate predicted ETA
            now = datetime.now()
            scheduled_parts = [int(p) for p in t["scheduled_arrival"].split(":")]
            scheduled_dt = now.replace(hour=scheduled_parts[0], minute=scheduled_parts[1], second=0, microsecond=0)
            predicted_dt = scheduled_dt + timedelta(minutes=delay_minutes)

            # XAI Feature Breakdown (SHAP-inspired weights summing to predicted delay)
            shap_breakdown = {
                "Track Congestion Factor": round(delay_minutes * 0.42, 1),
                "Weather / Fog Severity": round(delay_minutes * 0.28, 1),
                "Signal Interlocking Wait": round(delay_minutes * 0.18, 1),
                "Preceding Train Cushion": round(delay_minutes * 0.12, 1),
            }

            self.trains_state[train_id] = {
                "train_id": train_id,
                "train_name": t["train_name"],
                "type": t["type"],
                "corridor": t["corridor"],
                "origin": t["origin"],
                "destination": t["destination"],
                "direction": t["direction"],
                "progress_pct": t["progress_pct"],
                "current_latitude": lat,
                "current_longitude": lon,
                "current_speed": speed,
                "speed_band": get_speed_band(speed),
                "speed_color": get_speed_color(speed),
                "last_station_code": last_st,
                "next_station_code": next_st,
                "assigned_platform": t["assigned_platform"],
                "scheduled_arrival": t["scheduled_arrival"],
                "predicted_eta": predicted_dt.strftime("%H:%M"),
                "predicted_delay_minutes": delay_minutes,
                "confidence_score": round(random.uniform(91.5, 98.5), 1),
                "delay_reasons": reasons,
                "shap_breakdown": shap_breakdown,
                "has_platform_conflict": False,
                "crew_id": t["crew_id"],
                "rake_id": t["rake_id"],
                "priority": t["priority"],
                "last_updated": now.strftime("%H:%M:%S"),
            }

        self.detect_platform_conflicts()

    def tick_simulation(self, delta_time: float = 2.0):
        """
        Advances train telemetry forward along track corridors.
        Applies impact of active maintenance blocks and caution orders dynamically.
        """
        for train_id, data in self.trains_state.items():
            corridor = CORRIDOR_DELHI_HOWRAH if data["corridor"] == "NDLS-HWH" else CORRIDOR_DELHI_MUMBAI

            # Check if train is affected by any active maintenance blocks
            in_maintenance_block = False
            for mb in self.maintenance_blocks:
                if mb.get("active", True) and (data["next_station_code"] == mb.get("station") or data["last_station_code"] == mb.get("station")):
                    in_maintenance_block = True
                    break

            # Check if affected by caution orders
            in_caution_zone = False
            for co in self.caution_orders:
                if co.get("active", True) and (data["next_station_code"] == co.get("station") or data["last_station_code"] == co.get("station")):
                    in_caution_zone = True
                    break

            # Dynamic speed adjustment
            if in_maintenance_block:
                data["current_speed"] = max(0, min(8, data["current_speed"] - 15))
                data["predicted_delay_minutes"] += 1
                if "Track Maintenance Block active ahead" not in data["delay_reasons"]:
                    data["delay_reasons"].insert(0, "Track Maintenance Block active ahead")
            elif in_caution_zone:
                data["current_speed"] = min(30, max(15, data["current_speed"]))
                data["predicted_delay_minutes"] = max(data["predicted_delay_minutes"], 15)
                if "Caution Order (30 km/h limit) imposed" not in data["delay_reasons"]:
                    data["delay_reasons"].insert(0, "Caution Order (30 km/h limit) imposed")
            else:
                # Normal operational jitter
                jitter = random.uniform(-2.5, 3.0)
                # Keep train moving at reasonable speed
                if data["current_speed"] < 10 and not in_maintenance_block and random.random() < 0.2:
                    data["current_speed"] = random.uniform(35, 75)
                else:
                    data["current_speed"] = max(0, min(130, data["current_speed"] + jitter))

            # Progress train along route
            step = (data["current_speed"] / 3600.0) * delta_time * 0.008
            data["progress_pct"] = (data["progress_pct"] + step) % 1.0

            lat, lon, last_st, next_st = interpolate_coordinates(corridor, data["progress_pct"], data["direction"])
            data["current_latitude"] = lat
            data["current_longitude"] = lon
            data["last_station_code"] = last_st
            data["next_station_code"] = next_st
            data["speed_band"] = get_speed_band(data["current_speed"])
            data["speed_color"] = get_speed_color(data["current_speed"])

            # Recalculate ETA string
            now = datetime.now()
            sched_parts = [int(p) for p in data["scheduled_arrival"].split(":")]
            sched_dt = now.replace(hour=sched_parts[0], minute=sched_parts[1], second=0, microsecond=0)
            pred_dt = sched_dt + timedelta(minutes=data["predicted_delay_minutes"])
            data["predicted_eta"] = pred_dt.strftime("%H:%M")
            data["last_updated"] = now.strftime("%H:%M:%S")

        self.detect_platform_conflicts()

    def detect_platform_conflicts(self) -> List[Dict[str, Any]]:
        """
        Scans upcoming trains arriving at stations and identifies conflicting
        requests (same station, same platform, within 20 minutes window).
        """
        conflicts = []
        station_allocations: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}

        for train_id, t in self.trains_state.items():
            t["has_platform_conflict"] = False
            station = t["next_station_code"]
            platform = t["assigned_platform"]

            if station not in station_allocations:
                station_allocations[station] = {}
            if platform not in station_allocations[station]:
                station_allocations[station][platform] = []
            station_allocations[station][platform].append(t)

        for station, p_map in station_allocations.items():
            for platform, t_list in p_map.items():
                if len(t_list) > 1:
                    # Potential conflict
                    for i in range(len(t_list)):
                        for j in range(i + 1, len(t_list)):
                            t1 = t_list[i]
                            t2 = t_list[j]
                            t1["has_platform_conflict"] = True
                            t2["has_platform_conflict"] = True
                            conflicts.append({
                                "station": station,
                                "platform": platform,
                                "train_1_id": t1["train_id"],
                                "train_1_name": t1["train_name"],
                                "train_1_eta": t1["predicted_eta"],
                                "train_2_id": t2["train_id"],
                                "train_2_name": t2["train_name"],
                                "train_2_eta": t2["predicted_eta"],
                                "conflict_severity": "CRITICAL" if abs(t1["predicted_delay_minutes"] - t2["predicted_delay_minutes"]) < 10 else "MODERATE",
                            })
        return conflicts

    def auto_resolve_platform_conflicts(self, target_station: Optional[str] = None) -> int:
        """
        Bipartite greedy resolution algorithm: automatically reallocates conflicting
        trains to the lowest unoccupied platform at the destination station.
        """
        resolved_count = 0
        conflicts = self.detect_platform_conflicts()

        for c in conflicts:
            station = c["station"]
            if target_station and station != target_station:
                continue

            max_platforms = STATIONS.get(station, {}).get("platforms", 10)
            occupied_platforms = {
                t["assigned_platform"] for t in self.trains_state.values()
                if t["next_station_code"] == station and t["train_id"] != c["train_2_id"]
            }

            # Find lowest available platform
            for p in range(1, max_platforms + 1):
                if p not in occupied_platforms:
                    self.reassign_platform(c["train_2_id"], p, f"Auto-resolved conflict with Train {c['train_1_id']}")
                    resolved_count += 1
                    break

        self.detect_platform_conflicts()
        return resolved_count

    def reassign_platform(self, train_id: str, new_platform: int, reason: str = "Manual Override"):
        """Reassigns train to another platform and updates telemetry state."""
        if train_id in self.trains_state:
            old_p = self.trains_state[train_id]["assigned_platform"]
            self.trains_state[train_id]["assigned_platform"] = new_platform
            self.detect_platform_conflicts()
            return True, f"Train {train_id} platform changed from {old_p} -> {new_platform} ({reason})"
        return False, f"Train {train_id} not found"

    def add_maintenance_block(self, block_data: Dict[str, Any]):
        """Adds a Station Master track maintenance block."""
        block_data["id"] = f"MB-{len(self.maintenance_blocks) + 101}"
        block_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        block_data["active"] = True
        self.maintenance_blocks.append(block_data)

    def add_caution_order(self, caution_data: Dict[str, Any]):
        """Adds a Speed Restriction Caution Order (e.g. 30 km/h)."""
        caution_data["id"] = f"CO-{len(self.caution_orders) + 201}"
        caution_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caution_data["active"] = True
        self.caution_orders.append(caution_data)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates aggregate dashboard KPIs."""
        total = len(self.trains_state)
        delayed = sum(1 for t in self.trains_state.values() if t["predicted_delay_minutes"] > 10)
        halted = sum(1 for t in self.trains_state.values() if t["current_speed"] < 10)
        avg_delay = (
            sum(t["predicted_delay_minutes"] for t in self.trains_state.values()) / total
            if total > 0 else 0
        )
        conflicts = sum(1 for t in self.trains_state.values() if t["has_platform_conflict"])
        punctuality_pct = round(((total - delayed) / total * 100), 1) if total > 0 else 100.0

        return {
            "total_trains": total,
            "delayed_trains": delayed,
            "halted_trains": halted,
            "average_delay_minutes": round(avg_delay, 1),
            "platform_conflicts": conflicts // 2 if conflicts > 1 else conflicts,
            "punctuality_rate": punctuality_pct,
            "active_blocks": len([b for b in self.maintenance_blocks if b.get("active", True)]),
            "active_cautions": len([c for c in self.caution_orders if c.get("active", True)]),
        }

# Global singleton instance for shared state across Streamlit reruns
_TELEMETRY_INSTANCE: Optional[TelemetryFeed] = None

def get_telemetry_feed() -> TelemetryFeed:
    global _TELEMETRY_INSTANCE
    if _TELEMETRY_INSTANCE is None:
        _TELEMETRY_INSTANCE = TelemetryFeed()
    return _TELEMETRY_INSTANCE

