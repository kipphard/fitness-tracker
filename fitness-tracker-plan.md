# Fitness & Nutrition Tracker — Project Plan & Architecture

A self-hosted web app covering the full fitness journey: calorie needs (Kalorienbedarf),
adaptive weight tracking, food/calorie logging (barcode + custom + photo AI), step→calorie
tracking, and a workout tracker with progression. English first with a language selector
(EN/DE), German food data. Single-user first, multi-user later.

> **Not medical or nutrition advice.** This is an engineering plan. The app should include
> sensible guardrails (calorie floors, warnings on extreme deficits) — see §13.

---

## 0. Decisions locked in

- **Form factor:** React **PWA** web app (camera access for barcode + food photos, installable
  on your phone). Single-user first, user model built in from day one for later multi-user.
- **Calorie model:** **Mifflin-St Jeor BMR × occupational activity factor** as the base
  Kalorienbedarf (job/lifestyle only, *excluding* variable exercise/steps — exactly your design).
  Steps and workouts are added **on top, per day**. See §4.
- **Self-correcting target:** weekly average weight feeds back into the calculation **and**
  the app learns your *actual* maintenance from intake vs weight change over time
  (adaptive TDEE) — this is the upgrade your weekly-average instinct is pointing at. See §5.
- **Food data:** **Open Food Facts** (free, no API key, German product names, barcode
  lookup; full data dumps available to self-host). See §6.
- **Exercise data:** **free-exercise-db** (public domain, 800+ exercises with images, plain
  JSON — load it into your DB). See §10.
- **Photo calorie estimation:** backend calls a vision LLM (Claude) with structured output +
  clarifying questions. See §7.
- **Stack:** Python + FastAPI backend, Postgres, React (Vite) PWA — consistent with your
  other two projects.

---

## 1. Feature overview (everything for a full fitness journey)

You listed five; I'm adding the ones a complete journey needs (marked **+added**):

1. **Kalorienbedarf calculator** — profile → maintenance, with in-app explanations.
2. **Weight tracking** — daily weigh-in, weekly average, auto-feeds the calorie target.
3. **+Goal setting** — cut / maintain / bulk + rate. *Needed to turn "maintenance" into a
   daily target; without it the calorie number has no direction.*
4. **Macro targets** — protein/fat/carbs that sum to the calorie target, with auto-suggest.
5. **Food/calorie tracker** — barcode scan, search, custom foods, **+meals/recipes**,
   **+favorites/recent/copy-yesterday** (logging friction is what kills these apps).
6. **Photo estimation** — photograph a meal, AI estimates calories/macros, asks questions.
7. **Step tracking → calories** — added on top of the day for total deficit (honest webapp
   constraints in §8).
8. **Workout tracker** — routines, exercises, sets/weight/reps, live session with last-time
   performance, **+rest timer, +progression/PRs**.
9. **+Trends & history** — weight trend, calorie/macro adherence, strength progression.
10. **+Body measurements & progress photos** — for recomposition the scale alone lies.
11. **i18n (EN/DE)** + German food data.
12. **+Safety guardrails** — calorie floors, extreme-deficit warnings.

---

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | **Python 3.12 + FastAPI** | matches your other projects |
| Storage | **PostgreSQL** | profile, logs, foods, exercises, sessions |
| Frontend | **React + Vite, PWA** | installable, camera access, offline-friendly |
| i18n | **i18next / react-i18next** | EN/DE selector; UI strings only (food names come from data) |
| Barcode scan | **@zxing/browser** (or html5-qrcode) | in-browser camera barcode reading |
| Food data | **Open Food Facts** API + optional self-hosted dump | free, German names via `lc=de` |
| Exercise data | **free-exercise-db** JSON | public domain, vendor into Postgres |
| Photo AI | **Anthropic API (Claude vision)** | structured macro estimate + follow-up questions |
| Charts | Recharts | weight trend, macros, volume |
| Orchestration | Docker Compose | api + db + frontend |

---

## 3. Architecture

