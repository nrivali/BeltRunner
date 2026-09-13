// Local game preview. Only game files and public asset folders are served.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=__dirname,folders=['assets','vendor','sfx'].map(p=>path.join(root,p)+path.sep),files=['index.html','belt-runner-3d.html'].map(p=>path.join(root,p));
const server=http.createServer((req,res)=>{
 let p;try{p=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400).end();return;}
 if(p==='/')p='/belt-runner-3d.html';const file=path.resolve(root,'.'+p);
 if(!files.includes(file)&&!folders.some(f=>file.startsWith(f))){res.writeHead(403).end();return;}
 fs.stat(file,(err,stat)=>{if(err||!stat.isFile()){res.writeHead(404).end();return;}
  const mime={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.glb':'model/gltf-binary','.mp3':'audio/mpeg','.wav':'audio/wav','.gz':'application/gzip'};
  res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.setHeader('Content-Length',stat.size);fs.createReadStream(file).pipe(res);
 });
});
server.listen(Number(process.argv[2]||0),'127.0.0.1',()=>console.log(`Belt Runner: http://127.0.0.1:${server.address().port}/belt-runner-3d.html`));
