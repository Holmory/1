"""Native, offline LSA chart and signal-drop viewer."""
import sys
import tempfile
from pathlib import Path
import numpy as np
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
from lsa_data import load_excel, make_chart, export_csv, is_blank, trim_traces, signal_statistics

class Loader(QtCore.QThread):
    done = QtCore.Signal(str, object)
    failed = QtCore.Signal(str)
    def __init__(self, path):
        super().__init__()
        self.path = path
    def run(self):
        try:
            self.done.emit(self.path, load_excel(self.path))
        except Exception as error:
            self.failed.emit(str(error))

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.traces = []
        self.displayed = []
        self.statistics = []
        self.worker = None
        self.setWindowTitle('LSA Data Viewer · 原始曲线与信号下降统计')
        self.resize(1350, 880)
        pg.setConfigOptions(antialias=True, background='w', foreground='#253c53')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)
        side = QtWidgets.QWidget()
        side.setMaximumWidth(310)
        controls = QtWidgets.QVBoxLayout(side)
        title = QtWidgets.QLabel('LSA Data Viewer')
        title.setStyleSheet('font-size:24px;font-weight:600;color:#177f86')
        controls.addWidget(title)
        self.open_button = QtWidgets.QPushButton('打开 Excel (.xlsx)')
        self.open_button.clicked.connect(self.open_file)
        controls.addWidget(self.open_button)
        self.file_label = QtWidgets.QLabel('尚未选择文件')
        self.file_label.setWordWrap(True)
        controls.addWidget(self.file_label)
        controls.addWidget(QtWidgets.QLabel('样品'))
        self.sample = QtWidgets.QComboBox()
        controls.addWidget(self.sample)
        controls.addWidget(QtWidgets.QLabel('ROI（Ctrl / Shift 多选）'))
        self.roi_box = QtWidgets.QListWidget()
        self.roi_box.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        controls.addWidget(self.roi_box)
        controls.addWidget(QtWidgets.QLabel('绘图 cycle（Ctrl / Shift 多选）'))
        self.cycle_box = QtWidgets.QListWidget()
        self.cycle_box.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        controls.addWidget(self.cycle_box)
        controls.addWidget(QtWidgets.QLabel('统计的分析物名称'))
        self.analyte = QtWidgets.QComboBox()
        controls.addWidget(self.analyte)
        self.cut_enabled = QtWidgets.QCheckBox('省略截止时间之后的数据（秒）')
        self.cut_enabled.setChecked(True)
        controls.addWidget(self.cut_enabled)
        self.cutoff = QtWidgets.QDoubleSpinBox()
        self.cutoff.setRange(0, 1e9)
        self.cutoff.setDecimals(2)
        self.cutoff.setValue(12450)
        controls.addWidget(self.cutoff)
        for text, action in [('恢复全图范围', self.reset_view), ('导出筛选后 CSV', self.save_csv), ('导出交互 HTML（可选）', self.save_html), ('保存图谱 PNG', self.save_png)]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(action)
            controls.addWidget(button)
        note = QtWidgets.QLabel('Blank 自动识别 Buffer / Blank。统计用 cycle 的第一个采集点，不做平滑或取绝对值。时间按秒处理。')
        note.setWordWrap(True)
        controls.addWidget(note)
        right = QtWidgets.QVBoxLayout()
        self.plot = pg.PlotWidget()
        self.plot.setLabel('bottom', 'Time', units='s')
        self.plot.setLabel('left', 'Response', units='RU')
        self.plot.getAxis('bottom').enableAutoSIPrefix(False)
        self.plot.getAxis('left').enableAutoSIPrefix(False)
        self.plot.showGrid(x=True, y=True, alpha=.15)
        self.legend = self.plot.addLegend()
        right.addWidget(self.plot, 1)
        self.hover = QtWidgets.QLabel('滚轮缩放 · 拖动平移 · 右键菜单 · 点击图例隐藏 / 显示 ROI')
        self.hover.setWordWrap(True)
        right.addWidget(self.hover)
        right.addWidget(QtWidgets.QLabel('信号下降 = 第一段 blank 起始 RU − 分析物起始 RU；正值为下降，负值为上升'))
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['ROI / 工作表', '第一 blank 起始', '第一分析物起始', '最后分析物起始', '下降至第一分析物 (RU)', '下降至最后分析物 (RU)'])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(160)
        self.table.setMaximumHeight(230)
        right.addWidget(self.table)
        note = QtWidgets.QLabel('统计使用当前样品、选中 ROI 和截止时间内的全部 cycle；绘图 cycle 筛选不改变统计。每个工作表 / ROI 独立计算。缺少 blank 或分析物时显示 N/A。')
        note.setWordWrap(True)
        right.addWidget(note)
        layout.addWidget(side)
        layout.addLayout(right, 1)
        self.sample.currentTextChanged.connect(self.refresh)
        self.roi_box.itemSelectionChanged.connect(self.refresh_cycles)
        self.cycle_box.itemSelectionChanged.connect(self.redraw)
        self.analyte.currentTextChanged.connect(self.redraw)
        self.cut_enabled.toggled.connect(self.redraw)
        self.cutoff.valueChanged.connect(self.redraw)
        self.proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=25, slot=self.mouse_moved)
        self.statusBar().showMessage('所有数据在本地处理，不上传。')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.statusBar().showMessage('文件仍在读取，请等待完成后关闭。')
        else:
            event.accept()

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, '打开 LSA 数据', '', 'Excel (*.xlsx)')
        if not path:
            return
        self.open_button.setEnabled(False)
        self.statusBar().showMessage('正在读取 Excel…')
        self.worker = Loader(path)
        self.worker.done.connect(self.loaded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(lambda: self.open_button.setEnabled(True))
        self.worker.start()

    def failed(self, message):
        self.statusBar().showMessage('导入失败，保留之前的数据。')
        QtWidgets.QMessageBox.critical(self, '导入失败', message)

    def loaded(self, path, result):
        self.traces, warnings = result
        self.file_label.setText(Path(path).name)
        self.sample.blockSignals(True)
        self.sample.clear()
        self.sample.addItems(sorted({t.sample for t in self.traces}))
        self.sample.blockSignals(False)
        self.refresh()
        if warnings:
            QtWidgets.QMessageBox.warning(self, '跳过无法识别的行', '\n'.join(warnings[:12]))

    def refresh(self, *args):
        matching = [t for t in self.traces if t.sample == self.sample.currentText()]
        self.roi_box.blockSignals(True)
        self.roi_box.clear()
        for roi in sorted({t.roi for t in matching}):
            self.roi_box.addItem(str(roi))
        self.roi_box.selectAll()
        self.roi_box.blockSignals(False)
        self.analyte.blockSignals(True)
        self.analyte.clear()
        self.analyte.addItems(sorted({t.reagent for t in matching if not is_blank(t.reagent)}))
        self.analyte.blockSignals(False)
        self.refresh_cycles()

    def selected_rois(self):
        return {int(item.text()) for item in self.roi_box.selectedItems()}

    def refresh_cycles(self, *args):
        matching = [t for t in self.traces if t.sample == self.sample.currentText() and t.roi in self.selected_rois()]
        self.cycle_box.blockSignals(True)
        self.cycle_box.clear()
        for cycle in sorted({t.cycle for t in matching}):
            names = ', '.join(sorted({t.reagent for t in matching if t.cycle == cycle}))
            item = QtWidgets.QListWidgetItem(f'{cycle} · {names}')
            item.setData(QtCore.Qt.UserRole, cycle)
            self.cycle_box.addItem(item)
        self.cycle_box.selectAll()
        self.cycle_box.blockSignals(False)
        self.redraw()

    def filtered(self):
        traces = [t for t in self.traces if t.sample == self.sample.currentText() and t.roi in self.selected_rois()]
        return trim_traces(traces, self.cutoff.value() if self.cut_enabled.isChecked() else None)

    def selected(self):
        cycles = {item.data(QtCore.Qt.UserRole) for item in self.cycle_box.selectedItems()}
        return [t for t in self.filtered() if t.cycle in cycles]

    def redraw(self, *args):
        self.displayed = self.selected()
        self.statistics = signal_statistics(self.filtered(), self.analyte.currentText())
        self.plot.clear()
        self.legend.clear()
        groups = sorted({(t.sheet, t.roi) for t in self.displayed})
        colors = ['#147d87', '#c47732', '#7163b6', '#3576bd', '#ae527b']
        for index, (sheet, roi) in enumerate(groups):
            entries = [t for t in self.displayed if (t.sheet, t.roi) == (sheet, roi)]
            x, y = [], []
            for trace in entries:
                x.extend(trace.time + [float('nan')])
                y.extend(trace.response + [float('nan')])
            pen = pg.mkPen(colors[index % len(colors)], width=1.2, style=QtCore.Qt.SolidLine if index % 2 == 0 else QtCore.Qt.DashLine)
            self.plot.plot(x, y, connect='finite', pen=pen, name=f'ROI {roi} · {sheet}')
        self.table.setRowCount(len(self.statistics))
        def start(trace):
            return f'cycle {trace.cycle}\n{trace.time[0]:.3f} s · {trace.response[0]:.6f} RU' if trace else 'N/A'
        for row, stat in enumerate(self.statistics):
            values = [f'{stat["roi"]} · {stat["sheet"]}', start(stat['blank']), start(stat['first']), start(stat['last'])]
            values.extend('N/A' if stat[k] is None else f'{stat[k]:.6f}' for k in ['drop_first', 'drop_last'])
            for column, value in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        self.table.resizeRowsToContents()
        self.reset_view()
        cutoff = f' ≤ {self.cutoff.value():g} s' if self.cut_enabled.isChecked() else '（未截断）'
        self.statusBar().showMessage(f'{len(self.displayed)} 条 cycle/ROI 曲线 · {sum(len(t.time) for t in self.displayed):,} 个显示点{cutoff} · 原始文件不变')

    def reset_view(self, *args):
        self.plot.enableAutoRange()
        self.plot.autoRange()

    def mouse_moved(self, event):
        pos = event[0]
        if not self.plot.sceneBoundingRect().contains(pos) or not self.displayed:
            return
        time = self.plot.plotItem.vb.mapSceneToView(pos).x()
        candidates = []
        for trace in self.displayed:
            if trace.time[0] <= time <= trace.time[-1]:
                i = int(np.searchsorted(trace.time, time))
                i = min(i, len(trace.time)-1)
                if i and abs(trace.time[i-1]-time) < abs(trace.time[i]-time):
                    i -= 1
                candidates.append(f'ROI {trace.roi}: {trace.response[i]:.5f} RU @ {trace.time[i]:.3f} s · cycle {trace.cycle} {trace.reagent}')
        self.hover.setText(' | '.join(candidates) if candidates else f'Time: {time:.3f} s（此处没有采集点）')

    def export(self, kind):
        traces = self.selected()
        if not traces:
            QtWidgets.QMessageBox.warning(self, '没有数据', '请选择样品、ROI 和 cycle。')
            return
        extension = {'csv':'CSV (*.csv)', 'html':'HTML (*.html)', 'png':'PNG (*.png)'}[kind]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, '保存', f'lsa-sensorgram.{kind}', extension)
        if not path:
            return
        try:
            if kind == 'csv':
                export_csv(traces, path)
            elif kind == 'html':
                make_chart(traces, path, 's')
            else:
                from pyqtgraph.exporters import ImageExporter
                ImageExporter(self.plot.plotItem).export(path)
            self.statusBar().showMessage(f'已保存：{path}')
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, '导出失败', str(error))
    def save_csv(self): self.export('csv')
    def save_html(self): self.export('html')
    def save_png(self): self.export('png')


