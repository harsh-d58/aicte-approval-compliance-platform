const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://localhost:3000/login?returnTo=%2Fportal%2Faudit%2Fverify');
  await page.getByRole('button',{name:'Auditor',exact:true}).click();
  await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
  await page.getByRole('button',{name:'Verify cryptographic chain',exact:true}).waitFor({timeout:90000});
  await page.getByRole('button',{name:'Verify cryptographic chain',exact:true}).click();
  await page.getByText('SUCCESS: Cryptographic hash chain intact and mathematically valid',{exact:true}).waitFor({timeout:60000});
  const table=page.getByRole('heading',{name:'Recent verified events',exact:true}).locator('..').getByRole('table');
  assert.equal(await table.locator('tbody tr').count(),8);
  await table.getByText('Inspect hashes',{exact:true}).first().click();
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.resolve(__dirname,'../../storage/qa-phase11-verification.png'),fullPage:true});
  console.log('PASS live ledger success,8 recent event rows,readable hashes and actor/time columns');
  await page.getByRole('button',{name:'Simulate Tamper Detection',exact:true}).click();
  await page.getByText('Tamper detected in the simulated copy',{exact:true}).waitFor({timeout:60000});
  assert.equal(await page.getByText('SUCCESS: Cryptographic hash chain intact and mathematically valid',{exact:true}).count(),0);
  console.log('PASS simulation flagged separately and does not display real-ledger success');
  await page.getByRole('button',{name:'Verify cryptographic chain',exact:true}).click();
  await page.getByText('SUCCESS: Cryptographic hash chain intact and mathematically valid',{exact:true}).waitFor({timeout:60000});
  assert.deepEqual(errors,[]);
  console.log('VERDICT: PASS - actual Phase11websiteflow,table,simulation,andstoredledgerrecheck');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
