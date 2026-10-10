"""Crossing events on replay time, separate from controller wall-clock timers.

Count only an observed waiting-side -> crossing -> opposite-side trajectory.
Lost IDs and tracks first seen on the crossing never imply a completion.
"""
from collections import deque


class CrossingEvents:
    def __init__(self):
        self.stream = None
        self.tracks = {}
        self.completed_ids = set()
        self.left_to_right = self.right_to_left = 0
        self.wait_total_ms = self.wait_count = 0
        self.events = deque(maxlen=100)
        self.serial = 0
        self.stopped = []
        self.waiting = {'waiting_left': 0, 'waiting_right': 0}

    def reset_tracks(self, stream):
        self.stream = stream
        self.tracks.clear()
        self.completed_ids.clear()
        self.stopped = []
        self.waiting = {'waiting_left': 0, 'waiting_right': 0}

    def update(self, stream, video_ms, detections, width, height, valid=True):
        if stream != self.stream:
            self.reset_tracks(stream)
        self.stopped = []
        self.waiting = {'waiting_left': 0, 'waiting_right': 0}
        if not valid:
            self.tracks.clear()
            return
        self.tracks = {i:t for i,t in self.tracks.items() if video_ms-t['seen'] <= 1500}
        for d in detections:
            if d['class'] not in ('pedestrian', 'bicycle') or d['id'] is None:
                continue
            key, zone = d['id'], d['zone']
            if key in self.completed_ids or len(self.completed_ids) >= 8192:
                continue
            x1,y1,x2,y2 = d['bbox']
            point = ((x1+x2)/2/width, y2/height)
            t = self.tracks.setdefault(key, dict(origin=None, crossed_before_wait=False, entered=False, seen=video_ms,
                arrived=video_ms, exit_since=None, anchor=point, stationary=video_ms))
            t['seen'] = video_ms
            if zone != 'crossing' or sum((a-b)**2 for a,b in zip(point,t['anchor'])) > .015**2:
                t['anchor'],t['stationary'] = point,video_ms
            elif video_ms-t['stationary'] >= 3000:
                self.stopped.append(key)
            if zone == 'crossing' and t['origin'] is None:
                t['crossed_before_wait'] = True
            if zone in self.waiting and t['origin'] is None and not t['crossed_before_wait']:
                t['origin'],t['arrived'] = zone,video_ms
            if zone == 'crossing' and t['origin'] and not t['entered']:
                t['entered'] = True
                self.wait_total_ms += video_ms-t['arrived']
                self.wait_count += 1
            opposite = 'waiting_right' if t['origin']=='waiting_left' else 'waiting_left'
            if t['entered'] and zone == opposite:
                if t['exit_since'] is None: t['exit_since'] = video_ms
                if video_ms-t['exit_since'] >= 150:
                    direction = 'left_to_right' if t['origin']=='waiting_left' else 'right_to_left'
                    setattr(self,direction,getattr(self,direction)+1)
                    self.completed_ids.add(key)
                    self.serial += 1
                    self.events.append(dict(id=self.serial, type='CROSSING_COMPLETED', stream=stream,
                        track_id=key, direction=direction, video_ms=video_ms, object_class=d['class']))
                    del self.tracks[key]
            else:
                t['exit_since'] = None
                # A return to the origin aborts the crossing; a later departure
                # must traverse the crossing again.
                if t['entered'] and zone == t['origin']:
                    t['entered'] = False
                    t['arrived'] = video_ms
            if d['class'] == 'pedestrian' and zone == t['origin'] and not t['entered']:
                self.waiting[zone] += 1

    def snapshot(self):
        return dict(completed=self.left_to_right+self.right_to_left,
                    left_to_right=self.left_to_right,right_to_left=self.right_to_left,
                    average_wait_ms=round(self.wait_total_ms/self.wait_count) if self.wait_count else None,
                    wait_samples=self.wait_count,time_basis='video',stopped_ids=list(self.stopped),
                    waiting=dict(self.waiting),
                    counting_available=len(self.completed_ids)<8192,events=list(self.events))
