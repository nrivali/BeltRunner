/* Reusable hyperspace visuals: two draw calls, fixed buffers, no downloaded textures. */
(()=>{
  const clamp=x=>Math.max(0,Math.min(1,x));
  const ease=x=>{x=clamp(x);return x*x*(3-2*x);};
  const timing={charge:1.6,launch:.45,transit:2.45,arrival:1.15,settle:.6};
  const transitAt=timing.charge+timing.launch,arrivalAt=transitAt+timing.transit,duration=arrivalAt+timing.arrival+timing.settle;
  function sample(time){
    const t=Math.max(0,time),charge=clamp(t/timing.charge),launch=clamp((t-timing.charge)/timing.launch),arrival=clamp((t-arrivalAt)/timing.arrival);
    const phase=t<transitAt?'depart':t<arrivalAt?'transit':t<duration?'arrive':'done';
    const leaving=phase==='depart',inTransit=phase==='transit',arriving=phase==='arrive';
    const snap=clamp((t-arrivalAt)/.42);
    return {phase,charge,launch,arrival,done:t>=duration,
      offset:leaving?110000*launch**3:arriving?-85000*(1-snap)**5:0,
      stretch:leaving?1+2.8*ease(launch/.45)*(1-ease((launch-.8)/.2)):arriving?1+2.6*(1-snap)**3:1,
      engineGain:leaving?1+3*charge+2*launch:inTransit?4:arriving?1+3*(1-arrival):1,
      coverage:leaving?ease((launch-.48)/.52):inTransit?1:arriving?1-ease((t-arrivalAt)/.24):0,
      trails:leaving?ease((t-timing.charge+.18)/.3):inTransit?1:arriving?1-ease((t-arrivalAt)/.65):0,
      trailLength:leaving?.06+1.8*ease(launch):inTransit?2.6:arriving?.08+2.5*(1-arrival):0,
      flash:leaving?Math.sin(Math.PI*clamp((launch-.25)/.75))*.48:arriving?Math.sin(Math.PI*clamp((t-arrivalAt)/.32))*.24:0,
      fov:leaving?56-5*ease(charge)+18*ease(launch):inTransit?69:arriving?62+7*(1-ease(arrival)):62,
      arrivalAt,duration
    };
  }
  window.BeltRunnerHyperspace={sample,timing,transitAt,arrivalAt,duration};
  window.createBeltRunnerHyperspace=function({scene,renderer}){
    const T=THREE,root=new T.Group();root.name='hyperspace_fx';root.visible=false;scene.add(root);
    const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false;
    const uniforms={uTime:{value:0},uCoverage:{value:0},uFlash:{value:0},uAspect:{value:1},uTrails:{value:0},uLength:{value:0},uCenter:{value:new T.Vector2()},uResolution:{value:new T.Vector2(1,1)}};
    const tunnel=new T.Mesh(new T.PlaneGeometry(2,2),new T.ShaderMaterial({
      uniforms,transparent:true,depthTest:false,depthWrite:false,toneMapped:false,
      vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}',
      fragmentShader:`varying vec2 vUv;uniform float uTime,uCoverage,uFlash,uAspect;
float hash(vec3 p){p=fract(p*.3183099+vec3(.13,.37,.73));p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){return .57*noise(p)+.28*noise(p*2.03+8.7)+.15*noise(p*4.07+3.1);}
void main(){
 vec2 p=(vUv-.5)*vec2(uAspect,1.0);float r=length(p),a=atan(p.y,p.x),depth=1.0/(r+.075);
 float twist=a+.10*depth-.12*uTime;
 vec3 q=vec3(cos(twist)*3.0,sin(twist)*3.0,depth*1.15-uTime*2.5);
 float cloud=fbm(q),filament=pow(max(0.0,fbm(q*1.8+4.0)-.36),2.0)*3.0;
 float walls=smoothstep(.055,.38,r),haze=exp(-r*9.0);
 vec3 color=vec3(.004,.014,.042)+vec3(.025,.22,.55)*cloud*walls+vec3(.23,.52,.75)*filament*walls;
 color+=vec3(.12,.25,.34)*haze;color*=1.0-.48*smoothstep(.35,1.0,r);
 float alpha=max(uCoverage,uFlash*.72);color=mix(color,vec3(.65,.85,1.0),uFlash);
 gl_FragColor=vec4(color,alpha);
}`
    }));tunnel.name='hyperspace_tunnel';tunnel.frustumCulled=false;tunnel.renderOrder=9000;root.add(tunnel);
    // Camera-space star ribbons have actual depth and length, rather than a rotating radial texture.
    const count=640,positions=new Float32Array(count*18),rays=new Float32Array(count*24),corners=new Float32Array(count*12);
    let seed=23191;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    const quad=[[1,0],[-1,0],[-1,1],[1,0],[-1,1],[1,1]];
    for(let i=0;i<count;i++){const angle=random()*Math.PI*2,radius=140+Math.sqrt(random())*4000,phase=random(),speed=.65+random()*.65;
      for(let j=0;j<6;j++){const k=i*6+j;rays.set([Math.cos(angle)*radius,Math.sin(angle)*radius,phase,speed],k*4);corners.set(quad[j],k*2);}}
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(positions,3));geometry.setAttribute('aRay',new T.BufferAttribute(rays,4));geometry.setAttribute('aCorner',new T.BufferAttribute(corners,2));
    const streaks=new T.Mesh(geometry,new T.ShaderMaterial({uniforms,transparent:true,depthTest:false,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false,
      vertexShader:`attribute vec4 aRay;attribute vec2 aCorner;uniform float uTime,uTrails,uLength,uAspect;uniform vec2 uCenter,uResolution;varying vec2 vRibbon;varying float vFade;
void main(){
 float progress=fract(aRay.z+uTime*aRay.w*.85),z=5200.0-progress*5000.0;
 float tailZ=z+50.0+uLength*1050.0;vec2 head=aRay.xy/z,tail=aRay.xy/tailZ;
 head.x/=uAspect;tail.x/=uAspect;head+=uCenter;tail+=uCenter;
 vec2 d=normalize((head-tail)*uResolution+vec2(.00001));vec2 perpendicular=vec2(-d.y,d.x);
 vec2 p=mix(tail,head,aCorner.y)+perpendicular*aCorner.x*(1.2+aRay.w*.7)/uResolution;
 gl_Position=vec4(p,0.0,1.0);vRibbon=aCorner;vFade=uTrails*smoothstep(0.0,.08,progress)*(1.0-smoothstep(.92,1.0,progress));
}`,
      fragmentShader:`varying vec2 vRibbon;varying float vFade;void main(){float edge=1.0-smoothstep(.15,1.0,abs(vRibbon.x));float head=.16+.84*pow(vRibbon.y,1.8);vec3 color=mix(vec3(.12,.4,.85),vec3(.86,.96,1.0),vRibbon.y);gl_FragColor=vec4(color,edge*head*vFade);}`
    }));streaks.name='hyperspace_star_streaks';streaks.frustumCulled=false;streaks.renderOrder=9001;root.add(streaks);
    const point=new T.Vector3(),status={active:false,phase:'idle',drawCalls:2,stars:count,reducedMotion:reduced};
    function update({pose,time,camera,nose,quality='balanced'}){
      root.visible=true;status.active=true;status.phase=pose.phase;
      uniforms.uTime.value=time*(reduced?.15:1);uniforms.uCoverage.value=pose.coverage;uniforms.uFlash.value=reduced?0:pose.flash;
      uniforms.uTrails.value=pose.trails*(reduced?.25:1);uniforms.uLength.value=pose.trailLength*(reduced?.3:1);uniforms.uAspect.value=camera.aspect;
      renderer.getDrawingBufferSize(uniforms.uResolution.value);
      camera.updateMatrixWorld(true);point.copy(camera.position).addScaledVector(nose,200000).project(camera);
      const blend=pose.coverage;uniforms.uCenter.value.set(T.MathUtils.clamp(point.x,-1.5,1.5)*(1-blend),T.MathUtils.clamp(point.y,-1.5,1.5)*(1-blend));
      geometry.setDrawRange(0,(quality==='low'?256:count)*6);status.stars=quality==='low'?256:count;
    }
    function reset(){root.visible=false;status.active=false;status.phase='idle';uniforms.uCoverage.value=uniforms.uFlash.value=uniforms.uTrails.value=0;}
    return {root,status,reducedMotion:reduced,update,reset,dispose(){reset();scene.remove(root);tunnel.geometry.dispose();tunnel.material.dispose();geometry.dispose();streaks.material.dispose();}};
  };
})();
