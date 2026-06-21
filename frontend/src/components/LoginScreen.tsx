import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function LoginScreen() {
  const { login, register } = useAuth();
  const { t } = useTranslation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const title = mode === "login" ? t("auth.signInTitle") : t("auth.registerTitle");

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-card__top">
          <div className="brand">💪 {t("common.appName")}</div>
          <LanguageSwitcher />
        </div>
        <p className="muted auth-card__tagline">{t("auth.tagline")}</p>
        <h1>{title}</h1>

        <label className="field">
          <span>{t("auth.email")}</span>
          <input
            className="input"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="field">
          <span>{t("auth.password")}</span>
          <input
            className="input"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {mode === "register" && <small className="muted">{t("auth.passwordHint")}</small>}
        </label>

        {error && <div className="error">{error}</div>}

        <button className="btn btn--primary" type="submit" disabled={busy}>
          {mode === "login" ? t("auth.signIn") : t("auth.register")}
        </button>

        <button
          className="btn btn--link"
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
        >
          {mode === "login" ? t("auth.toRegister") : t("auth.toLogin")}
        </button>
      </form>
    </div>
  );
}
