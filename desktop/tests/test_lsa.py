import csv
from pathlib import Path
import sys
import tempfile
import unittest
import openpyxl
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lsa_data import load_excel, make_chart, export_csv

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'input.xlsx'
    def tearDown(self):
        self.temp.cleanup()
    def book(self, rows):
        workbook = openpyxl.Workbook()
        for row in rows: workbook.active.append(row)
        workbook.save(self.path)
    def label(self, cycle, kind, roi=378):
        return f'[U775Y049G0-92 ({roi}) - OSMR ({cycle})] {kind} values'
    def test_pairing_time_order_negative_values_and_boundaries(self):
        self.book([[self.label(12,'Time'),2,3], [self.label(11,'Ru'),1,-2], [self.label(12,'Ru'),-3,4], [self.label(11,'Time'),0,2]])
        traces, warnings = load_excel(self.path)
        self.assertEqual(warnings,[])
        self.assertEqual([t.cycle for t in traces],[11,12])
        self.assertEqual(traces[0].response,[1,-2])
        self.assertEqual(traces[1].time,[2,3])
        figure = make_chart(traces, Path(self.temp.name)/'chart.html')
        self.assertEqual(len(figure.data),2)
        self.assertFalse(figure.data[1].showlegend)
        html=(Path(self.temp.name)/'chart.html').read_text(encoding='utf-8')
        self.assertIn('plotly.js',html)
        self.assertNotIn('<script src=',html)
        path=Path(self.temp.name)/'out.csv';export_csv(traces,path)
        with path.open(encoding='utf-8-sig') as f: rows=list(csv.reader(f))
        self.assertEqual(len(rows),5)
    def test_padding_and_unknown_labels(self):
        self.book([['Header'],[self.label(11,'Time'),0,1,None],[self.label(11,'Ru'),2,3,None]])
        traces,warnings=load_excel(self.path)
        self.assertEqual(len(warnings),1)
        self.assertEqual(len(traces[0].time),2)
    def test_incomplete_or_invalid_pairs(self):
        cases=[[[self.label(11,'Time'),0,1]],
               [[self.label(11,'Time'),0,1],[self.label(11,'Ru'),2,None]],
               [[self.label(11,'Time'),1,0],[self.label(11,'Ru'),2,3]],
               [[self.label(11,'Time'),0,1],[self.label(11,'Time'),0,1],[self.label(11,'Ru'),2,3]],
               [[self.label(11,'Time'),0,1],[self.label(11,'Ru'),'bad',3]]]
        for rows in cases:
            with self.subTest(rows=rows):
                self.book(rows)
                with self.assertRaises(ValueError):load_excel(self.path)
    def test_reset_time_rejected(self):
        self.book([[self.label(11,'Time'),0,2],[self.label(11,'Ru'),2,3],[self.label(12,'Time'),0,1],[self.label(12,'Ru'),2,3]])
        with self.assertRaisesRegex(ValueError,'reset'):load_excel(self.path)
    def test_roi_and_sheet_kept_separate(self):
        self.book([[self.label(11,'Time',378),0,1],[self.label(11,'Ru',378),2,3],[self.label(11,'Time',380),0,1],[self.label(11,'Ru',380),4,5]])
        traces,_=load_excel(self.path)
        self.assertEqual({t.roi for t in traces},{378,380})
        figure=make_chart(traces,Path(self.temp.name)/'chart.html')
        self.assertTrue(all(t.showlegend for t in figure.data))

if __name__=='__main__':unittest.main()

class StatisticsTests(unittest.TestCase):
    def test_cutoff_inclusive_no_mutation_and_signed_drops(self):
        from lsa_data import Trace, trim_traces, signal_statistics
        traces=[Trace('S','A',1,5,'Buffer 5',[0,1],[10,9]),Trace('S','A',1,11,'OSMR',[2,3],[12,13]),Trace('S','A',1,17,'OSMR',[12449,12450,12451],[3,4,-140])]
        clipped=trim_traces(traces)
        self.assertEqual(clipped[-1].time,[12449,12450])
        self.assertEqual(traces[-1].time,[12449,12450,12451])
        stats=signal_statistics(clipped,'OSMR')[0]
        self.assertEqual(stats['drop_first'],-2)
        self.assertEqual(stats['drop_last'],7)
        self.assertEqual(trim_traces(traces,None),traces)
        self.assertEqual(trim_traces(traces,0)[0].time,[0])
    def test_missing_events_not_zero_and_rois_independent(self):
        from lsa_data import Trace, signal_statistics
        traces=[Trace('S','A',1,11,'OSMR',[2,3],[1,2]),Trace('S','A',2,5,'Blank',[0,1],[10,9])]
        stats=signal_statistics(traces,'OSMR')
        self.assertTrue(all(s['drop_first'] is None and s['drop_last'] is None for s in stats))
