from win32gui import (PumpMessages, PostQuitMessage, SendMessage)
from win32gui import (
    CreateDialogIndirect,
    CreateWindowEx, DestroyWindow, ShowWindow,
    GetDC, ReleaseDC,
    GetWindowRect, MoveWindow,
)
from win32con import (WS_VISIBLE, WS_OVERLAPPEDWINDOW, WS_CHILD, WS_TABSTOP)
from win32con import (WS_EX_NOPARENTNOTIFY, WS_EX_CLIENTEDGE)
from win32con import (WM_DESTROY, WM_CLOSE, WM_SIZE)
from win32con import (WM_SETFONT, WM_INITDIALOG)
from win32con import SW_SHOWNORMAL
from win32gui import GetStockObject
from win32gui import (SelectObject, GetTextMetrics)
from guis import label_key
from guis import InnerClass
from win32api import GetSystemMetrics
from win32con import (SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CYCAPTION)
from win32con import (BS_GROUPBOX, BS_PUSHBUTTON)
from win32api import (LOWORD, HIWORD)
from commctrl import (LVS_SHOWSELALWAYS, LVS_REPORT, WC_LISTVIEW)
from commctrl import LVM_GETEXTENDEDLISTVIEWSTYLE
from commctrl import LVM_SETEXTENDEDLISTVIEWSTYLE
from commctrl import (LVS_EX_FULLROWSELECT, LVCFMT_LEFT, LVM_INSERTCOLUMNW)
from win32gui_struct import PackLVCOLUMN
from collections import (Mapping, Iterable)
from win32gui import InitCommonControls

