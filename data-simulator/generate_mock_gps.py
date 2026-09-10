"""
Real-Time Indian Railway GPS Data Ingestion Service
====================================================

This service supports two data sources:

1. SIMULATION
   - Generates realistic train movement.
   - Simulates acceleration/deceleration.
   - Simulates station stops.
   - Adds GPS noise.
   - Simulates delays.
   - Publishes GPS events to Kafka.

2. REAL_TIME
   - Reads live train-location data from a configured API.
   - Normalizes provider-specific responses.
   - Validates GPS coordinates.
   - Detects stale data.
   - Publishes normalized events to Kafka.

Both modes produce the SAME Kafka event schema.

Environment variables
---------------------

DATA_SOURCE=SIMULATION

KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=railway.gps.location

SIMULATION_INTERVAL_SECONDS=2
REALTIME_INTERVAL_SECONDS=15

REALTIME_API_URL=
REALTIME_API_KEY=
TRACKED_TRAIN_NUMBERS=12951,12952

GPS_NOISE_DEGREES=0.00005
DEFAULT_MAX_SPEED_KMPH=110

STALE_DATA_THRESHOLD_SECONDS=120

Usage
-----

Simulation:

    DATA_SOURCE=SIMULATION python generate_mock_gps.py

Real-time:

    DATA_SOURCE=REAL_TIME python generate_mock_gps.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import random
import signal
import time
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel, Field, ValidationError


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("railway-gps-ingestion")


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(frozen=True)
class Settings:
    """
    Application configuration.

    Environment variables are intentionally used so the same container
    can run in simulation or real-time mode without code changes.
    """

    data_source: str

    kafka_bootstrap_servers: str
    kafka_topic: str

    simulation_interval_seconds: float
    realtime_interval_seconds: float

    realtime_api_url: str
    realtime_api_key: str

    tracked_train_numbers: tuple[str, ...]

    gps_noise_degrees: float

    default_max_speed_kmph: float

    stale_data_threshold_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":

        train_numbers = tuple(
            number.strip()
            for number in os.getenv(
                "TRACKED_TRAIN_NUMBERS",
                "12951,12952,12953",
            ).split(",")
            if number.strip()
        )

        return cls(
            data_source=os.getenv(
                "DATA_SOURCE",
                "SIMULATION",
            ).upper(),

            kafka_bootstrap_servers=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092",
            ),

            kafka_topic=os.getenv(
                "KAFKA_TOPIC",
                "railway.gps.location",
            ),

            simulation_interval_seconds=float(
                os.getenv(
                    "SIMULATION_INTERVAL_SECONDS",
                    "2",
                )
            ),

            realtime_interval_seconds=float(
                os.getenv(
                    "REALTIME_INTERVAL_SECONDS",
                    "15",
                )
            ),

            realtime_api_url=os.getenv(
                "REALTIME_API_URL",
                "",
            ),

            realtime_api_key=os.getenv(
                "REALTIME_API_KEY",
                "",
            ),

            tracked_train_numbers=train_numbers,

            gps_noise_degrees=float(
                os.getenv(
                    "GPS_NOISE_DEGREES",
                    "0.00005",
                )
            ),

            default_max_speed_kmph=float(
                os.getenv(
                    "DEFAULT_MAX_SPEED_KMPH",
                    "110",
                )
            ),

            stale_data_threshold_seconds=int(
                os.getenv(
                    "STALE_DATA_THRESHOLD_SECONDS",
                    "120",
                )
            ),
        )


# ============================================================================
# CANONICAL GPS EVENT
# ============================================================================

class GPSEvent(BaseModel):
    """
    Canonical GPS event.

    IMPORTANT:
    Simulation and real-world providers both produce this exact structure.

    Downstream Kafka consumers therefore do not need to know where the
    location originated.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    train_id: str

    train_number: str

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    speed_kmph: float = Field(
        default=0,
        ge=0,
    )

    heading_degrees: float | None = Field(
        default=None,
        ge=0,
        lt=360,
    )

    timestamp: datetime

    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    delay_seconds: int = Field(
        default=0,
        ge=0,
    )

    status: str

    source: str

    data_age_seconds: float = Field(
        default=0,
        ge=0,
    )

    is_stale: bool = False


# ============================================================================
# ROUTE / SIMULATION MODELS
# ============================================================================

@dataclass(frozen=True)
class RoutePoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Station:
    code: str
    name: str
    latitude: float
    longitude: float
    stop_seconds: int


