import { useTranslation } from "react-i18next";

import { Card } from "../Card";

export function FormulaExplainer() {
  const { t } = useTranslation();
  return (
    <div className="screen screen--prose">
      <header className="screen__head">
        <h1>{t("explainers.formula.title")}</h1>
      </header>
      <Card>
        <p>{t("explainers.formula.intro")}</p>
        <div className="formula">
          <code>{t("explainers.formula.male")}</code>
          <code>{t("explainers.formula.female")}</code>
        </div>

        <h3>{t("explainers.formula.termsTitle")}</h3>
        <ul className="prose-list">
          <li>{t("explainers.formula.terms.weight")}</li>
          <li>{t("explainers.formula.terms.height")}</li>
          <li>{t("explainers.formula.terms.age")}</li>
          <li>{t("explainers.formula.terms.constant")}</li>
        </ul>

        <h3>{t("explainers.formula.tdeeTitle")}</h3>
        <p>{t("explainers.formula.tdee")}</p>

        <h3>{t("explainers.formula.goalTitle")}</h3>
        <p>{t("explainers.formula.goal")}</p>

        <h3>{t("explainers.formula.excludeTitle")}</h3>
        <p>{t("explainers.formula.exclude")}</p>
      </Card>
    </div>
  );
}
