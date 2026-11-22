import math
import types
import unittest
from nuvem.continuous_tighten import graph_for,hook,apply_cuts

class ContinuousTightenTests(unittest.TestCase):
    def test_global_ranges_map_to_local_source_without_moving_cuts(self):
        graph=graph_for([(0,1),(2,3)],30,source_offset=25)
        self.assertIn('trim=start=5.000000:end=6.000000',graph)
        self.assertIn('atrim=start=7.000000:end=8.000000',graph)
        self.assertIn('concat=n=2:v=1:a=1',graph)
        self.assertIn('fps=30',graph)
        self.assertNotIn('file',graph)
    def test_invalid_ranges_never_start_renderer(self):
        for keeps in ([],[(0,1),(.5,2)],[(0,0)],[(0,math.inf)],[(0,61)],[(False,1)]):
            with self.assertRaises(ValueError):graph_for(keeps,0)
        with self.assertRaises(ValueError):graph_for([(0,1)],2,source_offset=3)
        with self.assertRaises(ValueError):graph_for([(0,1)],float('nan'))
    def test_native_hook_restored_on_success_and_failure(self):
        original=object();native=types.SimpleNamespace(apply_cuts=original)
        with hook(native):self.assertIs(native.apply_cuts,apply_cuts)
        self.assertIs(native.apply_cuts,original)
        with self.assertRaises(RuntimeError):
            with hook(native):raise RuntimeError('render failed')
        self.assertIs(native.apply_cuts,original)
