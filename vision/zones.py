"""Persistent normalized polygons, shared by inference and the web editor."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import threading

ZONE_NAMES = ('waiting_left', 'crossing', 'waiting_right', 'approach')
GAETANO_NAMES = ('ATTESA 1', 'ATTRAVERSAMENTO', 'ATTESA 2', 'CORSIA AUTO')


class RevisionConflict(ValueError):
    pass


def area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))/2


def orientation(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def intersects(a, b, c, d):
    def on_segment(p, q, r):
        return abs(orientation(p, q, r)) < 1e-12 and all(min(p[i], q[i])-1e-12 <= r[i] <= max(p[i], q[i])+1e-12 for i in (0, 1))
    return (orientation(a,b,c)*orientation(a,b,d) < 0 and orientation(c,d,a)*orientation(c,d,b) < 0) or any((on_segment(a,b,c),on_segment(a,b,d),on_segment(c,d,a),on_segment(c,d,b)))


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {'zones', 'tolerance'}:
        raise ValueError('Configurazione zone non valida')
    zones = config['zones']
    if not isinstance(zones, dict) or set(zones) != set(ZONE_NAMES):
        raise ValueError('Servono le quattro zone: attesa sinistra/destra, attraversamento, veicoli')
    tolerance = config['tolerance']
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 <= tolerance <= .05:
        raise ValueError('Tolleranza non valida')
    for name, points in zones.items():
        if not isinstance(points, list) or not 3 <= len(points) <= 32:
            raise ValueError(f'{name}: servono da 3 a 32 vertici')
        for p in points:
            if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
                raise ValueError(f'{name}: coordinate normalizzate tra 0 e 1')
        if len(set(map(tuple, points))) != len(points) or abs(area(points)) < 1e-6:
            raise ValueError(f'{name}: poligono degenere')
        edges = list(zip(points, points[1:]+points[:1]))
        for i, (a,b) in enumerate(edges):
            for j in range(i+1, len(edges)):
                if j == i+1 or (i == 0 and j == len(edges)-1): continue
                if intersects(a,b,*edges[j]): raise ValueError(f'{name}: lati incrociati')
    return copy.deepcopy(config)


def default_config():
    raw = json.loads((Path(__file__).parent/'config'/'gaetano-zones.json').read_text())
    return validate_config({'zones':{name:[[x/raw['width'],y/raw['height']] for x,y in raw['zones'][old]] for name,old in zip(ZONE_NAMES,GAETANO_NAMES)},'tolerance':12/min(raw['width'],raw['height'])})


def signed_distance(point, polygon):
    """Equivalent to Gaetano's pointPolygonTest(..., measureDist=True)."""
    x,y = point
    inside, nearest = False, float('inf')
    for a,b in zip(polygon, polygon[1:]+polygon[:1]):
        dx,dy = b[0]-a[0],b[1]-a[1]
        t = max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
        nearest = min(nearest,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: inside = not inside
    return nearest if inside else -nearest


def classify_position(x, y, width, height, config):
    best, distance = 'outside', -float('inf')
    for name in ZONE_NAMES:
        polygon = [[px*width,py*height] for px,py in config['zones'][name]]
        current = signed_distance((x,y),polygon)
        if current >= -config['tolerance']*min(width,height) and current > distance:
            best,distance = name,current
    return best


class ZoneStore:
    def __init__(self, path):
        self.path, self.lock = Path(path), threading.Lock()
        self.revision, self.config = 0, default_config()
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self.config = validate_config(raw['config'])
            if type(raw['revision']) is not int or raw['revision'] < 0: raise ValueError('Revisione zone non valida')
            self.revision = raw['revision']

    def snapshot(self):
        with self.lock: return {'revision':self.revision,'config':copy.deepcopy(self.config)}

    def update(self, data):
        if not isinstance(data,dict) or set(data) != {'revision','config'} or type(data['revision']) is not int:
            raise ValueError('Inviare config e revision')
        config = validate_config(data['config'])
        with self.lock:
            if data['revision'] != self.revision: raise RevisionConflict('Zone modificate da un altro browser: ricaricare prima di salvare')
            result = {'revision':self.revision+1,'config':config}
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as file:
                    temporary = file.name
                    json.dump(result,file,allow_nan=False)
                os.replace(temporary,self.path)
            finally:
                if temporary and Path(temporary).exists(): Path(temporary).unlink()
            self.config,self.revision = config,result['revision']
            return copy.deepcopy(result)
