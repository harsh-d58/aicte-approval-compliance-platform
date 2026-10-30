const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 let page;
 try {
  page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',error=>{errors.push(error.message);console.log('PAGE ERROR',error.message);});
  page.on('requestfailed',request=>console.log('REQUEST FAILED',new URL(request.url()).pathname,request.failure()?.errorText));
  const requests=[];
  page.on('response',response=>{const url=new URL(response.url());if(['/api/v1/me','/api/v1/prototype/session','/api/v1/portal/snapshot'].includes(url.pathname)){requests.push({path:url.pathname,status:response.status()});console.log('RESPONSE',url.pathname,response.status());}});
  async function openRole(role,name){
   const started=Date.now();
   console.log('Opening role',role);
   await page.getByRole('button',{name:role,exact:true}).click();
   await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
   await page.getByRole('button',{name:'Sign out',exact:true}).waitFor({timeout:90000});
   await page.getByText(name,{exact:true}).first().waitFor();
   console.log('PASS normal role sign-in',role,Math.round((Date.now()-started)/1000)+'s');
  }
  await page.goto('http://localhost:3000/login',{timeout:60000});
  await openRole('Regional officer','Meera Desai');
  await page.reload({timeout:60000});
  await page.getByRole('button',{name:'Sign out',exact:true}).waitFor({timeout:90000});
  await page.getByText('Meera Desai',{exact:true}).first().waitFor();
  console.log('PASS restored signed-in session after full reload');
  // Navigate back to sign-in with an existing session, as during demo recording.
  await page.goto('http://localhost:3000/login',{timeout:60000});
  await openRole('Central administrator','Arjun Iyer');
  await page.goto('http://localhost:3000/login',{timeout:60000});
  await openRole('Regional officer','Meera Desai');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.waitForURL('**/login',{timeout:15000});
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('aicte.live.session.v1')),null);
  assert.deepEqual(errors,[]);
  assert.ok(requests.every(request=>request.status===200),JSON.stringify(requests));
  console.log('VERDICT: PASS - real role login, reload, central-to-regional switch and sign-out; no JavaScript errors',JSON.stringify(requests));
 } catch(error) {if(page){console.log('PAGE',page.url(),(await page.locator('body').innerText()).slice(-3500));await page.screenshot({path:require('node:path').resolve(__dirname,'../../storage/qa-login-failure.png'),fullPage:true});}throw error;} finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
