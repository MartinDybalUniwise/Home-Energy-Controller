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

// Spotřebiče ve schématu toku energie. Stejný jednobarevný, liniový styl jako
// ikony počasí – žádná kresba třetí strany, jen princip 24x24 obrysu.
const APPLIANCE_SHAPES = {
  dishwasher: `
    <rect x="3" y="2" width="18" height="20" rx="2"/>
    <line x1="6" y1="5.5" x2="10" y2="5.5"/>
    <circle cx="12" cy="14" r="6"/>
    <circle cx="12" cy="14" r="2.2" fill="currentColor" stroke="none"/>`,
  washing_machine: `
    <rect x="3" y="2" width="18" height="20" rx="2"/>
    <circle cx="7" cy="5.2" r=".9" fill="currentColor" stroke="none"/>
    <circle cx="10.2" cy="5.2" r=".9" fill="currentColor" stroke="none"/>
    <circle cx="12" cy="14.5" r="6.5"/>
    <path d="M7.3 14.5a4.7 4.7 0 0 0 9.4 0"/>`,
  dryer: `
    <rect x="3" y="3.5" width="18" height="19" rx="2"/>
    <circle cx="12" cy="14" r="6"/>
    <path d="M9 11.5a3.6 3.6 0 0 1 5.6 3" stroke-linecap="round"/>
    <path d="M14.6 14.5v-2.6h-2.6" stroke-linecap="round" stroke-linejoin="round"/>`,
  fridge: `
    <rect x="6" y="1.5" width="12" height="21" rx="1.6"/>
    <line x1="6" y1="8.5" x2="18" y2="8.5"/>
    <line x1="15" y1="4" x2="15" y2="6.5"/>
    <line x1="15" y1="11.5" x2="15" y2="15.5"/>`,
  heatpump: `
    <rect x="1.5" y="8" width="13" height="10" rx="1.6"/>
    <line x1="4" y1="11" x2="11.5" y2="11"/>
    <line x1="4" y1="14.5" x2="11.5" y2="14.5"/>
    <circle cx="18.5" cy="13" r="4.6"/>
    <path d="M18.5 9.3v7.4M14.8 13h7.4" stroke-width="1.3"/>`,
  other: `
    <rect x="4" y="6" width="16" height="14" rx="3"/>
    <line x1="9.5" y1="11" x2="9.5" y2="15"/>
    <line x1="14.5" y1="11" x2="14.5" y2="15"/>`,
};

/** Obrys spotřebiče jako samostatná skupina (24x24 souřadný prostor), bez
 * vlastního <svg> – pro vložení do jiného SVG (schéma toku energie), kde je
 * potřeba vlastní pozicování přes transform, ne vlastní viewport. */
export function applianceIconGroup(type) {
  const shape = APPLIANCE_SHAPES[type] || APPLIANCE_SHAPES.other;
  return `<g fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${shape}</g>`;
}

export function applianceIcon(type, className = 'appliance-icon') {
  return `<svg class="${className}" viewBox="0 0 24 24" role="img" aria-hidden="true">${applianceIconGroup(type)}</svg>`;
}
