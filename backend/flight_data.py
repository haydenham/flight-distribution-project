"""CSV loader + lookup helpers for flight data."""
from __future__ import annotations

import math

import pandas as pd

from models import FlightInfo


# Columns we actually need (the raw CSV has ~100 columns).
_USECOLS = [
    "FlightDate",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Tail_Number",
    "Origin",
    "Dest",
    "OriginCityName",
    "DestCityName",
    "CRSDepTime",
    "CRSArrTime",
    "DepTime",
    "ArrTime",
    "DepDelay",
    "ArrDelay",
    "Cancelled",
]


def hhmm_to_min(t: int) -> int:
    """Convert an HHMM integer (e.g. 830) to minutes since midnight."""
    t = int(t)
    return (t // 100) * 60 + (t % 100)


def _clean_str(value) -> str:
    """Return a clean string, mapping NaN/None to ''."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    return s


def load_dataframe(csv_path: str) -> pd.DataFrame:
    """Load the BTS CSV.

    - Ensure FlightDate is str, Tail_Number is str (fillna "").
    - Keep only rows where Cancelled == 0.0 (don't propagate from/through cancellations).
    """
    df = pd.read_csv(
        csv_path,
        usecols=_USECOLS,
        dtype={
            "FlightDate": str,
            "Reporting_Airline": str,
            "Tail_Number": str,
            "Origin": str,
            "Dest": str,
            "OriginCityName": str,
            "DestCityName": str,
        },
        low_memory=False,
    )

    df["FlightDate"] = df["FlightDate"].astype(str)
    df["Tail_Number"] = df["Tail_Number"].fillna("").astype(str)

    # Keep only non-cancelled flights.
    df = df[df["Cancelled"] == 0.0].copy()

    # Normalise numeric schedule columns to ints.
    df["CRSDepTime"] = df["CRSDepTime"].astype(int)
    df["CRSArrTime"] = df["CRSArrTime"].astype(int)
    df["Flight_Number_Reporting_Airline"] = df[
        "Flight_Number_Reporting_Airline"
    ].astype(int)

    # Precompute minutes-since-midnight columns for fast filtering.
    df["CRSDepMin"] = df["CRSDepTime"].apply(hhmm_to_min)
    df["CRSArrMin"] = df["CRSArrTime"].apply(hhmm_to_min)

    df.reset_index(drop=True, inplace=True)
    return df


def get_flight(df: pd.DataFrame, flight_date: str, airline: str, flight_number: int):
    """Return matching row as dict, or None if not found."""
    mask = (
        (df["FlightDate"] == str(flight_date))
        & (df["Reporting_Airline"] == str(airline))
        & (df["Flight_Number_Reporting_Airline"] == int(flight_number))
    )
    sub = df[mask]
    if sub.empty:
        return None
    return sub.iloc[0].to_dict()


def get_aircraft_later_flights(
    df: pd.DataFrame, tail_number: str, flight_date: str, after_crsdeptime: int
):
    """Return all flights with matching tail_number and flight_date with
    CRSDepTime > after_crsdeptime, sorted by CRSDepTime ascending.

    Return [] for empty/blank tail_number.
    """
    tail = _clean_str(tail_number)
    if not tail:
        return []
    mask = (
        (df["Tail_Number"] == tail)
        & (df["FlightDate"] == str(flight_date))
        & (df["CRSDepTime"] > int(after_crsdeptime))
    )
    sub = df[mask].sort_values("CRSDepTime")
    return [r.to_dict() for _, r in sub.iterrows()]


def get_departures_from(
    df: pd.DataFrame,
    airport: str,
    flight_date: str,
    dep_min_from: int,
    dep_min_to: int,
):
    """Return flights from airport on flight_date where CRSDepTime (in minutes)
    falls in [dep_min_from, dep_min_to]. Sort by CRSDepTime ascending.
    """
    mask = (
        (df["Origin"] == str(airport))
        & (df["FlightDate"] == str(flight_date))
        & (df["CRSDepMin"] >= int(dep_min_from))
        & (df["CRSDepMin"] <= int(dep_min_to))
    )
    sub = df[mask].sort_values("CRSDepTime")
    return [r.to_dict() for _, r in sub.iterrows()]


def row_to_flight_info(row: dict) -> FlightInfo:
    """Convert a dataframe row dict to FlightInfo."""
    return FlightInfo(
        flight_date=str(row.get("FlightDate", "")),
        airline=_clean_str(row.get("Reporting_Airline", "")),
        flight_number=int(row.get("Flight_Number_Reporting_Airline", 0)),
        tail_number=_clean_str(row.get("Tail_Number", "")),
        origin=_clean_str(row.get("Origin", "")),
        dest=_clean_str(row.get("Dest", "")),
        origin_city=_clean_str(row.get("OriginCityName", "")),
        dest_city=_clean_str(row.get("DestCityName", "")),
        scheduled_dep=int(row.get("CRSDepTime", 0)),
        scheduled_arr=int(row.get("CRSArrTime", 0)),
    )
