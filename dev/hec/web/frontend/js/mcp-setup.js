// Separate form: never included in the ordinary HEC configuration payload.
export async function mountMcpSetup(view) {
  const panel = document.createElement('section');
  panel.className = 'panel';
  panel.innerHTML = `<h3>MCP / ChatGPT</h3>
    <p>Připojení energetických dat k ChatGPT pouze pro čtení.</p>
    <form data-mcp-key-form autocomplete="off">
      <label class="field" for="mcp-runtime-key"><span>OpenAI klíč pro tunel</span>
        <input id="mcp-runtime-key" type="password" autocomplete="new-password" spellcheck="false" autocapitalize="off" required minlength="23" maxlength="2051" placeholder="sk-…" disabled></label>
      <div class="controls"><button type="submit" disabled>Uložit klíč MCP</button></div>
      <p class="meta" data-mcp-message role="status" aria-live="polite">Ověřuji dostupnost nastavení…</p>
    </form>
    <details><summary>Jak získat a uložit klíč</summary>
      <p><a href="https://platform.openai.com/settings/organization/api-keys" target="_blank" rel="noopener noreferrer">Vytvořit klíč v OpenAI Platform</a>. Organizace musí odpovídat tunelu a klíč potřebuje Tunnels Read + Use.</p>
      <p>Klíč se ukládá soukromě k MCP službě, mimo konfiguraci HEC. Po uložení se nezobrazuje. Samotné uložení ještě nepotvrzuje propojení s ChatGPT.</p>
      <p>Při vzdáleném přístupu na domácí adresu 192.168.2.115:8080 používejte svou VPN.</p>
    </details>`;
  view.append(panel);
  const input = panel.querySelector('input');
  const button = panel.querySelector('button');
  const message = panel.querySelector('[data-mcp-message]');
  const ownerVpn = location.protocol === 'http:' && location.hostname === '192.168.2.115' && location.port === '8080';
  const secure = location.protocol === 'https:' || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname) || ownerVpn;
  try {
    const response = await fetch('/api/mcp/setup', {credentials: 'same-origin', cache: 'no-store'});
    const state = await response.json();
    if (!response.ok || !state.available) {
      message.textContent = 'Nastavení MCP je dostupné pouze na domácím serveru s nainstalovanou MCP službou.';
      return;
    }
    if (state.configured) {
      message.textContent = 'Klíč je uložený. Stav připojení k ChatGPT je potřeba ověřit.';
      return;
    }
    if (!secure) {
      message.textContent = 'Pro vložení klíče otevřete HEC přes vlastní VPN na 192.168.2.115:8080, přes HTTPS, nebo přímo na domácím PC. Běžné nastavení HEC funguje dál.';
      return;
    }
    input.disabled = button.disabled = false;
    message.textContent = 'Klíč po uložení nebude možné zobrazit ani přepsat tímto formulářem.';
  } catch {
    message.textContent = 'Nastavení MCP teď není dostupné. Běžné nastavení HEC funguje dál.';
    return;
  }
  panel.querySelector('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    const key = input.value.trim();
    input.value = '';
    try {
      const response = await fetch('/api/mcp/setup', {method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({api_key: key})});
      if (!response.ok) {
        message.textContent = response.status === 409 ? 'Klíč už je uložený; nic nebylo přepsáno.' : 'Klíč se nepodařilo uložit. Ověřte formát klíče a bezpečné připojení.';
        button.disabled = response.status === 409;
        return;
      }
      input.disabled = true;
      message.textContent = 'Klíč je bezpečně uložený. Připojení čeká na ověření.';
    } catch {
      message.textContent = 'Výsledek uložení není potvrzený. Obnovte Nastavení a ověřte stav klíče.';
      button.disabled = false;
    }
  });
}
