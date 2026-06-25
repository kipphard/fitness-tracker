import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LiveSession } from "./LiveSession";

// Mocked API client (vi.hoisted so the spies exist before vi.mock's hoisted factory runs).
const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));
vi.mock("../api/client", () => ({ apiGet, apiPost, apiPatch, apiDelete }));

// Translate to the key itself, so queries are stable and locale-independent.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "en" } }),
}));

// The thumbnail loads a CDN image we don't care about here.
vi.mock("./ExerciseThumb", () => ({ ExerciseThumb: () => null }));

beforeEach(() => {
  apiPost.mockResolvedValue({});
  apiPatch.mockResolvedValue({});
  apiDelete.mockResolvedValue({});
  apiGet.mockImplementation((path: string) => {
    if (path.startsWith("/workouts/")) {
      return Promise.resolve({ id: "sess1", started_at: "2020-01-01T00:00:00Z", sets: [] });
    }
    if (path === "/exercises") return Promise.resolve([]);
    if (path.includes("/last")) return Promise.resolve([]);
    return Promise.resolve(null);
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LiveSession set logging (#12 regression)", () => {
  it("accepts a German decimal comma in kg and logs the normalized dot value", async () => {
    const user = userEvent.setup();
    render(
      <LiveSession sessionId="sess1" initialExercises={[{ id: "ex1", name: "Bench Press" }]} onFinish={() => {}} />,
    );

    const weight = await screen.findByPlaceholderText("workouts.weight");
    const reps = screen.getByPlaceholderText("workouts.reps");

    await user.type(weight, "32,75");
    await user.type(reps, "10");

    // Symptom 1: the comma is actually accepted in the field (would be rejected by type="number").
    expect(weight).toHaveValue("32,75");

    // Mark the set done.
    await user.click(screen.getByLabelText("workouts.markDone"));

    // The logged set is posted with the comma normalized to a dot — safe for the Decimal API.
    expect(apiPost).toHaveBeenCalledWith("/workouts/sess1/sets", {
      exercise_id: "ex1",
      weight: "32.75",
      reps: 10,
    });
  });
});
