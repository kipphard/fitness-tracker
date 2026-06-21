import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiDelete, apiPut } from "../api/client";
import type { WeightTrend } from "../api/types";
import { useApi } from "../hooks/useApi";
import { num, oneDecimal, shortDate } from "../lib/format";
import { useTheme } from "../theme";
import { Card } from "./Card";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function WeightScreen() {
  const { t } = useTranslation();
  const { chart } = useTheme();
  const { data } = useApi<WeightTrend>("/weight/trend");

  const [date, setDate] = useState(todayIso());
  const [weight, setWeight] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiPut("/weight", { date, weight_kg: weight });
      setWeight("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = (day: string) => apiDelete(`/weight/${day}`).catch(() => undefined);

  const points = data?.points ?? [];
  const ewma = data?.ewma ?? [];
  const chartData = points.map((p, i) => ({
    label: shortDate(p.date),
    weight: num(p.weight_kg),
    trend: ewma[i] ? num(ewma[i].trend) : null,
  }));
  const recent = [...points].reverse();

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("weight.title")}</h1>
        <p className="muted">{t("weight.subtitle")}</p>
      </header>

      <div className="grid grid--2">
        <Card title={t("weight.logTitle")}>
          <form className="form" onSubmit={submit}>
            <div className="form__row">
              <label className="field">
                <span>{t("weight.date")}</span>
                <input
                  className="input"
                  type="date"
                  value={date}
                  max={todayIso()}
                  onChange={(e) => setDate(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>{t("weight.weight")}</span>
                <input
                  className="input"
                  type="number"
                  step="0.1"
                  min="20"
                  max="400"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  required
                />
              </label>
            </div>
            {error && <div className="error">{error}</div>}
            <button className="btn btn--primary" type="submit" disabled={busy}>
              {busy ? t("common.saving") : t("weight.logBtn")}
            </button>
          </form>

          {data && (data.current_trend || data.effective_weight) && (
            <div className="weight-summary">
              {data.current_trend && (
                <div className="result-row">
                  <span className="muted">{t("weight.trendWeight")}</span>
                  <strong className="tnum">{oneDecimal(data.current_trend)} kg</strong>
                </div>
              )}
              {data.effective_weight && (
                <div className="result-row">
                  <span className="muted">{t("weight.feedsTarget")}</span>
                  <strong className="tnum">{oneDecimal(data.effective_weight)} kg</strong>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card title={t("weight.trendTitle")}>
          {chartData.length >= 1 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke={chart.axis} fontSize={11} tickMargin={6} />
                <YAxis
                  stroke={chart.axis}
                  fontSize={11}
                  domain={[(min: number) => Math.floor(min - 1), (max: number) => Math.ceil(max + 1)]}
                />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="weight"
                  name={t("weight.weighIns")}
                  stroke={chart.weight}
                  dot={{ r: 2 }}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="trend"
                  name={t("weight.trendLine")}
                  stroke={chart.trend}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="muted">{t("weight.empty")}</p>
          )}
        </Card>
      </div>

      <Card title={t("weight.historyTitle")}>
        {recent.length ? (
          <ul className="list weight-list">
            {recent.map((p) => (
              <li key={p.date} className="weight-list__item">
                <span>{shortDate(p.date)}</span>
                <span className="tnum">{oneDecimal(p.weight_kg)} kg</span>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => remove(p.date)}
                  aria-label={t("weight.delete")}
                  title={t("weight.delete")}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{t("weight.empty")}</p>
        )}
      </Card>
    </div>
  );
}
