/*
 * Auto-shrink a slide's font size until its content fits within the
 * configured reveal.js canvas height, instead of silently overflowing past
 * the bottom edge (where it gets visually overlapped by the fixed-position
 * nav arrows/slide counter -- reveal.js's `.reveal .slides section` has no
 * fixed height and `overflow: visible`, so oversized content isn't clipped
 * by any container; it just renders past where reveal.js assumed the
 * slide would end).
 *
 * Compares scrollHeight against Reveal.getConfig().height (the *virtual*
 * canvas height, e.g. 1350 -- not the section's own clientHeight, which is
 * meaningless here since the section has no fixed box to overflow) --
 * this is unaffected by reveal.js's outer transform:scale() (a paint-time
 * visual transform, not a layout-affecting one), so this works the same
 * regardless of actual browser window size.
 *
 * No per-slide authoring needed -- runs automatically on every slide via
 * the `ready`/`slidechanged` events.
 */
(function () {
  var MIN_SCALE = 0.6;
  var STEP = 0.05;
  var MAX_STEPS = 20;

  function fitSlide(section) {
    if (!section || !window.Reveal) return;
    var maxHeight = Reveal.getConfig().height;
    if (!maxHeight) return;

    section.style.fontSize = '';
    var scale = 1.0;
    for (var i = 0; i < MAX_STEPS && section.scrollHeight > maxHeight && scale > MIN_SCALE; i++) {
      scale -= STEP;
      section.style.fontSize = scale + 'em';
    }
  }

  function fitCurrentSlide() {
    if (window.Reveal && typeof Reveal.getCurrentSlide === 'function') {
      fitSlide(Reveal.getCurrentSlide());
    }
  }

  function init() {
    if (!window.Reveal) return;
    Reveal.on('ready', function (event) { fitSlide(event.currentSlide); });
    Reveal.on('slidechanged', function (event) { fitSlide(event.currentSlide); });
    // Defensive re-check -- e.g. web fonts finishing load after the initial
    // measurement can change actual text metrics.
    window.addEventListener('resize', fitCurrentSlide);
  }

  if (window.Reveal && typeof Reveal.isReady === 'function' && Reveal.isReady()) {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
})();
