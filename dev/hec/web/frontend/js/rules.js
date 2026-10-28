import { currentLanguage, t } from './i18n.js';

export async function rulesPage(view) {
  const response = await fetch('/hec-rules.json', {cache:'no-store'});
  if (!response.ok) throw new Error('Rules unavailable');
  const registry = await response.json();
  const lang = currentLanguage();
  const text = value => value?.[lang] || value?.cs || '';
  view.replaceChildren();
  const heading = document.createElement('h1'); heading.textContent=t('rules.title');
  const intro = document.createElement('p'); intro.textContent=t('rules.intro');
  const updated = document.createElement('p'); updated.className='meta';
  updated.textContent=`${t('rules.updated')}: ${registry.updated_at}`;
  view.append(heading,intro,updated);
  for (const rule of registry.rules.filter(rule=>rule.status==='active')) {
    const section=document.createElement('section'); section.className='panel';
    const title=document.createElement('h2'); title.textContent=text(rule.title);
    const body=document.createElement('p'); body.textContent=text(rule.text);
    const meta=document.createElement('p'); meta.className='meta';
    meta.textContent=`${rule.id} · ${rule.recorded_on} · ${t('rules.source')}`;
    section.append(title,body,meta); view.append(section);
  }
  const history=document.createElement('details');
  const label=document.createElement('summary');label.textContent=t('rules.history');history.append(label);
  for (const entry of registry.history) {
    const row=document.createElement('p');
    row.textContent=`${entry.date} · ${entry.rule_id}: ${text(entry.change)}`;history.append(row);
  }
  view.append(history);
}
