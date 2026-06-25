import Model from "react-body-highlighter";

import { toMuscleSlugs } from "../lib/muscleMap";

const BODY = "#9aa1ad";
const STRONG = "#11936a"; // primary muscle (freq 2)
const LIGHT = "#8fcdb9"; // secondary muscle (freq 1)

// Detail view: front + back body diagrams with primary muscles strong and secondary light.
// Frequency drives the colour (highlightedColors index = frequency − 1), so primary is listed
// twice to land on the STRONG colour and secondary once on LIGHT.
export function MuscleMap({
  primary,
  secondary,
}: {
  primary?: string[] | null;
  secondary?: string[] | null;
}) {
  const prim = toMuscleSlugs(primary);
  const sec = toMuscleSlugs(secondary).filter((s) => !prim.includes(s));
  if (prim.length === 0 && sec.length === 0) return null;

  const data = [
    { name: "", muscles: prim },
    { name: "", muscles: prim },
    { name: "", muscles: sec },
  ];
  const colors = [LIGHT, STRONG];

  return (
    <div className="muscle-map">
      <Model type="anterior" data={data} bodyColor={BODY} highlightedColors={colors} />
      <Model type="posterior" data={data} bodyColor={BODY} highlightedColors={colors} />
    </div>
  );
}