class Win(object):
    def __init__(self):
        self.visible = set()
    
    def msg_loop(self):
        if self.visible:
            PumpMessages()
    
    class Window(object, metaclass=InnerClass):
        def __init__(self, gui, title=None, *, sections):
            self.gui = gui
            
            template = (title, (0, 0, 0, 0), WS_OVERLAPPEDWINDOW)
            handlers = {
                WM_INITDIALOG: self.on_init_dialog,
                WM_DESTROY: self.on_destroy,
                WM_CLOSE: self.on_close,
                WM_SIZE: self.on_size,
            }
            self.sections = sections
            
            self.init_exc = None
            try:
                CreateDialogIndirect(None, (template,), 0, handlers)
                if self.init_exc:
                    raise self.init_exc
            finally:
                del self.init_exc
            
            (left, top, _, _) = GetWindowRect(self.hwnd)
            width = round(80 * self.x_unit) + round(160 * self.x_unit)
            height = round(250 * self.y_unit)
            width += GetSystemMetrics(SM_CXSIZEFRAME) * 2
            height += GetSystemMetrics(SM_CYSIZEFRAME) * 2
            height += GetSystemMetrics(SM_CYCAPTION)
            MoveWindow(self.hwnd, left, top, width, height, 0)
            
            ShowWindow(self.hwnd, SW_SHOWNORMAL)
            self.gui.visible.add(self)
        
        def on_init_dialog(self, hwnd, msg, wparam, lparam):
            try:
                self.hwnd = hwnd
                
                dc = GetDC(self.hwnd)
                try:
                    prev = SelectObject(dc, GetStockObject(DEFAULT_GUI_FONT))
                    try:
                        tm = GetTextMetrics(dc)
                        self.x_unit = (tm["AveCharWidth"] + 1) / 4
                        self.y_unit = tm["Height"] / 8
                    finally:
                        SelectObject(dc, prev)
                finally:
                    ReleaseDC(self.hwnd, dc)
                
                self.label_height = round(9 * self.y_unit)
                
                self.fixed_height = 0
                self.var_heights = 0
                for section in self.sections:
                    if not isinstance(section, Iterable):
                        section.place_on(self)
                        self.fixed_height += section.height
                        continue
                    
                    access = section.pop("access", None)
                    label = label_key(section.pop("label"), access)
                    section["hwnd"] = create_control(self.hwnd, "BUTTON",
                        style=BS_GROUPBOX, text=label,
                    )
                    self.fixed_height += self.label_height
                    
                    for field in section["fields"]:
                        if isinstance(field, Mapping):
                            label = label_key(field.pop("label"), access)
                            access = field.pop("access", None)
                            target = field["field"]
                            
                            field["label"] = create_control(self.hwnd,
                                "STATIC", text=label)
                        else:
                            target = field
                        
                        target.place_on(self)
                        if target.height:
                            self.fixed_height += max(self.label_height,
                                target.height)
                        else:
                            self.var_heights += 1
                    
                    self.fixed_height += round(4 * self.y_unit)
            
            except BaseException as exc:
                self.init_exc = exc
        
        def on_destroy(self, hwnd, msg, wparam, lparam):
            self.gui.visible.remove(self)
            PostQuitMessage(0)
        
        def on_close(self, hwnd, msg, wparam, lparam):
            DestroyWindow(self.hwnd)
        
        def on_size(self, hwnd, msg, wparam, lparam):
            cx = LOWORD(lparam)
            cy = HIWORD(lparam)
            
            y = 0
            spare_width = cy - self.fixed_height
            for section in self.sections:
                if not isinstance(section, Iterable):
                    section.move(0, y, cx, section.height)
                    continue
                
                group_top = y
                y += self.label_height
                for field in section["fields"]:
                    if isinstance(field, Mapping):
                        target = field["field"]
                    else:
                        target = field
                    
                    if target.height:
                        field_height = max(self.label_height, target.height)
                        label_y = y + (field_height - self.label_height) // 2
                    else:
                        field_height = spare_width // self.var_heights
                        spare_width += 1  # Distribute rounding from division
                        label_y = y
                    
                    if isinstance(field, Mapping):
                        label_width = round(80 * self.x_unit)
                        MoveWindow(field["label"],
                            0, label_y, label_width, self.label_height, 1)
                    else:
                        label_width = 0
                    
                    target_width = cx - label_width
                    target.move(label_width, y, target_width, field_height)
                    
                    y += field_height
                
                y += round(4 * self.y_unit)
                group_height = y - group_top
                MoveWindow(section["hwnd"],
                    0, group_top, cx, group_height, 1)
            
            return 1
    
    class Entry(object):
        def __init__(self, value=None):
            self.value = value
        
        def place_on(self, parent):
            self.parent = parent.hwnd
            self.height = round(12 * parent.y_unit)
            self.width = 0
            self.hwnd = create_control(self.parent, "EDIT",
                tabstop=True,
                text=self.value,
                ex_style=WS_EX_CLIENTEDGE,
            )
        
        def move(self, left, top, width, height):
            top += (height - self.height) // 2
            MoveWindow(self.hwnd, left, top, width, self.height, 1)
    
    class Button(object):
        def __init__(self, label, access=None):
            self.label = label_key(label, access)
        
        def place_on(self, parent):
            self.parent = parent.hwnd
            self.width = round(50 * parent.x_unit)
            self.height = round(14 * parent.y_unit)
            self.hwnd = create_control(self.parent, "BUTTON",
                style=BS_PUSHBUTTON,
                tabstop=True,
                text=self.label,
            )
        
        def move(self, left, top, width, height):
            left += (width - self.width) // 2
            top += (height - self.height) // 2
            MoveWindow(self.hwnd, left, top, self.width, self.height, 1)
    
    class List(object):
        def __init__(self, headings):
            self.headings = headings
        
        def place_on(self, parent):
            self.parent = parent.hwnd
            self.height = 0
            InitCommonControls()
            self.hwnd = create_control(self.parent, WC_LISTVIEW,
                style=LVS_SHOWSELALWAYS | LVS_REPORT,
                tabstop=True,
                ex_style=WS_EX_CLIENTEDGE,
            )
            
            style = SendMessage(self.hwnd, LVM_GETEXTENDEDLISTVIEWSTYLE,
                0, 0)
            style |= LVS_EX_FULLROWSELECT
            SendMessage(self.hwnd, LVM_SETEXTENDEDLISTVIEWSTYLE, 0, style)
            
            self.columns = list()
            for (i, heading) in enumerate(self.headings):
                (param, obj) = PackLVCOLUMN(
                    fmt=LVCFMT_LEFT, text=heading, cx=50,
                )
                self.columns.append(obj)
                SendMessage(self.hwnd, LVM_INSERTCOLUMNW, i, param)
        
        def move(self, left, top, width, height):
            MoveWindow(self.hwnd, left, top, width, height, 1)
    
    class Layout(object):
        def __init__(self, cells):
            self.cells = cells
        
        def place_on(self, parent):
            self.height = 0
            self.fixed_width = 0
            self.var_widths = 0
            for cell in self.cells:
                cell.place_on(parent)
                self.height = max(self.height, cell.height)
                
                if cell.width:
                    self.fixed_width += cell.width
                else:
                    self.var_widths += 1
        
        def move(self, left, top, width, height):
            var_widths = self.var_widths
            all_vary = not var_widths
            if all_vary:
                var_widths = len(self.cells)
            
            width -= self.fixed_width
            for cell in self.cells:
                cell_width = cell.width
                if all_vary or not cell_width:
                    cell_width += width // var_widths
                    width += 1  # Distribute rounding from the division
                cell.move(left, top, cell_width, self.height)
                left += cell_width

def create_control(parent, wndclass, text=None,
    tabstop=False, style=0,
    x=0, y=0, width=0, height=0,
    ex_style=0,
):
    style |= tabstop * WS_TABSTOP
    hwnd = CreateWindowEx(
        WS_EX_NOPARENTNOTIFY | ex_style,
        wndclass,
        text,
        WS_CHILD | WS_VISIBLE | style,
        x, y, width, height,
        parent,
        None,
        None,
    None)
    SendMessage(hwnd, WM_SETFONT, GetStockObject(DEFAULT_GUI_FONT), 0 << 0)
    return hwnd

DEFAULT_GUI_FONT = 17
