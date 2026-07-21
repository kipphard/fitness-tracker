import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Trends } from "../api/types";
import { useApi } from "../hooks/useApi";
import { kcal, num, oneDecimal, shortDate } from "../lib/format";
import { useTheme } from "../theme";
import { Card } from "./Card";
import { StatTile } from "./ui";

export function TrendsScreen() {
  const { t } = useTranslation();
  const { chart } = useTheme();
  const trends = useApi<Trends>("/trends");
  const d = trends.data;

  const adherence = (d?.adherence ?? []).map((a) => ({
    label: shortDate(a.date),
    consumed: num(a.consumed),
  }));
  const target = d?.target_kcal ? num(d.target_kcal) : 0;
  const weekly = (d?.weekly_weight ?? []).map((w) => ({
    label: shortDate(w.week_start),
    avg: num(w.average),
  }));
  const change = d?.weekly_change_kg ?? null;

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("trends.title")}</h1>
        <p className="muted">{t("trends.subtitle")}</p>
      </header>

      {d?.rate_warning && <div className="alert alert--warn">{t("trends.rateWarning")}</div>}

      {change != null && (
        <div className="grid grid--2">
          <StatTile
            icon="⚖️"
            value={`${oneDecimal(change)} kg`}
            label={t("trends.weeklyChange")}
          />
        </div>
      )}

      <Card title={t("trends.adherence")}>
        {adherence.some((a) => a.consumed > 0) ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={adherence} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
              <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke={chart.axis} fontSize={10} />
              <YAxis stroke={chart.axis} fontSize={11} />
              <Tooltip />
              {target > 0 && (
                <ReferenceLine
                  y={target}
                  stroke={chart.trend}
                  strokeDasharray="4 4"
                  label={{ value: t("trends.target"), fontSize: 10, fill: chart.axis }}
                />
              )}
              <Bar dataKey="consumed" name={t("today.eaten")} fill={chart.weight} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">{t("trends.noData")}</p>
        )}
        {target > 0 && d?.target_kcal && (
          <p className="muted">{t("trends.targetLine", { target: kcal(d.target_kcal) })}</p>
        )}
      </Card>

      <Card title={t("trends.weightTrend")}>
        {change != null && (
          <div className="result-row">
            <span className="muted">{t("trends.weeklyChange")}</span>
            <strong className="tnum">{oneDecimal(change)} kg</strong>
          </div>
        )}
        {weekly.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={weekly} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke={chart.axis} fontSize={11} />
              <YAxis stroke={chart.axis} fontSize={11} domain={["auto", "auto"]} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="avg"
                name={t("trends.weeklyAvg")}
                stroke={chart.trend}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted">{t("trends.noWeight")}</p>
        )}
      </Card>
    </div>
  );
}
