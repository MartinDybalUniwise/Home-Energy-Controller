import {t} from './i18n.js';

// Only the common controller supplies alerts; this view never resolves a plan.
export function thermalAlerts(current, now = new Date()) {
  const controller = current?.status?.controller;
  const plan = controller?.thermal_plan;
  const age = (+now - Date.parse(plan?.planned_at)) / 1000;
  if (!controller?.enabled || !Number.isFinite(age) || age < -60 || age > 900) return '';
  const allowed = new Set(['heating_response_insufficient', 'dhw_deferred_for_comfort']);
  return (plan.alerts || []).filter(a => allowed.has(a.code)).map(a =>
    `<p class="notice error thermal-alert" role="alert">${t(`thermal_alert.${a.code}`)}</p>`).join('');
}
