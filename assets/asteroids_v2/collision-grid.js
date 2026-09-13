// Collision broad phase for mixed-size rocks. Each rock occupies one cell at a
// scale large enough for its conservative collision radius, including colossals.
(function(root, factory){
  if(typeof module==='object' && module.exports) module.exports=factory();
  else root.BeltRunnerCollisionGrid=factory();
})(typeof window==='undefined' ? globalThis : window, ()=>{
  class RockCollisionGrid {
    constructor(cellSize=1200){
      this.cellSize=cellSize;
      this.levels=new Map();
      this.entries=new Map();
      this.stats={queries:0, cells:0, candidates:0};
    }
    clear(){
      this.levels.clear(); this.entries.clear();
      this.stats.queries=this.stats.cells=this.stats.candidates=0;
    }
    radius(rock){ return rock.r*3+4; } // Same three-radius bound as rockPair, plus contact padding.
    rebuild(rocks){
      this.clear();
      for(const rock of rocks) this.update(rock);
    }
    update(rock){
      const radius=this.radius(rock);
      let size=this.cellSize;
      while(size<radius*2) size*=2;
      const x=Math.floor(rock.pos.x/size), y=Math.floor(rock.pos.y/size), z=Math.floor(rock.pos.z/size);
      let entry=this.entries.get(rock);
      if(entry && entry.level.size===size && entry.x===x && entry.y===y && entry.z===z){ entry.radius=radius; return; }
      if(entry){
        const bucket=entry.level.cells.get(entry.key);
        bucket.delete(entry);
        if(!bucket.size) entry.level.cells.delete(entry.key);
      }
      let level=this.levels.get(size);
      if(!level){ level={size, cells:new Map()}; this.levels.set(size,level); }
      const key=x+','+y+','+z;
      let bucket=level.cells.get(key);
      if(!bucket){ bucket=new Set(); level.cells.set(key,bucket); }
      if(!entry){ entry={rock}; this.entries.set(rock,entry); }
      Object.assign(entry,{level,key,x,y,z,radius}); bucket.add(entry);
    }
    query(pos, radius, out){
      out.length=0; this.stats.queries++;
      const visit=bucket=>{
        this.stats.cells++;
        if(!bucket) return;
        for(const entry of bucket){
          const p=entry.rock.pos, dx=p.x-pos.x, dy=p.y-pos.y, dz=p.z-pos.z, reach=radius+entry.radius;
          if(dx*dx+dy*dy+dz*dz<=reach*reach){ out.push(entry.rock); this.stats.candidates++; }
        }
      };
      for(const level of this.levels.values()){
        const size=level.size, reach=radius+size/2;
        const x0=Math.floor((pos.x-reach)/size), x1=Math.floor((pos.x+reach)/size);
        const y0=Math.floor((pos.y-reach)/size), y1=Math.floor((pos.y+reach)/size);
        const z0=Math.floor((pos.z-reach)/size), z1=Math.floor((pos.z+reach)/size);
        // A drifting colossal can span many fine cells. Visit occupied cells
        // directly when that costs less than looking up all the empty ones.
        if((x1-x0+1)*(y1-y0+1)*(z1-z0+1)>level.cells.size){
          for(const bucket of level.cells.values()){
            const entry=bucket.values().next().value;
            if(entry.x>=x0 && entry.x<=x1 && entry.y>=y0 && entry.y<=y1 && entry.z>=z0 && entry.z<=z1) visit(bucket);
          }
        } else {
          for(let x=x0;x<=x1;x++) for(let y=y0;y<=y1;y++) for(let z=z0;z<=z1;z++) visit(level.cells.get(x+','+y+','+z));
        }
      }
      return out;
    }
  }
  return RockCollisionGrid;
});
