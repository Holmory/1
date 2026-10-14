"""LSA row-pair import; preserves original values and cycle boundaries."""
from dataclasses import dataclass
import csv
import math
import re
from pathlib import Path
import openpyxl

PATTERN = re.compile(r'^\[(.+?)\s+\((\d+)\)\s*-\s*(.+?)\s*\((\d+)\)\]\s*(Ru|Response|Time)\s+values$', re.I)

@dataclass
class Trace:
    sheet: str
    sample: str
    roi: int
    cycle: int
    reagent: str
    time: list
    response: list


def load_excel(path):
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    pairs = {}
    warnings = []
    try:
        for sheet in book:
            for rownum, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if not row or all(v is None for v in row):
                    continue
                match = PATTERN.fullmatch(str(row[0]))
                if not match:
                    warnings.append(f'{sheet.title} row {rownum}: unrecognized label; skipped')
                    continue
                sample, roi, reagent, cycle, kind = match.groups()
                key = (sheet.title, sample, int(roi), int(cycle), reagent)
                kind = 'time' if kind.lower() == 'time' else 'response'
                pair = pairs.setdefault(key, {})
                if kind in pair:
                    raise ValueError(f'Duplicate {kind} row: {key}')
                pair[kind] = (rownum, row[1:])
        traces = []
        for key, pair in pairs.items():
            if set(pair) != {'time', 'response'}:
                raise ValueError(f'Missing time/response partner: {key}')
            trow, times = pair['time']
            rrow, responses = pair['response']
            if len(times) != len(responses):
                raise ValueError(f'Unequal row lengths: {key}')
            points = []
            for column, (time, response) in enumerate(zip(times, responses), 2):
                if time is None and response is None:
                    continue
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (time, response)):
                    raise ValueError(f'Invalid/unpaired numeric value in {key}, column {column} (rows {trow}/{rrow})')
                points.append((time, response))
            if not points:
                raise ValueError(f'Empty data pair: {key}')
            if any(points[i][0] <= points[i-1][0] for i in range(1, len(points))):
                raise ValueError(f'Time must increase strictly within each cycle: {key}')
            traces.append(Trace(*key, [p[0] for p in points], [p[1] for p in points]))
        if not traces:
            raise ValueError('No LSA time/response rows found. Expected [sample (ROI) - reagent (cycle)] Time/Ru values.')
        traces.sort(key=lambda t: (t.sample, t.roi, t.time[0], t.cycle, t.sheet))
        groups = {}
        for trace in traces:
            group = (trace.sheet, trace.sample, trace.roi)
            previous = groups.get(group)
            if previous and trace.time[0] < previous.time[-1]:
                raise ValueError(f'Overlapping or reset cycle time: {group}. Absolute time is required; no offset was invented.')
            groups[group] = trace
        return traces, warnings
    finally:
        book.close()


def export_csv(traces, path):
    with Path(path).open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.writer(handle)
        writer.writerow(['sheet', 'sample', 'ROI', 'cycle', 'reagent', 'time_original', 'response_RU'])
        for trace in traces:
            for time, response in zip(trace.time, trace.response):
                writer.writerow([trace.sheet, trace.sample, trace.roi, trace.cycle, trace.reagent, time, response])


def make_chart(traces, path, time_unit='original units'):
    import plotly.graph_objects as go
    if not traces:
        raise ValueError('Select at least one ROI and cycle.')
    figure = go.Figure()
    groups = sorted({(t.sheet, t.sample, t.roi) for t in traces})
    palette = ['#147d87', '#c47732', '#7163b6', '#3576bd', '#ae527b', '#64843d']
    seen = set()
    for trace in traces:
        group = (trace.sheet, trace.sample, trace.roi)
        index = groups.index(group)
        label = f'{trace.sample} · ROI {trace.roi} · {trace.sheet}'
        figure.add_trace(go.Scatter(
            x=trace.time, y=trace.response, mode='lines', name=label,
            legendgroup=str(index), showlegend=group not in seen,
            line=dict(color=palette[index % len(palette)], width=1.2, dash='solid' if index % 2 == 0 else 'dash'),
            customdata=[[trace.cycle, trace.reagent] for _ in trace.time],
            hovertemplate='Time: %{x}<br>Response: %{y:.5f} RU<br>Cycle: %{customdata[0]}<br>Reagent: %{customdata[1]}<extra>%{fullData.name}</extra>',
        ))
        seen.add(group)
    figure.update_layout(
        title='LSA raw sensorgram', template='plotly_white',
        xaxis_title=f'Time ({time_unit})', yaxis_title='Response (RU)',
        xaxis=dict(rangeslider=dict(visible=True)), hovermode='closest',
        legend=dict(groupclick='togglegroup'), margin=dict(l=70, r=30, t=80, b=50),
    )
    figure.write_html(str(path), include_plotlyjs=True, full_html=True,
                       config=dict(scrollZoom=True, displaylogo=False, toImageButtonOptions=dict(format='png', filename='lsa-sensorgram', scale=2)))
    return figure
