const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE',m.text().slice(0,240));});
 await page.goto('http://127.0.0.1:3000/login',{timeout:60000});
 await page.getByRole('button',{name:'Central administrator',exact:true}).click();
 await page.getByRole('button',{name:'Enter demonstration portal',exact:true}).click();
 await page.waitForURL('**/portal',{timeout:60000});
 await page.getByRole('heading',{name:'Records behind the numbers'}).waitFor({timeout:60000});
 console.log('PASS central live analytics rendered');
 await page.screenshot({path:'storage/qa-live-dashboard.png',fullPage:true});
 for(const route of ['applications','documents','evc','compliance','reports']){
  await page.goto('http://127.0.0.1:3000/portal/'+route,{timeout:60000});
  await page.locator('#main-content h1').waitFor({timeout:60000});
  await page.waitForTimeout(1000);
  console.log('PAGE',route,await page.locator('#main-content h1').innerText());
  const alert=await page.getByRole('alert').allTextContents();if(alert.length)console.log('ALERT',alert);
 }
 console.log('PAGE ERRORS',JSON.stringify(errors));
 await browser.close();if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
