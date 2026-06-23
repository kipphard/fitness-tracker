import { useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiPatch, apiPost } from "../api/client";
import type { Settings, ShoppingItem } from "../api/types";
import { useApi } from "../hooks/useApi";
import { currencySymbol, money, num, oneDecimal } from "../lib/format";
import { Card } from "./Card";

// Shopping list (issue #5 §3): generated from a day plan minus the pantry, or added by hand.
// Tick items off while shopping; clear the checked ones (or all) when done.
export function ShoppingScreen() {
  const { t } = useTranslation();
  const list = useApi<ShoppingItem[]>("/shopping");
  const settings = useApi<Settings>("/settings");
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const items = list.data ?? [];
  const remaining = items.filter((i) => !i.checked).length;
  const currency = settings.data?.currency ?? "EUR";
  const total = items.reduce((a, i) => a + num(i.price), 0);
  const budget = num(settings.data?.food_budget_weekly);
  const overBudget = budget > 0 && total > budget;

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    try {
      await apiPost("/shopping", {
        name: name.trim(),
        ...(amount.trim() ? { amount_g: amount.trim() } : {}),
      });
      setName("");
      setAmount("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const toggle = (i: ShoppingItem) =>
    apiPatch(`/shopping/${i.id}`, { checked: !i.checked }).catch(() => undefined);
  const setPrice = (i: ShoppingItem, value: string) =>
    apiPatch(`/shopping/${i.id}`, { price: value === "" ? null : value }).catch(() => undefined);
  const remove = (i: ShoppingItem) => apiDelete(`/shopping/${i.id}`).catch(() => undefined);
  const clear = (checkedOnly: boolean) =>
    apiDelete(`/shopping${checkedOnly ? "?checked=true" : ""}`).catch(() => undefined);

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>🛒 {t("shopping.title")}</h1>
      </header>

      <Card title={t("shopping.addTitle")}>
        <form className="form shopping-add" onSubmit={add}>
          <input
            className="input"
            placeholder={t("shopping.namePlaceholder")}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="input shopping-add__amount"
            type="number"
            min="0"
            placeholder={t("shopping.amountPlaceholder")}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <button className="btn btn--primary" type="submit" disabled={!name.trim()}>
            {t("shopping.add")}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </Card>

      <Card title={t("shopping.listTitle", { remaining, total: items.length })}>
        {items.length === 0 ? (
          <p className="muted">{t("shopping.empty")}</p>
        ) : (
          <>
            <ul className="list shopping-list">
              {items.map((i) => (
                <li key={i.id} className={"shopping-item" + (i.checked ? " is-checked" : "")}>
                  <label className="shopping-item__main">
                    <input type="checkbox" checked={i.checked} onChange={() => toggle(i)} />
                    <span className="shopping-item__name">{i.name}</span>
                    {i.amount_g && (
                      <span className="muted tnum">{oneDecimal(i.amount_g)} g</span>
                    )}
                  </label>
                  <input
                    className="input shopping-item__price"
                    type="number"
                    min="0"
                    step="0.01"
                    defaultValue={i.price ?? ""}
                    placeholder={currencySymbol(currency)}
                    onBlur={(e) => {
                      if ((i.price ?? "") !== e.target.value) setPrice(i, e.target.value);
                    }}
                  />
                  <button
                    className="icon-btn"
                    onClick={() => remove(i)}
                    aria-label={t("shopping.remove")}
                    title={t("shopping.remove")}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
            <div className={"result-row result-row--target" + (overBudget ? " is-over" : "")}>
              <span>
                {t("shopping.total")}
                {budget > 0 && ` · ${t("shopping.budget")} ${money(budget, currency)}`}
              </span>
              <strong className="tnum">{money(total, currency)}</strong>
            </div>
            <div className="diary-actions">
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => clear(true)}
                disabled={items.every((i) => !i.checked)}
              >
                {t("shopping.clearChecked")}
              </button>
              <button className="btn btn--ghost btn--sm" onClick={() => clear(false)}>
                {t("shopping.clearAll")}
              </button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
