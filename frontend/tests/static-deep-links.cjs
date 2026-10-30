const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await browser.newPage();const base=process.env.DEMO_TEST_URL||'http://127.0.0.1:4173';
 const bad=[];await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.port==='8000'||u.pathname.startsWith('/api/v1')){bad.push(u.pathname);return route.abort();}return route.continue();});
 await page.goto(base+'/login?returnTo=%2Fportal%2Finstitutions');
 await page.getByRole('button',{name:'Regional officer',exact:true}).click();await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
 const record=page.locator('a[href*="/portal/institutions/item/"]').first();await record.waitFor();
 const canonical=new URL(await record.getAttribute('href'),base);const legacy=canonical.searchParams.get('__path');assert.ok(legacy);
 await page.goto(base+legacy);await page.waitForURL('**/portal/institutions/item/**',{timeout:20000});
 assert.equal(new URL(page.url()).searchParams.get('__path'),legacy);
 await page.reload();await page.getByRole('button',{name:'Sign out',exact:true}).waitFor({timeout:20000});
 // Brand-new IDs must reach their own detail component, even though absent.
 await page.goto(base+'/portal/applications/new-unbuilt-record/deficiencies/new-unbuilt-notice');
 await page.waitForURL('**/portal/applications/item/deficiencies/item/**',{timeout:20000});
 assert.equal(new URL(page.url()).searchParams.get('__path'),'/portal/applications/new-unbuilt-record/deficiencies/new-unbuilt-notice');
 await page.getByRole('heading',{name:'Application unavailable',exact:true}).waitFor();
 assert.deepEqual(bad,[]);console.log('VERDICT: PASS - legacy direct detail,reload and unbuilt nested IDs resolve on static files without API');
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
