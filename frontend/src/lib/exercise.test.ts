import { describe, expect, it } from "vitest";

import { endFrameImageUrl, exerciseImageUrl } from "./exercise";

describe("exercise image urls", () => {
  it("prefixes the CDN base for the start frame", () => {
    expect(exerciseImageUrl({ image_url: "Squat/0.jpg" })).toContain("/exercises/Squat/0.jpg");
  });

  it("returns null when there is no image", () => {
    expect(exerciseImageUrl({ image_url: null })).toBeNull();
  });

  it("derives the end frame from the start frame (#17 movement)", () => {
    expect(endFrameImageUrl({ image_url: "Squat/0.jpg" })).toContain("/exercises/Squat/1.jpg");
  });

  it("has no end frame when the start isn't /0.jpg or is missing", () => {
    expect(endFrameImageUrl({ image_url: "Squat/2.jpg" })).toBeNull();
    expect(endFrameImageUrl({ image_url: null })).toBeNull();
  });
});
