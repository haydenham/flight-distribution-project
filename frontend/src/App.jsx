import React, { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";

const styles = {
  page: {
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    background: "#ffffff",
    color: "#1a1a1a",
    minHeight: "100vh",
    margin: 0,
    padding: "24px",
    boxSizing: "border-box",
  },
  container: { maxWidth: "900px", margin: "0 auto" },
  h1: { fontSize: "24px", marginBottom: "4px" },
  subtitle: { color: "#666", marginTop: 0, marginBottom: "24px" },
  formRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "16px",
    alignItems: "flex-end",
    marginBottom: "16px",
  },
  field: { display: "flex", flexDirection: "column", gap: "4px" },
  label: { fontSize: "13px", color: "#444", fontWeight: 600 },
  input: {
    padding: "8px 10px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    fontSize: "14px",
  },
  button: {
    padding: "10px 18px",
    border: "none",
    borderRadius: "6px",
    background: "#1f6feb",
    color: "#fff",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  buttonDisabled: {
    padding: "10px 18px",
    border: "none",
    borderRadius: "6px",
    background: "#9bb8e6",
    color: "#fff",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "not-allowed",
  },
  error: {
    background: "#fdecea",
    color: "#9b1c1c",
    padding: "12px",
    borderRadius: "6px",
    marginTop: "16px",
  },
  resultBox: {
    marginTop: "24px",
    border: "1px solid #e5e5e5",
    borderRadius: "8px",
    padding: "16px",
  },
  summaryLine: { fontSize: "16px", fontWeight: 600, marginBottom: "12px" },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  },
  th: {
    textAlign: "left",
    borderBottom: "2px solid #ddd",
    padding: "8px",
    background: "#fafafa",
  },
  td: { borderBottom: "1px solid #eee", padding: "8px" },
  badge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: "10px",
    fontSize: "12px",
    fontWeight: 600,
  },
};

function flightLabel(f) {
  return `${f.airline} ${f.flight_number}`;
}

function routeLabel(f) {
  return `${f.origin} \u2192 ${f.dest}`;
}

function formatDepTime(hhmm) {
  // hhmm is an integer like 830 or 1745.
  const t = String(hhmm).padStart(4, "0");
  return `${t.slice(0, 2)}:${t.slice(2)}`;
}

function flightOptionLabel(f) {
  return `${f.airline} ${f.flight_number} \u2014 ${routeLabel(f)} (${formatDepTime(
    f.scheduled_dep
  )})`;
}