```
   Camera (barcode / photo) ─┐
                             ▼
   ┌──────────────────────────────────────────────────────────┐
   │                  Backend (FastAPI)                         │
   │                                                            │
   │  Profile/Goals ─► Calorie Engine ◄── Weight Tracker        │
   │       │              │   ▲              (daily + weekly avg │
   │       │              │   │               + adaptive TDEE)   │
   │       │              ▼   │                                  │
   │       │         Daily Target ──► Daily Dashboard            │
   │       │          (kcal + macros)      ▲                     │
   │       │                               │                     │
   │  Food Service ─► Food Log ────────────┤                     │
   │   (OFF barcode/search,                │                     │
   │    custom, meals, photo-AI)           │                     │
   │                                       │                     │
   │  Step Service ─► activity kcal ───────┘                     │
   │                                                            │
   │  Workout Service ─► routines, sessions, set logs, PRs      │
   │                                                            │
   │  Persistence (Postgres)   |   i18n   |   Auth (later)      │
   └──────────────────────────────────────────────────────────┘
                             ▼
                     React PWA dashboard
```

---

## 4. Calorie engine (the math, with explanations for the in-app info screens)

### 4.1 BMR (Grundumsatz) — Mifflin-St Jeor (current standard)
- Men:   `BMR = 10·weight(kg) + 6.25·height(cm) − 5·age + 5`
- Women: `BMR = 10·weight(kg) + 6.25·height(cm) − 5·age − 161`
- (Offer a "diverse/other" option that lets the user pick which formula variant to use.)

### 4.2 Base maintenance = BMR × occupational activity factor
Activity factor reflects **job/lifestyle only**, *not* deliberate exercise or steps (those
get added per day). Dropdown options with typical factors (label them as estimates):

| Activity level (DE / EN) | Factor |
|---|---|
| Überwiegend sitzend, Bürojob / Desk job, mostly sitting | ~1.2–1.3 |
| Sitzend + etwas Bewegung / Sitting + some walking | ~1.4 |
| Überwiegend stehend/gehend / Mostly standing or walking | ~1.5–1.6 |
| Körperlich belastender Job (z.B. Bauarbeiter) / Heavy physical labor | ~1.7–2.0 |

`base_maintenance = BMR × factor`. This is the "Kalorienbedarf" you described.

### 4.3 Daily activity added on top (variable)
- **Steps → kcal:** `kcal ≈ steps × 0.0005 × weight(kg)` (e.g. 10k steps @ 95 kg ≈ ~475 kcal).
  Treat as an estimate — the adaptive TDEE in §5 corrects systematic error.
- **Workout → kcal:** MET estimate `kcal = MET × weight(kg) × hours` (strength ≈ 3–6 MET),
  derived from the logged session, or a manual entry.

### 4.4 Daily target (the eating budget)
```
daily_target = base_maintenance − goal_adjustment
net_deficit_today = (base_maintenance + activity_kcal) − calories_consumed
```
- `goal_adjustment`: e.g. −300 to −500 for fat loss, 0 for maintenance, + for bulk
  (derived from the goal + chosen rate in §3/feature list).
- **Toggle: "eat back activity calories?"** Some people add steps/workout kcal to the eating
  budget; others don't. Default off; show both "calories left" and "net deficit" regardless,
  since you specifically want to see the **total daily deficit**.

### 4.5 In-app explainer
A short info screen per concept (BMR formula, why exercise is excluded from the base,
what each activity level means, how the deficit works). You explicitly want this.

---

## 5. Weight tracking + self-correcting target

