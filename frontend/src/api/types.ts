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
  eat_back_activity: boolean;
}

export interface Steps {
  date: string;
  steps: number;
  kcal: string;
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

export interface Consumed {
  kcal: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

export interface Today {
  date: string;
  calories: MyCalories;
  macros: MacroResult;
  consumed: Consumed;
  remaining_kcal: string;
  steps: number;
  activity_kcal: string;
  workout_kcal: string;
  net_deficit_kcal: string;
  eat_back_activity: boolean;
}

// --- food + diary (Phase 4) ---

export type MealSlot = "breakfast" | "lunch" | "dinner" | "snack";
export const MEAL_SLOTS: MealSlot[] = ["breakfast", "lunch", "dinner", "snack"];

export interface Food {
  id: string;
  source: "off" | "custom";
  barcode: string | null;
  name: string;
  per100_kcal: string;
  per100_protein_g: string;
  per100_fat_g: string;
  per100_carbs_g: string;
  serving_g: string | null;
}

// A transient OFF search result (no id yet).
export type FoodData = Omit<Food, "id" | "source">;

export interface DiaryEntry {
  id: string;
  date: string;
  slot: MealSlot;
  food_id: string | null;
  food_name: string;
  amount_g: string;
  kcal: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

export interface DiaryDay {
  date: string;
  entries: DiaryEntry[];
  totals: Consumed;
}

// --- photo estimation (Phase 5) ---

export interface EstimateItem {
  name: string;
  amount_g: string;
  kcal: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

export interface PhotoEstimate {
  items: EstimateItem[];
  total: Consumed;
  confidence: "low" | "medium" | "high";
  questions: string[];
  notes: string;
}

// --- workouts (Phase 7) ---

export type SetType = "warmup" | "working";

export interface Exercise {
  id: string;
  source: "lib" | "custom";
  name: string;
  name_de: string | null;
  primary_muscles: string[] | null;
  secondary_muscles: string[] | null;
  equipment: string | null;
  category: string | null;
  instructions: string | null;
  image_url: string | null;
}

export interface RoutineExerciseRef {
  exercise_id: string;
  exercise_name: string;
  position: number;
  planned_sets: number;
  planned_reps: number | null;
}

export interface Routine {
  id: string;
  name: string;
  exercises: RoutineExerciseRef[];
}

export interface WorkoutSet {
  id: string;
  exercise_id: string | null;
  exercise_name: string;
  set_index: number;
  weight: string;
  reps: number;
  set_type: SetType;
  rpe: string | null;
}

export interface WorkoutSession {
  id: string;
  routine_id: string | null;
  routine_name: string | null;
  started_at: string;
  ended_at: string | null;
  sets: WorkoutSet[];
}

export interface WorkoutSummary {
  id: string;
  routine_name: string | null;
  started_at: string;
  ended_at: string | null;
  set_count: number;
  total_volume: string;
}

export interface ProgressionPoint {
  date: string;
  top_weight: string;
  volume: string;
  est_1rm: string;
}

export interface PRs {
  best_weight: string;
  best_est_1rm: string;
}

export interface Progression {
  exercise_id: string;
  exercise_name: string;
  points: ProgressionPoint[];
  prs: PRs | null;
}

// --- body measurements + trends (Phase 8) ---

export interface Measurement {
  date: string;
  waist_cm: string | null;
  chest_cm: string | null;
  hips_cm: string | null;
  arm_cm: string | null;
  thigh_cm: string | null;
  notes: string | null;
}

export type MeasureField = "waist_cm" | "chest_cm" | "hips_cm" | "arm_cm" | "thigh_cm";
export const MEASURE_FIELDS: MeasureField[] = [
  "waist_cm",
  "chest_cm",
  "hips_cm",
  "arm_cm",
  "thigh_cm",
];

export interface AdherenceDay {
  date: string;
  consumed: string;
  target: string;
}

export interface WeeklyWeight {
  week_start: string;
  average: string;
}

export interface Trends {
  target_kcal: string | null;
  adherence: AdherenceDay[];
  weekly_weight: WeeklyWeight[];
  weekly_change_kg: string | null;
  rate_warning: boolean;
}