export default function App() {
  const [flightDate, setFlightDate] = useState("2022-12-19");
  const [airline, setAirline] = useState("AA");
  const [flightNumber, setFlightNumber] = useState("");
  const [delayMinutes, setDelayMinutes] = useState(60);
  const [cancelled, setCancelled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [flightOptions, setFlightOptions] = useState([]);
  const [flightsLoading, setFlightsLoading] = useState(false);
  const [airlineOptions, setAirlineOptions] = useState([]);

  // Load the airlines that operated on the chosen date so the user can pick a
  // carrier code from a dropdown instead of memorising it.
  useEffect(() => {
    if (!flightDate) {
      setAirlineOptions([]);
      return;
    }
    let cancelledFetch = false;
    const params = new URLSearchParams({ date: flightDate });
    fetch(`${API_BASE}/airlines?${params.toString()}`)
      .then((resp) => (resp.ok ? resp.json() : []))
      .then((data) => {
        if (cancelledFetch) return;
        const list = Array.isArray(data) ? data : [];
        setAirlineOptions(list);
        // Clear the selected airline if it didn't fly on this date.
        if (list.length > 0 && !list.includes(airline.toUpperCase())) {
          setAirline("");
        }
      })
      .catch(() => {
        if (!cancelledFetch) setAirlineOptions([]);
      });
    return () => {
      cancelledFetch = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flightDate]);

  // Load the flights available for the chosen date + airline so the user can
  // pick one from a dropdown instead of guessing a flight number.
  useEffect(() => {
    if (!flightDate || !airline) {
      setFlightOptions([]);
      return;
    }
    let cancelledFetch = false;
    setFlightsLoading(true);
    const params = new URLSearchParams({
      date: flightDate,
      airline: airline.toUpperCase(),
      limit: "1000",
    });
    fetch(`${API_BASE}/flights?${params.toString()}`)
      .then((resp) => (resp.ok ? resp.json() : []))
      .then((data) => {
        if (cancelledFetch) return;
        const list = Array.isArray(data) ? data : [];
        list.sort((a, b) => a.scheduled_dep - b.scheduled_dep);
        setFlightOptions(list);
        // Clear the selected flight if it's no longer in the list.
        if (!list.some((f) => String(f.flight_number) === String(flightNumber))) {
          setFlightNumber("");
        }
      })
      .catch(() => {
        if (!cancelledFetch) setFlightOptions([]);
      })
      .finally(() => {
        if (!cancelledFetch) setFlightsLoading(false);
      });
    return () => {
      cancelledFetch = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flightDate, airline]);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        flight_date: flightDate,
        airline: airline.toUpperCase(),
        flight_number: parseInt(flightNumber, 10),
        delay_minutes: parseInt(delayMinutes, 10),
        cancelled: cancelled,
      };
      const resp = await fetch(`${API_BASE}/disruption`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Request failed (${resp.status}): ${txt}`);
      }
      const data = await resp.json();
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  const src = result ? result.source_flight : null;

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h1 style={styles.h1}>Flight Disruption Propagation</h1>
        <p style={styles.subtitle}>
          Analyze how a delayed or cancelled flight cascades through the network.
        </p>

        <form onSubmit={handleSubmit}>
          <div style={styles.formRow}>
            <div style={styles.field}>
              <label style={styles.label}>Flight date</label>
              <input
                style={styles.input}
                type="date"
                value={flightDate}
                onChange={(e) => setFlightDate(e.target.value)}
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Airline</label>
              <select
                style={{ ...styles.input, minWidth: "120px" }}
                value={airline.toUpperCase()}
                onChange={(e) => setAirline(e.target.value)}
                disabled={airlineOptions.length === 0}
              >
                <option value="">
                  {airlineOptions.length === 0
                    ? "No airlines for this date"
                    : "Select an airline"}
                </option>
                {airlineOptions.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Flight</label>
              <select
                style={{ ...styles.input, minWidth: "260px" }}
                value={flightNumber}
                onChange={(e) => setFlightNumber(e.target.value)}
                disabled={flightsLoading || flightOptions.length === 0}
              >
                <option value="">
                  {flightsLoading
                    ? "Loading flights…"
                    : flightOptions.length === 0
                    ? "No flights for this date/airline"
                    : `Select a flight (${flightOptions.length} available)`}
                </option>
                {flightOptions.map((f) => (
                  <option key={f.flight_number} value={f.flight_number}>
                    {flightOptionLabel(f)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={styles.formRow}>
            <div style={styles.field}>
              <label style={styles.label}>
                Additional delay (min): {delayMinutes}
              </label>
              <input
                type="range"
                min={0}
                max={360}
                step={15}
                value={delayMinutes}
                onChange={(e) => setDelayMinutes(parseInt(e.target.value, 10))}
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Cancelled</label>
              <input
                type="checkbox"
                checked={cancelled}
                onChange={(e) => setCancelled(e.target.checked)}
              />
            </div>
            <div style={styles.field}>
              <button
                type="submit"
                style={
                  loading || !flightNumber
                    ? styles.buttonDisabled
                    : styles.button
                }
                disabled={loading || !flightNumber}
              >
                {loading ? "Analyzing\u2026" : "Analyze Disruption"}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div style={styles.error}>
            <strong>Error:</strong> {error.message}
          </div>
        )}

        {result && src && (
          <div style={styles.resultBox}>
            <div style={styles.summaryLine}>
              {flightLabel(src)} | {routeLabel(src)} | {src.flight_date} |{" "}
              {result.cancelled
                ? "CANCELLED"
                : `+${result.input_delay_minutes} min delay`}
            </div>

            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Flight</th>
                  <th style={styles.th}>Route</th>
                  <th style={styles.th}>Reason</th>
                  <th style={styles.th}>Extra Delay</th>
                  <th style={styles.th}>Depth</th>
                </tr>
              </thead>
              <tbody>
                {result.affected_flights.map((af, idx) => {
                  const isTail = af.reason === "tail_propagation";
                  const rowBg = isTail ? "#fff1e0" : "#e6f2fb";
                  const badgeBg = isTail ? "#f0a04b" : "#4b9cf0";
                  return (
                    <tr key={idx} style={{ background: rowBg }}>
                      <td style={styles.td}>{flightLabel(af.flight)}</td>
                      <td style={styles.td}>{routeLabel(af.flight)}</td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.badge,
                            background: badgeBg,
                            color: "#fff",
                          }}
                        >
                          {af.reason}
                        </span>
                      </td>
                      <td style={styles.td}>{af.extra_delay_minutes} min</td>
                      <td style={styles.td}>{af.depth}</td>
                    </tr>
                  );
                })}
                {result.affected_flights.length === 0 && (
                  <tr>
                    <td style={styles.td} colSpan={5}>
                      No downstream flights affected.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            <div style={{ marginTop: "12px", color: "#444" }}>
              {result.total_affected} flights affected, max cascade depth{" "}
              {result.max_depth}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
