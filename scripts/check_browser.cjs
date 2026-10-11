// Headless dashboard smoke test. The explicit "unoq" mode contacts the board.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(process.argv[2]||'http://127.0.0.1:8097');
    if(process.argv[3]==='unoq'){
      await page.waitForFunction(()=>document.getElementById('mode').value==='replay');
      await page.waitForFunction(()=>document.getElementById('video-select').options.length>1);
      await page.waitForFunction(()=>document.getElementById('transport-status').textContent.includes('MCU via Bridge'));
      const config=await (await page.request.get((process.argv[2]||'')+'/api/config')).json();
      assert.equal(config.controller,'bridge');
      await page.locator('#video-select').selectOption({index:1});
      await page.waitForFunction(()=>document.getElementById('video-note').textContent.includes('Video selezionato'));
      await page.locator('#video-play').click();
      await page.waitForFunction(()=>Number(document.getElementById('waiting').textContent)>0,{},{timeout:45000});
      await page.locator('[data-request="accessible"]').click();
      await page.waitForTimeout(300);assert.deepEqual(errors,[]);
      await page.waitForFunction(()=>document.getElementById('request-status').textContent.includes('servita'),{},{timeout:75000});
      const downloadPromise=page.waitForEvent('download');
      await page.locator('#export').click();
      const download=await downloadPromise;
      await download.saveAs(path.join(__dirname,'../.local/dashboard-unoq-export.json'));
      const report=JSON.parse(fs.readFileSync(path.join(__dirname,'../.local/dashboard-unoq-export.json'),'utf8'));
      assert.equal(report.source,'replay');assert.equal(typeof report.metrics.completed,'number');
      await page.route('**/api/**',route=>route.abort());
      await page.waitForFunction(()=>document.getElementById('phase-name').textContent==='Controller disconnesso',{},{timeout:10000});
      assert.equal(await page.locator('[data-request="pedestrian"]').isDisabled(),true);
      assert.equal(await page.locator('#ped-signal').textContent(),'—');
      await page.unroute('**/api/**');
      await page.waitForFunction(()=>document.getElementById('phase-name').textContent!=='Controller disconnesso',{},{timeout:15000});
      await page.screenshot({path:path.join(__dirname,'../.local/dashboard-unoq.png'),fullPage:true});
      assert.deepEqual(errors,[]);
      console.log('UNOQ_BROWSER_OK: live Bridge state, JPEG, source switch, accessible request served, real JSON export, browser API outage/recovery, no JS exceptions');
      return;
    }
    if(process.argv[3]==='replay'){
      await page.waitForFunction(()=>document.getElementById('mode').value==='replay');
      await page.waitForFunction(()=>document.getElementById('video-select').options.length>1);
      await page.locator('#video-select').selectOption({index:1});
      await page.locator('#video-play').click();
      await page.waitForFunction(()=>Number(document.getElementById('count').textContent)>=4,{},{timeout:90000});
      assert.match(await page.locator('#transport-status').textContent(),/Firmware nativo/);
      await page.locator('#video-select').selectOption({index:2});
      await page.locator('#video-play').click();
      await page.waitForFunction(()=>Number(document.getElementById('waiting').textContent)>0,{},{timeout:30000});
      await page.locator('[data-request="accessible"]').click();
      await page.waitForFunction(()=>document.getElementById('request-status').textContent.includes('servita'),{},{timeout:30000});
      const downloadPromise=page.waitForEvent('download');
      await page.locator('#export').click();
      const download=await downloadPromise;
      await download.saveAs(path.join(__dirname,'../.local/dashboard-export.json'));
      const report=JSON.parse(fs.readFileSync(path.join(__dirname,'../.local/dashboard-export.json'),'utf8'));
      assert.equal(report.source,'replay');assert.ok(report.metrics.completed>=4);
      await page.screenshot({path:path.join(__dirname,'../.local/dashboard-replay.png'),fullPage:true});
      assert.deepEqual(errors,[]);
      console.log('REPLAY_BROWSER_OK: real video/JPEG, four crossings, source switch, waiting users, served accessible request and JSON export');
      return;
    }
    if(process.argv[3]==='camera'){
      await page.waitForFunction(()=>document.getElementById('mode').value==='replay');
      assert.equal(await page.locator('#mode-camera').isDisabled(),false);
      await page.locator('#mode').selectOption('camera');
      await page.waitForFunction(()=>document.getElementById('mode-label').textContent==='TELECAMERA');
      assert.equal(await page.locator('#camera-controls').isVisible(),true);
      assert.equal(await page.locator('#video-controls').isVisible(),false);
      const vision=await (await page.request.get((process.argv[2]||'')+'/api/vision')).json();
      assert.equal(vision.mode,'camera');
      assert.equal(vision.status,'ready');
      assert.equal(vision.frame,null);
      assert.deepEqual(errors,[]);
      console.log('CAMERA_BROWSER_OK: manual source selection does not start capture; camera controls visible.');
      return;
    }
    await page.waitForFunction(()=>document.getElementById('mode').value==='replay');
    await page.waitForFunction(()=>document.getElementById('phase-name').textContent==='Controller disconnesso');
    assert.equal(await page.locator('[data-request="pedestrian"]').isDisabled(),true);
    assert.equal(await page.locator('#mode-camera').isDisabled(),true);
    await page.getByRole('button',{name:'Configura zone YOLO'}).click();
    assert.equal(await page.locator('#zone-controls').isVisible(),true);
    await page.locator('#zone-cancel').click();
    fs.mkdirSync(path.join(__dirname,'../.local'),{recursive:true});
    await page.screenshot({path:path.join(__dirname,'../.local/dashboard-smoke.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('BROWSER_OK: Replay default, disconnected state, ROI editor, no JS exceptions');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
