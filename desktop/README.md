# LSA Data Viewer (Windows 11 x64)

Desktop Excel picker with offline interactive Plotly charts in your default browser. Python is not needed to run the packaged EXE. The existing SPR simulation web app is unchanged.

## Use

1. Start `LSA-Data-Viewer.exe` and click **Open Excel (.xlsx)**.
2. Select a sample, one or more ROIs, and cycles (Ctrl/Shift for multiple).
3. Click **Open interactive chart**. In the browser, hover for values, drag to zoom, double-click to reset, scroll to zoom, use the lower time slider, or click legend entries to hide/show ROIs. The toolbar exports PNG.
4. **Save HTML** writes a standalone offline interactive file. **Export selected CSV** exports precisely the selected traces.

The EXE window and labels are English. Time units default to `original units` because the export labels do not specify units. Choosing `s` or `min` only changes the axis label; it does not convert values.

## Supported format and checks

Rows must look like `[sample (ROI) - reagent (cycle)] Time values` and matching `Ru values` (also accepts `Response values`). Values run horizontally from column B. Pairing uses worksheet + sample + ROI + reagent + cycle, not row adjacency. Each original column becomes one time/response pair. All sheets are read. Blank trailing cells are ignored, unknown labels are reported, and unmatched/non-numeric cells fail import rather than being silently removed. Formula cells must have cached numeric values saved by Excel.

Original continuous times and negative responses are preserved. Each cycle is a separate plotted segment, preventing artificial connections between different response values at the same boundary time. Time must increase within a cycle. Overlapping/reset times across cycles fail import with a diagnostic; automatic offsets are not guessed. No fitting, smoothing, baseline subtraction or averaging is performed.

Opening a chart writes experimental data into a local temporary `lsa-viewer-*` folder. The path is shown in the desktop window; delete that folder when no longer needed. Exported HTML and CSV also contain experimental data. The application does not upload data, use a CDN, or host a server. Windows/browser policy may restrict opening local files.

## Download Windows EXE from GitHub Actions

After this code is pushed, open the repository **Actions → Build LSA Windows EXE**. Select a successful run and download artifact **LSA-Data-Viewer-Windows-x64**. Extract the ZIP and run the EXE. GitHub artifact downloads require login; artifacts expire after 30 days. Run the workflow again to regenerate. The workflow can also be started with **Run workflow** on its branch.

Builds are unsigned. Windows may show an unknown publisher/SmartScreen notice. Verify that the file came from your repository's successful build. Signing requires a separate certificate; none is fabricated or included.

## Build on your own Windows computer

Install Python 3.12 x64 (including Tcl/Tk), then double-click `build_windows.bat`. It creates a virtual environment, installs dependencies, runs tests and packages `dist/LSA-Data-Viewer.exe`. Internet is needed for installation; the resulting application runs offline.

## Develop and test

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r desktop/requirements.txt
python -m unittest discover -s desktop/tests -v
python desktop/lsa_app.py
```

Linux needs Tcl/Tk and a graphical display for the desktop window. Windows packaging must run on Windows; a Linux test does not validate the Windows executable.
