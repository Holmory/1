import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@unittest.skipUnless(sys.platform=='win32','Desktop window smoke test requires Windows')
class WindowsGui(unittest.TestCase):
    def test_window_load_and_roi_cycle_filter(self):
        import tkinter as tk
        from lsa_app import App
        from lsa_data import Trace
        root=tk.Tk()
        root.withdraw()
        try:
            app=App(root)
            traces=[Trace('Sheet1','Sample',378,11,'OSMR',[0,1],[0,1]),Trace('Sheet1','Sample',380,11,'OSMR',[0,1],[0,2])]
            app.loaded('test.xlsx',(traces,[]))
            root.update()
            self.assertEqual(len(app.selected()),2)
            app.roi_box.selection_clear(0,'end')
            app.roi_box.selection_set(0)
            app.refresh_cycles()
            self.assertEqual(len(app.selected()),1)
            self.assertEqual(app.unit.get(),'original units')
        finally:root.destroy()
