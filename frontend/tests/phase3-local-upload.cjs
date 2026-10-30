const assert = require('node:assert/strict');
const path = require('node:path');
const {chromium} = require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  console.log('Checking institution session');
  const response = await fetch('http://127.0.0.1:8000/api/v1/prototype/session', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({persona_id:'user-institution'}),signal:AbortSignal.timeout(60000)});
  assert.equal(response.status,200);
  const session = await response.json();
  console.log('Loading notice records');
  const snapshot = await fetch('http://127.0.0.1:8000/api/v1/portal/snapshot',{headers:{Authorization:'Bearer '+session.access_token},signal:AbortSignal.timeout(90000)});
  assert.equal(snapshot.status,200);
  const data = await snapshot.json();
  const notice = data.deficiencies.find(row=>row.status==='OPEN' && row.items.some(item=>item.status!=='RESOLVED'));
  assert(notice,'An open institution notice is required');
  console.log('Opening the live notice in Edge');
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    page.on('requestfailed',request=>console.log('Request failed:',request.url().split('?')[0],request.failure()?.errorText));
    await page.addInitScript(value=>sessionStorage.setItem('aicte.live.session.v1',JSON.stringify(value)),session);
    const url=`http://127.0.0.1:3000/portal/applications/${notice.applicationId}/deficiencies/${notice.id}`;
    await page.goto(url,{timeout:60000});
    const button=page.getByRole('button',{name:'Upload correction evidence',exact:true}).first();
    try { await button.waitFor({timeout:90000}); }
    catch (error) { console.log('URL:',page.url());console.log('Page:',(await page.locator('body').innerText()).slice(0,3500));console.log('Page errors:',errors);await page.screenshot({path:path.resolve(__dirname,'../../tmp/phase3-upload-debug.png')});throw error; }
    const chooser=page.waitForEvent('filechooser');
    await button.click();
    const fileChooser=await chooser;
    await fileChooser.setFiles(path.resolve(__dirname,'../../sample_documents/official_delhi_fire_safety_certificate.pdf'));
    await page.getByText('Selected local file: official_delhi_fire_safety_certificate.pdf',{exact:true}).waitFor();
    assert.equal(page.url(),url);
    assert(await page.getByRole('button',{name:'Upload and attach selected file',exact:true}).isVisible());
    assert.deepEqual(errors,[]);
    console.log('VERDICT: PASS — native local chooser opened; selected PDF shown; notice URL unchanged; no file uploaded or response submitted');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
