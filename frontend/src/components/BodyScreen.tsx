import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiPut } from "../api/client";
import { MEASURE_FIELDS, type MeasureField, type Measurement } from "../api/types";
import { useApi } from "../hooks/useApi";
import { num, oneDecimal, shortDate } from "../lib/format";
import { useTheme } from "../theme";
import { Card } from "./Card";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function BodyScreen() {
  const { t } = useTranslation();
  const { chart } = useTheme();
  const data = useApi<Measurement[]>("/measurements");
  const [form, setForm] = useState<Record<string, string>>({ date: todayIso() });
  const [field, setField] = useState<MeasureField>("waist_cm");
  const [saving, setSaving] = useState(false);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const body: Record<string, unknown> = { date: form.date };
    MEASURE_FIELDS.forEach((f) => {
      if (form[f]) body[f] = form[f];
    });
    if (form.notes) body.notes = form.notes;
    try {
      await apiPut("/measurements", body);
    } finally {
      setSaving(false);
    }
  };

  const series = (data.data ?? []).map((m) => ({
    label: shortDate(m.date),
    value: m[field] != null ? num(m[field]) : null,
  }));
  const recent = [...(data.data ?? [])].reverse();

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("body.title")}</h1>
        <p className="muted">{t("body.subtitle")}</p>
      </header>

      <div className="grid grid--2">
        <Card title={t("body.logTitle")}>
          <form className="form" onSubmit={save}>
            <label className="field">
              <span>{t("weight.date")}</span>
              <input
                className="input"
                type="date"
                max={todayIso()}
                value={form.date}
                onChange={(e) => set("date", e.target.value)}
                required
              />
            </label>
            <div className="form__row">
              {(["waist_cm", "chest_cm"] as MeasureField[]).map((f) => (
                <label className="field" key={f}>
                  <span>{t(`body.fields.${f}`)}</span>
                  <input
                    className="input"
                    type="number"
                    step="0.1"
                    min="0"
                    value={form[f] ?? ""}
                    onChange={(e) => set(f, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <div className="form__row">
              {(["hips_cm", "arm_cm"] as MeasureField[]).map((f) => (
                <label className="field" key={f}>
                  <span>{t(`body.fields.${f}`)}</span>
                  <input
                    className="input"
                    type="number"
                    step="0.1"
                    min="0"
                    value={form[f] ?? ""}
                    onChange={(e) => set(f, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <label className="field">
              <span>{t("body.fields.thigh_cm")}</span>
              <input
                className="input"
                type="number"
                step="0.1"
                min="0"
                value={form.thigh_cm ?? ""}
                onChange={(e) => set("thigh_cm", e.target.value)}
              />
            </label>
            <label className="field">
              <span>{t("body.notes")}</span>
              <input
                className="input"
                value={form.notes ?? ""}
                onChange={(e) => set("notes", e.target.value)}
              />
            </label>
            <button className="btn btn--primary" type="submit" disabled={saving}>
              {saving ? t("common.saving") : t("common.save")}
            </button>
          </form>
        </Card>

        <Card title={t("body.trendTitle")}>
          <select
            className="select"
            value={field}
            onChange={(e) => setField(e.target.value as MeasureField)}
          >
            {MEASURE_FIELDS.map((f) => (
              <option key={f} value={f}>
                {t(`body.fields.${f}`)}
              </option>
            ))}
          </select>
          {series.some((s) => s.value != null) ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke={chart.axis} fontSize={11} />
                <YAxis stroke={chart.axis} fontSize={11} domain={["auto", "auto"]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={chart.trend}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="muted">{t("body.empty")}</p>
          )}
        </Card>
      </div>

      <Card title={t("body.historyTitle")}>
        {recent.length ? (
          <ul className="list">
            {recent.map((m) => (
              <li key={m.date} className="diary-entry">
                <span className="diary-entry__name">{shortDate(m.date)}</span>
                <span className="muted">
                  {MEASURE_FIELDS.filter((f) => m[f] != null)
                    .map((f) => `${t(`body.fields.${f}`)} ${oneDecimal(m[f])}`)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{t("body.empty")}</p>
        )}
      </Card>
    </div>
  );
}
