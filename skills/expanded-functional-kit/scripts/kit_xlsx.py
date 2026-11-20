#!/usr/bin/env python3
"""openpyxl helpers shared by the two Excel builders (helper module, not an entry script)."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import kit_common as kc

THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def new_book():
    wb = Workbook()
    wb.remove(wb.active)
    return wb


def add_sheet(wb, title, headers, rows, th, widths=None, note=None, zone_col=None):
    """Add a styled table sheet. Returns the worksheet."""
    ws = wb.create_sheet(title[:31])
    r0 = 1
    if note:
        ws.cell(row=1, column=1, value=note).font = Font(italic=True, color="525252")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(headers)))
        ws.row_dimensions[1].height = 30
        ws.cell(row=1, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        r0 = 3
    hfill = PatternFill("solid", fgColor=th["primary"].lstrip("#").upper())
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=r0, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = hfill
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = BORDER
    for r, row in enumerate(rows, r0 + 1):
        for c, v in enumerate(row, 1):
            if isinstance(v, (list, tuple)):
                v = ", ".join(str(x) for x in v)
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = BORDER
            if zone_col is not None and c == zone_col + 1 and v in kc.ZONES:
                color = {"GREEN": "DEFBE6", "AMBER": "FCF4D6", "RED": "FFF1F1"}[v]
                cell.fill = PatternFill("solid", fgColor=color)
    for i, h in enumerate(headers, 1):
        longest = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if i - 1 < len(r)] or [10])
        w = (widths or {}).get(h) or min(60, max(12, longest + 2))
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
    if rows:
        ws.auto_filter.ref = "A%d:%s%d" % (r0, get_column_letter(len(headers)), r0 + len(rows))
    return ws


def join(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return v
