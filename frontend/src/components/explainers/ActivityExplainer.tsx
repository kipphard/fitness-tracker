import { useTranslation } from "react-i18next";

import { ACTIVITY_LEVELS, type ActivityLevelInfo } from "../../api/types";
import { useApi } from "../../hooks/useApi";
import { oneDecimal } from "../../lib/format";
import { Card } from "../Card";

export function ActivityExplainer() {
  const { t } = useTranslation();
  const { data } = useApi<ActivityLevelInfo[]>("/calories/activity-levels");
  const multiplier = (key: string) => data?.find((l) => l.key === key)?.multiplier;

  return (
    <div className="screen screen--prose">
      <header className="screen__head">
        <h1>{t("explainers.activity.title")}</h1>
      </header>
      <Card>
        <p>{t("explainers.activity.intro")}</p>
        <ul className="level-list">
          {ACTIVITY_LEVELS.map((key) => {
            const mult = multiplier(key);
            return (
              <li key={key} className="level-list__item">
                <div className="level-list__head">
                  <strong>{t(`calories.levels.${key}.label`)}</strong>
                  {mult && (
                    <span className="badge">
                      {t("explainers.activity.factor")} ×{oneDecimal(mult)}
                    </span>
                  )}
                </div>
                <p className="muted">{t(`calories.levels.${key}.desc`)}</p>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
