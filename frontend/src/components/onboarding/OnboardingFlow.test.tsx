import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OnboardingFlow } from "./OnboardingFlow";

const { apiGet, apiPut } = vi.hoisted(() => ({ apiGet: vi.fn(), apiPut: vi.fn() }));
vi.mock("../../api/client", () => ({ apiGet, apiPut }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

beforeEach(() => {
  apiPut.mockResolvedValue({});
  apiGet.mockResolvedValue({ target: "2000" });
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OnboardingFlow", () => {
  it("collects the profile across steps and saves it, then finishes", async () => {
    const onDone = vi.fn();
    const user = userEvent.setup();
    render(<OnboardingFlow onDone={onDone} />);

    // Welcome → goal
    await user.click(screen.getByRole("button", { name: "onboarding.start" }));

    // Goal: Continue is gated until a choice is made.
    const next = () => screen.getByRole("button", { name: "onboarding.next" });
    expect(next()).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /profile\.goalOptions\.cut/ }));
    await user.click(next());

    // Gender
    await user.click(screen.getByRole("radio", { name: /profile\.genderOptions\.male/ }));
    await user.click(next());

    // Age / height / weight come prefilled with valid defaults → just advance.
    await user.click(next()); // age
    await user.click(next()); // height
    await user.click(next()); // weight

    // Activity → finish (saves)
    await user.click(screen.getByRole("radio", { name: /calories\.levels\.sedentary/ }));
    await user.click(next());

    // Summary shows after the save resolves.
    await screen.findByText("onboarding.summaryTitle");
    expect(apiPut).toHaveBeenCalledWith("/profile", {
      height_cm: "175",
      age: 30,
      gender: "male",
      weight_kg: "75",
      activity_level: "sedentary",
      goal: "cut",
    });

    await user.click(screen.getByRole("button", { name: "onboarding.enterApp" }));
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