def self_test(app):
    import openpyxl
    with tempfile.TemporaryDirectory(prefix='lsa-selftest-') as directory:
        directory = Path(directory)
        workbook = openpyxl.Workbook()
        for reagent, cycle, times, responses in [('Buffer 5',5,[0,1],[20,19]), ('OSMR',11,[2,3],[15,14]), ('OSMR',17,[12449,12450,12451],[9,8,-140])]:
            for kind, values in [('Time',times), ('Ru',responses)]:
                workbook.active.append([f'[Synthetic (1) - {reagent} ({cycle})] {kind} values', *values])
        source = directory/'synthetic.xlsx'
        workbook.save(source)
        app.loaded(str(source), load_excel(source))
        app.show()
        QtWidgets.QApplication.processEvents()
        assert len(app.displayed) == 3
        assert max(t for trace in app.displayed for t in trace.time) == 12450
        assert app.statistics[0]['drop_first'] == 5
        assert app.statistics[0]['drop_last'] == 11
        assert len(app.plot.listDataItems()) == 1
        from pyqtgraph.exporters import ImageExporter
        ImageExporter(app.plot.plotItem).export(str(directory/'chart.png'))
        assert (directory/'chart.png').stat().st_size > 1000
        make_chart(app.displayed, directory/'chart.html')
        export_csv(app.displayed, directory/'data.csv')
        assert (directory/'chart.html').stat().st_size > 1000000
        assert (directory/'data.csv').is_file()

if __name__ == '__main__':
    qt = QtWidgets.QApplication(sys.argv)
    app = App()
    if '--self-test' in sys.argv:
        try:
            self_test(app)
        except Exception:
            import traceback
            Path(tempfile.gettempdir(), 'lsa-selftest-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
    else:
        app.show()
        sys.exit(qt.exec())
