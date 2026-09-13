/* Conservative sphere contact for the exported curved pressure hull and three engine shrouds. */
(function(root){
  'use strict';
  function rawContact(p,radius,shape){
    const rows=shape.stations,first=rows[0],last=rows[rows.length-1],N=shape.exponent;
    let body=null;
    if(p.x>=first[0]-radius&&p.x<=last[0]+radius){
      const x=Math.max(first[0],Math.min(last[0],p.x));let a=first,b=rows[1];
      for(let i=0;i<rows.length-1;i++)if(x>=rows[i][0]&&x<=rows[i+1][0]){a=rows[i];b=rows[i+1];break;}
      const t=(x-a[0])/(b[0]-a[0]),w=a[1]+(b[1]-a[1])*t+radius,h=a[2]+(b[2]-a[2])*t+radius;
      const yy=Math.abs(p.y)/h,zz=Math.abs(p.z)/w,level=yy**N+zz**N;
      if(level<1){
        const s=level>1e-12?level**(-1/N):0;
        const y=s?p.y*s:h,z=s?p.z*s:0;
        const sideDistance=Math.hypot(y-p.y,z-p.z),capDistance=Math.min(p.x-first[0]+radius,last[0]+radius-p.x);
        if(capDistance<sideDistance){const sign=p.x<(first[0]+last[0])/2?-1:1;body={position:[sign<0?first[0]-radius:last[0]+radius,p.y,p.z],normal:[sign,0,0]};}
        else{
          const dy=(b[2]-a[2])/(b[0]-a[0]),dz=(b[1]-a[1])/(b[0]-a[0]);
          const gy=Math.abs(y)/h,gz=Math.abs(z)/w,n=[-(gy**N*dy/h+gz**N*dz/w),(Math.sign(y)||1)*gy**(N-1)/h,Math.sign(z)*gz**(N-1)/w],len=Math.hypot(...n);
          body={position:[p.x,y,z],normal:n.map(v=>v/len)};
        }
      }
    }
    // Closed envelope around the hot engine bank, including the faired outer cowls.
    for(const [x0,x1,cy,cz,r] of shape.engines){
      if(p.x<x0-radius||p.x>x1+radius)continue;
      const y=p.y-cy,z=p.z-cz,d=Math.hypot(y,z),allow=r+radius;
      if(d>=allow)continue;
      const side=allow-d,cap=Math.min(p.x-x0+radius,x1+radius-p.x);
      let candidate;
      if(cap<side){const sign=p.x<(x0+x1)/2?-1:1;candidate={position:[sign<0?x0-radius:x1+radius,p.y,p.z],normal:[sign,0,0]};}
      else {const ny=d?y/d:1,nz=d?z/d:0;candidate={position:[p.x,cy+ny*allow,cz+nz*allow],normal:[0,ny,nz]};}
      if(!body||Math.hypot(...candidate.position.map((v,i)=>v-[p.x,p.y,p.z][i]))>Math.hypot(...body.position.map((v,i)=>v-[p.x,p.y,p.z][i])))body=candidate;
    }
    return body;
  }
  function contact(p,radius,shape){
    const hit=rawContact(p,radius,shape);if(!hit)return null;
    const q={x:hit.position[0],y:hit.position[1],z:hit.position[2]};
    if(!rawContact(q,Math.max(0,radius-.001),shape))return hit;
    // At overlapping engine shoulders, project out of the entire union. Choosing
    // one bell's nearest wall alone can put the player inside the adjacent bell.
    const len=Math.hypot(p.y,p.z),ny=len?p.y/len:1,nz=len?p.z/len:0;
    let lo=0,hi=2048;
    const at=d=>({x:p.x,y:p.y+ny*d,z:p.z+nz*d});
    while(rawContact(at(hi),radius,shape))hi*=2;
    for(let i=0;i<28;i++){const mid=(lo+hi)/2;if(rawContact(at(mid),radius,shape))lo=mid;else hi=mid;}
    const outer=at(hi+.01),edge=rawContact(at(lo),radius,shape);
    return {position:[outer.x,outer.y,outer.z],normal:edge?.normal||[0,ny,nz]};
  }
  root.BeltRunnerCarrierHull={contact};
})(typeof window==='undefined'?globalThis:window);
