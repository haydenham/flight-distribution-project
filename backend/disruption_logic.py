"""
Deterministic flight-disruption propagation.

This replaces the inner Claude tool-use loop (disruption_agent.py) for the core
computation. The propagation rules are pure arithmetic with a single correct
answer, so a plain function is faster (milliseconds vs. ~10s), free (no API call),
and deterministic (no silent fallback to an empty report).

Returns the exact same DisruptionReport schema, so the API and frontend are unchanged.
"""
from __future__ import annotations

import pandas as pd

from flight_data import (
    get_aircraft_later_flights,
    get_departures_from,
    get_flight,
    hhmm_to_min,
    row_to_flight_info,
)
from models import AffectedFlight, DisruptionInput, DisruptionReport, FlightInfo

# Rule constants (mirroring the task spec).
SLACK_ABSORB_MIN = 5      # a departure delay <= this is absorbed; cascade stops
CONNECTION_WINDOW_MIN = 120   # connections within 2h of scheduled arrival are considered
MIN_CONNECTION_MIN = 45       # below this connect time, a connection is "at risk"
# A cancelled source flight has no aircraft for the next legs — model it as an
# effectively unbounded delay so the whole downstream chain is affected.
CANCELLED_DELAY = 100_000


def _stub_flight(inp: DisruptionInput) -> FlightInfo:
    return FlightInfo(
        flight_date=inp.flight_date, airline=inp.airline,
        flight_number=inp.flight_number, tail_number="", origin="", dest="",
        origin_city="", dest_city="", scheduled_dep=0, scheduled_arr=0,
    )


def compute_disruption(df: pd.DataFrame, inp: DisruptionInput) -> DisruptionReport:
    source_row = get_flight(df, inp.flight_date, inp.airline, inp.flight_number)
    if source_row is None:
        return DisruptionReport(
            source_flight=_stub_flight(inp), input_delay_minutes=inp.delay_minutes,
            cancelled=inp.cancelled, affected_flights=[], total_affected=0, max_depth=0,
        )

    source = row_to_flight_info(source_row)
    effective_delay = CANCELLED_DELAY if inp.cancelled else inp.delay_minutes
    affected: list[AffectedFlight] = []
    seen: set[tuple] = {(source.flight_date, source.airline, source.flight_number)}

    # ── Tail propagation ─────────────────────────────────────────────────────
    # Walk the aircraft's subsequent legs in order. Each leg departs late by
    # (inbound delay − scheduled ground slack); that becomes the next leg's
    # inbound delay. Stop once the schedule absorbs the delay.
    if source.tail_number:
        legs = get_aircraft_later_flights(
            df, source.tail_number, inp.flight_date, source.scheduled_dep
        )
        prev_arr_min = hhmm_to_min(source.scheduled_arr)
        inbound_delay = effective_delay
        depth = 1
        for leg in legs:
            li = row_to_flight_info(leg)
            slack = hhmm_to_min(li.scheduled_dep) - prev_arr_min
            dep_delay = max(0, inbound_delay - slack)
            if dep_delay <= SLACK_ABSORB_MIN:
                break
            key = (li.flight_date, li.airline, li.flight_number)
            affected.append(AffectedFlight(
                flight=li, reason="tail_propagation",
                extra_delay_minutes=dep_delay, depth=depth,
            ))
            seen.add(key)
            inbound_delay = dep_delay
            prev_arr_min = hhmm_to_min(li.scheduled_arr)
            depth += 1

    # ── Connection propagation ───────────────────────────────────────────────
    # Flights leaving the source's destination within the window. A connection
    # is at risk if the delay cuts the available connect time below the minimum.
    arr_min = hhmm_to_min(source.scheduled_arr)
    departures = get_departures_from(
        df, source.dest, inp.flight_date, arr_min, arr_min + CONNECTION_WINDOW_MIN
    )
    for dep in departures:
        ci = row_to_flight_info(dep)
        key = (ci.flight_date, ci.airline, ci.flight_number)
        if key in seen:
            continue  # already counted as a tail leg; don't double-list
        original_connect = hhmm_to_min(ci.scheduled_dep) - arr_min
        remaining_connect = original_connect - effective_delay
        # Only flag connections that were viable to begin with (>= the minimum)
        # but break once the delay is applied. A flight leaving 10 min after you
        # land was never a real connection, so the delay didn't "break" it.
        if original_connect >= MIN_CONNECTION_MIN and remaining_connect < MIN_CONNECTION_MIN:
            affected.append(AffectedFlight(
                flight=ci, reason="connection_at_risk",
                extra_delay_minutes=inp.delay_minutes, depth=1,
            ))
            seen.add(key)

    return DisruptionReport(
        source_flight=source,
        input_delay_minutes=inp.delay_minutes,
        cancelled=inp.cancelled,
        affected_flights=affected,
        total_affected=len(affected),
        max_depth=max((a.depth for a in affected), default=0),
    )
