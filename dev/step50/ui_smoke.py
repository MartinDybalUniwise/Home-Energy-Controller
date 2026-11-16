"""Headless mobile QA using synthetic alerts and a static-only local server."""
import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


class StaticPreview(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/__test__':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html data-theme="dark"><head><meta name="viewport" content="width=device-width,initial-scale=1">'
                             b'<link rel="stylesheet" href="/css/tokens.css">'
                             b'<link rel="stylesheet" href="/css/app.css">'
                             b'<link rel="stylesheet" href="/css/today.css"></head>'
                             b'<body><main id="view" style="padding:8px"></main></body></html>')
        else:
            super().do_GET()

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    product = Path(__file__).resolve().parents[1] / 'hec'
    catalog = json.loads((product / 'locales/cs.json').read_text(encoding='utf-8'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(StaticPreview, directory=str(product / 'web/frontend')))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport=dict(width=390, height=844))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/__test__')
            for view in ('overview', 'control'):
                page.evaluate('''async ({catalog,view})=>{
                  const {setLanguage}=await import('/js/i18n.js');
                  await setLanguage('cs',{translations:async()=>({lang:'cs',catalog,available:['cs','en']})});
                  const now=new Date();
                  const plan={planned_at:now.toISOString(),mode:'heating',heating_temperature:42,
                    boiler_temperature:50,room_target:21.5,phase:'readiness_veto',
                    alerts:[{code:'heating_response_insufficient'},{code:'dhw_deferred_for_comfort'}]};
                  const current={status:{controller:{enabled:true,planner:'unified',thermal_plan:plan}},sources:{
                    tng:{timestamp:now.toISOString(),sample_time:now.toISOString(),room_temperature:20.9,
                      water_output_temperature:36.5,boiler_temperature:29,heating_on:true,boiler_on:false,
                      heating_set_temperature:42,boiler_set_temperature:45}}};
                  const config={tng:{enabled:true,write_enabled:true,heating:{enabled:true,default_temperature:42},
                    thermostat:{enabled:true,default_temperature:21.5},boiler:{enabled:true,default_temperature:50},
                    operation:{default_mode:'heating'}}};
                  if(view==='overview'){
                    const {heatpumpPanel}=await import('/js/heatpump-panel.js');
                    document.querySelector('#view').innerHTML=heatpumpPanel(current,config,now);
                  }else{
                    const {renderControlLive}=await import('/js/control-plan.js');
                    document.querySelector('#view').innerHTML=renderControlLive({current,config,status:current.status},now);
                  }
                }''', dict(catalog=catalog, view=view))
                assert page.locator('[role="alert"]').count() == 2
                assert page.locator('body').evaluate('(e)=>e.scrollWidth') <= 390
                page.screenshot(path=str(args.out / f'{view}-390.png'), full_page=True)
            assert not errors, errors
            browser.close()
        print('Mobile overview/control alerts: PASS; no overflow or browser errors.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
