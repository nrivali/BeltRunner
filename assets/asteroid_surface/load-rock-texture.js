window.BeltRunnerRockSurface=(()=>{
  const status={state:'loading',error:null};let texture,veins;
  function apply(mat){
    if(!texture||!mat.userData.asteroidSurface)return;
    const previous=mat.onBeforeCompile,ore=mat.userData.asteroidOre;
    mat.map=texture;
    if(mat.isMeshStandardMaterial){mat.roughnessMap=null;mat.metalnessMap=null;mat.roughness=.92;mat.metalness=.025;mat.bumpMap=texture;mat.bumpScale=.35;mat.envMapIntensity=.4;}
    if(ore){mat.emissiveMap=veins;mat.emissiveIntensity=.12;}
    mat.onBeforeCompile=shader=>{
      previous(shader);
      Object.assign(shader.uniforms,{uRockVeins:{value:veins},uRockOre:{value:new THREE.Color(ore||0)},uRockHasOre:{value:ore?1:0}});
      shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vStoneP; varying vec3 vStoneN;').replace('#include <begin_vertex>','#include <begin_vertex>\nvStoneP=position; vStoneN=normal;');
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>',`#include <common>
varying vec3 vStoneP; varying vec3 vStoneN;
uniform sampler2D uRockVeins; uniform vec3 uRockOre; uniform float uRockHasOre;
vec3 stoneSample(sampler2D tex, vec3 p, vec3 w){return texture2D(tex,p.yz+vec2(.31,.19)).rgb*w.x+texture2D(tex,p.zx+vec2(.59,.73)).rgb*w.y+texture2D(tex,p.xy+vec2(.17,.43)).rgb*w.z;}
`).replace('#include <map_fragment>',`
vec3 stoneW=pow(abs(normalize(vStoneN)),vec3(4.0));stoneW/=max(dot(stoneW,vec3(1.0)),0.0001);
vec3 stoneP=vStoneP/120.0;
vec3 stoneColor=stoneSample(map,stoneP,stoneW);
float stoneHeight=dot(stoneColor,vec3(.2126,.7152,.0722));
float stoneVein=0.0;
if(uRockHasOre>.5)stoneVein=smoothstep(.38,.95,stoneSample(uRockVeins,stoneP*.6,stoneW).r);
diffuseColor.rgb=mix(diffuseColor.rgb*stoneColor*1.85,(uRockOre*.12+stoneColor*.15),stoneVein*.28);
`).replace('#include <emissivemap_fragment>','totalEmissiveRadiance *= stoneVein * .08;');
      if(mat.isMeshStandardMaterial)shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`normal=perturbNormalArb(-vViewPosition,normal,vec2(dFdx(stoneHeight),dFdy(stoneHeight))*bumpScale,faceDirection);`);
    };
    mat.customProgramCacheKey=()=>'heat-stone-triplanar-v1';mat.needsUpdate=true;
  }
  async function load({renderer,baseMaterials,oreMaterials,ores,veinMask,veinSize,asteroids,heatable}){
    try{
      let url=new URL('assets/asteroid_surface/asteroid_albedo.png',document.baseURI).href;
      if(location.protocol==='file:'){
        await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=new URL('assets/asteroid_surface/asteroid_surface.data.js',document.baseURI);s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(new Error('Rock texture data unavailable'));};document.head.append(s);});url=window.BeltRunnerRockData;delete window.BeltRunnerRockData;
      }
      const loaded=await new THREE.TextureLoader().loadAsync(url);loaded.colorSpace=THREE.SRGBColorSpace;loaded.wrapS=loaded.wrapT=THREE.RepeatWrapping;loaded.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());loaded.name='ImageGen asteroid stone';
      const cv=document.createElement('canvas');cv.width=cv.height=veinSize;const ctx=cv.getContext('2d'),img=ctx.createImageData(veinSize,veinSize);
      for(let i=0;i<veinMask.length;i++){const v=Math.round(veinMask[i]*255);img.data.set([v,v,v,255],i*4);}ctx.putImageData(img,0,0);
      veins=new THREE.CanvasTexture(cv);veins.wrapS=veins.wrapT=THREE.MirroredRepeatWrapping;veins.name='Ore veins without spot flecks';texture=loaded;
      for(const mat of baseMaterials){mat.userData.asteroidSurface=true;heatable(mat);}
      for(const [key,set] of Object.entries(oreMaterials))for(const mat of Object.values(set)){mat.userData.asteroidSurface=true;mat.userData.asteroidOre=ores[key].hex;heatable(mat);}
      for(const rock of asteroids())if(rock.hotMat){rock.hotMat.userData.asteroidSurface=true;if(!rock.barren)rock.hotMat.userData.asteroidOre=ores[rock.ore].hex;heatable(rock.hotMat);}
      Object.assign(status,{state:'ready',width:loaded.image.width,height:loaded.image.height});
    }catch(error){status.state='fallback';status.error=error.message||'Rock image failed to load';console.warn('Keeping procedural asteroid textures.',error);}
  }
  return {status,apply,load};
})();
