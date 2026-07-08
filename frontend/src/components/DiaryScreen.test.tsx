import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DiaryScreen } from "./DiaryScreen";
import { addDays, todayIso } from "../lib/format";

// Mock the API client; the real useApi/useMealSlots hooks run against these spies.
const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));
vi.mock("../api/client", () => ({ apiGet, apiPost, apiPatch, apiDelete }));

// Translate to the key itself so queries are stable and locale-independent.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "en" } }),
}));

const TODAY = todayIso();
const YESTERDAY = addDays(TODAY, -1);

const entry = (id: string, slot: string, name: string, amount: string) => ({
  id,
  date: YESTERDAY,
  slot,
  food_id: null,
  food_name: name,
  amount_g: amount,
  kcal: "0",
  protein_g: "0",
  fat_g: "0",
  carbs_g: "0",
});

const emptyDay = (d: string) => ({
  date: d,
  entries: [],
  totals: { kcal: "0", protein_g: "0", fat_g: "0", carbs_g: "0" },
});

beforeEach(() => {
  apiPost.mockResolvedValue({});
  apiPatch.mockResolvedValue({});
  apiDelete.mockResolvedValue({});
  apiGet.mockImplementation((path: string) => {
    if (path === `/diary?date=${YESTERDAY}`) {
      return Promise.resolve({
        date: YESTERDAY,
        entries: [
          entry("mq", "breakfast", "Magerquark", "250"),
          entry("oats", "breakfast", "Haferflocken", "80"),
          entry("chk", "lunch", "Haehnchen", "200"),
        ],
        totals: { kcal: "0", protein_g: "0", fat_g: "0", carbs_g: "0" },
      });
    }
    if (path.startsWith("/diary?date=")) return Promise.resolve(emptyDay(TODAY));
    if (path === "/diary/recent") return Promise.resolve([]);
    if (path === "/meal-slots") return Promise.resolve(null); // hook falls back to built-ins
    return Promise.resolve(null);
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DiaryScreen copy-from-another-day sheet", () => {
  it("copies only the checked foods from the source day into the viewed day", async () => {
    const user = userEvent.setup();
    render(<DiaryScreen />);

    // Open the copy sheet; it loads yesterday's diary and lists its foods (all pre-checked).
    await user.click(await screen.findByRole("button", { name: "diary.copyFrom" }));
    const mq = await screen.findByText("Magerquark");
    expect(screen.getByText("Haferflocken")).toBeInTheDocument();
    expect(screen.getByText("Haehnchen")).toBeInTheDocument();

    // Uncheck the two we don't want, leaving just Magerquark selected.
    await user.click(within(screen.getByText("Haferflocken").closest("label")!).getByRole("checkbox"));
    await user.click(within(screen.getByText("Haehnchen").closest("label")!).getByRole("checkbox"));

    // Sanity: Magerquark is still checked.
    expect(within(mq.closest("label")!).getByRole("checkbox")).toBeChecked();

    await user.click(screen.getByRole("button", { name: "diary.copyBtn" }));

    expect(apiPost).toHaveBeenCalledWith("/diary/copy", {
      from_date: YESTERDAY,
      to_date: TODAY,
      entry_ids: ["mq"],
    });
  });

  it("selecting a meal's header checkbox toggles all of its foods", async () => {
    const user = userEvent.setup();
    render(<DiaryScreen />);

    await user.click(await screen.findByRole("button", { name: "diary.copyFrom" }));
    await screen.findByText("Magerquark");

    // The breakfast header checkbox is the first checkbox; unchecking it drops both breakfast foods,
    // leaving only the lunch entry selected.
    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]); // breakfast "select all"

    await user.click(screen.getByRole("button", { name: "diary.copyBtn" }));

    expect(apiPost).toHaveBeenCalledWith("/diary/copy", {
      from_date: YESTERDAY,
      to_date: TODAY,
      entry_ids: ["chk"],
    });
  });
});
