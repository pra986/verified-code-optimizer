"""Exercise the real compiler-backed app in Chromium."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect

out=Path('evaluation/browser-artifacts');out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as data:
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env=dict(os.environ,OPTIMIZER_DATA_DIR=data)
    server=subprocess.Popen([sys.executable,'-m','uvicorn','optimizer.app:app','--host','127.0.0.1','--port',str(port)],env=env,stdout=subprocess.DEVNULL)
    try:
        url=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:urllib.request.urlopen(url+'/api/health',timeout=1);break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Server failed to start')
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url);expect(page.locator('#pythonSource')).to_contain_text('for i in range')
            page.locator('#repeats').select_option('3');page.locator('#run').click()
            expect(page.locator('#verdict')).to_have_text('Fixture agreement verified',timeout=60000)
            expect(page.locator('#timingCards')).to_be_visible();expect(page.locator('#fixtureRows tr')).to_have_count(9)
            with page.expect_download() as event:page.locator('#download').click()
            download=event.value;download.save_as(out/download.suggested_filename)
            report=json.loads(next(out.glob('*.json')).read_text());assert report['status']=='verified_fixture_agreement';assert len(report['timing']['cpp']['samples_ms'])==3
            page.screenshot(path=str(out/'desktop.png'),full_page=True)
            page.locator('#candidate').select_option('wrong');expect(page.locator('#cppSource')).to_contain_text('i < n');page.locator('#run').click()
            expect(page.locator('#verdict')).to_have_text('Correctness rejected',timeout=60000);expect(page.locator('#timingCards')).not_to_be_visible();expect(page.locator('#fixtureRows')).to_contain_text('FAIL')
            page.locator('#candidate').select_option('compile-error');page.locator('#run').click()
            expect(page.locator('#verdict')).to_have_text('Compilation rejected',timeout=60000);expect(page.locator('#noFixtures')).to_be_visible()
            page.reload();expect(page.locator('#history button')).to_have_count(3);page.locator('#history button').last.click();expect(page.locator('#verdict')).to_have_text('Fixture agreement verified')
            page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)');assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile overflow'
            page.screenshot(path=str(out/'mobile.png'),full_page=True)
            assert not errors,errors
            browser.close();print('Browser smoke passed: real compile, correctness gate, timings, JSON download, two rejection modes, saved history, responsive layout.')
    finally:server.terminate();server.wait(timeout=10)
