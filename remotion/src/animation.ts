export const smoothstep = (value:number) => {const v=Math.max(0,Math.min(1,value));return v*v*(3-2*v);};
// Ease both edges without crossing the midpoint even on very short words.
export const wordEnvelope = (time:number,start:number,end:number,duration=.08) => {
  const edge=Math.min(duration,(end-start)/2);
  return edge>0?smoothstep(Math.min((time-start)/edge,(end-time)/edge)):0;
};
export const entranceEnvelope = (time:number,start:number,end:number,duration=.15) => duration===0?1:smoothstep((time-start)/Math.min(duration,end-start));
