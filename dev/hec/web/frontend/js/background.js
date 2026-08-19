// Dynamické pozadí podle počasí a denní doby. Pozadí nikdy nesnižuje čitelnost –
// nad ním leží scrim a panel.

export function applyScene(weather, motion = 'full') {
  const scene = document.getElementById('scene');
  if (!scene) return;
  const current = weather?.current || {};
  const condition = current.condition || 'unknown';

  scene.dataset.condition = condition;
  scene.dataset.daytime = daytime(weather);
  scene.dataset.motion = motion;
  document.body.dataset.motion = motion;
}

function daytime(weather) {
  const now = new Date();
  const sunrise = weather?.sunrise ? new Date(weather.sunrise) : null;
  const sunset = weather?.sunset ? new Date(weather.sunset) : null;
  if (!sunrise || !sunset || Number.isNaN(sunrise.getTime()) || Number.isNaN(sunset.getTime())) {
    return weather?.current?.is_day === false ? 'night' : 'day';
  }
  const minutes = (a, b) => Math.abs(a - b) / 60000;
  if (now < sunrise || now > sunset) return 'night';
  if (minutes(now, sunset) < 60) return 'sunset';
  if (minutes(now, sunrise) < 60) return 'sunrise';
  return 'day';
}
