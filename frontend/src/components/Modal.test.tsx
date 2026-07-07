import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";

import { Modal } from "./Modal";

afterEach(() => {
  cleanup();
  document.body.style.overflow = "";
});

describe("Modal background scroll lock", () => {
  it("restores body overflow after stacked modals close (the stuck-scroll bug)", () => {
    document.body.style.overflow = "auto";

    const { rerender, unmount } = render(
      <>
        <Modal onClose={() => {}} bare>
          outer
        </Modal>
        <Modal onClose={() => {}} bare>
          inner
        </Modal>
      </>,
    );
    expect(document.body.style.overflow).toBe("hidden");

    // Close the inner modal — background must stay locked while the outer one is open.
    rerender(
      <>
        <Modal onClose={() => {}} bare>
          outer
        </Modal>
      </>,
    );
    expect(document.body.style.overflow).toBe("hidden");

    // Close everything — overflow returns to its original value, so the page scrolls again.
    unmount();
    expect(document.body.style.overflow).toBe("auto");
  });

  it("does not leak the lock when the parent re-renders with a fresh onClose", () => {
    document.body.style.overflow = "auto";
    const { rerender, unmount } = render(
      <Modal onClose={() => {}} bare>
        x
      </Modal>,
    );
    // A new onClose closure on every render must not tear the lock effect down and back up.
    rerender(
      <Modal onClose={() => {}} bare>
        x
      </Modal>,
    );
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("auto");
  });
});
