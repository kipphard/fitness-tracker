import { describe, expect, it } from "vitest";

import { distanceToSteps } from "./steps";

// Regression cover for GH #13 (km → steps calculator).
describe("distanceToSteps", () => {
  it("converts walking distance with the default stride (EU 42): 1 km ≈ 1333 steps", () => {
    expect(distanceToSteps(1, 42, "walking")).toBe(1333);
  });

  it("yields fewer steps for faster gaits (longer stride)", () => {
    const walk = distanceToSteps(2, 42, "walking");
    const jog = distanceToSteps(2, 42, "jogging");
    const run = distanceToSteps(2, 42, "running");
    expect(walk).toBeGreaterThan(jog);
    expect(jog).toBeGreaterThan(run);
  });

  it("yields fewer steps for larger feet (longer stride)", () => {
    expect(distanceToSteps(5, 46, "walking")).toBeLessThan(distanceToSteps(5, 38, "walking"));
  });

  it("falls back to a default shoe size when unset", () => {
    expect(distanceToSteps(1, null, "walking")).toBe(distanceToSteps(1, 42, "walking"));
    expect(distanceToSteps(1, undefined, "walking")).toBe(1333);
  });

  it("returns 0 for zero / negative / NaN distance", () => {
    expect(distanceToSteps(0, 42, "walking")).toBe(0);
    expect(distanceToSteps(-3, 42, "walking")).toBe(0);
    expect(distanceToSteps(Number.NaN, 42, "walking")).toBe(0);
  });
});