@dataclass
class SimulatedTrain:
    """
    Runtime state of one simulated train.
    """

    train_id: str
    train_number: str
    train_name: str

    route: list[Station]

    current_station_index: int = 0

    progress: float = 0.0

    speed_kmph: float = 0.0

    heading_degrees: float = 0.0

    delay_seconds: int = 0

    stop_remaining_seconds: float = 0.0

    running: bool = True

    # Maximum permitted train speed.
    max_speed_kmph: float = 110.0


# ============================================================================
# GEOSPATIAL FUNCTIONS
# ============================================================================

EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two coordinates.
    """

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return EARTH_RADIUS_KM * c


def calculate_heading(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate bearing from point A to point B.
    """

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lon = math.radians(lon2 - lon1)

    x = (
        math.sin(delta_lon)
        * math.cos(lat2_rad)
    )

    y = (
        math.cos(lat1_rad)
        * math.sin(lat2_rad)
        -
        math.sin(lat1_rad)
        * math.cos(lat2_rad)
        * math.cos(delta_lon)
    )

    heading = math.degrees(
        math.atan2(x, y)
    )

    return (heading + 360) % 360


def interpolate_coordinate(
    start: RoutePoint,
    end: RoutePoint,
    progress: float,
) -> RoutePoint:
    """
    Interpolate a coordinate between two route points.

    This is sufficient for a mock simulator. For production railway
    geometry, replace this with actual track geometry from GeoJSON.
    """

    progress = max(
        0.0,
        min(1.0, progress),
    )

    return RoutePoint(
        latitude=(
            start.latitude
            +
            (end.latitude - start.latitude)
            * progress
        ),

        longitude=(
            start.longitude
            +
            (end.longitude - start.longitude)
            * progress
        ),
    )


# ============================================================================
# GPS NOISE
# ============================================================================

def add_gps_noise(
    latitude: float,
    longitude: float,
    noise_degrees: float,
) -> tuple[float, float]:
    """
    Simulate normal GPS measurement error.

    This is NOT movement.
    It only represents measurement uncertainty.
    """

    latitude += random.gauss(
        0,
        noise_degrees,
    )

    longitude += random.gauss(
        0,
        noise_degrees,
    )

    return latitude, longitude


# ============================================================================
# SIMULATION ENGINE
# ============================================================================

