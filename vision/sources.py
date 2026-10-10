"""Only local MP4s in the configured catalog may be selected by the browser."""
import json
import os
from pathlib import Path
import tempfile


class VideoCatalog:
    def __init__(self, directory, selection_file=None):
        self.directory=Path(directory).resolve() if directory else None
        self.selection_file=Path(selection_file) if selection_file else None

    def files(self):
        if self.directory is None: return {}
        return {p.relative_to(self.directory).as_posix():p for p in sorted(self.directory.rglob('*.mp4'))
                if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(self.directory)}

    def initial(self, fallback):
        files=self.files()
        if self.selection_file and self.selection_file.exists():
            try:
                selected=json.loads(self.selection_file.read_text()).get('video')
                if selected in files: return files[selected]
            except (ValueError,TypeError,AttributeError): pass
        if fallback and Path(fallback).resolve() in files.values(): return Path(fallback)
        return next(iter(files.values()),fallback)

    def snapshot(self, current):
        files=self.files()
        selected=next((name for name,path in files.items() if current and path==Path(current).resolve()),None)
        return {'videos':[{'id':name,'label':name} for name in files],'selected_video':selected}

    def select(self, data):
        files=self.files()
        if not isinstance(data,dict) or set(data)!={'video'} or not isinstance(data['video'],str) or data['video'] not in files:
            raise ValueError('Scegliere un video disponibile nel catalogo')
        if self.selection_file:
            self.selection_file.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w',dir=self.selection_file.parent,delete=False) as f:
                temporary=Path(f.name)
                json.dump(data,f)
            try: os.replace(temporary,self.selection_file)
            finally: temporary.unlink(missing_ok=True)
        return files[data['video']]
