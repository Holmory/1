"""Offline desktop importer; the default browser displays self-contained charts."""
import sys
from pathlib import Path
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from lsa_data import load_excel, make_chart, export_csv

class App:
    def __init__(self, root):
        self.root = root
        self.traces = []
        self.rois = []
        self.cycles = []
        root.title('LSA Data Viewer')
        root.geometry('820x620')
        root.minsize(680, 520)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='LSA Data Viewer', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Local Excel import · interactive offline charts', foreground='#547083').pack(anchor='w', pady=(4, 18))
        self.open_button = ttk.Button(frame, text='Open Excel (.xlsx)', command=self.open_file)
        self.open_button.pack(anchor='w')
        self.file_label = ttk.Label(frame, text='No file selected', wraplength=720)
        self.file_label.pack(anchor='w', pady=10)
        ttk.Label(frame, text='Sample').pack(anchor='w')
        self.sample = ttk.Combobox(frame, state='readonly')
        self.sample.pack(fill='x', pady=(4, 12))
        self.sample.bind('<<ComboboxSelected>>', self.refresh)
        selections = ttk.Frame(frame)
        selections.pack(fill='both', expand=True)
        for col, title in enumerate(['ROI (Ctrl/Shift for multiple)', 'Cycle (Ctrl/Shift for multiple)']):
            block = ttk.Frame(selections)
            block.grid(row=0, column=col, sticky='nsew', padx=(0, 12))
            ttk.Label(block, text=title).pack(anchor='w')
            box = tk.Listbox(block, selectmode='extended', exportselection=False, height=9)
            box.pack(fill='both', expand=True, pady=6)
            if col == 0:
                self.roi_box = box
                box.bind('<<ListboxSelect>>', self.refresh_cycles)
            else:
                self.cycle_box = box
        selections.columnconfigure(0, weight=1)
        selections.columnconfigure(1, weight=1)
        selections.rowconfigure(0, weight=1)
        options = ttk.Frame(frame)
        options.pack(fill='x', pady=12)
        ttk.Label(options, text='Time unit (label only):').pack(side='left')
        self.unit = ttk.Combobox(options, values=['original units', 's', 'min'], state='readonly', width=18)
        self.unit.set('original units')
        self.unit.pack(side='left', padx=8)
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Open interactive chart', command=self.view).pack(side='left', padx=(0, 8))
        ttk.Button(buttons, text='Save HTML', command=self.save_html).pack(side='left', padx=(0, 8))
        ttk.Button(buttons, text='Export selected CSV', command=self.save_csv).pack(side='left')
        self.status = ttk.Label(frame, text='No smoothing or baseline correction. Original negative values retained.', wraplength=720)
        self.status.pack(anchor='w', pady=(16, 0))

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[('Excel workbook', '*.xlsx')])
        if not path:
            return
        self.open_button.config(state='disabled')
        self.status.config(text='Reading workbook…')
        def read():
            try:
                result = load_excel(path)
                self.root.after(0, lambda: self.loaded(path, result))
            except Exception as error:
                message = str(error)
                self.root.after(0, lambda: self.failed(message))
        threading.Thread(target=read, daemon=True).start()

    def failed(self, message):
        self.open_button.config(state='normal')
        self.status.config(text='Import failed; previous valid dataset remains available.')
        messagebox.showerror('Import failed', message)

    def loaded(self, path, result):
        self.traces, warnings = result
        self.open_button.config(state='normal')
        self.file_label.config(text=Path(path).name)
        self.sample['values'] = sorted({t.sample for t in self.traces})
        self.sample.current(0)
        self.refresh()
        self.status.config(text=f'{len(self.traces)} cycle/ROI traces · {sum(len(t.time) for t in self.traces):,} points · {len(warnings)} skipped labels')
        if warnings:
            messagebox.showwarning('Import warnings', '\n'.join(warnings[:12]) + ('\n…' if len(warnings) > 12 else ''))

    def refresh(self, event=None):
        self.rois = sorted({t.roi for t in self.traces if t.sample == self.sample.get()})
        self.roi_box.delete(0, 'end')
        for roi in self.rois:
            self.roi_box.insert('end', str(roi))
        self.roi_box.selection_set(0, 'end')
        self.refresh_cycles()

    def refresh_cycles(self, event=None):
        rois = {self.rois[i] for i in self.roi_box.curselection()}
        matching = [t for t in self.traces if t.sample == self.sample.get() and t.roi in rois]
        self.cycles = sorted({t.cycle for t in matching})
        self.cycle_box.delete(0, 'end')
        for cycle in self.cycles:
            reagents = sorted({t.reagent for t in matching if t.cycle == cycle})
            self.cycle_box.insert('end', f'{cycle} · {", ".join(reagents)}')
        self.cycle_box.selection_set(0, 'end')

    def selected(self):
        rois = {self.rois[i] for i in self.roi_box.curselection()}
        cycles = {self.cycles[i] for i in self.cycle_box.curselection()}
        traces = [t for t in self.traces if t.sample == self.sample.get() and t.roi in rois and t.cycle in cycles]
        if not traces:
            raise ValueError('Open Excel and select at least one ROI and cycle.')
        return traces

    def action(self, operation):
        try:
            operation(self.selected())
        except Exception as error:
            messagebox.showerror('Unable to complete operation', str(error))

    def view(self):
        def show(traces):
            directory = Path(tempfile.mkdtemp(prefix='lsa-viewer-'))
            path = directory / 'sensorgram.html'
            make_chart(traces, path, self.unit.get())
            if not webbrowser.open(path.as_uri()):
                messagebox.showinfo('Chart saved', f'Open this file in your browser:\n{path}')
            self.status.config(text=f'Local chart: {path}. Contains experimental data; delete when no longer needed.')
        self.action(show)

    def save_html(self):
        def save(traces):
            path = filedialog.asksaveasfilename(defaultextension='.html', initialfile='lsa-sensorgram.html', filetypes=[('HTML', '*.html')])
            if path:
                make_chart(traces, path, self.unit.get())
                self.status.config(text=f'Saved: {path}')
        self.action(save)

    def save_csv(self):
        def save(traces):
            path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='lsa-data.csv', filetypes=[('CSV', '*.csv')])
            if path:
                export_csv(traces, path)
                self.status.config(text=f'Saved: {path}')
        self.action(save)

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    if '--self-test' in sys.argv:
        root.withdraw()
        try:
            import openpyxl
            with tempfile.TemporaryDirectory(prefix='lsa-selftest-') as directory:
                directory = Path(directory)
                workbook = openpyxl.Workbook()
                workbook.active.append(['[Synthetic (1) - Buffer 5 (5)] Ru values', 1, -1])
                workbook.active.append(['[Synthetic (1) - Buffer 5 (5)] Time values', 0, 1])
                source = directory / 'synthetic.xlsx'
                workbook.save(source)
                app.loaded(str(source), load_excel(source))
                root.update()
                traces = app.selected()
                assert len(traces) == 1 and traces[0].response == [1, -1]
                make_chart(traces, directory / 'chart.html')
                export_csv(traces, directory / 'data.csv')
                assert (directory / 'chart.html').stat().st_size > 1000000
                assert (directory / 'data.csv').is_file()
        except Exception:
            root.destroy()
            sys.exit(1)
        root.destroy()
    else:
        root.mainloop()
