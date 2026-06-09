"""Pydantic v2 data models for the Flight Disruption Propagation system."""
from __future__ import annotations

from pydantic import BaseModel


class DisruptionInput(BaseModel):
    flight_date: str        # "YYYY-MM-DD"
    airline: str            # 2-letter code
    flight_number: int
    delay_minutes: int      # additional delay applied to this flight
    cancelled: bool = False


class FlightInfo(BaseModel):
    flight_date: str
    airline: str
    flight_number: int
    tail_number: str        # empty string if NaN
    origin: str
    dest: str
    origin_city: str
    dest_city: str
    scheduled_dep: int      # HHMM integer
    scheduled_arr: int      # HHMM integer


class AffectedFlight(BaseModel):
    flight: FlightInfo
    reason: str             # "tail_propagation" or "connection_at_risk"
    extra_delay_minutes: int
    depth: int              # hops from source (1 = directly affected)


class DisruptionReport(BaseModel):
    source_flight: FlightInfo
    input_delay_minutes: int
    cancelled: bool
    affected_flights: list[AffectedFlight]
    total_affected: int
    max_depth: int
