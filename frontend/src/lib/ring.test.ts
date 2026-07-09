import { describe, expect, it } from "vitest";

import { ringDash } from "./ring";

describe("ringDash", () => {
  const r = 80;
  const circ = 2 * Math.PI * r;

  it("is a full offset at fraction 0 (empty ring)", () => {
    expect(ringDash(r, 0).offset).toBeCloseTo(circ);
  });
  it("is zero offset at fraction 1 (full ring)", () => {
    expect(ringDash(r, 1).offset).toBeCloseTo(0);
  });
  it("is half the circumference at 0.5", () => {
    expect(ringDash(r, 0.5).offset).toBeCloseTo(circ / 2);
  });
  it("clamps fractions above 1 to a full ring", () => {
    expect(ringDash(r, 1.7).offset).toBeCloseTo(0);
  });
  it("clamps negatives and non-finite input to an empty ring", () => {
    expect(ringDash(r, -3).offset).toBeCloseTo(circ);
    expect(ringDash(r, Number.NaN).offset).toBeCloseTo(circ);
  });
});
