// Vlastní jednobarevné SVG ikony. Kresba vysílatele se nepřebírá – jen princip.

const SUN = '<circle cx="24" cy="24" r="9" fill="currentColor"/><g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M24 5v6M24 37v6M5 24h6M37 24h6M10.5 10.5l4.2 4.2M33.3 33.3l4.2 4.2M37.5 10.5l-4.2 4.2M14.7 33.3l-4.2 4.2"/></g>';
const CLOUD = '<path d="M16 38a9 9 0 0 1-.6-18 13 13 0 0 1 24.5 3.4A8 8 0 0 1 38 38z" fill="currentColor" opacity=".85"/>';
const SMALL_SUN = '<circle cx="17" cy="16" r="7" fill="currentColor" opacity=".9"/>';

const SHAPES = {
  clear: SUN,
  partly_cloudy: SMALL_SUN + CLOUD,
  cloudy: CLOUD,
  fog: CLOUD + '<g stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".7"><path d="M10 42h28M14 46h20"/></g>',
  drizzle: CLOUD + '<g stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 41v3M26 41v4M34 41v3"/></g>',
  rain: CLOUD + '<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M17 40l-2 6M26 40l-2 7M35 40l-2 6"/></g>',
  snow: CLOUD + '<g stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 44h4M20 42v4M30 44h4M32 42v4"/></g>',
  thunderstorm: CLOUD + '<path d="M26 39l-6 8h5l-2 7 9-10h-5l3-5z" fill="currentColor"/>',
  unknown: '<circle cx="24" cy="24" r="12" fill="none" stroke="currentColor" stroke-width="2.4"/><path d="M24 30v-3a4 4 0 1 0-4-4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><circle cx="24" cy="35" r="1.6" fill="currentColor"/>',
  night: '<path d="M30 8a16 16 0 1 0 12 24A14 14 0 0 1 30 8z" fill="currentColor"/>',
};

export function weatherIcon(condition, isDay = true, className = 'col-icon') {
  const shape = (!isDay && (condition === 'clear' || condition === 'partly_cloudy'))
    ? SHAPES.night + (condition === 'partly_cloudy' ? CLOUD : '')
    : (SHAPES[condition] || SHAPES.unknown);
  return `<svg class="${className}" viewBox="0 0 48 56" role="img" aria-hidden="true">${shape}</svg>`;
}
