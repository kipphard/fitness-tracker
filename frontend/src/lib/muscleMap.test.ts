import { describe, expect, it } from "vitest";

import { modelSideFor, toMuscleSlugs } from "./muscleMap";

// Regression cover for GH #17 (muscle-highlight thumbnails).
describe("toMuscleSlugs", () => {
  it("maps free-exercise-db names to library slugs", () => {
    expect(toMuscleSlugs(["chest", "triceps"])).toEqual(["chest", "triceps"]);
    expect(toMuscleSlugs(["lats"])).toEqual(["upper-back"]);
    expect(toMuscleSlugs(["glutes"])).toEqual(["gluteal"]);
    expect(toMuscleSlugs(["shoulders"])).toEqual(["front-deltoids"]);
    expect(toMuscleSlugs(["abdominals"])).toEqual(["abs"]);
    expect(toMuscleSlugs(["lower back"])).toEqual(["lower-back"]);
  });

  it("is case-insensitive and de-dupes (e.g. lats + middle back both → upper-back)", () => {
    expect(toMuscleSlugs(["Lats", "Middle Back"])).toEqual(["upper-back"]);
  });

  it("drops unmapped / empty values", () => {
    expect(toMuscleSlugs(["bogus", "chest"])).toEqual(["chest"]);
    expect(toMuscleSlugs(null)).toEqual([]);
    expect(toMuscleSlugs([])).toEqual([]);
  });
});

describe("modelSideFor", () => {
  it("uses posterior when a primary muscle is on the back", () => {
    expect(modelSideFor(["lats"])).toBe("posterior");
    expect(modelSideFor(["hamstrings"])).toBe("posterior");
    expect(modelSideFor(["triceps"])).toBe("posterior");
  });

  it("uses anterior for front muscles", () => {
    expect(modelSideFor(["chest"])).toBe("anterior");
    expect(modelSideFor(["quadriceps"])).toBe("anterior");
    expect(modelSideFor([])).toBe("anterior");
  });
});
