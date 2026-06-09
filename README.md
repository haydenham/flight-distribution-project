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

**Any time span works.** The app doesn't assume a specific month or year — any BTS
extract with the columns and formats above will load (a single day, a different month,
a full year). Just enter a date present in your data. Two things to note:
- Propagation is computed **within a single calendar day** — cascades and connections
  that cross midnight are not tracked.
- The frontend's default date (`2022-12-19`) is just a starting value; change it to any
  date in your dataset.

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

## Examples to try

All from the December 2022 dataset. Use `GET /flights?date=&airline=` to find more.

| Flight | Date | Delay | What it shows |
|---|---|---|---|
| **AA 1146** PHL→BOS | 2022-12-19 | 15 vs 120+ | Aircraft N109UW flies 7 legs. At 15 min the slack absorbs it (few effects); at 120+ min you get a multi-leg tail cascade (depth grows to 3) plus many broken BOS connections. The clearest demo of both mechanisms. |
| **DL 2979** LAX→ATL | 2022-12-22 | 120 | Huge connection fan-out at the ATL hub — 70+ at-risk connections. Shows how a hub amplifies a single delay. |
| **WN 576** CLE→BWI | 2022-12-22 | 120 | Southwest point-to-point: a depth-2 aircraft cascade across consecutive legs. |
| **B6 2867** MCO→PSE | 2022-12-22 | 120 | A contained case — only 2 downstream flights and no broken connections. Shows propagation doesn't always explode. |

**Tip:** for any flight, slide the delay from low to high to watch the tail cascade
deepen and connections begin to break.
