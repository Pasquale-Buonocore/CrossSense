import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layout import LayoutStore, DEFAULTS


class LayoutTests(unittest.TestCase):
    def test_persistence_and_merge(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'layout.json';store=LayoutStore(path)
            self.assertEqual(store.snapshot()['positions'],DEFAULTS)
            store.update({'ped-left':{'x':25.51,'y':53.09}})
            store.update({'vehicles':{'x':59.42,'y':38.34}})
            other=LayoutStore(path).snapshot()
            self.assertEqual(other['positions']['ped-left']['x'],25.51)
            self.assertEqual(other['positions']['vehicles']['x'],59.42)
            self.assertEqual(other['revision'],2)

    def test_invalid_data_preserves_saved_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LayoutStore(Path(folder)/'layout.json');before=store.snapshot()
            for patch in ({},{'unknown':{'x':20,'y':30}},{'ped-left':{'x':False,'y':30}},{'ped-left':{'x':float('nan'),'y':30}},{'ped-left':{'x':20,'y':99}},{'ped-left':{'x':20}}):
                with self.assertRaises(ValueError):store.update(patch)
            self.assertEqual(store.snapshot(),before)

    def test_parallel_clients_preserve_other_signals(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'layout.json';store=LayoutStore(path)
            with ThreadPoolExecutor() as pool:
                futures=[pool.submit(store.update,{key:{'x':50+i,'y':50}}) for i,key in enumerate(DEFAULTS)]
                for future in futures:future.result()
            saved=LayoutStore(path).snapshot()
            self.assertEqual(saved['revision'],3)
            for i,key in enumerate(DEFAULTS):self.assertEqual(saved['positions'][key],{'x':50+i,'y':50})


if __name__=='__main__':unittest.main()
