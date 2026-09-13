// Shared triangle BVHs: visible Blender geometry is also the collision surface.
window.BeltRunnerRockBVH=(()=>{
 const V=THREE.Vector3;
 function build(geometry){
  const pos=geometry.attributes.position.array,index=geometry.index.array,triangles=[];
  for(let i=0;i<index.length;i+=3){const ids=[index[i]*3,index[i+1]*3,index[i+2]*3],min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const p of ids)for(let a=0;a<3;a++){min[a]=Math.min(min[a],pos[p+a]);max[a]=Math.max(max[a],pos[p+a]);}triangles.push({i,min,max});}
  function node(list){const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const t of list)for(let a=0;a<3;a++){min[a]=Math.min(min[a],t.min[a]);max[a]=Math.max(max[a],t.max[a]);}const n={min,max};if(list.length<=16)n.tris=list.map(t=>t.i);else{let axis=0;for(let a=1;a<3;a++)if(max[a]-min[a]>max[axis]-min[axis])axis=a;list.sort((a,b)=>(a.min[axis]+a.max[axis])-(b.min[axis]+b.max[axis]));const h=list.length>>1;n.left=node(list.slice(0,h));n.right=node(list.slice(h));}return n;}
  const root=node(triangles),a=new V(),b=new V(),c=new V(),hit=new V(),closest=new V(),triangle=new THREE.Triangle(),ray=new THREE.Ray();
  function vertices(i){a.fromArray(pos,index[i]*3);b.fromArray(pos,index[i+1]*3);c.fromArray(pos,index[i+2]*3);}
  function boxRay(n,o,d,limit){let lo=0,hi=limit;for(let k=0;k<3;k++){const x=o.getComponent(k),v=d.getComponent(k);if(Math.abs(v)<1e-12){if(x<n.min[k]||x>n.max[k])return false;}else{let p=(n.min[k]-x)/v,q=(n.max[k]-x)/v;if(p>q)[p,q]=[q,p];lo=Math.max(lo,p);hi=Math.min(hi,q);if(hi<lo)return false;}}return true;}
  function cast(origin,direction,limit=Infinity,all=false){ray.set(origin,direction);const stack=[root],hits=[];let best=limit,bestPoint=null;while(stack.length){const n=stack.pop();if(!boxRay(n,origin,direction,all?limit:best))continue;if(n.tris){for(const i of n.tris){vertices(i);if(ray.intersectTriangle(a,b,c,false,hit)){const distance=hit.distanceTo(origin);if(distance>1e-7&&distance<=limit){if(all)hits.push(distance);else if(distance<best){best=distance;bestPoint=hit.clone();}}}}}else stack.push(n.left,n.right);}
   if(all){hits.sort((a,b)=>a-b);let count=0,prev=-Infinity;for(const t of hits)if(t-prev>1e-5){count++;prev=t;}return count;}return bestPoint?{point:bestPoint,distance:best}:null;}
  function boxDistance(n,p){let d=0;for(let k=0;k<3;k++){const x=p.getComponent(k),delta=x<n.min[k]?n.min[k]-x:x>n.max[k]?x-n.max[k]:0;d+=delta*delta;}return d;}
  function nearest(p){let best=Infinity,result=null;const stack=[root];while(stack.length){const n=stack.pop();if(boxDistance(n,p)>best)continue;if(n.tris){for(const i of n.tris){vertices(i);triangle.set(a,b,c).closestPointToPoint(p,closest);const d=closest.distanceToSquared(p);if(d<best){best=d;result={point:closest.clone(),normal:triangle.getNormal(new V()),distance:Math.sqrt(d)};}}}else{const l=boxDistance(n.left,p),r=boxDistance(n.right,p);if(l<r)stack.push(n.right,n.left);else stack.push(n.left,n.right);}}return result;}
  const insideDirection=new V(1,.271,.419).normalize();
  function inside(p){for(let k=0;k<3;k++)if(p.getComponent(k)<root.min[k]||p.getComponent(k)>root.max[k])return false;return cast(p,insideDirection,Infinity,true)%2===1;}
  return {cast,nearest,inside,bounds:root};
 }
 return {build};
})();