class GPSSimulator:
    """
    Generates realistic-ish GPS telemetry for development/testing.

    This simulator intentionally produces the same GPSEvent structure as
    the real-time ingestion pipeline.
    """

    def __init__(
        self,
        settings: Settings,
    ):
        self.settings = settings

        self.trains = self._create_trains()

    def _create_trains(
        self,
    ) -> list[SimulatedTrain]:

        # Development route only.
        #
        # Replace with actual route/track geometry when available.
        route = [
            Station(
                code="MMCT",
                name="Mumbai Central",
                latitude=18.9690,
                longitude=72.8193,
                stop_seconds=60,
            ),

            Station(
                code="BVI",
                name="Bandra Terminus",
                latitude=19.0620,
                longitude=72.8400,
                stop_seconds=45,
            ),

            Station(
                code="ST",
                name="Surat",
                latitude=21.1702,
                longitude=72.8311,
                stop_seconds=90,
            ),

            Station(
                code="BRC",
                name="Vadodara",
                latitude=22.3072,
                longitude=73.1812,
                stop_seconds=90,
            ),

            Station(
                code="NDLS",
                name="New Delhi",
                latitude=28.6139,
                longitude=77.2090,
                stop_seconds=120,
            ),
        ]

        train_names = [
            "Mumbai Rajdhani",
            "August Kranti Rajdhani",
            "Mumbai Central Express",
        ]

        trains = []

        for index, train_number in enumerate(
            self.settings.tracked_train_numbers
        ):

            trains.append(
                SimulatedTrain(
                    train_id=f"SIM-{train_number}",
                    train_number=train_number,
                    train_name=train_names[
                        index % len(train_names)
                    ],
                    route=route,
                    max_speed_kmph=(
                        self.settings.default_max_speed_kmph
                    ),
                    stop_remaining_seconds=0,
                )
            )

        return trains

    def _update_train(
        self,
        train: SimulatedTrain,
        delta_seconds: float,
    ) -> GPSEvent:

        current_station = train.route[
            train.current_station_index
        ]

        next_index = (
            train.current_station_index + 1
        )

        # Train has reached the final station.
        if next_index >= len(train.route):

            train.running = False
            train.speed_kmph = 0

            return self._create_event(
                train=train,
                station=current_station,
                latitude=current_station.latitude,
                longitude=current_station.longitude,
                status="TERMINATED",
            )

        next_station = train.route[next_index]

        # ------------------------------------------------------------
        # STATION STOP
        # ------------------------------------------------------------

        if train.stop_remaining_seconds > 0:

            train.speed_kmph = max(
                0,
                train.speed_kmph - (
                    2.0 * delta_seconds
                ),
            )

            train.stop_remaining_seconds -= (
                delta_seconds
            )

            if train.stop_remaining_seconds <= 0:

                train.stop_remaining_seconds = 0

                return self._create_event(
                    train=train,
                    station=current_station,
                    latitude=current_station.latitude,
                    longitude=current_station.longitude,
                    status="ACCELERATING",
                )

            return self._create_event(
                train=train,
                station=current_station,
                latitude=current_station.latitude,
                longitude=current_station.longitude,
                status="STOPPED",
            )

        # ------------------------------------------------------------
        # MOVEMENT
        # ------------------------------------------------------------

        distance_km = haversine_distance_km(
            current_station.latitude,
            current_station.longitude,
            next_station.latitude,
            next_station.longitude,
        )

        # Start moving.
        acceleration = 1.0 * delta_seconds

        train.speed_kmph = min(
            train.max_speed_kmph,
            train.speed_kmph + acceleration,
        )

        # Begin braking when approaching destination.
        remaining_distance = (
            distance_km
            * (1 - train.progress)
        )

        if remaining_distance < 5:

            train.speed_kmph = max(
                15,
                train.speed_kmph - (
                    1.5 * delta_seconds
                ),
            )

        distance_travelled_km = (
            train.speed_kmph
            * delta_seconds
            / 3600
        )

        progress_increment = (
            distance_travelled_km
            / max(distance_km, 0.000001)
        )

        train.progress += progress_increment

        # ------------------------------------------------------------
        # ARRIVAL AT NEXT STATION
        # ------------------------------------------------------------

        if train.progress >= 1:

            train.progress = 0

            train.current_station_index = (
                next_index
            )

            train.speed_kmph = 0

            arrived_station = train.route[
                train.current_station_index
            ]

            train.stop_remaining_seconds = (
                arrived_station.stop_seconds
            )

            # Occasionally simulate operational delay.
            if random.random() < 0.02:

                train.delay_seconds += random.randint(
                    30,
                    180,
                )

            return self._create_event(
                train=train,
                station=arrived_station,
                latitude=arrived_station.latitude,
                longitude=arrived_station.longitude,
                status="STOPPED",
            )

        # ------------------------------------------------------------
        # POSITION BETWEEN STATIONS
        # ------------------------------------------------------------

        start = RoutePoint(
            latitude=current_station.latitude,
            longitude=current_station.longitude,
        )

        end = RoutePoint(
            latitude=next_station.latitude,
            longitude=next_station.longitude,
        )

        position = interpolate_coordinate(
            start,
            end,
            train.progress,
        )

        train.heading_degrees = calculate_heading(
            position.latitude,
            position.longitude,
            end.latitude,
            end.longitude,
        )

        latitude, longitude = add_gps_noise(
            position.latitude,
            position.longitude,
            self.settings.gps_noise_degrees,
        )

        status = (
            "ACCELERATING"
            if train.speed_kmph < 30
            else "RUNNING"
        )

        return self._create_event(
            train=train,
            station=current_station,
            latitude=latitude,
            longitude=longitude,
            status=status,
        )

    def _create_event(
        self,
        train: SimulatedTrain,
        station: Station,
        latitude: float,
        longitude: float,
        status: str,
    ) -> GPSEvent:

        now = datetime.now(timezone.utc)

        return GPSEvent(
            train_id=train.train_id,
            train_number=train.train_number,
            latitude=latitude,
            longitude=longitude,
            speed_kmph=round(
                train.speed_kmph,
                2,
            ),
            heading_degrees=round(
                train.heading_degrees,
                2,
            ),
            timestamp=now,
            ingested_at=now,
            delay_seconds=train.delay_seconds,
            status=status,
            source="SIMULATION",
            data_age_seconds=0,
            is_stale=False,
        )

    def generate_events(
        self,
        delta_seconds: float,
    ) -> list[GPSEvent]:

        events = []

        for train in self.trains:

            if train.running:

                events.append(
                    self._update_train(
                        train,
                        delta_seconds,
                    )
                )

        return events


