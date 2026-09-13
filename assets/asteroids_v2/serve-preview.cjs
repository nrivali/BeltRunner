const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const project=path.resolve(__dirname,'../..');
const allowed=[__dirname,path.join(project,'vendor/three-r158')];
const server=http.createServer((req,res)=>{
 let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400).end();return;}
 if(pathname==='/'){res.writeHead(302,{Location:'/assets/asteroids_v2/preview.html'}).end();return;}
 const file=path.resolve(project,'.'+pathname);
 if(!allowed.some(dir=>file.startsWith(dir+path.sep))){res.writeHead(403).end();return;}
 const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png','.glb':'model/gltf-binary','.md':'text/plain'};
 fs.stat(file,(err,stat)=>{if(err||!stat.isFile()){res.writeHead(404).end();return;}res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.setHeader('Content-Length',stat.size);fs.createReadStream(file).pipe(res);});
});
server.listen(Number(process.argv[2]||0),'127.0.0.1',()=>console.log(`Asteroid preview: http://127.0.0.1:${server.address().port}/assets/asteroids_v2/preview.html`));
