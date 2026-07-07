import { afterEach, describe, expect, it } from "vitest";
import { lock, unlock } from "./scrollLock";

afterEach(() => {
  document.body.style.overflow = "";
});

describe("scrollLock", () => {
  it("locks on the first lock and restores the original overflow on the last unlock", () => {
    document.body.style.overflow = "auto";
    lock();
    expect(document.body.style.overflow).toBe("hidden");
    unlock();
    expect(document.body.style.overflow).toBe("auto");
  });

  it("stays locked while stacked and restores only after the last unlock", () => {
    document.body.style.overflow = "";
    lock(); // outer modal
    lock(); // inner modal on top
    expect(document.body.style.overflow).toBe("hidden");
    unlock(); // inner closes — still locked by the outer
    expect(document.body.style.overflow).toBe("hidden");
    unlock(); // outer closes — now released
    expect(document.body.style.overflow).toBe("");
  });

  it("ignores extra unlocks (never leaves the count negative)", () => {
    unlock();
    unlock();
    document.body.style.overflow = "scroll";
    lock();
    expect(document.body.style.overflow).toBe("hidden");
    unlock();
    expect(document.body.style.overflow).toBe("scroll");
  });
});