# ============================================================================
# REAL-TIME TRAIN API
# ============================================================================

class RealtimeTrainClient:
    """
    Generic real-time train-location API client.

    The actual Indian train provider is intentionally configurable.

    Different providers expose different JSON structures, so the response
    is normalized by RealtimeParser below.
    """

    def __init__(
        self,
        settings: Settings,
    ):
        self.settings = settings

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Railway-GPS-Ingestion/1.0"
            ),
        }

        if settings.realtime_api_key:

            headers["Authorization"] = (
                f"Bearer {settings.realtime_api_key}"
            )

        self.client = httpx.AsyncClient(
            timeout=15,
            headers=headers,
        )

    async def fetch(
        self,
    ) -> Any:

        if not self.settings.realtime_api_url:

            raise RuntimeError(
                "REALTIME_API_URL is not configured."
            )

        response = await self.client.get(
            self.settings.realtime_api_url,
            params={
                "train_numbers": ",".join(
                    self.settings.tracked_train_numbers
                )
            },
        )

        response.raise_for_status()

        return response.json()

    async def close(self) -> None:

        await self.client.aclose()


# ============================================================================
# REAL-TIME RESPONSE PARSER
# ============================================================================

class RealtimeParser:
    """
    Converts provider-specific API responses into GPSEvent.

    The parser accepts common field names, but the exact mapping MUST be
    adjusted once the actual provider/API specification is known.
    """

    TRAIN_NUMBER_FIELDS = (
        "train_number",
        "trainNumber",
        "train_no",
        "trainNo",
        "number",
    )

    LATITUDE_FIELDS = (
        "latitude",
        "lat",
        "Latitude",
    )

    LONGITUDE_FIELDS = (
        "longitude",
        "lon",
        "lng",
        "Longitude",
    )

    SPEED_FIELDS = (
        "speed_kmph",
        "speed",
        "speedKmph",
    )

    HEADING_FIELDS = (
        "heading",
        "bearing",
        "direction",
    )

    DELAY_FIELDS = (
        "delay_seconds",
        "delay",
        "delaySeconds",
    )

    TIMESTAMP_FIELDS = (
        "timestamp",
        "time",
        "updated_at",
        "updatedAt",
    )

    STATUS_FIELDS = (
        "status",
        "train_status",
        "trainStatus",
    )

    @classmethod
    def _get(
        cls,
        payload: dict,
        fields: tuple[str, ...],
        default=None,
    ):

        for field in fields:

            if field in payload:

                value = payload[field]

                if value is not None:
                    return value

        return default

    @classmethod
    def parse_one(
        cls,
        payload: dict,
        stale_threshold_seconds: int,
    ) -> GPSEvent:

        train_number = cls._get(
            payload,
            cls.TRAIN_NUMBER_FIELDS,
        )

        latitude = cls._get(
            payload,
            cls.LATITUDE_FIELDS,
        )

        longitude = cls._get(
            payload,
            cls.LONGITUDE_FIELDS,
        )

        if not train_number:
            raise ValueError(
                "Train number missing from API response."
            )

        if latitude is None:
            raise ValueError(
                f"Latitude missing for train {train_number}."
            )

        if longitude is None:
            raise ValueError(
                f"Longitude missing for train {train_number}."
            )

        speed = cls._get(
            payload,
            cls.SPEED_FIELDS,
            0,
        )

        heading = cls._get(
            payload,
            cls.HEADING_FIELDS,
        )

        delay = cls._get(
            payload,
            cls.DELAY_FIELDS,
            0,
        )

        status = cls._get(
            payload,
            cls.STATUS_FIELDS,
            "RUNNING",
        )

        timestamp = cls._parse_timestamp(
            cls._get(
                payload,
                cls.TIMESTAMP_FIELDS,
            )
        )

        now = datetime.now(timezone.utc)

        data_age = max(
            0,
            (
                now - timestamp
            ).total_seconds(),
        )

        is_stale = (
            data_age
            > stale_threshold_seconds
        )

        if is_stale:

            status = "STALE"

        return GPSEvent(
            train_id=f"IND-{train_number}",
            train_number=str(train_number),

            latitude=float(latitude),
            longitude=float(longitude),

            speed_kmph=max(
                0,
                float(speed or 0),
            ),

            heading_degrees=(
                float(heading)
                if heading is not None
                else None
            ),

            timestamp=timestamp,

            ingested_at=now,

            delay_seconds=max(
                0,
                int(delay or 0),
            ),

            status=str(status).upper(),

            source="REAL_TIME",

            data_age_seconds=round(
                data_age,
                2,
            ),

            is_stale=is_stale,
        )

    @staticmethod
    def _parse_timestamp(
        value: Any,
    ) -> datetime:

        if value is None:

            return datetime.now(
                timezone.utc
            )

        if isinstance(value, (int, float)):

            # Support Unix timestamps.
            return datetime.fromtimestamp(
                value,
                tz=timezone.utc,
            )

        if isinstance(value, str):

            normalized = value.replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(
                normalized
            )

            if parsed.tzinfo is None:

                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        return datetime.now(
            timezone.utc
        )

    @classmethod
    def parse_response(
        cls,
        payload: Any,
        stale_threshold_seconds: int,
    ) -> list[GPSEvent]:

        # Providers commonly return:
        #
        # {
        #     "trains": [...]
        # }
        #
        # or simply:
        #
        # [...]
        #

        if isinstance(payload, dict):

            for key in (
                "trains",
                "data",
                "results",
                "locations",
            ):

                if key in payload:

                    payload = payload[key]
                    break

            else:

                payload = [payload]

        if not isinstance(payload, list):

            raise ValueError(
                "Unsupported real-time API response format."
            )

        events = []

        for train_payload in payload:

            if not isinstance(
                train_payload,
                dict,
            ):
                continue

            try:

                event = cls.parse_one(
                    train_payload,
                    stale_threshold_seconds,
                )

                events.append(event)

            except (
                ValueError,
                ValidationError,
            ) as exc:

                logger.warning(
                    "Skipping invalid train event: %s",
                    exc,
                )

        return events


