import { t } from './i18n.js';

export function releaseTime(value) {
  if (!value) return t('release.pending');
  return new Intl.DateTimeFormat('cs-CZ', {
    timeZone: 'Europe/Prague', day: 'numeric', month: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value));
}

export async function setupReleases() {
  const button = document.getElementById('app-version');
  const dialog = document.getElementById('release-dialog');
  const body = document.getElementById('release-body');
  let payload;
  const load = async () => {
    if (!payload) {
      const response = await fetch('/api/releases', { credentials: 'same-origin', cache: 'no-cache' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      payload = await response.json();
    }
    button.textContent = `v${payload.current}`;
  };
  const show = async () => {
    body.replaceChildren();
    try {
      await load();
      for (const release of [...payload.releases].sort((a, b) => (b.released_at || '9999').localeCompare(a.released_at || '9999'))) {
        const section = document.createElement('section');
        const title = document.createElement('h3');
        title.textContent = `v${release.version}`;
        const date = document.createElement('p');
        date.className = 'release-time';
        date.textContent = releaseTime(release.released_at);
        const changes = document.createElement('ul');
        for (const key of release.changes) {
          const item = document.createElement('li');
          item.textContent = t(key);
          changes.append(item);
        }
        section.append(title, date, changes);
        body.append(section);
      }
    } catch {
      body.textContent = t('error.load_failed');
    }
    if (!dialog.open) dialog.showModal();
  };
  button.addEventListener('click', show);
  document.getElementById('release-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => button.focus());
  try { await load(); } catch { button.textContent = t('release.title'); }
}
