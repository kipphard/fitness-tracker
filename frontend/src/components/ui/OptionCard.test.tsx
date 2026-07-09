import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OptionCard } from "./OptionCard";

afterEach(cleanup);

describe("OptionCard", () => {
  it("reflects selected state and fires onSelect when clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <OptionCard selected={false} onSelect={onSelect} label="Lose weight" description="Cut" />,
    );
    const btn = screen.getByRole("radio", { name: /lose weight/i });
    expect(btn).toHaveAttribute("aria-checked", "false");

    await user.click(btn);
    expect(onSelect).toHaveBeenCalledTimes(1);

    rerender(
      <OptionCard selected onSelect={onSelect} label="Lose weight" description="Cut" />,
    );
    expect(screen.getByRole("radio", { name: /lose weight/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("uses a checkbox role in multi-select mode", () => {
    render(<OptionCard selected={false} onSelect={() => {}} label="Vegan" multi />);
    expect(screen.getByRole("checkbox", { name: /vegan/i })).toBeInTheDocument();
  });
});