# ============================================================================
# KAFKA PRODUCER
# ============================================================================

class KafkaGPSProducer:
    """
    Publishes normalized GPS events to Kafka.

    Kafka message key = train number.

    This is intentional:
    events belonging to the same train can remain ordered within
    the same Kafka partition.
    """

    def __init__(
        self,
        settings: Settings,
    ):

        self.settings = settings

        self.producer = AIOKafkaProducer(
            bootstrap_servers=(
                settings.kafka_bootstrap_servers
            ),

            key_serializer=lambda key:
                key.encode("utf-8"),

            value_serializer=lambda value:
                json.dumps(
                    value,
                    separators=(",", ":"),
                ).encode("utf-8"),
        )

    async def start(self) -> None:

        logger.info(
            "Connecting to Kafka: %s",
            self.settings.kafka_bootstrap_servers,
        )

        await self.producer.start()

        logger.info(
            "Kafka producer connected."
        )

    async def publish(
        self,
        event: GPSEvent,
    ) -> None:

        payload = event.model_dump(
            mode="json"
        )

        metadata = await self.producer.send_and_wait(
            self.settings.kafka_topic,
            key=event.train_number,
            value=payload,
        )

        logger.debug(
            (
                "Kafka event published | "
                "train=%s | "
                "partition=%s | "
                "offset=%s"
            ),
            event.train_number,
            metadata.partition,
            metadata.offset,
        )

    async def stop(self) -> None:

        await self.producer.stop()

        logger.info(
            "Kafka producer stopped."
        )


# ============================================================================
# DATA INGESTION SERVICE
# ============================================================================

