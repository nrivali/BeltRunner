/* Camera paths shared by the warp handoff, colony approach, and hangar cutscenes. */
(()=>{
  const T=THREE,V=T.Vector3,clamp=x=>Math.max(0,Math.min(1,x));
  const ease=x=>{x=clamp(x);return x*x*x*(x*(x*6-15)+10);};
  function capture(position,target,up,anchor,rotation){
    const shot={position:position.clone().sub(anchor),target:target.clone().sub(anchor),up:up.clone()};
    if(rotation){const inverse=rotation.clone().invert();shot.position.applyQuaternion(inverse);shot.target.applyQuaternion(inverse);shot.up.applyQuaternion(inverse);}
    return shot;
  }
  function orbit(out,from,to,k){
    const a=Math.atan2(from.z,from.x),b=Math.atan2(to.z,to.x),delta=Math.atan2(Math.sin(b-a),Math.cos(b-a));
    const radius=T.MathUtils.lerp(Math.hypot(from.x,from.z),Math.hypot(to.x,to.z),k),angle=a+delta*k;
    return out.set(Math.cos(angle)*radius,T.MathUtils.lerp(from.y,to.y,k),Math.sin(angle)*radius);
  }
  const endPosition=new V(),endTarget=new V(),follow=new V(),look=new V(0,6,0),pad=new V(190,56,0),worldUp=new V(0,1,0);
  function holding(position,target,ship,forward,side,time=0){
    position.copy(ship).addScaledVector(forward,-15500).addScaledVector(side,7000+Math.sin(time*.04)*3500).addScaledVector(worldUp,7000);
    target.copy(ship).addScaledVector(forward,22000).addScaledVector(worldUp,-11000);
  }
  function hub({start,progress,ship,forward,side,position,target,up}){
    const k=ease(progress);
    holding(endPosition,endTarget,ship,forward,side);endPosition.sub(ship);endTarget.sub(ship);
    // Move around the carrier at a safe radius, rather than cutting through its hull.
    orbit(position,start.position,endPosition,k).add(ship);
    target.copy(start.target).lerp(endTarget,k).add(ship);up.copy(start.up).lerp(worldUp,k).normalize();
  }
  function hangar({mode,side,time,duration,phase,settleTime=0,start,chasePosition,chaseTarget,position,target}){
    const k=ease(time/(mode==='dock'?2.6:1.25));
    follow.set(mode==='dock'?190:150,mode==='dock'?66:75,-side*320);
    orbit(position,start.position,follow,k);target.copy(start.target).lerp(look,ease(time/(mode==='dock'?.85:1.25)));
    if(mode==='depart'){
      const out=ease((time/duration-.55)/.45);position.lerp(chasePosition,out);target.lerp(chaseTarget,out);
    }else if(phase==='settle'){
      const land=ease((settleTime-.5)/2.5);position.lerp(pad,land);target.lerp(look,land);
    }
  }
  function cover(time,duration){return ease((time-duration+.35)/.35);}
  function uncover(time){return 1-ease(time/.5);}
  window.BeltRunnerCameraShots={ease,capture,orbit,holding,hub,hangar,cover,uncover};
})();
