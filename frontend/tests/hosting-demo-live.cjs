const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const base=process.env.DEMO_TEST_URL||'http://localhost:3000';
 try{
  const page=await browser.newPage();const forbidden=[],errors=[];
  await page.route('**/*',route=>{
   const u=new URL(route.request().url());
   if(u.pathname.startsWith('/api/v1')||u.port==='8000'){forbidden.push(u.pathname);return route.abort();}
   return route.continue();
  });
  page.on('pageerror',e=>errors.push(e.message));
  async function login(role,dest='/portal'){
   await page.goto(base+'/login?returnTo='+encodeURIComponent(dest));
   await page.getByRole('button',{name:role,exact:true}).click();
   await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
   await page.getByRole('button',{name:'Sign out',exact:true}).waitFor({timeout:20000});
  }
  await login('Regional officer','/portal/institutions/new');
  await page.getByRole('heading',{name:'Create institution',exact:true}).waitFor();
  await page.locator('input[name=name]').fill('Hosting browser persistence institute');
  await page.locator('input[name=code]').fill('LOCAL-HOSTING-001');
  await page.locator('input[name=type]').fill('TECHNICAL');
  await page.locator('select[name=regionId]').selectOption('region-west');
  await page.locator('input[name=campusName]').fill('Main');
  await page.locator('input[name=city]').fill('Pune');
  await page.getByRole('button',{name:'Save changes',exact:true}).click();
  await page.getByRole('heading',{name:'Hosting browser persistence institute',exact:true}).waitFor();
  const newURL=page.url();await page.reload();
  await page.getByRole('heading',{name:'Hosting browser persistence institute',exact:true}).waitFor();
  console.log('PASS browser mutation,new record navigation and reload',newURL);
  await login('Auditor','/portal/audit/verify');
  await page.getByRole('button',{name:'Verify cryptographic chain',exact:true}).click();
  await page.getByText('SUCCESS: Cryptographic hash chain intact and mathematically valid',{exact:true}).waitFor();
  await page.getByText('Browser-local demo ledger.',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Simulate Tamper Detection',exact:true}).click();
  await page.getByText('Tamper detected in the simulated copy',{exact:true}).waitFor();
  console.log('PASS actual local hashing and tamper simulation');
  await login('Central administrator','/portal/reports/region-performance');
  await page.getByRole('button',{name:'Generate export snapshot',exact:true}).click();
  await page.getByRole('heading',{name:'Export run',exact:true}).waitFor();
  for(const ext of ['CSV','XLSX','PDF']){
   const event=page.waitForEvent('download');await page.getByRole('button',{name:ext+' ↓',exact:true}).click();
   const file=await event;assert.ok(file.suggestedFilename().endsWith('.'+ext.toLowerCase()));
  }
  console.log('PASS frozen report generation andthree realdownloads');
  await login('Institutional representative','/portal/documents/new');
  await page.getByRole('heading',{name:'Register a document',exact:true}).waitFor();
  await page.locator('select[name=institutionId]').selectOption('inst-001');
  await page.locator('input[name=issuer]').fill('Demo only');
  await page.locator('input[name=reference]').fill('LOCAL-DEMO-FILE');
  await page.locator('input[name=issuedAt]').fill('2026-10-01');
  if(await page.locator('input[name=expiryDate]').count())await page.locator('input[name=expiryDate]').fill('2027-10-01');
  await page.locator('input[type=file][name=file]').setInputFiles({name:'local-proof.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n% demo upload bytes\n%%EOF')});
  await page.getByRole('button',{name:'Register document',exact:true}).click();
  await page.getByRole('button',{name:'Download file',exact:true}).waitFor();
  await page.reload();await page.getByRole('button',{name:'Download file',exact:true}).waitFor();
  console.log('PASS local upload andblob survives reload');
  for(const role of ['Scrutiny officer','EVC coordinator','EVC expert','Compliance officer','Policy administrator','System administrator']){
   await login(role);console.log('PASS role',role);
  }
  assert.deepEqual(forbidden,[]);assert.deepEqual(errors,[]);
  console.log('VERDICT: PASS - all10personas,mutations,persistence,files,reports,audit withbackendrequestsblocked');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