class GPSIngestionService:
    """
    Main orchestration layer.

    Notice that Kafka does NOT care whether the event came from simulation
    or from a real-time provider.
    """

    def __init__(
        self,
        settings: Settings,
    ):

        self.settings = settings

        self.producer = KafkaGPSProducer(
            settings
        )

        self.simulator = None
        self.realtime_client = None

        self.shutdown_event = asyncio.Event()

    async def start(self) -> None:

        await self.producer.start()

        if self.settings.data_source == "SIMULATION":

            logger.info(
                "Starting GPS simulator."
            )

            self.simulator = GPSSimulator(
                self.settings
            )

        elif self.settings.data_source == "REAL_TIME":

            logger.info(
                "Starting real-time train ingestion."
            )

            self.realtime_client = (
                RealtimeTrainClient(
                    self.settings
                )
            )

        else:

            raise ValueError(
                (
                    "Unsupported DATA_SOURCE: "
                    f"{self.settings.data_source}"
                )
            )

    async def run(self) -> None:

        await self.start()

        try:

            if (
                self.settings.data_source
                == "SIMULATION"
            ):

                await self._run_simulation()

            else:

                await self._run_realtime()

        finally:

            await self.stop()

    async def _run_simulation(
        self,
    ) -> None:

        interval = (
            self.settings.simulation_interval_seconds
        )

        logger.info(
            "Simulation interval: %.2f seconds",
            interval,
        )

        previous_time = time.monotonic()

        while not self.shutdown_event.is_set():

            current_time = time.monotonic()

            delta_seconds = (
                current_time
                - previous_time
            )

            previous_time = current_time

            events = (
                self.simulator.generate_events(
                    delta_seconds
                )
            )

            await self._publish_events(
                events
            )

            try:

                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=interval,
                )

            except asyncio.TimeoutError:

                pass

    async def _run_realtime(
        self,
    ) -> None:

        interval = (
            self.settings.realtime_interval_seconds
        )

        logger.info(
            "Real-time polling interval: %.2f seconds",
            interval,
        )

        while not self.shutdown_event.is_set():

            cycle_start = time.monotonic()

            try:

                payload = (
                    await self.realtime_client.fetch()
                )

                events = (
                    RealtimeParser.parse_response(
                        payload,
                        self.settings
                        .stale_data_threshold_seconds,
                    )
                )

                await self._publish_events(
                    events
                )

            except httpx.HTTPError as exc:

                logger.error(
                    "Real-time API request failed: %s",
                    exc,
                )

            except Exception:

                logger.exception(
                    "Real-time ingestion cycle failed."
                )

            elapsed = (
                time.monotonic()
                - cycle_start
            )

            sleep_seconds = max(
                0,
                interval - elapsed,
            )

            try:

                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=sleep_seconds,
                )

            except asyncio.TimeoutError:

                pass

    async def _publish_events(
        self,
        events: list[GPSEvent],
    ) -> None:

        if not events:

            logger.warning(
                "No GPS events received/generated."
            )

            return

        results = await asyncio.gather(
            *(
                self._publish_safe(event)
                for event in events
            ),
            return_exceptions=True,
        )

        successful = sum(
            result is True
            for result in results
        )

        logger.info(
            (
                "GPS ingestion cycle complete | "
                "events=%d | "
                "published=%d"
            ),
            len(events),
            successful,
        )

    async def _publish_safe(
        self,
        event: GPSEvent,
    ) -> bool:

        try:

            await self.producer.publish(
                event
            )

            logger.info(
                (
                    "GPS | "
                    "train=%s | "
                    "lat=%.6f | "
                    "lon=%.6f | "
                    "speed=%.2f km/h | "
                    "delay=%ss | "
                    "source=%s | "
                    "status=%s"
                ),
                event.train_number,
                event.latitude,
                event.longitude,
                event.speed_kmph,
                event.delay_seconds,
                event.source,
                event.status,
            )

            return True

        except Exception:

            logger.exception(
                "Failed to publish GPS event for %s",
                event.train_number,
            )

            return False

    async def stop(self) -> None:

        self.shutdown_event.set()

        if self.realtime_client:

            await self.realtime_client.close()

        await self.producer.stop()

        logger.info(
            "GPS ingestion service stopped."
        )

    def request_shutdown(self) -> None:

        logger.info(
            "Shutdown requested."
        )

        self.shutdown_event.set()


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

async def main() -> None:

    settings = Settings.from_environment()

    logger.info(
        "=============================================="
    )

    logger.info(
        "Indian Railway GPS Ingestion Service"
    )

    logger.info(
        "=============================================="
    )

    logger.info(
        "Data source: %s",
        settings.data_source,
    )

    logger.info(
        "Kafka: %s",
        settings.kafka_bootstrap_servers,
    )

    logger.info(
        "Kafka topic: %s",
        settings.kafka_topic,
    )

    logger.info(
        "Tracked trains: %s",
        ", ".join(
            settings.tracked_train_numbers
        ),
    )

    service = GPSIngestionService(
        settings
    )

    loop = asyncio.get_running_loop()

    for signal_name in (
        signal.SIGINT,
        signal.SIGTERM,
    ):

        try:

            loop.add_signal_handler(
                signal_name,
                service.request_shutdown,
            )

        except NotImplementedError:

            # Windows event-loop compatibility.
            pass

    try:

        await service.run()

    except KeyboardInterrupt:

        service.request_shutdown()

    except Exception:

        logger.exception(
            "Fatal application error."
        )

        raise


if __name__ == "__main__":

    asyncio.run(main())