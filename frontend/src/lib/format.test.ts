import { describe, expect, it } from "vitest";

import { datetimeLocalToIso, isoToDatetimeLocal, parseDecimalInput } from "./format";

// Regression cover for GH #12: kg fields must accept the German decimal comma and
// normalize it to a dot-decimal string the API can parse.
describe("parseDecimalInput", () => {
  it("normalizes a German decimal comma to a dot (#12)", () => {
    expect(parseDecimalInput("32,75")).toBe("32.75");
  });

  it("passes a dot decimal through unchanged", () => {
    expect(parseDecimalInput("32.75")).toBe("32.75");
  });

  it("accepts plain integers", () => {
    expect(parseDecimalInput("40")).toBe("40");
  });

  it("trims surrounding whitespace", () => {
    expect(parseDecimalInput("  12,5  ")).toBe("12.5");
  });

  it("keeps a trailing separator while still typing", () => {
    expect(parseDecimalInput("30,")).toBe("30.");
    expect(Number(parseDecimalInput("30,"))).toBe(30);
  });

  it("returns empty string for blank input", () => {
    expect(parseDecimalInput("")).toBe("");
    expect(parseDecimalInput("   ")).toBe("");
  });

  it("returns empty string for non-numeric input", () => {
    expect(parseDecimalInput("abc")).toBe("");
    expect(parseDecimalInput("1,2,3")).toBe("");
  });
});

describe("datetime-local converters", () => {
  it("round-trips an ISO timestamp through the local input format", () => {
    const iso = "2026-07-01T15:30:00.000Z";
    const local = isoToDatetimeLocal(iso); // local wall-clock, tz-dependent
    expect(local).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    // Converting back yields the same instant (to the minute).
    expect(datetimeLocalToIso(local).slice(0, 16)).toBe(iso.slice(0, 16));
  });

  it("returns empty string for blank/invalid input", () => {
    expect(isoToDatetimeLocal(null)).toBe("");
    expect(isoToDatetimeLocal("not-a-date")).toBe("");
    expect(datetimeLocalToIso("")).toBe("");
  });
});
