import { useEffect, useRef, useState } from "react";
import { HashRouter } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthProvider, useAuth } from "./auth";
import { AppShell } from "./components/AppShell";
import { LoginScreen } from "./components/LoginScreen";

function Root() {
  const { user, loading, demoLogin } = useAuth();
  const { t } = useTranslation();
  const [demoStarting, setDemoStarting] = useState(false);
  const triedDemo = useRef(false);

  // `/?demo=1` auto-starts a sandbox (e.g. a "Live demo" link).
  useEffect(() => {
    if (loading || user || triedDemo.current) return;
    if (new URLSearchParams(window.location.search).get("demo") === "1") {
      triedDemo.current = true;
      setDemoStarting(true);
      demoLogin().catch(() => setDemoStarting(false));
    }
  }, [loading, user, demoLogin]);

  if (loading || (demoStarting && !user)) {
    return <div className="auth-screen muted">{t("common.loading")}</div>;
  }
  if (!user) return <LoginScreen />;
  return (
    <HashRouter>
      <AppShell />
    </HashRouter>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Root />
    </AuthProvider>
  );
}
