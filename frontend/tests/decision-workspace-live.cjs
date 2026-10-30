const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    page.on('requestfailed',request=>console.log('REQUEST FAILED',request.url().split('?')[0],request.failure()?.errorText));
    page.on('console',message=>{if(message.type()==='error')console.log('CONSOLE',message.text().slice(0,300));});
    await page.goto('http://localhost:3000/login',{timeout:60000});
    await page.getByRole('button',{name:'Regional officer',exact:true}).click({timeout:15000});
    await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
    console.log('Selected Meera through normal demo sign-in');
    await page.waitForURL('**/portal',{timeout:90000});
    await page.getByRole('link',{name:'Applications',exact:true}).click({timeout:90000});
    await page.locator('a[href="/portal/applications/76e9a91b-343a-5d90-8f73-8f96b7b83603"]').first().click({timeout:90000});
    await page.locator('a[href="/portal/applications/76e9a91b-343a-5d90-8f73-8f96b7b83603/decision"]').first().click({timeout:30000});
    console.log('Opened case decision workspace through website navigation');
    await page.getByRole('heading',{name:'Approval conditions',exact:true}).waitFor({timeout:90000});
    await page.getByText('PWD Structural Safety Attestation; Geotagged Photographs',{exact:true}).waitFor();
    const link=page.getByRole('link',{name:'Open condition and evidence',exact:true});
    assert.equal(await link.getAttribute('href'),'/portal/compliance/0def79df-6df3-401c-ba69-e8a9a1d93c9c');
    const recordingReady=process.argv.includes('--ready');
    if(recordingReady){
      assert.equal(await page.getByText('Complete the EVC visit and approve its report before recording a decision.',{exact:true}).count(),0);
      assert.equal(await page.getByRole('button',{name:'Record decision',exact:true}).isEnabled(),true);
      await page.locator('select[name="outcome"]').selectOption('APPROVE');
      await page.getByText('No decision has been recorded for AICTE-2026-DECISION-001.',{exact:true}).waitFor();
    }else{
      await page.getByText('Complete the EVC visit and approve its report before recording a decision.',{exact:true}).waitFor();
      assert.equal(await page.getByRole('button',{name:'Record decision',exact:true}).isDisabled(),true);
    }
    assert.deepEqual(errors,[]);
    await page.screenshot({path:path.resolve(__dirname,recordingReady?'../../storage/qa-phase8-ready.png':'../../storage/qa-decision-closure.png'),fullPage:true});
    console.log('VERDICT: PASS - saved condition/checklist visible, correct compliance link, '+(recordingReady?'APPROVE and Record decision enabled':'missing EVC approval explained')+', no final decision or closure performed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
