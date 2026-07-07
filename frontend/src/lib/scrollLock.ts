// Ref-counted body-scroll lock shared by every Modal / overlay.
//
// A per-modal save/restore of `document.body.style.overflow` leaks `overflow: hidden`
// whenever two modals are mounted at once (the normal add-food → food-detail flow): the
// inner modal captures the outer modal's already-"hidden" value as the "previous" state,
// so the last restore writes "hidden" back and the page can never scroll again.
//
// Ref-counting fixes that: only the first lock() saves the real overflow and disables
// scrolling; only the last unlock() restores it.
let count = 0;
let saved = "";

export function lock(): void {
  if (count === 0) {
    saved = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  count += 1;
}

export function unlock(): void {
  if (count === 0) return;
  count -= 1;
  if (count === 0) {
    document.body.style.overflow = saved;
  }
}
