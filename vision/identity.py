"""Conservative motion association across short ByteTrack ID interruptions.

IDs are monotonic within a stream. Matching uses predicted image position and
box size, never a guessed identity/category of a person. Ambiguous new matches
are left as new tracks, so incomplete trajectories do not inflate counts.
"""
import math


def deduplicate_users(detections):
    """A person strongly overlapping a bicycle is one crossing participant.

    Retain the person detection; a bicycle without a person remains detectable.
    This prevents COCO person+bicycle boxes on one rider/assistive sprite from
    creating two completed crossings. No accessibility category is inferred.
    """
    people=[d for d in detections if d['class']=='pedestrian']
    result=[]
    for d in detections:
        duplicate=False
        if d['class']=='bicycle':
            ax,ay,bx,by=d['bbox']
            for p in people:
                cx,cy,dx,dy=p['bbox']
                intersection=max(0,min(bx,dx)-max(ax,cx))*max(0,min(by,dy)-max(ay,cy))
                smaller=min((bx-ax)*(by-ay),(dx-cx)*(dy-cy))
                if smaller>0 and intersection/smaller>=.65:
                    duplicate=True;break
        if not duplicate:result.append(d)
    return result


class IdentityTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.tracks = {}
        self.sequence = 0

    def update(self, detections, seconds, width, height):
        self.tracks = {key:t for key,t in self.tracks.items() if seconds-t['time'] <= 1.5}
        points=[]
        for d in detections:
            x1,y1,x2,y2=d['bbox']
            points.append(((x1+x2)/2/width,(y1+y2)/2/height,(x2-x1)/width,(y2-y1)/height))
        candidates=[]
        for i,d in enumerate(detections):
            if d['id'] is None:continue
            x,y,w,h=points[i]
            options=[]
            for key,t in self.tracks.items():
                if t['kind']!=d['class']:continue
                dt=max(0,seconds-t['time'])
                px,py=t['x']+t['vx']*dt,t['y']+t['vy']*dt
                distance=math.hypot(x-px,y-py)
                same_raw=d['id']==t['raw'] and dt<.2
                # At low resolution partial boxes can jump while ByteTrack
                # keeps the same trajectory. Trust that short association
                # within a bounded gate; teleports still start a new identity.
                gate=.12 if same_raw else min(.12,.035+.055*dt)
                if distance>gate:continue
                cost=distance+.15*(abs(w-t['w'])+abs(h-t['h']))
                if same_raw:cost=max(0,cost-.04)
                options.append((cost,key))
            options.sort()
            if options and (len(options)==1 or options[1][0]-options[0][0]>.004 or self.tracks[options[0][1]]['raw']==d['id']):
                candidates.append((options[0][0],i,options[0][1]))
        matches={};used=set()
        for _,i,key in sorted(candidates):
            if i not in matches and key not in used:matches[i]=key;used.add(key)
        for i,d in enumerate(detections):
            if d['id'] is None:continue
            raw=d['id'];x,y,w,h=points[i]
            key=matches.get(i)
            if key is None:
                self.sequence+=1;key=self.sequence
                vx=vy=0.
            else:
                previous=self.tracks[key];dt=seconds-previous['time']
                vx,vy=previous['vx'],previous['vy']
                if dt>0:
                    vx=.6*vx+.4*(x-previous['x'])/dt
                    vy=.6*vy+.4*(y-previous['y'])/dt
            self.tracks[key]=dict(raw=raw,kind=d['class'],time=seconds,x=x,y=y,w=w,h=h,vx=vx,vy=vy)
            d['tracker_id']=raw;d['id']=key
        return detections