### 5.1 Weekly average feedback (your spec)
- Log weight daily. Compute each completed week's **7-day average**.
- This week's calorie calc uses **last completed week's average weight** as the weight input.
  (Last week avg 95 → this week's BMR uses 95.)
- Show a **trend weight** line (exponentially weighted moving average) so daily noise/water
  fluctuations don't mislead you day to day.

### 5.2 Adaptive TDEE (the upgrade — strongly recommended)
After 2–3 weeks of intake + weight data, *measure* your real maintenance instead of trusting
the formula:
```
measured_TDEE ≈ mean_daily_intake − (Δ trend_weight_kg × 7700 kcal/kg) / days
```
(Lost weight on X kcal/day → your true maintenance was above X.) Blend the formula estimate
with the measured value once enough data exists, and recompute weekly. This is what makes the
whole thing self-correcting and is ideal for your body-recomposition goal — the scale + the
food log together reveal the truth the formula only approximates.

---

## 6. Food / calorie tracker

### 6.1 Data sources & lookup
- **Barcode → Open Food Facts:** `GET /api/v2/product/{barcode}?lc=de` returns name (German
  where available), per-100g nutrition, serving size. **No API key needed.**
- **Constraints to design around:** OFF read API is rate-limited (~15 req/min/IP) and is
  community data (coverage/accuracy varies). So: **cache every looked-up product locally**,
  and for heavy/offline German coverage, optionally **import the nightly OFF data dump** into
  your own Postgres and query that first, hitting the live API only on a miss.
- **Search** (by name) and **manual "create your own food"** (per-100g or per-serving macros)
  saved to your personal food DB.

### 6.2 Logging UX (make it frictionless)
- **Favorites, recent foods, "copy yesterday," and saved meals/recipes** — combine foods into
  a reusable meal/recipe with computed per-serving macros.
- Portion scaling: store per-100g, log by grams / ml / pieces / servings.
- Meal slots: breakfast/lunch/dinner/snack (optional but expected).

### 6.3 The day view
Shows: calories consumed, **calories left**, macro rings (protein/fat/carbs vs target),
activity kcal earned, and **net deficit** for the day.

### 6.4 Macro targets
- Set protein/fat/carbs that must reconcile to the calorie target:
  `protein_g·4 + carbs_g·4 + fat_g·9 = daily_target`.
- Auto-suggest: **protein ~1.6–2.2 g/kg** bodyweight (higher end while cutting + lifting to
  preserve muscle), **fat ≥ ~0.6–0.8 g/kg**, carbs fill the remainder. Let the user override
  any two and compute the third; warn if they don't reconcile.

---

## 7. Photo-based estimation (AI)

- User photographs a meal → backend sends the image to **Claude (vision)** with a structured
  prompt: "estimate calories + protein/fat/carbs; if uncertain, return clarifying questions."
- Return **structured JSON** (items, per-item estimate, total, confidence) + optional
  questions ("Is that ~150 g chicken? Was it fried or grilled? Any oil?").
- User answers → re-estimate → user confirms → logged like any other entry (and can tweak).
- **Be honest in the UI:** photo estimation is approximate; it's a fast-entry aid, not a scale.
  Encourage barcode/weighed entry for staples and photos for restaurant/unpackaged meals.

---

## 8. Steps → calories (honest constraint)

A plain web app **cannot silently read your phone's step counter** the way a native app can.
Realistic options, in order:
1. **Manual entry** (v1) — type today's steps; convert with §4.3.
2. **Import** — Apple Health / Google Fit / **Health Connect** exports, or a periodic sync if
   you later add a thin native/PWA companion. Health Connect (Android) and Apple HealthKit
   (iOS) require native code or a wrapper, not browser JS.
3. **Future:** a small companion app or wearable integration to push steps to your API.
Plan for manual now, design a `steps` ingestion endpoint so any source can feed it later.

---

## 9. Workout tracker

### 9.1 Building blocks
- **Exercise library** (from free-exercise-db: name, primary/secondary muscles, equipment,
  category, instructions, images) + **custom exercises** you add.
- **Routines/templates** — build a workout, add exercises, set planned Sätze/reps. Supports
  your 6-day Push/Pull/Legs split as reusable templates.

### 9.2 Live session (the part you described)
- Start a workout → app shows the **current/next exercise**, displays **last time's sets
  (weight × reps)** for that exercise, you enter **this week's weight/reps per set**.
- **+Rest timer** between sets, set types (warmup/working), optional RPE.

### 9.3 Progression (so the data means something)
- Per-exercise charts: top set, total **volume** (Σ weight×reps), estimated **1RM** (Epley:
  `1RM = weight × (1 + reps/30)`), and **PR detection** (new best weight/volume/est-1RM).
- This closes the loop on "see progression and stuff."

---

## 10. Exercise data details

- **free-exercise-db** (`yuhonas/free-exercise-db`): public domain, ~800+ exercises, JSON
  with `force/level/mechanic/equipment/primaryMuscles/secondaryMuscles/instructions/
  category/images`. Vendor the JSON into Postgres on first boot; images can be referenced
  from the repo's raw URLs or mirrored locally.
- **Alternative if you want more (gifs/videos):** ExerciseDB (11k+ exercises) — richer but
  heavier and its hosted endpoints aren't meant for production; you'd self-host its dataset.
- Recommendation: start with free-exercise-db; it's the cleanest self-contained option.

---

## 11. Data model (Postgres, sketch)

- `users(id, email, ...)` — present from day one even while single-user
- `profile(user_id, height_cm, age, gender, activity_factor, goal, goal_rate, eat_back_activity)`
- `weigh_ins(user_id, date, weight_kg)` → derive weekly avg + EWMA trend
- `daily_targets(user_id, date, base_maintenance, target_kcal, protein_g, fat_g, carbs_g)`
- `foods(id, source[off|custom], barcode, name, per100_kcal, per100_protein, per100_fat, per100_carbs, serving_g, owner_user_id)`
- `meals(id, user_id, name)` + `meal_items(meal_id, food_id, amount_g)`
- `food_log(id, user_id, date, slot, food_id|meal_id, amount_g, kcal, protein, fat, carbs, source[barcode|search|custom|photo])`
- `steps(user_id, date, steps, kcal)`
- `exercises(id, source[lib|custom], name, primary_muscles, secondary_muscles, equipment, category, instructions, images)`
- `routines(id, user_id, name)` + `routine_exercises(routine_id, exercise_id, order, planned_sets)`
- `workout_sessions(id, user_id, routine_id, started_at, ended_at)`
- `set_logs(id, session_id, exercise_id, set_index, weight, reps, type, rpe)`
- `body_measurements(user_id, date, chest, waist, arm, ...)` + `progress_photos(...)`
- `settings(user_id, language, units)`

---

## 12. Dashboard / screens

- **Today:** calories left, consumed, macro rings, activity kcal, net deficit, quick-add.
- **Diary:** food log by day/slot with inline edit; copy-yesterday.
- **Weight:** daily entry, weekly average, trend line, adaptive-TDEE readout.
- **Workouts:** routine list, live session screen, exercise progression charts, PRs.
- **Trends:** weight trend, calorie/macro adherence, training volume/strength over time.
- **Body:** measurements + progress photos.
- **Settings:** language (EN/DE), units, goal, activity level, info/explainer screens.

---

## 13. Safety guardrails (build these in)

- **Calorie floor:** warn if the target drops below a sensible minimum (e.g. below BMR, or
  below common floors ~1500 kcal men / ~1200 kcal women) and don't silently set extreme targets.
- **Rate-of-change warning:** flag very aggressive deficits or rapid weekly weight loss.
- Keep guidance neutral and supportive; the app is a tool, not a coach pushing extremes.

---

## 14. Phased roadmap

- **Phase 0 — Scaffold.** FastAPI + Postgres + React PWA + Docker Compose, user model,
  i18n (EN/DE) wiring, settings, units.
- **Phase 1 — Calorie engine.** Profile, Mifflin-St Jeor, activity dropdown, goals, explainer
  screens → base maintenance + daily target.
- **Phase 2 — Weight.** Daily weigh-in, weekly average, EWMA trend, feed last week's avg into
  the target; then adaptive TDEE once data exists.
- **Phase 3 — Macros + Today view.** Macro auto-suggest/validation, daily dashboard.
- **Phase 4 — Food tracking.** Open Food Facts barcode + search + caching, custom foods,
  meals/recipes, favorites/recent/copy-day.
- **Phase 5 — Photo AI.** Claude vision estimate + clarifying questions + confirm/edit.
- **Phase 6 — Steps.** Manual entry + ingestion endpoint, step→kcal, net deficit.
- **Phase 7 — Workouts.** Import free-exercise-db, routines, live session with last-time
  performance + rest timer, progression charts + PRs.
- **Phase 8 — Trends, body metrics, guardrails polish.**
- **Phase 9 — Later (going native & sharing).** Hosted backend, multi-user (auth, per-user
  isolation), Capacitor wrapper + Health Connect/HealthKit step sync, private distribution
  (APK / TestFlight). See §17.

---

## 15. Suggested repo structure

```
fitness-tracker/
├── docker-compose.yml
├── backend/
│   ├── calories/      # BMR, activity factors, target, adaptive TDEE
│   ├── weight/        # weigh-ins, weekly avg, EWMA trend
│   ├── food/          # OFF client + cache, custom foods, meals, photo-AI
│   ├── steps/         # ingestion + kcal conversion
│   ├── workouts/      # library import, routines, sessions, progression
│   ├── persistence/   # db models, repositories
│   └── api/           # FastAPI routes
├── frontend/          # React + Vite PWA, i18next (en/de)
├── data/              # free-exercise-db import, optional OFF dump import
├── config/
└── tests/
```

---

## 16. First task for Claude Code

> Set up Phase 0 + Phase 1 in `fitness-tracker/`: Python 3.12 + FastAPI, Postgres, Docker
> Compose, a React + Vite PWA with react-i18next configured for English and German and a
> language switcher, a `users`/`profile`/`settings` schema (SQLAlchemy), and a Calorie Engine
> that takes height, age, gender, weight, and an occupational activity factor (dropdown:
> desk job → heavy labor) and returns base maintenance via Mifflin-St Jeor, plus a goal
> adjustment for cut/maintain/bulk. Add the in-app explainer screens for the formula and the
> activity levels. Include pytest for the calorie math. Don't build food/workout tracking yet.

Then proceed phase by phase. Keep the food layer behind a service interface so Open Food Facts
can be swapped/augmented with a self-hosted dump, and keep `steps` as an ingestion endpoint so
any source can feed it later.

---

## 17. Going native, step tracking & private sharing (no app store)

You can turn this into an installable app, read device step data, and share it with friends —
all **without publishing to the App Store / Play Store**.

### Wrapping & device access
- Wrap the React app with **Capacitor** (keeps your web codebase; native shell + webview).
  Add plugins: Camera (barcode/photo — already works in the PWA), **Health Connect** (Android
  steps), **HealthKit** (iOS steps).
- Include **both** health plugins so one cross-platform build runs on your Android *and*
  friends' iPhones; at runtime it uses whichever platform it's on.
- Android steps → **Health Connect** (Google Fit is end-of-life by end of 2026; don't build on
  it). iOS steps → **HealthKit** (no Android-style shortcut; it's a separate native integration).

### Sharing privately (no store listing)
- **Android friends:** build the signed APK and send it; they enable "install unknown apps."
  No account, no review. (Firebase App Distribution is a nicer optional delivery channel.)
- **iPhone friends:** use **TestFlight**. Needs a paid Apple Developer account (~$99/yr).
  External testers (up to ~10,000) just install the TestFlight app and tap your invite link.
  External builds get a *light* beta review (not full App Store review) and expire after ~90
  days, so you re-push a build periodically. Up to 100 internal testers skip beta review.
  No public store listing required — you can stay off the stores indefinitely.

### What "sharing" pulls forward (independent of any store release)
- **Deploy the backend:** friends can't reach `localhost`. Host FastAPI + Postgres on a small
  VPS / container host with HTTPS.
- **Turn on multi-user:** the `users` model is in from Phase 0 — enable auth + strict per-user
  data isolation *before* inviting anyone.
- **Health-data privacy:** weight, body metrics, and step/health data are sensitive personal
  data (special category under GDPR). Even among friends: get consent, encrypt at rest, support
  deletion. Lightweight, but don't be cavalier.

### Sequencing
Nothing changes for your personal use: build the PWA, wrap with Capacitor, add Health Connect,
run it on your Android. Sharing is a later, separate milestone (hosted backend + multi-user +
an iOS build via TestFlight) and does **not** require a public store release.
