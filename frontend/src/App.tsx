import { HashRouter } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthProvider, useAuth } from "./auth";
import { AppShell } from "./components/AppShell";
import { LoginScreen } from "./components/LoginScreen";

function Root() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading) return <div className="auth-screen muted">{t("common.loading")}</div>;
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
