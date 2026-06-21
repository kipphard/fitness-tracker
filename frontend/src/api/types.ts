// TypeScript mirrors of the backend Pydantic DTOs. Decimals arrive as strings.

export interface UserOut {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export type Gender = "male" | "female";
export type Goal = "cut" | "maintain" | "bulk";
export type ActivityLevel =
  | "sedentary"
  | "lightly_active"
  | "moderately_active"
  | "heavy"
  | "very_heavy";
export type Language = "en" | "de";
export type UnitSystem = "metric" | "imperial";

export const ACTIVITY_LEVELS: ActivityLevel[] = [
  "sedentary",
  "lightly_active",
  "moderately_active",
  "heavy",
  "very_heavy",
];
export const GENDERS: Gender[] = ["male", "female"];
export const GOALS: Goal[] = ["cut", "maintain", "bulk"];

export interface ProfileInput {
  height_cm: string;
  age: number;
  gender: Gender;
  weight_kg: string;
  activity_level: ActivityLevel;
  goal: Goal;
}

export interface Profile extends ProfileInput {
  created_at: string;
}

export interface CalorieResult {
  bmr: string;
  activity_multiplier: string;
  maintenance: string;
  goal_adjustment: string;
  target: string;
  floor: string;
  below_floor: boolean;
}

export type WeightSource = "weekly_average" | "latest_weigh_in" | "profile";

export interface MyCalories extends CalorieResult {
  weight_kg: string;
  weight_source: WeightSource;
}

export interface ActivityLevelInfo {
  key: ActivityLevel;
  multiplier: string;
}

export interface Settings {
  language: Language;
  unit_system: UnitSystem;
}

// --- weight (Phase 2) ---

export interface WeighIn {
  date: string;
  weight_kg: string;
}

export interface TrendPoint {
  date: string;
  trend: string;
}

export interface WeekAverage {
  week_start: string;
  average: string;
  count: number;
}

export interface WeightTrend {
  points: WeighIn[];
  ewma: TrendPoint[];
  weekly: WeekAverage[];
  current_trend: string | null;
  effective_weight: string | null;
  effective_source: WeightSource | null;
}

// --- macros + today (Phase 3) ---

export interface MacroPrefs {
  protein_g_per_kg: string;
  fat_g_per_kg: string;
}

export interface MacroResult {
  protein_g: string;
  fat_g: string;
  carbs_g: string;
  protein_kcal: string;
  fat_kcal: string;
  carbs_kcal: string;
  target_kcal: string;
  reconciled: boolean;
  over_kcal: string;
}

export interface Today {
  date: string;
  calories: MyCalories;
  macros: MacroResult;
}
