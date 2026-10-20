// Older Android System WebViews (Chrome < 87) ignore the `inset` shorthand Tailwind emits,
// which leaves absolutely/fixed positioned layers (hero image, drawer, dialogs) unanchored.
// Emit top/right/bottom/left longhands before every `inset` declaration.
const postcss = require("postcss");

const insetFallback = () => ({
  postcssPlugin: "inset-fallback",
  Declaration: {
    inset(decl) {
      const [t, r = t, b = t, l = r] = postcss.list.space(decl.value);
      [["top", t], ["right", r], ["bottom", b], ["left", l]].forEach(([prop, value]) => decl.cloneBefore({ prop, value }));
    },
  },
});
insetFallback.postcss = true;

module.exports = insetFallback;
