# Flight Disruption Propagation

A full-stack tool that models how a single delayed (or cancelled) flight cascades
through an airline's network. Enter a flight and an added delay; the app returns
every downstream flight it affects, split into two propagation mechanisms.

- **Backend:** FastAPI + pandas. The propagation is a pure, deterministic function.
- **Frontend:** React + Vite. A form and a results table.

---

## How propagation works

Given a source flight and an additional delay (minutes):

**1. Tail propagation (aircraft cascade)**
The same aircraft (`Tail_Number`) flies a sequence of legs in a day. If it arrives
`D` minutes late, its next departure from that airport is late by
`max(0, D − scheduled_ground_slack)`. That delay carries to the next leg, and so on,
until the schedule's slack absorbs it (≤ 5 minutes).

**2. Connection propagation (passenger risk)**
Flights leaving the source's destination within 2 hours are "at risk" if they were a
viable connection (≥ 45 min connect time) but the delay cuts the remaining connect
time below 45 minutes.

A cancelled source flight is modelled as an effectively unbounded delay.

---

## Project layout

```
flight_data_project/
├── Flight_Data_correct.csv      # data (not in repo — see "Data" below)
├── backend/
│   ├── main.py                  # FastAPI app + endpoints
│   ├── disruption_logic.py      # compute_disruption() — the core algorithm
│   ├── flight_data.py           # CSV loader + lookup helpers
│   ├── models.py                # Pydantic models
│   └── requirements.txt
└── frontend/
    ├── src/App.jsx              # the UI
    └── ...
```

---

## Data

The app expects `Flight_Data_correct.csv` in the project root. It is the U.S. DOT
Bureau of Transportation Statistics **Reporting Carrier On-Time Performance** dataset
for **December 2022** (~240 MB, which is why it is not committed here).

Download it from the BTS TranStats site
(<https://www.transtats.bts.gov/>, "Reporting Carrier On-Time Performance"), selecting
December 2022, and save it as `Flight_Data_correct.csv` in the project root. Required
columns include: `FlightDate, Reporting_Airline, Flight_Number_Reporting_Airline,
Tail_Number, Origin, Dest, OriginCityName, DestCityName, CRSDepTime, CRSArrTime,
DepTime, ArrTime, DepDelay, ArrDelay, Cancelled`.

---

## Running it

**Backend** (terminal 1):

```bash
cd backend
pip3 install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

Check it's up: `curl http://localhost:8000/health` → `{"status":"ok","rows":...}`
(loading the CSV at startup takes a few seconds).

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (`http://localhost:5173`).

No API keys or external services are required — the computation is entirely local.

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{"status":"ok","rows":N}` |
| GET | `/flights?date=&airline=&limit=100` | Browse flights (useful for finding test inputs) |
| POST | `/disruption` | Body: `DisruptionInput` → returns a `DisruptionReport` |

---

## Example

Try **AA 1146 on 2022-12-19** (aircraft N109UW flies 7 legs that day). Compare a
**15-minute** delay (absorbed — few effects) against **120+ minutes** (a multi-leg
tail cascade plus broken connections at BOS).
