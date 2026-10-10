"""Persistent shared overlay layout; atomic writes and serialized updates."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import threading

DEFAULTS = {'ped-left':{'x':20,'y':66},'ped-right':{'x':81,'y':65},'vehicles':{'x':57,'y':30}}


def validate_positions(positions):
    if not isinstance(positions,dict) or not positions or not set(positions) <= set(DEFAULTS):
        raise ValueError('Semafori non validi')
    for position in positions.values():
        if not isinstance(position,dict) or set(position) != {'x','y'}:
            raise ValueError('Coordinate non valide')
        for key,low,high in (('x',5,95),('y',12,88)):
            value=position[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError('Coordinate fuori intervallo')
    return copy.deepcopy(positions)


class LayoutStore:
    def __init__(self,path):
        self.path=Path(path)
        self.lock=threading.Lock()
        self.positions=copy.deepcopy(DEFAULTS)
        self.revision=0
        if self.path.exists():
            saved=json.loads(self.path.read_text())
            positions=validate_positions(saved['positions'])
            if set(positions) != set(DEFAULTS): raise ValueError('Layout salvato incompleto')
            self.positions=positions
            self.revision=saved['revision']
            if type(self.revision) is not int or self.revision < 0: raise ValueError('Revisione non valida')

    def snapshot(self):
        with self.lock:
            return {'positions':copy.deepcopy(self.positions),'revision':self.revision}

    def update(self,positions):
        patch=validate_positions(positions)
        with self.lock:
            merged=copy.deepcopy(self.positions)
            merged.update(patch)
            saved={'positions':merged,'revision':self.revision+1}
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=None
            try:
                with tempfile.NamedTemporaryFile('w',dir=self.path.parent,delete=False) as output:
                    temporary=output.name
                    json.dump(saved,output,allow_nan=False)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary,self.path)
            finally:
                if temporary and os.path.exists(temporary): os.unlink(temporary)
            self.positions=merged
            self.revision=saved['revision']
            return copy.deepcopy(saved)
