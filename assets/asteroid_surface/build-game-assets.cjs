const fs=require('node:fs'),path=require('node:path');
fs.writeFileSync(path.join(__dirname,'asteroid_surface.data.js'),'// ImageGen texture embedded for direct HTML play.\nwindow.BeltRunnerRockData="data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'asteroid_albedo.png')).toString('base64')+'";\n');
