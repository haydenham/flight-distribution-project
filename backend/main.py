"""FastAPI app for the Flight Disruption Propagation system."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import flight_data
from disruption_logic import compute_disruption
from models import DisruptionInput, DisruptionReport

# Resolve CSV path relative to project root (parent of backend/).
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
CSV_PATH = os.environ.get(
    "FLIGHT_DATA_CSV", os.path.join(_PROJECT_ROOT, "Flight_Data_correct.csv")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.df = flight_data.load_dataframe(CSV_PATH)
    yield
    # No special teardown needed.


app = FastAPI(title="Flight Disruption Propagation", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    df = app.state.df
    return {"status": "ok", "rows": int(len(df))}


@app.get("/flights")
def flights(
    date: str | None = Query(default=None),
    airline: str | None = Query(default=None),
    limit: int = Query(default=100),
):
    df = app.state.df
    sub = df
    if date:
        sub = sub[sub["FlightDate"] == str(date)]
    if airline:
        sub = sub[sub["Reporting_Airline"] == str(airline)]
    sub = sub.sort_values(["FlightDate", "CRSDepTime"]).head(int(limit))
    result = []
    for row in sub.itertuples(index=False):
        result.append(
            {
                "flight_date": str(row.FlightDate),
                "airline": str(row.Reporting_Airline),
                "flight_number": int(row.Flight_Number_Reporting_Airline),
                "origin": str(row.Origin),
                "dest": str(row.Dest),
            }
        )
    return result


@app.post("/disruption", response_model=DisruptionReport)
def disruption(payload: DisruptionInput):
    # Pure, fast, deterministic — no API call. FastAPI runs sync endpoints in a
    # worker thread automatically, so the event loop is not blocked.
    df = app.state.df
    return compute_disruption(df, payload)
