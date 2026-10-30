/* Local CDN-style preview. No API handlers or application server rendering. */
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../out');
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.txt':'text/plain','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2','.pdf':'application/pdf'};
http.createServer((request,response)=>{
 let pathname;
 try{pathname=decodeURIComponent(new URL(request.url,'http://preview.local').pathname);}catch{response.writeHead(400).end();return;}
 let file=path.resolve(root,'.'+pathname);
 if(file!==root&&!file.startsWith(root+path.sep)){response.writeHead(403).end();return;}
 if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,'index.html');
 if(!fs.existsSync(file)){
  if(pathname.startsWith('/portal/')&&!path.extname(pathname))file=path.join(root,'portal/open/index.html');
  else{response.writeHead(404).end('Static asset not found');return;}
 }
 response.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-cache'});
 fs.createReadStream(file).pipe(response);
}).listen(Number(process.env.PORT||4173),'127.0.0.1',()=>console.log('Static demo preview: http://127.0.0.1:'+(process.env.PORT||4173)));
