import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6 import QtWidgets, QtCore
from lsa_app import App, self_test
from lsa_data import Trace

class Gui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):self.app=App()
    def tearDown(self):self.app.close()
    def test_embedded_plot_cutoff_statistics_and_roi_filter(self):
        traces=[]
        for roi in [378,380]:
            for reagent,cycle,time,response in [('Buffer 5',5,[0,1],[20,19]),('OSMR',11,[2,3],[15,14]),('OSMR',17,[12449,12450,12451],[9,8,-140])]:
                traces.append(Trace('Sheet1','Sample',roi,cycle,reagent,time,response))
        self.app.loaded('test.xlsx',(traces,[]))
        self.qt.processEvents()
        self.assertEqual(len(self.app.plot.listDataItems()),2)
        self.app.plot.setXRange(1, 3, padding=0)
        self.assertEqual(self.app.plot.viewRange()[0], [1, 3])
        self.app.reset_view()
        self.assertEqual(max(t for trace in self.app.displayed for t in trace.time),12450)
        self.assertEqual(self.app.table.rowCount(),2)
        self.assertEqual(self.app.statistics[0]['drop_first'],5)
        self.assertEqual(self.app.statistics[0]['drop_last'],11)
        # Hiding cycles changes the graph, not the measurement definition.
        self.app.cycle_box.clearSelection()
        self.app.cycle_box.item(0).setSelected(True)
        self.assertEqual(len(self.app.displayed),2)
        self.assertEqual(self.app.statistics[0]['drop_last'],11)
        self.app.roi_box.clearSelection()
        self.app.roi_box.item(0).setSelected(True)
        self.assertEqual(self.app.table.rowCount(),1)
        self.app.cut_enabled.setChecked(False)
        self.assertEqual(max(t for trace in self.app.displayed for t in trace.time),12451)
    def test_offline_selftest(self):self_test(self.app)

if __name__=='__main__':unittest.main()
