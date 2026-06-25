export type Pace = "walking" | "jogging" | "running";
export const PACES: Pace[] = ["walking", "jogging", "running"];

// Faster gaits lengthen the stride, so a km is covered in fewer, longer steps.
const PACE_STRIDE_FACTOR: Record<Pace, number> = { walking: 1, jogging: 1.2, running: 1.4 };
const DEFAULT_SHOE_EU = 42;

// Rough walking step length (m) from EU shoe size: ~0.75 m at EU 42, ±1.2 cm per size.
export function walkingStrideM(shoeEu: number): number {
  return 0.75 + (shoeEu - 42) * 0.012;
}

// Estimate the step count for a distance (km), given EU shoe size as a stride basis and the
// gait. A rough rule-of-thumb for cardio machines that report distance but not steps (#13).
export function distanceToSteps(km: number, shoeEu: number | null | undefined, pace: Pace): number {
  if (!(km > 0)) return 0;
  const eu = shoeEu && shoeEu > 0 ? shoeEu : DEFAULT_SHOE_EU;
  const stride = Math.max(0.3, walkingStrideM(eu) * PACE_STRIDE_FACTOR[pace]);
  return Math.round((km * 1000) / stride);
}
