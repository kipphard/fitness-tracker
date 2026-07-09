import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SegmentedControl, type Segment } from "./SegmentedControl";

afterEach(cleanup);

const OPTS: Segment<"vol" | "reps">[] = [
  { value: "vol", label: "Volume" },
  { value: "reps", label: "Reps" },
];

describe("SegmentedControl", () => {
  it("marks the active option and calls onChange with the clicked value", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<SegmentedControl options={OPTS} value="vol" onChange={onChange} />);

    expect(screen.getByRole("tab", { name: "Volume" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Reps" })).toHaveAttribute("aria-selected", "false");

    await user.click(screen.getByRole("tab", { name: "Reps" }));
    expect(onChange).toHaveBeenCalledWith("reps");
  });
});
