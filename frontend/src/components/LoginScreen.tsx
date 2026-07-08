import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function LoginScreen() {
  const { login, register, demoLogin } = useAuth();
  const { t } = useTranslation();
  const [mode, setMode] = useState<"signIn" | "register">("signIn");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);

  const isRegister = mode === "register";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (isRegister ? register(email, password) : login(email, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleMode = () => {
    setMode(isRegister ? "signIn" : "register");
    setError(null);
  };

  const startDemo = async () => {
    setDemoBusy(true);
    setError(null);
    try {
      await demoLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setDemoBusy(false);
    }
  };

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-card__top">
          <div className="brand">💪 {t("common.appName")}</div>
          <LanguageSwitcher />
        </div>
        <p className="muted auth-card__tagline">{t("auth.tagline")}</p>
        <h1>{t(isRegister ? "auth.registerTitle" : "auth.signInTitle")}</h1>

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
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {isRegister && <small className="muted">{t("auth.passwordHint")}</small>}
        </label>

        {error && <div className="error">{error}</div>}

        <button className="btn btn--primary" type="submit" disabled={busy || demoBusy}>
          {busy ? t("common.loading") : t(isRegister ? "auth.register" : "auth.signIn")}
        </button>

        <button className="btn btn--link btn--sm" type="button" onClick={toggleMode} disabled={busy || demoBusy}>
          {t(isRegister ? "auth.toLogin" : "auth.toRegister")}
        </button>

        <div className="auth-divider"><span>{t("demo.or")}</span></div>

        <button
          className="btn btn--ghost"
          type="button"
          onClick={startDemo}
          disabled={busy || demoBusy}
        >
          {demoBusy ? t("demo.starting") : `🎬 ${t("demo.tryDemo")}`}
        </button>
        <small className="muted auth-card__demo-hint">{t("demo.tryHint")}</small>
      </form>
    </div>
  );
}
