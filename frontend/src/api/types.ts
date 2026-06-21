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

export interface ActivityLevelInfo {
  key: ActivityLevel;
  multiplier: string;
}

export interface Settings {
  language: Language;
  unit_system: UnitSystem;
}
