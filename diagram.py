import json
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Port:
    name: str
    kind: str
    canvas_id: int | None = None
    connected: bool = True
    manual_y: float | None = None
    color: str = "black"
    side: str = "left"
    offset: float = 0.5


@dataclass
class Node:
    name: str
    kind: str
    inputs: list[Port]
    outputs: list[Port]
    x: int
    y: int
    width: int = 160
    height: int = 100
    base_height: int = 100
    items: list[int] = field(default_factory=list)
    resize_enabled: bool = False
    outline_color: str = "#BBBBBB"
    fill_color: str = "#e0e0e0"
    outline_enabled: bool = True
    outline_style: str = "solid"
    outline_scale: float = 1.0
    label_font_size: int = 12
    label_font_family: str = "Arial"
    label_font_weight: str = "bold"
    label_h_align: str = "left"
    label_v_align: str = "top"
    level: int = 0
    rotation: int = 0
    image: tk.PhotoImage | None = None
    image_id: int | None = None
    image_subsample: int = 10


@dataclass
class Connection:
    src: tuple[str, str] | None
    dst: tuple[str, str] | None
    line_id: int | None = None
    manual_mid_x: float | None = None
    manual_mid_y: float | None = None
    line_color: str = "#333333"
    line_thickness: float = 1.0
    label: str | None = None
    label_id: int | None = None
    label_font_family: str = "Arial"
    label_font_size: int = 12
    label_font_weight: str = "normal"
    label_angle: int = 0
    label_x: float | None = None
    label_y: float | None = None
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    free_points: list[tuple[float, float]] = field(default_factory=list)
    show_arrow: bool = True
    junction_ports: list[dict] = field(default_factory=list)
    pending_wire_ports: list[dict] = field(default_factory=list)


class DiagramApp:
    GRID_STEP = 5
    MID_STEP = 5
    PORT_RADIUS = 5
    COLOR_NAME_TO_HEX = {
        "GRAY": "#BBBBBB",
        "BLUE": "blue",
        "RED": "red",
        "GREEN": "green",
        "BLACK": "black",
        "YELLOW": "yellow",
        "WHITE": "white",
    }
    COLOR_HEX_TO_NAME = {value.lower(): key for key, value in COLOR_NAME_TO_HEX.items()}

    def __init__(
        self,
        nodes: dict[str, Node],
        connections: list[Connection],
        input_path: Path,
        output_path: Path,
    ):
        self.nodes = nodes
        self.connections = connections
        self.input_path = input_path
        self.output_path = output_path
        self.root = tk.Tk()
        self.root.title("Block Diagram")
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Toolbar.TFrame", background="white")
        self.style.configure(
            "Tool.TButton",
            font=("Arial", 9),
            padding=(6, 3),
            background="#f0f0f0",
            foreground="#333333",
        )
        self.style.map(
            "Tool.TButton",
            background=[("active", "#e0e0e0"), ("pressed", "#d0d0d0")],
        )
        self.root.configure(bg="white")

        self.toolbar = ttk.Frame(self.root, style="Toolbar.TFrame")
        self.toolbar.pack(fill=tk.X, padx=4, pady=(4, 0))
        self.toolbar_row1 = ttk.Frame(self.toolbar, style="Toolbar.TFrame")
        self.toolbar_row1.pack(fill=tk.X, pady=(0, 2))
        self.toolbar_row2 = ttk.Frame(self.toolbar, style="Toolbar.TFrame")
        self.toolbar_row2.pack(fill=tk.X, pady=(0, 2))
        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X, pady=(2, 0))

        self._status_frame = tk.Frame(self.root, bg="#f5f5f5", height=22)
        self._status_frame.pack(fill=tk.X)
        self._status_frame.pack_propagate(False)
        self._status_mode_label = tk.Label(
            self._status_frame, text="Mode: normal", font=("Arial", 9),
            bg="#f5f5f5", fg="#555555", anchor="w",
        )
        self._status_mode_label.pack(side=tk.LEFT, padx=6)
        self._status_selection_label = tk.Label(
            self._status_frame, text="", font=("Arial", 9),
            bg="#f5f5f5", fg="#555555", anchor="w",
        )
        self._status_selection_label.pack(side=tk.LEFT, padx=6)
        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X)

        self.new_button = ttk.Button(self.toolbar_row1, text="NEW (I)", command=self._open_new_block, style="Tool.TButton")
        self.new_button.pack(side=tk.LEFT, padx=2)
        self.edit_button = ttk.Button(self.toolbar_row1, text="EDIT (E)", command=self._open_edit_block, style="Tool.TButton")
        self.edit_button.pack(side=tk.LEFT, padx=2)
        self.rotate_button = ttk.Button(
            self.toolbar_row1, text="ROTATE (R)", command=self._rotate_active_selection, style="Tool.TButton"
        )
        self.rotate_button.pack(side=tk.LEFT, padx=2)
        self.remove_button = ttk.Button(self.toolbar_row1, text="REMOVE (Del)", command=self._toggle_delete_mode, style="Tool.TButton")
        self.remove_button.pack(side=tk.LEFT, padx=2)
        self.save_button = ttk.Button(self.toolbar_row1, text="SAVE (Ctrl+S)", command=self._save_json, style="Tool.TButton")
        self.save_button.pack(side=tk.LEFT, padx=2)
        self.save_png_button = ttk.Button(self.toolbar_row1, text="SAVE PNG (Ctrl+P)", command=self._save_png, style="Tool.TButton")
        self.save_png_button.pack(side=tk.LEFT, padx=2)
        self.connect_button = ttk.Button(self.toolbar_row1, text="CONNECT (W)", command=self._toggle_connect_mode, style="Tool.TButton")
        self.connect_button.pack(side=tk.LEFT, padx=2)
        self.wire_name_button = ttk.Button(self.toolbar_row1, text="LABEL (L)", command=self._toggle_wire_name_mode, style="Tool.TButton")
        self.wire_name_button.pack(side=tk.LEFT, padx=2)
        self.create_wire_button = ttk.Button(
            self.toolbar_row1, text="CREATE WIRE (CTRL+W)", command=self._toggle_create_wire_mode, style="Tool.TButton"
        )
        self.create_wire_button.pack(side=tk.LEFT, padx=2)

        self.resize_button = ttk.Button(self.toolbar_row2, text="RESIZE (S)", command=self._toggle_resize_active_node, style="Tool.TButton")
        self.resize_button.pack(side=tk.LEFT, padx=2)
        self.create_port_button = ttk.Button(self.toolbar_row2, text="CREATE PORT (A)", command=self._toggle_create_port_mode, style="Tool.TButton")
        self.create_port_button.pack(side=tk.LEFT, padx=2)
        self.delete_port_button = ttk.Button(
            self.toolbar_row2, text="DELETE PORT (CTRL+A)", command=self._toggle_delete_port_mode, style="Tool.TButton"
        )
        self.delete_port_button.pack(side=tk.LEFT, padx=2)
        self.move_port_button = ttk.Button(
            self.toolbar_row2, text="MOVE PORT (SHIFT+A)", command=self._toggle_move_port_mode, style="Tool.TButton"
        )
        self.move_port_button.pack(side=tk.LEFT, padx=2)
        self.port_toggle_button = ttk.Button(
            self.toolbar_row2, text="SHOW/HIDE PORT (`)", command=self._toggle_ports, style="Tool.TButton"
        )
        self.port_toggle_button.pack(side=tk.LEFT, padx=2)
        self.bring_front_button = ttk.Button(
            self.toolbar_row2, text="BRING FRONT (F)", command=self._bring_active_front, style="Tool.TButton"
        )
        self.bring_front_button.pack(side=tk.LEFT, padx=2)
        self.send_back_button = ttk.Button(
            self.toolbar_row2, text="SEND BACK (B)", command=self._send_active_back, style="Tool.TButton"
        )
        self.send_back_button.pack(side=tk.LEFT, padx=2)
        self.zoom_in_button = ttk.Button(
            self.toolbar_row2, text="ZOOM IN (CTRL+WHEEL)", command=self._zoom_in, style="Tool.TButton"
        )
        self.zoom_in_button.pack(side=tk.LEFT, padx=2)
        self.zoom_out_button = ttk.Button(
            self.toolbar_row2, text="ZOOM OUT (CTRL+WHEEL)", command=self._zoom_out, style="Tool.TButton"
        )
        self.zoom_out_button.pack(side=tk.LEFT, padx=2)
        self.guide_button = ttk.Button(self.toolbar_row2, text="GUIDE", command=self._open_guide, style="Tool.TButton")
        self.guide_button.pack(side=tk.LEFT, padx=2)
        self._canvas_frame = tk.Frame(self.root)
        self._canvas_frame.pack(fill=tk.BOTH, expand=True)
        self._h_scroll = tk.Scrollbar(self._canvas_frame, orient=tk.HORIZONTAL)
        self._h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self._v_scroll = tk.Scrollbar(self._canvas_frame, orient=tk.VERTICAL)
        self._v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas = tk.Canvas(
            self._canvas_frame, width=1200, height=800, bg="white",
            xscrollcommand=self._h_scroll.set,
            yscrollcommand=self._v_scroll.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._h_scroll.config(command=self.canvas.xview)
        self._v_scroll.config(command=self.canvas.yview)
        self._drag_data = {"node": None, "x": 0, "y": 0}
        self._drag_wire = {"connection": None, "offset": 0.0, "mode": None, "port": None, "node": None}
        self._resize_data = {"node": None, "mode": None, "x": 0, "y": 0, "orig": None}
        self._port_drag_data: dict = {"node": None, "port": None, "x": 0, "y": 0}
        self._mode = "normal"
        self._show_ports = True
        self._port_items: dict[int, tuple[str, str]] = {}
        self._selected_ports: list[tuple[str, str]] = []
        self._active_node_name: str | None = None
        self._gate_images: dict[tuple[str, int], tk.PhotoImage] = {}
        self._gate_source_images: dict[str, tk.PhotoImage] = {}
        self._zoom_scale = 1.0
        self._outline_backup: dict[str, str] = {}
        self._history: list[dict[str, object]] = []
        self._redo_stack: list[dict[str, object]] = []
        self._pending_midpoints: list[tuple[float, float]] = []
        self._wire_direction: str | None = None
        self._suspend_history = False
        self._delete_mode = False
        self._delete_blink_on = False
        self._delete_blink_job: str | None = None
        self._delete_overlays: dict[str, int] = {}
        self._wire_color_backup: dict[int, str] = {}
        self._node_color_backup: dict[str, tuple[str, str]] = {}
        self._wire_preview_id: int | None = None
        self._pan_data: dict[str, object] = {"active": False, "x": 0, "y": 0}
        self._selected_wire: Connection | None = None
        self._selected_label_conn: Connection | None = None
        self._selected_label_border: int | None = None
        self._label_drag_data: dict[str, object] = {"connection": None, "x": 0, "y": 0}
        self._pending_port_node_select = False
        self._wire_port_backup: dict[int, int] = {}
        self._create_wire_data: dict[str, object] = {
            "start": None,
            "preview_id": None,
            "color": "#333333",
            "thickness": 1.0,
        }
        self._clipboard: dict[str, object] | None = None
        self._align_guides: list[int] = []
        self._align_threshold = 8
        self._grid_items: list[int] = []
        self._node_highlight_id: int | None = None
        # Multi-select state
        self._multi_select: dict = {
            "active": False, "rect_id": None,
            "start_x": 0, "start_y": 0,
            "nodes": [], "wires": [], "labels": [],
            "dragging": False, "drag_x": 0, "drag_y": 0,
            "highlights": [],
        }
        self._build_ui()

    def _cx(self, event):
        return int(self.canvas.canvasx(event.x))

    def _cy(self, event):
        return int(self.canvas.canvasy(event.y))

    def _materialize_pending_ports(self):
        """Create PORT nodes for connections with pending_wire_ports (w-wires loaded from JSON)."""
        old_suspend = self._suspend_history
        self._suspend_history = True
        for connection in self.connections:
            if not connection.pending_wire_ports:
                continue
            coords = self._connection_line_coords(connection)
            if not coords or len(coords) < 4:
                continue
            for pr in connection.pending_wire_ports:
                ratio = pr["ratio"]
                pname = pr.get("name")
                px, py = self._point_from_ratio_on_polyline(coords, ratio)
                seg_dir = self._segment_direction_at(coords, px, py)
                port_side = "top" if seg_dir == "horizontal" else "left"
                jname = self._create_junction_at(px, py, port_side=port_side, name=pname)
                connection.junction_ports.append({"node": jname, "ratio": ratio})
            connection.pending_wire_ports.clear()
        self._suspend_history = old_suspend

    def _build_ui(self):
        self._draw_grid()
        for node in self.nodes.values():
            self._draw_node(node)
        for connection in self.connections:
            self._draw_connection(connection)
        self._materialize_pending_ports()
        self.canvas.tag_bind("node", "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind("node", "<ButtonRelease-1>", self._on_release)
        self.canvas.tag_bind("node", "<B1-Motion>", self._on_motion)
        self.canvas.tag_bind("port", "<ButtonPress-1>", self._on_port_press)
        self.canvas.tag_bind("port", "<B1-Motion>", self._on_port_motion)
        self.canvas.tag_bind("port", "<ButtonRelease-1>", self._on_port_release)
        self.canvas.tag_bind("wire", "<ButtonPress-1>", self._on_wire_press)
        self.canvas.tag_bind("wire", "<B1-Motion>", self._on_wire_motion)
        self.canvas.tag_bind("wire", "<ButtonRelease-1>", self._on_wire_release)
        self.canvas.tag_bind("label", "<ButtonPress-1>", self._on_label_press)
        self.canvas.tag_bind("label", "<B1-Motion>", self._on_label_motion)
        self.canvas.tag_bind("label", "<ButtonRelease-1>", self._on_label_release)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Control-MouseWheel>", self._on_zoom_wheel)
        self.canvas.bind("<Control-Button-4>", self._on_zoom_wheel)
        self.canvas.bind("<Control-Button-5>", self._on_zoom_wheel)
        self.root.bind("i", lambda _event: self._open_new_block())
        self.root.bind("e", lambda _event: self._handle_edit_key())
        self.root.bind("<Delete>", lambda _event: self._toggle_delete_mode())
        self.root.bind("<Control-a>", lambda _event: self._toggle_delete_port_mode())
        self.root.bind("`", lambda _event: self._toggle_ports())
        self.root.bind("<Control-s>", lambda _event: self._save_json())
        self.root.bind("<Control-z>", lambda _event: self._undo())
        self.root.bind("<Control-y>", lambda _event: self._redo())
        self.root.bind("s", lambda _event: self._handle_s_key())
        self.root.bind("w", lambda _event: self._toggle_connect_mode())
        self.root.bind("a", lambda _event: self._toggle_create_port_mode())
        self.root.bind("A", lambda _event: self._toggle_move_port_mode())
        self.root.bind("<Control-w>", lambda _event: self._toggle_create_wire_mode())
        self.canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_motion)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_release)
        self.root.bind("l", lambda _event: self._toggle_wire_name_mode())
        self.root.bind("f", lambda _event: self._bring_active_front())
        self.root.bind("b", lambda _event: self._send_active_back())
        self.root.bind("r", lambda _event: self._rotate_active_selection())
        self.root.bind("<Escape>", lambda _event: self._handle_escape())
        self.root.bind("<Control-c>", lambda _event: self._copy_selection())
        self.root.bind("<Control-v>", lambda _event: self._paste_selection())
        self.root.bind("<Control-p>", lambda _event: self._save_png())
        self.root.bind("<Tab>", lambda _event: self._toggle_wire_arrow())
        self.root.after(300, lambda: self.save_diagram(self.output_path))
        self._record_history(initial=True)
        self._schedule_status_update()

    GRID_SPACING = 20

    def _update_scroll_region(self):
        bbox = self._content_bbox()
        if not bbox:
            self.canvas.configure(scrollregion=(0, 0, 1200, 800))
            return
        cw = self.canvas.winfo_width() or 1200
        ch = self.canvas.winfo_height() or 800
        margin = 200
        x1 = min(bbox[0] - margin, 0)
        y1 = min(bbox[1] - margin, 0)
        x2 = max(bbox[2] + margin, cw)
        y2 = max(bbox[3] + margin, ch)
        self.canvas.configure(scrollregion=(x1, y1, x2, y2))
        sr_w = x2 - x1
        sr_h = y2 - y1
        if sr_w > 0 and sr_h > 0:
            target_x = (0 - x1) / sr_w
            target_y = (0 - y1) / sr_h
            self.canvas.xview_moveto(target_x)
            self.canvas.yview_moveto(target_y)

    def _draw_grid(self):
        self._clear_grid()
        if not self._show_ports:
            return
        canvas_w = max(self.canvas.winfo_width(), 1200)
        canvas_h = max(self.canvas.winfo_height(), 800)
        bbox = self._content_bbox()
        if bbox:
            x_start = min(int(bbox[0]), 0) - 200
            y_start = min(int(bbox[1]), 0) - 200
            x_end = max(int(bbox[2]), canvas_w) + 200
            y_end = max(int(bbox[3]), canvas_h) + 200
        else:
            x_start, y_start = -200, -200
            x_end = canvas_w + 200
            y_end = canvas_h + 200
        step = self.GRID_SPACING
        x_start = (x_start // step) * step
        y_start = (y_start // step) * step
        color = "#d0d0d0"
        for x in range(x_start, x_end + 1, step):
            gid = self.canvas.create_line(x, y_start, x, y_end, fill=color, width=1, tags="grid")
            self._grid_items.append(gid)
        for y in range(y_start, y_end + 1, step):
            gid = self.canvas.create_line(x_start, y, x_end, y, fill=color, width=1, tags="grid")
            self._grid_items.append(gid)
        self.canvas.tag_lower("grid")

    def _clear_grid(self):
        for gid in self._grid_items:
            self.canvas.delete(gid)
        self._grid_items.clear()

    _CUSTOM_GATE_KINDS = ("MUX_2x1", "MUX_4x1", "DEMUX_1x2", "DEMUX_1x4", "DFF",
                          "AND2", "AND4", "OR2", "OR4", "XOR2", "XOR4", "INV")

    def _render_gate_image(self, kind: str, w: int, h: int, rotation: int = 0,
                           fill_color: str = "white", outline_color: str = "black",
                           outline_width: float = 1.0, outline_style: str = "solid") -> "tk.PhotoImage | None":
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk
        except ImportError:
            return None
        w = max(1, int(round(w)))
        h = max(1, int(round(h)))
        # For 90°/270° rotation, draw at pre-rotation dimensions to avoid distortion
        draw_w, draw_h = (h, w) if rotation in (90, 270) else (w, h)
        scale = 3
        sw, sh = draw_w * scale, draw_h * scale
        img = Image.new("RGBA", (sw, sh), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        lw = max(1, int(round(2 * outline_width))) * scale

        def _font(size, bold=False):
            weight = "bold" if bold else ""
            for name in ("DejaVuSans.ttf", "arial.ttf"):
                try:
                    return ImageFont.truetype(name, size * scale)
                except Exception:
                    pass
            try:
                return ImageFont.load_default(size=size * scale)
            except Exception:
                return ImageFont.load_default()

        def _arc_points(cx, cy, radius, start_deg, end_deg, steps=60):
            import math

            points = []
            for i in range(steps + 1):
                t = i / steps
                angle = math.radians(start_deg + (end_deg - start_deg) * t)
                points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
            return points

        if kind.startswith("MUX"):
            indent = int(sh * 0.2)
            points = [(0, 0), (sw, indent), (sw, sh - indent), (0, sh)]
            draw.polygon(points, fill=fill_color, outline=outline_color, width=lw)
            n_label = kind.split("_")[1]

        elif kind.startswith("DEMUX"):
            indent = int(sh * 0.2)
            points = [(0, indent), (sw, 0), (sw, sh), (0, sh - indent)]
            draw.polygon(points, fill=fill_color, outline=outline_color, width=lw)
            n_label = kind.split("_")[1]

        elif kind == "DFF":
            draw.rectangle([0, 0, sw - 1, sh - 1], fill=fill_color, outline=outline_color, width=lw)
            tri_y = int(sh * 0.67)
            tri_s = 12 * scale
            tri_points = [(0, tri_y - tri_s), (tri_s, tri_y), (0, tri_y + tri_s)]
            draw.polygon(tri_points, fill=fill_color, outline=outline_color, width=lw)

        elif kind.startswith("AND"):
            import math
            # AND gate: flat left side + semicircle on right (D-shape)
            radius = sh / 2
            mid_x = sw - radius  # semicircle center, so arc reaches right edge
            body_pts = []
            body_pts.append((0, 0))
            body_pts.append((mid_x, 0))
            n_curve = 60
            for i in range(n_curve + 1):
                angle = -math.pi / 2 + math.pi * i / n_curve
                cx = mid_x + radius * math.cos(angle)
                cy = sh / 2 + radius * math.sin(angle)
                body_pts.append((cx, cy))
            body_pts.append((mid_x, sh))
            body_pts.append((0, sh))
            draw.polygon(body_pts, fill=fill_color, outline=outline_color, width=lw)

        elif kind.startswith("OR"):
            import math
            n_curve = 80
            curve_depth = sw * 0.15
            # Build outline path: top-left → top curve → tip → bottom curve → bottom-left → left curve back to top-left
            outline = []
            # Top curve: from top-left (0,0) to tip (sw, sh/2)
            tip_x, tip_y = sw, sh * 0.5
            for i in range(n_curve + 1):
                t = i / n_curve
                cp1x, cp1y = sw * 0.35, 0
                cp2x, cp2y = sw * 0.8, sh * 0.15
                x = (1-t)**3*0 + 3*(1-t)**2*t*cp1x + 3*(1-t)*t**2*cp2x + t**3*tip_x
                y = (1-t)**3*0 + 3*(1-t)**2*t*cp1y + 3*(1-t)*t**2*cp2y + t**3*tip_y
                outline.append((x, y))
            # Bottom curve: from tip back to bottom-left (0, sh)
            for i in range(1, n_curve + 1):
                t = i / n_curve
                cp1x, cp1y = sw * 0.8, sh * 0.85
                cp2x, cp2y = sw * 0.35, sh
                x = (1-t)**3*tip_x + 3*(1-t)**2*t*cp1x + 3*(1-t)*t**2*cp2x + t**3*0
                y = (1-t)**3*tip_y + 3*(1-t)**2*t*cp1y + 3*(1-t)*t**2*cp2y + t**3*sh
                outline.append((x, y))
            # Left concave curve: from bottom-left (0, sh) back to top-left (0, 0)
            for i in range(1, n_curve + 1):
                t = i / n_curve
                y = sh * (1 - t)
                x = curve_depth * math.sin((1 - t) * math.pi)
                outline.append((x, y))
            draw.polygon(outline, fill=fill_color, outline=outline_color, width=lw)

        elif kind.startswith("XOR"):
            import math
            n_curve = 80
            curve_depth = sw * 0.15
            xor_gap = sw * 0.10
            tip_x, tip_y = sw, sh * 0.5
            # Build body outline (same as OR but left curve shifted right by xor_gap)
            outline = []
            # Top curve: from top-left (xor_gap, 0) to tip
            for i in range(n_curve + 1):
                t = i / n_curve
                cp1x, cp1y = sw * 0.35, 0
                cp2x, cp2y = sw * 0.8, sh * 0.15
                x = (1-t)**3*xor_gap + 3*(1-t)**2*t*cp1x + 3*(1-t)*t**2*cp2x + t**3*tip_x
                y = (1-t)**3*0 + 3*(1-t)**2*t*cp1y + 3*(1-t)*t**2*cp2y + t**3*tip_y
                outline.append((x, y))
            # Bottom curve: from tip back to bottom-left (xor_gap, sh)
            for i in range(1, n_curve + 1):
                t = i / n_curve
                cp1x, cp1y = sw * 0.8, sh * 0.85
                cp2x, cp2y = sw * 0.35, sh
                x = (1-t)**3*tip_x + 3*(1-t)**2*t*cp1x + 3*(1-t)*t**2*cp2x + t**3*xor_gap
                y = (1-t)**3*tip_y + 3*(1-t)**2*t*cp1y + 3*(1-t)*t**2*cp2y + t**3*sh
                outline.append((x, y))
            # Left concave curve of body: from (xor_gap, sh) to (xor_gap, 0)
            for i in range(1, n_curve + 1):
                t = i / n_curve
                y = sh * (1 - t)
                x = xor_gap + curve_depth * math.sin((1 - t) * math.pi)
                outline.append((x, y))
            draw.polygon(outline, fill=fill_color, outline=outline_color, width=lw)
            # Extra XOR input curve (separate, to the left of the body)
            for i in range(n_curve):
                t0 = i / n_curve
                t1 = (i + 1) / n_curve
                y0 = t0 * sh
                x0 = curve_depth * math.sin(t0 * math.pi)
                y1 = t1 * sh
                x1 = curve_depth * math.sin(t1 * math.pi)
                draw.line([(x0, y0), (x1, y1)], fill=outline_color, width=lw)

        elif kind == "INV":
            import math
            # INV gate: triangle pointing right + bubble at output
            bubble_r = max(int(sw * 0.10), lw + 2)
            tri_right = sw - bubble_r * 2 - lw
            margin_y = int(sh * 0.08)
            tri_pts = [(lw, margin_y), (tri_right, sh // 2), (lw, sh - margin_y)]
            draw.polygon(tri_pts, fill=fill_color, outline=outline_color, width=lw)
            # Bubble (circle) at output
            bx = tri_right + bubble_r
            by = sh // 2
            draw.ellipse(
                [bx - bubble_r, by - bubble_r, bx + bubble_r, by + bubble_r],
                fill=fill_color, outline=outline_color, width=lw
            )

        elif kind == "CIRCLE":
            m = lw
            draw.ellipse([m, m, sw - m, sh - m], fill=fill_color, outline=outline_color, width=lw)

        elif kind == "RECTANGLE":
            m = lw
            draw.rectangle([m, m, sw - m, sh - m], fill=fill_color, outline=outline_color, width=lw)

        elif kind == "ROUNDED_RECT":
            m = lw
            r = min(sw, sh) * 0.2
            draw.rounded_rectangle([m, m, sw - m, sh - m], radius=r,
                                   fill=fill_color, outline=outline_color, width=lw)

        elif kind == "CLOUD":
            import math
            cx, cy = sw / 2, sh / 2
            # Cloud shape: overlapping circles traced from center
            m = lw
            # Top half bumps (mirrored to bottom for symmetry)
            top_bumps = [
                (0.50, 0.25, 0.26),   # top center bump
                (0.30, 0.30, 0.22),   # top-left bump
                (0.70, 0.30, 0.22),   # top-right bump
            ]
            cloud_circles = [
                (0.15, 0.48, 0.22),   # left bump (widest zone)
                (0.85, 0.48, 0.22),   # right bump (widest zone)
                (0.38, 0.48, 0.24),   # center-left fill
                (0.62, 0.48, 0.24),   # center-right fill
                (0.50, 0.50, 0.25),   # center core
            ]
            for (bx, by, br) in top_bumps:
                cloud_circles.append((bx, by, br))
                cloud_circles.append((bx, 1.0 - by, br))  # mirror to bottom
            # Convert fractional positions to pixel coords
            circles_px = []
            for (cxf, cyf, rf) in cloud_circles:
                circles_px.append((cxf * sw, cyf * sh, rf * min(sw, sh)))
            # Trace outer boundary by ray-casting from center
            n_pts = 720
            pts = []
            for i in range(n_pts):
                angle = 2 * math.pi * i / n_pts
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                max_r = 0
                for (ccx, ccy, cr) in circles_px:
                    dx = ccx - cx
                    dy = ccy - cy
                    proj = dx * cos_a + dy * sin_a
                    perp = abs(-dx * sin_a + dy * cos_a)
                    if perp < cr:
                        extend = proj + math.sqrt(cr * cr - perp * perp)
                        if extend > max_r:
                            max_r = extend
                pts.append((cx + max_r * cos_a, cy + max_r * sin_a))
            draw.polygon(pts, fill=fill_color, outline=outline_color, width=lw)

        if rotation:
            img = img.rotate(-rotation, expand=True)
        img = img.resize((w, h), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    _DIAGRAM_SHAPES = {"CIRCLE", "RECTANGLE", "ROUNDED_RECT", "CLOUD"}

    def _draw_gate_custom(self, node: Node):
        x1, y1 = node.x, node.y
        w, h = node.width, node.height
        kind = node.kind

        # Pass styling parameters for all gates
        gate_img = self._render_gate_image(
            kind, w, h, rotation=node.rotation,
            fill_color=node.fill_color, outline_color=node.outline_color,
            outline_width=node.outline_scale, outline_style=node.outline_style,
        )
        if gate_img:
            node.image = gate_img
            node.image_id = self.canvas.create_image(x1, y1, image=gate_img, anchor="nw")
            node.items.append(node.image_id)
        else:
            x2, y2 = x1 + w, y1 + h
            fc = node.fill_color
            oc = node.outline_color
            olw = max(1, int(round(2 * node.outline_scale)))
            if kind.startswith("MUX"):
                indent = h * 0.2
                poly = self.canvas.create_polygon(
                    x1, y1, x2, y1 + indent, x2, y2 - indent, x1, y2,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(poly)
            elif kind.startswith("DEMUX"):
                indent = h * 0.2
                poly = self.canvas.create_polygon(
                    x1, y1 + indent, x2, y1, x2, y2, x1, y2 - indent,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(poly)
            elif kind == "DFF":
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(rect)
            elif kind == "CIRCLE":
                oval = self.canvas.create_oval(
                    x1, y1, x2, y2,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(oval)
            elif kind in ("RECTANGLE", "ROUNDED_RECT", "CLOUD"):
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(rect)
            else:
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fc, outline=oc, width=olw,
                )
                node.items.append(rect)
        if node.resize_enabled:
            outline_width = max(2, int(round(2 * node.outline_scale)))
            outline_rect = self.canvas.create_rectangle(
                x1,
                y1,
                x1 + w,
                y1 + h,
                outline="black",
                width=outline_width,
            )
            node.items.append(outline_rect)

    def _draw_node(self, node: Node):
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        if node.kind != "BLOCK":
            self._draw_gate_custom(node)
        else:
            base_width = 4 if node.resize_enabled else 2
            outline_width = max(1, base_width * node.outline_scale)
            dash = (4, 2) if node.outline_style == "dashed" else None
            if node.resize_enabled:
                outline = "black"
                width = outline_width
            else:
                outline = node.outline_color if node.outline_enabled else ""
                width = outline_width if node.outline_enabled else 0
            rect = self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=node.fill_color,
                outline=outline,
                width=width,
                dash=dash,
            )
            node.items.append(rect)
        if node.kind != "PORT":
            pad = 6
            h_align = getattr(node, "label_h_align", "left")
            v_align = getattr(node, "label_v_align", "top")
            if h_align == "left":
                lx = x1 + pad
                anchor_h = "w"
            elif h_align == "center":
                lx = (x1 + x2) / 2
                anchor_h = ""
            else:
                lx = x2 - pad
                anchor_h = "e"
            if v_align == "top":
                ly = y1 + pad
                anchor_v = "n"
            elif v_align == "center":
                ly = (y1 + y2) / 2
                anchor_v = ""
            else:
                ly = y2 - pad
                anchor_v = "s"
            anchor = anchor_v + anchor_h if (anchor_v or anchor_h) else "center"
            label = self.canvas.create_text(
                lx,
                ly,
                text=node.name,
                font=(node.label_font_family, node.label_font_size, node.label_font_weight),
                anchor=anchor,
            )
            node.items.append(label)

        self._clamp_ports_to_node(node)
        ports = node.inputs + node.outputs
        for port in ports:
            px, py = self._port_position(node, port)
            port_id = self._create_port_oval(px, py, port.color)
            port.canvas_id = port_id
            node.items.append(port_id)
            self._register_port(node.name, port)

        for item in node.items:
            self.canvas.addtag_withtag("node", item)
            self.canvas.addtag_withtag(f"node:{node.name}", item)

    def _draw_connection(self, connection: Connection):
        coords = self._connection_line_coords(connection)
        if not coords:
            if connection.label and not connection.src and not connection.dst:
                lx = connection.label_x if connection.label_x is not None else 200
                ly = connection.label_y if connection.label_y is not None else 200
                font = (connection.label_font_family, connection.label_font_size, connection.label_font_weight)
                connection.label_id = self.canvas.create_text(
                    lx, ly, text=connection.label, font=font, anchor="s", angle=connection.label_angle,
                )
                self.canvas.addtag_withtag("label", connection.label_id)
            return
        line = self.canvas.create_line(
            *coords,
            smooth=False,
            arrow=tk.LAST if connection.show_arrow else tk.NONE,
            width=self._wire_width(connection),
            fill=connection.line_color,
        )
        self.canvas.addtag_withtag("wire", line)
        connection.line_id = line
        if connection.label:
            if connection.label_x is not None and connection.label_y is not None:
                label_x, label_y = connection.label_x, connection.label_y
            else:
                label_x, label_y = self._label_position(coords)
            font = (connection.label_font_family, connection.label_font_size, connection.label_font_weight)
            label_id = self.canvas.create_text(
                label_x,
                label_y,
                text=connection.label,
                font=font,
                anchor="s",
                angle=connection.label_angle,
            )
            self.canvas.addtag_withtag("label", label_id)
            connection.label_id = label_id

    @staticmethod
    def _wire_width(connection: Connection) -> int:
        return max(1, int(round(connection.line_thickness * 2)))

    @staticmethod
    def _wire_selected_width(connection: Connection) -> int:
        base = DiagramApp._wire_width(connection)
        return max(base + 2, int(round(base * 1.5)))

    def _get_port_canvas_id(self, node_name: str, port_name: str, kind: str | None = None) -> int | None:
        node = self.nodes.get(node_name)
        if not node:
            return None
        for port in node.inputs + node.outputs:
            if port.name == port_name:
                return port.canvas_id
        return None

    def _port_center(self, canvas_id: int) -> tuple[float, float]:
        x1, y1, x2, y2 = self.canvas.coords(canvas_id)
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _highlight_node(self, node: Node):
        self._unhighlight_node()
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        self._node_highlight_id = self.canvas.create_rectangle(
            x1 - 2, y1 - 2, x2 + 2, y2 + 2,
            outline="#4A90D9", width=2, dash=(4, 2),
        )
        self.canvas.addtag_withtag(f"node:{node.name}", self._node_highlight_id)
        node.items.append(self._node_highlight_id)

    def _unhighlight_node(self):
        if self._node_highlight_id:
            self.canvas.delete(self._node_highlight_id)
            # Remove from node items list
            for node in self.nodes.values():
                if self._node_highlight_id in node.items:
                    node.items.remove(self._node_highlight_id)
                    break
            self._node_highlight_id = None

    def _on_press(self, event):
        self._deselect_wire()
        self._deselect_label()
        # Check if clicking on a multi-selected node → start multi-drag
        if self._multi_select["nodes"] or self._multi_select["wires"] or self._multi_select["labels"]:
            item = self.canvas.find_withtag("current")
            if item:
                tags = self.canvas.gettags(item[0])
                node_tag = next((t for t in tags if t.startswith("node:")), None)
                if node_tag:
                    clicked_name = node_tag.split(":", 1)[1]
                    if clicked_name in self._multi_select["nodes"]:
                        cx, cy = self._cx(event), self._cy(event)
                        self._multi_select["dragging"] = True
                        self._multi_select["drag_x"] = cx
                        self._multi_select["drag_y"] = cy
                        return
            self._clear_multi_select()
        if self._delete_mode:
            item = self.canvas.find_withtag("current")
            if not item:
                return
            tags = self.canvas.gettags(item[0])
            node_tag = next((tag for tag in tags if tag.startswith("node:")), None)
            if not node_tag:
                return
            node_name = node_tag.split(":", 1)[1]
            node = self.nodes.get(node_name)
            if not node:
                return
            self._remove_node(node)
            return
        if self._mode == "create_port":
            self._handle_create_port_click(event)
            return
        if self._mode != "normal":
            return
        item = self.canvas.find_withtag("current")
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        node_tag = next((tag for tag in tags if tag.startswith("node:")), None)
        if not node_tag:
            return
        node_name = node_tag.split(":", 1)[1]
        node = self.nodes[node_name]
        self._unhighlight_node()
        self._active_node_name = node.name
        self._highlight_node(node)
        self._apply_z_order(active_node_name=node.name)
        cx, cy = self._cx(event), self._cy(event)
        if node.resize_enabled:
            resize_mode = self._hit_test_edge(node, cx, cy)
            if resize_mode:
                self._resize_data["node"] = node
                self._resize_data["mode"] = resize_mode
                self._resize_data["x"] = cx
                self._resize_data["y"] = cy
                if node.kind == "BLOCK" or node.kind in self._CUSTOM_GATE_KINDS or node.kind in self._DIAGRAM_SHAPES:
                    self._resize_data["orig"] = (node.x, node.y, node.width, node.height)
                else:
                    self._resize_data["orig"] = (
                        node.x,
                        node.y,
                        node.width,
                        node.height,
                        node.image_subsample,
                    )
                self.canvas.bind("<B1-Motion>", self._on_resize_motion)
                self.canvas.bind("<ButtonRelease-1>", self._on_resize_release)
            return
        resize_mode = self._hit_test_edge(node, cx, cy)
        if resize_mode:
            self._resize_data["node"] = node
            self._resize_data["mode"] = resize_mode
            self._resize_data["x"] = cx
            self._resize_data["y"] = cy
            self._resize_data["orig"] = (node.x, node.y, node.width, node.height)
            return
        self._drag_data["node"] = node
        self._drag_data["x"] = cx
        self._drag_data["y"] = cy

    def _on_canvas_press(self, event):
        if self._mode == "wire_port":
            self._handle_wire_port_click(event)
            return
        if self._mode == "create_wire":
            self._handle_create_wire_press(event)
            return
        if self._mode != "connect":
            item = self.canvas.find_withtag("current")
            if item:
                tags = self.canvas.gettags(item[0])
                if "label" in tags or "wire" in tags or "node" in tags or "port" in tags:
                    return
            # Background click: unhighlight, deselect, start multi-select
            self._unhighlight_node()
            self._active_node_name = None
            self._deselect_wire()
            self._deselect_label()
            self._clear_multi_select()
            if self._mode == "normal" and not self._delete_mode:
                cx, cy = self._cx(event), self._cy(event)
                self._multi_select["start_x"] = cx
                self._multi_select["start_y"] = cy
                self._multi_select["active"] = True
            return
        if len(self._selected_ports) != 1:
            return
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            # Don't block bend creation when clicking on grid lines or wire preview
            if "grid" not in tags and item[0] != self._wire_preview_id:
                return
        node_name, port_name = self._selected_ports[0]
        port_id = self._get_port_canvas_id(node_name, port_name)
        if not port_id:
            return
        start_x, start_y = self._port_center(port_id)
        if self._pending_midpoints:
            last_x, last_y = self._pending_midpoints[-1]
        else:
            last_x, last_y = start_x, start_y
        cx, cy = self._cx(event), self._cy(event)
        snapped_x = self._snap_value(cx)
        snapped_y = self._snap_value(cy)
        cur_dir = self._current_wire_direction()
        if cur_dir == "horizontal":
            bend = (snapped_x, last_y)
        else:
            bend = (last_x, snapped_y)
        self._pending_midpoints.append(bend)
        self._update_wire_preview(cx, cy)

    def _on_canvas_motion(self, event):
        cx, cy = self._cx(event), self._cy(event)
        if self._mode == "create_wire":
            self._update_create_wire_preview(cx, cy)
            return
        if self._mode == "connect" and len(self._selected_ports) == 1:
            self._update_wire_preview(cx, cy)

    def _clear_multi_select(self):
        for hid in self._multi_select["highlights"]:
            self.canvas.delete(hid)
        if self._multi_select["rect_id"]:
            self.canvas.delete(self._multi_select["rect_id"])
        # Restore wire widths for selected wires
        for conn in self._multi_select["wires"]:
            if conn.line_id:
                self.canvas.itemconfigure(conn.line_id, width=self._wire_width(conn))
        self._multi_select = {
            "active": False, "rect_id": None,
            "start_x": 0, "start_y": 0,
            "nodes": [], "wires": [], "labels": [],
            "dragging": False, "drag_x": 0, "drag_y": 0,
            "highlights": [],
        }
        self._update_status_bar()

    def _on_canvas_drag(self, event):
        if not self._multi_select["active"]:
            return
        # If multi-select dragging mode (moving selected items)
        if self._multi_select["dragging"]:
            self._on_multi_drag(event)
            return
        # Don't draw selection rect if a node/wire drag is active
        if self._drag_data.get("node") or self._drag_wire.get("connection"):
            return
        if self._label_drag_data.get("connection"):
            return
        cx, cy = self._cx(event), self._cy(event)
        sx, sy = self._multi_select["start_x"], self._multi_select["start_y"]
        if self._multi_select["rect_id"]:
            self.canvas.coords(self._multi_select["rect_id"], sx, sy, cx, cy)
        else:
            self._multi_select["rect_id"] = self.canvas.create_rectangle(
                sx, sy, cx, cy,
                outline="#4A90D9", width=1, dash=(4, 2),
            )

    def _on_canvas_release(self, event):
        if not self._multi_select["active"]:
            return
        if self._multi_select["dragging"]:
            self._multi_select["dragging"] = False
            self._record_history()
            return
        # If no selection rectangle was drawn, just reset
        if not self._multi_select["rect_id"] and not self._multi_select["nodes"]:
            self._multi_select["active"] = False
            return
        cx, cy = self._cx(event), self._cy(event)
        sx, sy = self._multi_select["start_x"], self._multi_select["start_y"]
        # Remove selection rectangle
        if self._multi_select["rect_id"]:
            self.canvas.delete(self._multi_select["rect_id"])
            self._multi_select["rect_id"] = None
        x1, y1 = min(sx, cx), min(sy, cy)
        x2, y2 = max(sx, cx), max(sy, cy)
        # If rectangle is too small, treat as a click (clear)
        if abs(x2 - x1) < 5 and abs(y2 - y1) < 5:
            self._multi_select["active"] = False
            return
        # Find nodes in rectangle
        selected_nodes = []
        for node in self.nodes.values():
            nx1, ny1 = node.x, node.y
            nx2, ny2 = node.x + node.width, node.y + node.height
            if nx1 >= x1 and ny1 >= y1 and nx2 <= x2 and ny2 <= y2:
                selected_nodes.append(node.name)
        # Find wires in rectangle
        selected_wires = []
        for conn in self.connections:
            coords = self._connection_line_coords(conn)
            if not coords or len(coords) < 4:
                continue
            all_inside = True
            for i in range(0, len(coords), 2):
                px, py = coords[i], coords[i + 1]
                if px < x1 or px > x2 or py < y1 or py > y2:
                    all_inside = False
                    break
            if all_inside:
                selected_wires.append(conn)
        # Find labels in rectangle
        selected_labels = []
        for conn in self.connections:
            if conn.label_id:
                bbox = self.canvas.bbox(conn.label_id)
                if bbox:
                    lx1, ly1, lx2, ly2 = bbox
                    if lx1 >= x1 and ly1 >= y1 and lx2 <= x2 and ly2 <= y2:
                        if conn not in selected_wires:
                            selected_labels.append(conn)
        if not selected_nodes and not selected_wires and not selected_labels:
            self._multi_select["active"] = False
            return
        self._multi_select["nodes"] = selected_nodes
        self._multi_select["wires"] = selected_wires
        self._multi_select["labels"] = selected_labels
        # Draw highlights
        highlights = []
        for name in selected_nodes:
            node = self.nodes[name]
            hid = self.canvas.create_rectangle(
                node.x - 2, node.y - 2,
                node.x + node.width + 2, node.y + node.height + 2,
                outline="#4A90D9", width=2, dash=(4, 2),
            )
            highlights.append(hid)
        for conn in selected_wires:
            if conn.line_id:
                self.canvas.itemconfigure(conn.line_id, width=self._wire_selected_width(conn))
        self._multi_select["highlights"] = highlights
        self._multi_select["active"] = True
        self._update_status_bar()

    def _on_multi_drag(self, event):
        cx, cy = self._cx(event), self._cy(event)
        dx = cx - self._multi_select["drag_x"]
        dy = cy - self._multi_select["drag_y"]
        sdx = self._snap_value(dx) if abs(dx) >= self.GRID_STEP / 2 else 0
        sdy = self._snap_value(dy) if abs(dy) >= self.GRID_STEP / 2 else 0
        if sdx == 0 and sdy == 0:
            return
        self._multi_select["drag_x"] = cx
        self._multi_select["drag_y"] = cy
        # Move nodes
        for name in self._multi_select["nodes"]:
            node = self.nodes.get(name)
            if not node:
                continue
            self.canvas.move(f"node:{name}", sdx, sdy)
            node.x += sdx
            node.y += sdy
            for port in node.inputs + node.outputs:
                if port.manual_y is not None:
                    port.manual_y += sdy
        # Move free wires
        moved_junctions: set[str] = set()
        for conn in self._multi_select["wires"]:
            if conn.free_points:
                conn.free_points = [(px + sdx, py + sdy) for px, py in conn.free_points]
            if conn.waypoints:
                conn.waypoints = [(wx + sdx, wy + sdy) for wx, wy in conn.waypoints]
            if conn.manual_mid_x is not None:
                conn.manual_mid_x += sdx
            if conn.manual_mid_y is not None:
                conn.manual_mid_y += sdy
            if conn.label_x is not None:
                conn.label_x += sdx
            if conn.label_y is not None:
                conn.label_y += sdy
            # Move junction PORTs that aren't already in selected nodes
            for jp in conn.junction_ports:
                jname = jp.get("node")
                if jname and jname not in self._multi_select["nodes"] and jname not in moved_junctions:
                    jnode = self.nodes.get(jname)
                    if jnode:
                        self.canvas.move(f"node:{jname}", sdx, sdy)
                        jnode.x += sdx
                        jnode.y += sdy
                        for port in jnode.inputs + jnode.outputs:
                            if port.manual_y is not None:
                                port.manual_y += sdy
                        moved_junctions.add(jname)
        # Move label positions for selected labels
        for conn in self._multi_select["labels"]:
            if conn.label_x is not None:
                conn.label_x += sdx
            if conn.label_y is not None:
                conn.label_y += sdy
        # Move highlight rectangles
        for hid in self._multi_select["highlights"]:
            self.canvas.move(hid, sdx, sdy)
        self._update_connections()

    def _find_junctions_on_segment(self, connection: Connection, ax: float, ay: float,
                                     bx: float, by: float, direction: str) -> list[str]:
        """Find PORT junction node names sitting on the given segment of a connection."""
        result = []
        tol = 8
        min_x, max_x = min(ax, bx), max(ax, bx)
        min_y, max_y = min(ay, by), max(ay, by)
        # Check junction_ports first
        jp_names = {jp.get("node") for jp in connection.junction_ports}
        for jnode in self.nodes.values():
            if jnode.kind != "PORT":
                continue
            ref_x, ref_y = self._junction_port_xy(jnode)
            on_seg = False
            if direction == "h":
                if abs(ref_y - ay) < tol and min_x - tol <= ref_x <= max_x + tol:
                    on_seg = True
            else:
                if abs(ref_x - ax) < tol and min_y - tol <= ref_y <= max_y + tol:
                    on_seg = True
            if on_seg and (jnode.name in jp_names or self._find_parent_wire(jnode) is connection):
                result.append(jnode.name)
        return result

    def _snap_junctions_to_wires(self):
        """Snap all PORT (junction) nodes so their port circle sits on the parent wire."""
        for node in list(self.nodes.values()):
            if node.kind != "PORT":
                continue
            parent = self._find_parent_wire(node)
            if not parent:
                continue
            coords = self._connection_line_coords(parent)
            if not coords or len(coords) < 4:
                continue
            # Use port position as reference, not node center
            ref_x, ref_y = self._junction_port_xy(node)
            px, py = self._nearest_point_on_polyline(coords, ref_x, ref_y)
            # Compute new node position so port is at (px, py)
            ports = node.inputs + node.outputs
            port_side = ports[0].side if ports else "left"
            new_x, new_y = self._junction_node_pos(px, py, port_side, node.width)
            ddx = new_x - node.x
            ddy = new_y - node.y
            if ddx == 0 and ddy == 0:
                continue
            self.canvas.move(f"node:{node.name}", ddx, ddy)
            node.x += ddx
            node.y += ddy
            for port in node.inputs + node.outputs:
                if port.manual_y is not None:
                    port.manual_y += ddy

    def _reposition_junctions(self, connection: Connection):
        """Reposition all junction PORTs on a connection to stay on the wire."""
        coords = self._connection_line_coords(connection)
        if not coords or len(coords) < 4:
            return
        for jp in connection.junction_ports:
            jnode = self.nodes.get(jp.get("node"))
            if not jnode:
                continue
            ref_x, ref_y = self._junction_port_xy(jnode)
            px, py = self._nearest_point_on_polyline(coords, ref_x, ref_y)
            ports = jnode.inputs + jnode.outputs
            port_side = ports[0].side if ports else "left"
            new_x, new_y = self._junction_node_pos(px, py, port_side, jnode.width)
            ddx = new_x - jnode.x
            ddy = new_y - jnode.y
            if ddx == 0 and ddy == 0:
                continue
            self.canvas.move(f"node:{jnode.name}", ddx, ddy)
            jnode.x += ddx
            jnode.y += ddy
            for port in jnode.inputs + jnode.outputs:
                if port.manual_y is not None:
                    port.manual_y += ddy

    def _on_release(self, _event):
        # Multi-select drag release is handled by _on_canvas_release
        if self._multi_select["dragging"]:
            return
        if self._drag_data["node"] and not self._resize_data["node"]:
            node = self._drag_data["node"]
            for connection in self.connections:
                if connection.waypoints and (connection.src or connection.dst):
                    src_node = connection.src[0] if connection.src else None
                    dst_node = connection.dst[0] if connection.dst else None
                    if src_node == node.name or dst_node == node.name:
                        self._simplify_waypoints(connection)
            self._update_connections()
            self._snap_junctions_to_wires()
            self._update_connections()
            self._record_history()
        self._drag_data["node"] = None
        self._resize_data["node"] = None
        self._resize_data["mode"] = None
        self._resize_data["orig"] = None
        self._clear_alignment_guides()

    def _on_motion(self, event):
        if self._mode != "normal":
            return
        # Multi-select drag is handled by _on_canvas_drag
        if self._multi_select["dragging"]:
            return
        if self._resize_data["node"] is not None:
            self._on_resize_motion(event)
            return
        node = self._drag_data["node"]
        if not node:
            return
        cx, cy = self._cx(event), self._cy(event)
        # PORT nodes: constrain movement along parent wire
        if node.kind == "PORT":
            parent_wire = self._find_parent_wire(node)
            if parent_wire:
                coords = self._connection_line_coords(parent_wire)
                if coords and len(coords) >= 4:
                    px, py = self._nearest_point_on_polyline(coords, cx, cy)
                    # Snap to grid for consistent movement granularity
                    px = self._snap_value(px)
                    py = self._snap_value(py)
                    # Re-project snapped point onto wire
                    px, py = self._nearest_point_on_polyline(coords, px, py)
                    ports = node.inputs + node.outputs
                    port_side = ports[0].side if ports else "left"
                    new_x, new_y = self._junction_node_pos(px, py, port_side, node.width)
                    ddx = new_x - node.x
                    ddy = new_y - node.y
                    if ddx == 0 and ddy == 0:
                        return
                    self._drag_data["x"] = cx
                    self._drag_data["y"] = cy
                    self.canvas.move(f"node:{node.name}", ddx, ddy)
                    node.x += ddx
                    node.y += ddy
                    for port in node.inputs + node.outputs:
                        if port.manual_y is not None:
                            port.manual_y += ddy
                    self._update_connections()
                    self._draw_point_alignment_guides(px, py)
                    return
        dx = cx - self._drag_data["x"]
        dy = cy - self._drag_data["y"]
        target_x = node.x + dx
        target_y = node.y + dy
        snapped_x = self._snap_value(target_x)
        snapped_y = self._snap_value(target_y)
        # Auto-alignment snapping
        align_x, align_y = self._calc_alignment(node, snapped_x, snapped_y)
        snapped_x = align_x
        snapped_y = align_y
        dx = snapped_x - node.x
        dy = snapped_y - node.y
        if dx == 0 and dy == 0:
            return
        self._drag_data["x"] = cx
        self._drag_data["y"] = cy
        self.canvas.move(f"node:{node.name}", dx, dy)
        node.x += dx
        node.y += dy
        for port in node.inputs + node.outputs:
            if port.manual_y is not None:
                port.manual_y += dy
        self._update_connections()
        # Reposition junction PORTs on wires connected to this block
        for conn in self.connections:
            if conn.junction_ports and (
                (conn.src and conn.src[0] == node.name) or
                (conn.dst and conn.dst[0] == node.name)
            ):
                self._reposition_junctions(conn)
        self._update_connections()
        self._draw_alignment_guides(node)

    def _hit_test_edge(self, node: Node, x: float, y: float, threshold: float = 6.0) -> str | None:
        if not node.resize_enabled:
            return None
        left = node.x
        right = node.x + node.width
        top = node.y
        bottom = node.y + node.height
        corner_t = threshold * 1.5
        if abs(x - left) <= corner_t and abs(y - top) <= corner_t:
            return "top_left"
        if abs(x - right) <= corner_t and abs(y - top) <= corner_t:
            return "top_right"
        if abs(x - left) <= corner_t and abs(y - bottom) <= corner_t:
            return "bottom_left"
        if abs(x - right) <= corner_t and abs(y - bottom) <= corner_t:
            return "bottom_right"
        if left - threshold <= x <= right + threshold and abs(y - top) <= threshold:
            return "top"
        if left - threshold <= x <= right + threshold and abs(y - bottom) <= threshold:
            return "bottom"
        if top - threshold <= y <= bottom + threshold and abs(x - left) <= threshold:
            return "left"
        if top - threshold <= y <= bottom + threshold and abs(x - right) <= threshold:
            return "right"
        return None

    def _edge_for_point(self, node: Node, x: float, y: float, threshold: float = 6.0) -> str | None:
        left = node.x
        right = node.x + node.width
        top = node.y
        bottom = node.y + node.height
        if left - threshold <= x <= right + threshold and abs(y - top) <= threshold:
            return "top"
        if left - threshold <= x <= right + threshold and abs(y - bottom) <= threshold:
            return "bottom"
        if top - threshold <= y <= bottom + threshold and abs(x - left) <= threshold:
            return "left"
        if top - threshold <= y <= bottom + threshold and abs(x - right) <= threshold:
            return "right"
        return None

    def _edge_offset(self, node: Node, side: str, x: float, y: float) -> float:
        if side in ("left", "right"):
            if node.height == 0:
                return 0.5
            return max(0.0, min(1.0, (y - node.y) / node.height))
        if node.width == 0:
            return 0.5
        return max(0.0, min(1.0, (x - node.x) / node.width))

    def _toggle_resize_active_node(self):
        if self._mode != "normal":
            return
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node:
            return
        saved = [(p, p.manual_y, p.offset) for p in node.inputs + node.outputs]
        node.resize_enabled = not node.resize_enabled
        self._redraw_node(node)
        for p, my, off in saved:
            p.manual_y = my
            p.offset = off
            if p.canvas_id:
                px, py = self._port_position(node, p)
                r = self.PORT_RADIUS
                self.canvas.coords(p.canvas_id, px - r, py - r, px + r, py + r)
        self._update_connections()

    def _on_resize_motion(self, event):
        node = self._resize_data["node"]
        mode = self._resize_data["mode"]
        orig = self._resize_data["orig"]
        if not node or not mode or not orig:
            return
        cx, cy = self._cx(event), self._cy(event)
        if node.kind != "BLOCK" and node.kind not in self._CUSTOM_GATE_KINDS and node.kind not in self._DIAGRAM_SHAPES:
            self._resize_gate(node, mode, orig, cx, cy)
            return
        orig_x, orig_y, orig_width, orig_height = orig
        dx = cx - self._resize_data["x"]
        dy = cy - self._resize_data["y"]
        if node.kind == "BLOCK":
            min_width = 80
            min_height = 60
        else:
            gate_def = self._gate_definitions().get(node.kind, {})
            default_w = gate_def.get("width", orig_width)
            default_h = gate_def.get("height", orig_height)
            min_width = max(self.GRID_STEP, default_w // 2)
            min_height = max(self.GRID_STEP, default_h // 2)
        old_port_positions = []
        for port in node.inputs + node.outputs:
            if port.canvas_id:
                old_port_positions.append((port, self._port_center(port.canvas_id)))
        if mode == "left":
            new_width = max(min_width, orig_width - dx)
            new_width = self._snap_value(new_width, min_width)
            node.x = orig_x + (orig_width - new_width)
            node.width = new_width
        elif mode == "right":
            node.width = self._snap_value(max(min_width, orig_width + dx), min_width)
        elif mode == "top":
            new_height = max(min_height, orig_height - dy)
            new_height = self._snap_value(new_height, min_height)
            node.y = orig_y + (orig_height - new_height)
            node.height = new_height
            if node.kind == "BLOCK":
                for port, prev in old_port_positions:
                    if port.side in ("left", "right"):
                        port.manual_y = prev[1]
            else:
                self._reposition_gate_ports(node)
        elif mode == "bottom":
            node.height = self._snap_value(max(min_height, orig_height + dy), min_height)
            if node.kind == "BLOCK":
                for port, prev in old_port_positions:
                    if port.side in ("left", "right"):
                        port.manual_y = prev[1]
            else:
                self._reposition_gate_ports(node)
        elif mode.startswith("top_") or mode.startswith("bottom_"):
            aspect = orig_width / orig_height if orig_height else 1.0
            if mode == "bottom_right":
                new_width = max(min_width, orig_width + dx)
                new_height = new_width / aspect if aspect else new_width
                if new_height < min_height:
                    new_height = min_height
                    new_width = new_height * aspect
                new_width = self._snap_value(new_width, min_width)
                new_height = self._snap_value(new_width / aspect if aspect else new_width, min_height)
                node.width = new_width
                node.height = new_height
            elif mode == "bottom_left":
                new_width = max(min_width, orig_width - dx)
                new_height = new_width / aspect if aspect else new_width
                if new_height < min_height:
                    new_height = min_height
                    new_width = new_height * aspect
                new_width = self._snap_value(new_width, min_width)
                new_height = self._snap_value(new_width / aspect if aspect else new_width, min_height)
                node.x = orig_x + (orig_width - new_width)
                node.width = new_width
                node.height = new_height
            elif mode == "top_right":
                new_width = max(min_width, orig_width + dx)
                new_height = new_width / aspect if aspect else new_width
                if new_height < min_height:
                    new_height = min_height
                    new_width = new_height * aspect
                new_width = self._snap_value(new_width, min_width)
                new_height = self._snap_value(new_width / aspect if aspect else new_width, min_height)
                node.y = orig_y + (orig_height - new_height)
                node.width = new_width
                node.height = new_height
            elif mode == "top_left":
                new_width = max(min_width, orig_width - dx)
                new_height = new_width / aspect if aspect else new_width
                if new_height < min_height:
                    new_height = min_height
                    new_width = new_height * aspect
                new_width = self._snap_value(new_width, min_width)
                new_height = self._snap_value(new_width / aspect if aspect else new_width, min_height)
                node.x = orig_x + (orig_width - new_width)
                node.y = orig_y + (orig_height - new_height)
                node.width = new_width
                node.height = new_height
            if node.kind != "BLOCK":
                self._reposition_gate_ports(node)
            else:
                for port in node.inputs + node.outputs:
                    if port.side in ("left", "right"):
                        port.manual_y = node.y + port.offset * node.height
        self._redraw_node(node)
        self._update_connections()
        self._draw_alignment_guides(node)

    def _reposition_gate_ports(self, node: Node):
        # Group ports by side for proper offset calculation
        by_side: dict[str, list[Port]] = {}
        for port in node.inputs + node.outputs:
            by_side.setdefault(port.side, []).append(port)
        for side, ports in by_side.items():
            n = len(ports)
            for idx, port in enumerate(ports):
                port.offset = (idx + 1) / (n + 1)
                if side in ("left", "right"):
                    port.manual_y = node.y + port.offset * node.height

    def _resize_gate(self, node: Node, mode: str, orig: tuple, cx: float, cy: float):
        base_image = self._gate_base_image(node.kind)
        if not base_image:
            return
        old_port_positions = []
        for port in node.inputs + node.outputs:
            if port.canvas_id:
                old_port_positions.append((port, self._port_center(port.canvas_id)))
        orig_x, orig_y, orig_width, orig_height, _orig_subsample = orig
        orig_right = orig_x + orig_width
        orig_bottom = orig_y + orig_height
        base_w = base_image.width()
        base_h = base_image.height()
        aspect = base_w / base_h if base_h else 1.0
        min_size = self.GRID_STEP

        anchor_x = orig_x
        anchor_y = orig_y
        if mode == "right" or mode == "bottom_right":
            desired_w = max(min_size, cx - orig_x)
            desired_w = self._snap_value(desired_w, min_size)
            desired_h = desired_w / aspect if aspect else desired_w
            anchor_x = orig_x
            anchor_y = orig_y
        elif mode == "top" or mode == "top_right":
            desired_h = max(min_size, orig_bottom - cy)
            desired_h = self._snap_value(desired_h, min_size)
            desired_w = desired_h * aspect
            anchor_x = orig_x
            anchor_y = orig_bottom
        elif mode == "left" or mode == "top_left":
            desired_w = max(min_size, orig_right - cx)
            desired_w = self._snap_value(desired_w, min_size)
            desired_h = desired_w / aspect if aspect else desired_w
            anchor_x = orig_right
            anchor_y = orig_bottom
        elif mode == "bottom" or mode == "bottom_left":
            desired_h = max(min_size, cy - orig_y)
            desired_h = self._snap_value(desired_h, min_size)
            desired_w = desired_h * aspect
            anchor_x = orig_right
            anchor_y = orig_y
        else:
            return

        desired_w = max(min_size, desired_w)
        subsample = max(1, int(round(base_w / desired_w))) if base_w else 1
        node.image_subsample = subsample
        node.width = base_w / subsample if subsample else base_w
        node.height = base_h / subsample if subsample else base_h
        if anchor_x == orig_x:
            node.x = orig_x
        else:
            node.x = anchor_x - node.width
        if anchor_y == orig_y:
            node.y = orig_y
        else:
            node.y = anchor_y - node.height
        self._reposition_gate_ports(node)
        self._clamp_ports_to_node(node)
        self._redraw_node(node)
        self._update_connections()
        self._draw_alignment_guides(node)

    def _on_resize_release(self, _event):
        if self._resize_data["node"]:
            self._record_history()
        self._resize_data["node"] = None
        self._resize_data["mode"] = None
        self._resize_data["orig"] = None
        self._clear_alignment_guides()
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

    def _redraw_node(self, node: Node):
        for item in node.items:
            self.canvas.delete(item)
        node.items.clear()
        self._port_items = {key: value for key, value in self._port_items.items() if value[0] != node.name}
        self._draw_node(node)
        self._apply_z_order(active_node_name=node.name)

    def _snap_value(self, value: float, min_value: int | None = None) -> int:
        snapped = int(round(value / self.GRID_STEP) * self.GRID_STEP)
        if min_value is not None:
            return max(min_value, snapped)
        return snapped

    def _clamp_ports_to_node(self, node: Node):
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        radius = self.PORT_RADIUS
        for port in node.inputs + node.outputs:
            if port.side in ("left", "right"):
                if port.manual_y is None:
                    port.manual_y = y1 + port.offset * (y2 - y1)
                min_y = y1 + radius
                max_y = y2 - radius
                clamped = max(min_y, min(port.manual_y, max_y))
                port.manual_y = clamped
                port.offset = 0 if y2 == y1 else (clamped - y1) / (y2 - y1)
            else:
                port.manual_y = None
                port.offset = max(0.0, min(1.0, port.offset))

    @staticmethod
    def _snap_to_step(value: float, step: int) -> float:
        return round(value / step) * step

    def _apply_z_order(self, active_node_name: str | None = None):
        nodes = list(self.nodes.values())
        nodes.sort(
            key=lambda node: (
                node.level,
                1 if active_node_name and node.name == active_node_name else 0,
            )
        )
        non_port_nodes = [n for n in nodes if n.kind != "PORT"]
        port_nodes = [n for n in nodes if n.kind == "PORT"]
        for node in non_port_nodes:
            self.canvas.tag_raise(f"node:{node.name}")
        for connection in self.connections:
            self._raise_connection(connection)
        for node in port_nodes:
            self.canvas.tag_raise(f"node:{node.name}")

    def _next_level(self) -> int:
        if not self.nodes:
            return 0
        return max(node.level for node in self.nodes.values()) + 1

    @classmethod
    def _color_to_hex(cls, color: str) -> str:
        if not color:
            return "#666666"
        lookup = cls.COLOR_NAME_TO_HEX.get(color.upper())
        return lookup if lookup else color

    @classmethod
    def _color_to_name(cls, color: str) -> str:
        if not color:
            return "GRAY"
        return cls.COLOR_HEX_TO_NAME.get(color.lower(), color)

    def _raise_connection(self, connection: Connection):
        if connection.line_id:
            self.canvas.tag_raise(connection.line_id)
        if connection.label_id:
            self.canvas.tag_raise(connection.label_id)

    def _lower_connection(self, connection: Connection):
        if connection.line_id:
            self.canvas.tag_lower(connection.line_id)
        if connection.label_id:
            self.canvas.tag_lower(connection.label_id)

    def _create_port_oval(self, x: float, y: float, color: str) -> int:
        radius = self.PORT_RADIUS
        hidden = not self._show_ports and color == "black"
        fill = "" if hidden else color
        outline = "" if hidden else color
        width = 0 if hidden else 1
        return self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    def _port_position(self, node: Node, port: Port) -> tuple[float, float]:
        import math as _math
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        if port.side == "left":
            py = port.manual_y if port.manual_y is not None else y1 + port.offset * (y2 - y1)
            px = x1
            # Adjust for OR/XOR gate curved left side
            kind = node.kind
            if (y2 - y1) > 0 and (kind.startswith("OR") or kind.startswith("XOR")):
                f = (py - y1) / (y2 - y1)
                curve_depth = node.width * 0.15
                px = x1 + curve_depth * _math.sin(f * _math.pi)
            return (px, py)
        if port.side == "right":
            py = port.manual_y if port.manual_y is not None else y1 + port.offset * (y2 - y1)
            return (x2, py)
        if port.side == "top":
            px = x1 + port.offset * (x2 - x1)
            return (px, y1)
        if port.side == "bottom":
            px = x1 + port.offset * (x2 - x1)
            return (px, y2)
        py = port.manual_y if port.manual_y is not None else (y1 + y2) / 2
        return (x1, py)

    def _register_port(self, node_name: str, port: Port):
        if port.canvas_id is None:
            return
        self._port_items[port.canvas_id] = (node_name, port.name)
        self.canvas.addtag_withtag("port", port.canvas_id)
        self.canvas.addtag_withtag(f"port:{node_name}:{port.name}", port.canvas_id)

    def _port_side(self, port_info: tuple[str, str] | None) -> str | None:
        if not port_info:
            return None
        node_name, port_name = port_info
        node = self.nodes.get(node_name)
        if not node:
            return None
        port = next((p for p in node.inputs + node.outputs if p.name == port_name), None)
        if not port:
            return None
        return port.side

    def _update_connections(self):
        for connection in self.connections:
            if not connection.line_id:
                continue
            coords = self._connection_line_coords(connection)
            if not coords:
                continue
            self.canvas.coords(
                connection.line_id,
                *coords,
            )
            self._update_label(connection, coords)

    def _connection_coords_horizontal(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        manual_mid_x: float | None = None,
    ) -> list[float]:
        x1, y1 = start
        x2, y2 = end
        if x1 == x2 or y1 == y2:
            return [x1, y1, x2, y2]
        mid_x = manual_mid_x if manual_mid_x is not None else (x1 + x2) / 2
        return [x1, y1, mid_x, y1, mid_x, y2, x2, y2]

    def _connection_coords_vertical(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        manual_mid_y: float | None = None,
    ) -> list[float]:
        x1, y1 = start
        x2, y2 = end
        if x1 == x2 or y1 == y2:
            return [x1, y1, x2, y2]
        mid_y = manual_mid_y if manual_mid_y is not None else (y1 + y2) / 2
        return [x1, y1, x1, mid_y, x2, mid_y, x2, y2]

    def _connection_coords_orthogonal(
        self,
        connection: Connection,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> list[float]:
        x1, y1 = start
        x2, y2 = end
        src_side = self._port_side(connection.src) if connection.src else None
        if src_side in ("top", "bottom"):
            return [x1, y1, x1, y2, x2, y2]
        return [x1, y1, x2, y1, x2, y2]

    def _connection_orientation(self, connection: Connection) -> str | None:
        if connection.manual_mid_x is not None:
            return "horizontal"
        if connection.manual_mid_y is not None:
            return "vertical"
        if not connection.src or not connection.dst:
            return None
        src_node, src_port = connection.src
        dst_node, dst_port = connection.dst
        src_side = self._port_side((src_node, src_port))
        dst_side = self._port_side((dst_node, dst_port))
        if not src_side or not dst_side:
            return None
        if src_side in ("left", "right") and dst_side in ("left", "right"):
            return "horizontal"
        if src_side in ("top", "bottom") and dst_side in ("top", "bottom"):
            return "vertical"
        return "orthogonal"

    def _connection_manual_locked(self, connection: Connection) -> bool:
        if connection.manual_mid_x is not None or connection.manual_mid_y is not None:
            return False
        return self._connection_orientation(connection) == "orthogonal"

    def _connection_line_coords(self, connection: Connection) -> list[float] | None:
        if connection.free_points:
            coords = [c for point in connection.free_points for c in point]
            return coords if len(coords) >= 4 else None
        if connection.src and connection.dst:
            src_node, src_port = connection.src
            dst_node, dst_port = connection.dst
            src_port_id = self._get_port_canvas_id(src_node, src_port, "out")
            dst_port_id = self._get_port_canvas_id(dst_node, dst_port, "in")
            if not src_port_id or not dst_port_id:
                return None
            x1, y1 = self._port_center(src_port_id)
            x2, y2 = self._port_center(dst_port_id)
            if connection.waypoints:
                src_side = self._port_side((src_node, src_port))
                dst_side = self._port_side((dst_node, dst_port))
                points = [(x1, y1)]
                first_wp = True
                for wx, wy in connection.waypoints:
                    last_x, last_y = points[-1]
                    if first_wp and src_side in ("top", "bottom"):
                        if last_y != wy:
                            points.append((last_x, wy))
                        if last_x != wx:
                            points.append((wx, wy))
                    else:
                        if last_x != wx:
                            points.append((wx, last_y))
                        if last_y != wy:
                            points.append((wx, wy))
                    first_wp = False
                last_x, last_y = points[-1]
                if dst_side in ("left", "right"):
                    if last_y != y2:
                        points.append((last_x, y2))
                    if last_x != x2:
                        points.append((x2, y2))
                else:
                    if last_x != x2:
                        points.append((x2, last_y))
                    if last_y != y2:
                        points.append((x2, y2))
                # Clean up collinear and backtracking points
                cleaned = [points[0]]
                for i in range(1, len(points)):
                    p = points[i]
                    if p == cleaned[-1]:
                        continue
                    while len(cleaned) >= 2:
                        prev = cleaned[-2]
                        curr = cleaned[-1]
                        if (prev[0] == curr[0] == p[0]) or (prev[1] == curr[1] == p[1]):
                            cleaned.pop()
                        else:
                            break
                    cleaned.append(p)
                coords = [c for p in cleaned for c in p]
                return coords if len(coords) >= 4 else [x1, y1, x2, y2]
            if connection.manual_mid_x is not None:
                return self._connection_coords_horizontal((x1, y1), (x2, y2), connection.manual_mid_x)
            if connection.manual_mid_y is not None:
                return self._connection_coords_vertical((x1, y1), (x2, y2), connection.manual_mid_y)
            orientation = self._connection_orientation(connection)
            if orientation == "horizontal":
                return self._connection_coords_horizontal((x1, y1), (x2, y2), connection.manual_mid_x)
            if orientation == "vertical":
                return self._connection_coords_vertical((x1, y1), (x2, y2), connection.manual_mid_y)
            if orientation == "orthogonal":
                return self._connection_coords_orthogonal(connection, (x1, y1), (x2, y2))
            return self._connection_coords_horizontal((x1, y1), (x2, y2), connection.manual_mid_x)
        if connection.dst:
            dst_node, dst_port = connection.dst
            dst_port_id = self._get_port_canvas_id(dst_node, dst_port, "in")
            if not dst_port_id:
                return None
            x2, y2 = self._port_center(dst_port_id)
            return [x2 - 50, y2, x2, y2]
        if connection.src:
            src_node, src_port = connection.src
            src_port_id = self._get_port_canvas_id(src_node, src_port, "out")
            if not src_port_id:
                return None
            x1, y1 = self._port_center(src_port_id)
            return [x1, y1, x1 + 50, y1]
        return None

    def _label_position(self, coords: list[float]) -> tuple[float, float]:
        if len(coords) >= 8:
            x1, y1, x2 = coords[0], coords[1], coords[2]
            return ((x1 + x2) / 2, y1 - 4)
        x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
        mid_x = (x1 + x2) / 2
        top_y = min(y1, y2) - 4
        return (mid_x, top_y)

    def _update_label(self, connection: Connection, coords: list[float]):
        if not connection.label_id:
            return
        if connection.label_x is not None and connection.label_y is not None:
            return
        label_x, label_y = self._label_position(coords)
        self.canvas.coords(connection.label_id, label_x, label_y)

    def _simplify_waypoints(self, connection: Connection):
        if not connection.waypoints or not connection.src or not connection.dst:
            return
        src_id = self._get_port_canvas_id(connection.src[0], connection.src[1])
        dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1])
        if not src_id or not dst_id:
            return
        src = self._port_center(src_id)
        dst = self._port_center(dst_id)
        points = [src] + list(connection.waypoints) + [dst]
        # Remove duplicates and collinear/backtracking points
        cleaned = [points[0]]
        for i in range(1, len(points)):
            p = points[i]
            if p == cleaned[-1]:
                continue
            while len(cleaned) >= 2:
                prev = cleaned[-2]
                curr = cleaned[-1]
                if (prev[0] == curr[0] == p[0]) or (prev[1] == curr[1] == p[1]):
                    cleaned.pop()
                else:
                    break
            cleaned.append(p)
        connection.waypoints = list(cleaned[1:-1])

    def _find_port(self, node_name: str, port_name: str, kind: str | None = None) -> tuple[Node, Port] | None:
        node = self.nodes.get(node_name)
        if not node:
            return None
        for port in node.inputs + node.outputs:
            if port.name == port_name:
                return node, port
        return None

    def _on_wire_press(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        if self._delete_mode:
            item = self.canvas.find_withtag("current")
            if not item:
                return
            line_id = item[0]
            connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
            if not connection:
                return
            self._remove_connection(connection)
            return
        if self._mode != "normal":
            return
        # Check if clicking on a multi-selected wire → start multi-drag
        if self._multi_select["nodes"] or self._multi_select["wires"] or self._multi_select["labels"]:
            item = self.canvas.find_withtag("current")
            if item:
                line_id = item[0]
                clicked_conn = next((c for c in self.connections if c.line_id == line_id), None)
                if clicked_conn and clicked_conn in self._multi_select["wires"]:
                    self._multi_select["dragging"] = True
                    self._multi_select["active"] = True
                    self._multi_select["drag_x"] = event.x
                    self._multi_select["drag_y"] = event.y
                    return
            self._clear_multi_select()
        self._deselect_label()
        item = self.canvas.find_withtag("current")
        if not item:
            return
        line_id = item[0]
        connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
        if not connection:
            return
        self._deselect_wire()
        self._selected_wire = connection
        self.canvas.itemconfigure(line_id, width=self._wire_selected_width(connection))
        # Free-point wire: enable whole-wire drag
        if connection.free_points and not connection.src and not connection.dst:
            self._drag_wire["connection"] = connection
            self._drag_wire["mode"] = "free_wire"
            self._drag_wire["x"] = event.x
            self._drag_wire["y"] = event.y
            return
        coords = self._connection_line_coords(connection)
        if not coords:
            return
        if len(coords) == 4:
            # Check proximity to the single segment (horizontal or vertical)
            on_h = self._near_horizontal_segment(event.x, event.y, coords[0], coords[2], coords[1])
            on_v = self._near_vertical_segment(event.x, event.y, coords[0], coords[1], coords[3])
            if not on_h and not on_v:
                return
            # Straight wire with both endpoints and no waypoints: move both ports
            if connection.src and connection.dst and not connection.waypoints:
                src_info = self._find_port(connection.src[0], connection.src[1], "out")
                dst_info = self._find_port(connection.dst[0], connection.dst[1], "in")
                if src_info and dst_info:
                    src_node, src_port = src_info
                    dst_node, dst_port = dst_info
                    if not src_node.resize_enabled and not dst_node.resize_enabled:
                        self._drag_wire["connection"] = connection
                        self._drag_wire["mode"] = "both_ports"
                        self._drag_wire["src_node"] = src_node
                        self._drag_wire["src_port"] = src_port
                        self._drag_wire["dst_node"] = dst_node
                        self._drag_wire["dst_port"] = dst_port
                        self._drag_wire["x"] = event.x
                        self._drag_wire["y"] = event.y
                        return
            if connection.dst:
                port_info = self._find_port(connection.dst[0], connection.dst[1], "in")
                if not port_info:
                    return
                node, port = port_info
                if node.resize_enabled:
                    return
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "dst_port"
                self._drag_wire["node"] = node
                self._drag_wire["port"] = port
                return
            if connection.src:
                port_info = self._find_port(connection.src[0], connection.src[1], "out")
                if not port_info:
                    return
                node, port = port_info
                if node.resize_enabled:
                    return
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "src_port"
                self._drag_wire["node"] = node
                self._drag_wire["port"] = port
                return
            return
        if connection.waypoints:
            coords = self._connection_line_coords(connection)
            if not coords or len(coords) < 6:
                return
            points = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
            n = len(points)
            for i in range(n - 1):
                ax, ay = points[i]
                bx, by = points[i + 1]
                is_first = (i == 0)
                is_last = (i == n - 2)
                if ay == by and self._near_horizontal_segment(event.x, event.y, ax, bx, ay):
                    if is_first and connection.src:
                        port_info = self._find_port(connection.src[0], connection.src[1])
                        if port_info:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "src_port"
                            self._drag_wire["node"], self._drag_wire["port"] = port_info
                            self._drag_wire["seg_dir"] = "h"
                            return
                    if is_last and connection.dst:
                        port_info = self._find_port(connection.dst[0], connection.dst[1])
                        if port_info:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "dst_port"
                            self._drag_wire["node"], self._drag_wire["port"] = port_info
                            self._drag_wire["seg_dir"] = "h"
                            return
                    self._drag_wire["connection"] = connection
                    self._drag_wire["mode"] = "wp_h"
                    self._drag_wire["offset"] = event.y - ay
                    self._drag_wire["seg_index"] = i
                    self._drag_wire["points"] = points
                    # Find PORT junctions on this segment at drag start
                    self._drag_wire["seg_junctions"] = self._find_junctions_on_segment(
                        connection, ax, ay, bx, by, "h")
                    return
                if ax == bx and self._near_vertical_segment(event.x, event.y, ax, ay, by):
                    if is_first and connection.src:
                        port_info = self._find_port(connection.src[0], connection.src[1])
                        if port_info:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "src_port"
                            self._drag_wire["node"], self._drag_wire["port"] = port_info
                            self._drag_wire["seg_dir"] = "v"
                            return
                    if is_last and connection.dst:
                        port_info = self._find_port(connection.dst[0], connection.dst[1])
                        if port_info:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "dst_port"
                            self._drag_wire["node"], self._drag_wire["port"] = port_info
                            self._drag_wire["seg_dir"] = "v"
                            return
                    self._drag_wire["connection"] = connection
                    self._drag_wire["mode"] = "wp_v"
                    self._drag_wire["offset"] = event.x - ax
                    self._drag_wire["seg_index"] = i
                    self._drag_wire["points"] = points
                    # Find PORT junctions on this segment at drag start
                    self._drag_wire["seg_junctions"] = self._find_junctions_on_segment(
                        connection, ax, ay, bx, by, "v")
                    return
            return
        if len(coords) == 6 and not connection.waypoints:
            p0 = (coords[0], coords[1])
            p1 = (coords[2], coords[3])
            p2 = (coords[4], coords[5])
            if p0[1] == p1[1] and self._near_horizontal_segment(event.x, event.y, p0[0], p1[0], p0[1]):
                if connection.src:
                    port_info = self._find_port(connection.src[0], connection.src[1])
                    if port_info:
                        node, port = port_info
                        if not node.resize_enabled:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "src_port"
                            self._drag_wire["node"] = node
                            self._drag_wire["port"] = port
                            return
            if p0[0] == p1[0] and self._near_vertical_segment(event.x, event.y, p0[0], p0[1], p1[1]):
                if connection.src:
                    port_info = self._find_port(connection.src[0], connection.src[1])
                    if port_info:
                        node, port = port_info
                        if not node.resize_enabled:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "src_port"
                            self._drag_wire["node"] = node
                            self._drag_wire["port"] = port
                            return
            if p1[1] == p2[1] and self._near_horizontal_segment(event.x, event.y, p1[0], p2[0], p1[1]):
                if connection.dst:
                    port_info = self._find_port(connection.dst[0], connection.dst[1])
                    if port_info:
                        node, port = port_info
                        if not node.resize_enabled:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "dst_port"
                            self._drag_wire["node"] = node
                            self._drag_wire["port"] = port
                            return
            if p1[0] == p2[0] and self._near_vertical_segment(event.x, event.y, p1[0], p1[1], p2[1]):
                if connection.dst:
                    port_info = self._find_port(connection.dst[0], connection.dst[1])
                    if port_info:
                        node, port = port_info
                        if not node.resize_enabled:
                            self._drag_wire["connection"] = connection
                            self._drag_wire["mode"] = "dst_port"
                            self._drag_wire["node"] = node
                            self._drag_wire["port"] = port
                            return
            return
        orientation = self._connection_orientation(connection)
        if orientation == "vertical":
            mid_y = coords[3]
            x1 = coords[2]
            x2 = coords[4]
            if self._near_horizontal_segment(event.x, event.y, x1, x2, mid_y):
                self._drag_wire["connection"] = connection
                self._drag_wire["offset"] = event.y - mid_y
                self._drag_wire["mode"] = "mid_y"
                return
            if self._near_vertical_segment(event.x, event.y, coords[0], coords[1], mid_y):
                if not connection.src:
                    return
                port_info = self._find_port(connection.src[0], connection.src[1], "out")
                if not port_info:
                    return
                node, port = port_info
                if node.resize_enabled:
                    return
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "src_port"
                self._drag_wire["node"] = node
                self._drag_wire["port"] = port
                return
            if self._near_vertical_segment(event.x, event.y, coords[6], mid_y, coords[7]):
                if not connection.dst:
                    return
                port_info = self._find_port(connection.dst[0], connection.dst[1], "in")
                if not port_info:
                    return
                node, port = port_info
                if node.resize_enabled:
                    return
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "dst_port"
                self._drag_wire["node"] = node
                self._drag_wire["port"] = port
                return
            return
        mid_x = coords[2]
        y1a = coords[3]
        y2a = coords[5]
        if self._near_vertical_segment(event.x, event.y, mid_x, y1a, y2a):
            self._drag_wire["connection"] = connection
            self._drag_wire["offset"] = event.x - mid_x
            self._drag_wire["mode"] = "mid"
            return
        if self._near_horizontal_segment(event.x, event.y, coords[0], mid_x, y1a):
            if not connection.src:
                return
            port_info = self._find_port(connection.src[0], connection.src[1], "out")
            if not port_info:
                return
            node, port = port_info
            if node.resize_enabled:
                return
            self._drag_wire["connection"] = connection
            self._drag_wire["mode"] = "src_port"
            self._drag_wire["node"] = node
            self._drag_wire["port"] = port
            return
        if self._near_horizontal_segment(event.x, event.y, mid_x, coords[6], y2a):
            if not connection.dst:
                return
            port_info = self._find_port(connection.dst[0], connection.dst[1], "in")
            if not port_info:
                return
            node, port = port_info
            if node.resize_enabled:
                return
            self._drag_wire["connection"] = connection
            self._drag_wire["mode"] = "dst_port"
            self._drag_wire["node"] = node
            self._drag_wire["port"] = port
            return

    def _on_wire_motion(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        # Multi-select drag is handled by _on_canvas_drag
        if self._multi_select["dragging"]:
            return
        connection: Connection | None = self._drag_wire["connection"]
        if not connection:
            return
        mode = self._drag_wire["mode"]
        if mode == "free_wire":
            dx = event.x - self._drag_wire["x"]
            dy = event.y - self._drag_wire["y"]
            snapped_dx = self._snap_value(dx) if abs(dx) >= self.GRID_STEP / 2 else 0
            snapped_dy = self._snap_value(dy) if abs(dy) >= self.GRID_STEP / 2 else 0
            if snapped_dx == 0 and snapped_dy == 0:
                return
            self._drag_wire["x"] = event.x
            self._drag_wire["y"] = event.y
            connection.free_points = [(px + snapped_dx, py + snapped_dy) for px, py in connection.free_points]
            coords = self._connection_line_coords(connection)
            if coords and connection.line_id:
                self.canvas.coords(connection.line_id, *coords)
            # Move PORT nodes registered on this wire by same delta
            for jp in connection.junction_ports:
                jnode = self.nodes.get(jp.get("node"))
                if not jnode:
                    continue
                self.canvas.move(f"node:{jnode.name}", snapped_dx, snapped_dy)
                jnode.x += snapped_dx
                jnode.y += snapped_dy
                for port in jnode.inputs + jnode.outputs:
                    if port.manual_y is not None:
                        port.manual_y += snapped_dy
            # Also move any PORT not in junction_ports but nearby (fallback)
            jp_names = {jp.get("node") for jp in connection.junction_ports}
            for node in list(self.nodes.values()):
                if node.kind == "PORT" and node.name not in jp_names:
                    if self._find_parent_wire(node) is connection:
                        self.canvas.move(f"node:{node.name}", snapped_dx, snapped_dy)
                        node.x += snapped_dx
                        node.y += snapped_dy
                        for port in node.inputs + node.outputs:
                            if port.manual_y is not None:
                                port.manual_y += snapped_dy
            self._update_connections()
            # Alignment guides based on wire center
            if connection.free_points:
                avg_x = sum(p[0] for p in connection.free_points) / len(connection.free_points)
                avg_y = sum(p[1] for p in connection.free_points) / len(connection.free_points)
                self._draw_point_alignment_guides(avg_x, avg_y)
            return
        if mode == "mid":
            raw_mid = event.x - self._drag_wire["offset"]
            connection.manual_mid_x = self._snap_to_step(raw_mid, self.MID_STEP)
            self._draw_single_axis_guide(connection.manual_mid_x, "x")
            if not connection.src or not connection.dst:
                return
            src_id = self._get_port_canvas_id(connection.src[0], connection.src[1], "out")
            dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1], "in")
            if not src_id or not dst_id:
                return
            x1, y1 = self._port_center(src_id)
            x2, y2 = self._port_center(dst_id)
            coords = self._connection_coords_horizontal((x1, y1), (x2, y2), connection.manual_mid_x)
            self.canvas.coords(connection.line_id, *coords)
            self._reposition_junctions(connection)
            self._update_connections()
            return
        if mode == "mid_y":
            raw_mid = event.y - self._drag_wire["offset"]
            connection.manual_mid_y = self._snap_to_step(raw_mid, self.MID_STEP)
            self._draw_single_axis_guide(connection.manual_mid_y, "y")
            if not connection.src or not connection.dst:
                return
            src_id = self._get_port_canvas_id(connection.src[0], connection.src[1], "out")
            dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1], "in")
            if not src_id or not dst_id:
                return
            x1, y1 = self._port_center(src_id)
            x2, y2 = self._port_center(dst_id)
            coords = self._connection_coords_vertical((x1, y1), (x2, y2), connection.manual_mid_y)
            self.canvas.coords(connection.line_id, *coords)
            self._reposition_junctions(connection)
            self._update_connections()
            return
        if mode == "both_ports":
            if self._mode != "normal":
                return
            dx = event.x - self._drag_wire["x"]
            dy = event.y - self._drag_wire["y"]
            sdx = self._snap_value(dx) if abs(dx) >= self.GRID_STEP / 2 else 0
            sdy = self._snap_value(dy) if abs(dy) >= self.GRID_STEP / 2 else 0
            if sdx == 0 and sdy == 0:
                return
            self._drag_wire["x"] = event.x
            self._drag_wire["y"] = event.y
            for key in ("src", "dst"):
                n = self._drag_wire.get(f"{key}_node")
                p = self._drag_wire.get(f"{key}_port")
                if n and p and p.canvas_id:
                    cx, cy = self._port_center(p.canvas_id)
                    self._move_port(n, p, cx + sdx, cy + sdy)
            self._update_connections()
            self._reposition_junctions(connection)
            self._update_connections()
            return
        if mode in ("src_port", "dst_port"):
            if self._mode != "normal":
                return
            node = self._drag_wire["node"]
            port = self._drag_wire["port"]
            if not node or not port:
                return
            self._move_port(node, port, event.x, event.y)
            if port.canvas_id:
                ppx, ppy = self._port_center(port.canvas_id)
                self._draw_point_alignment_guides(ppx, ppy)
            seg_dir = self._drag_wire.get("seg_dir")
            if seg_dir and connection.waypoints and port.canvas_id:
                px, py = self._port_center(port.canvas_id)
                wp_idx = 0 if mode == "src_port" else -1
                wx, wy = connection.waypoints[wp_idx]
                if seg_dir == "h":
                    connection.waypoints[wp_idx] = (wx, py)
                else:
                    connection.waypoints[wp_idx] = (px, wy)
                self._update_connections()
            self._reposition_junctions(connection)
            self._update_connections()
            return
        if mode in ("wp_h", "wp_v"):
            seg_idx = self._drag_wire.get("seg_index")
            points = self._drag_wire.get("points")
            if seg_idx is None or not points:
                return
            # Save old segment endpoints to compute delta
            old_a = points[seg_idx]
            old_b = points[seg_idx + 1]
            if mode == "wp_h":
                new_y = self._snap_to_step(event.y - self._drag_wire["offset"], self.MID_STEP)
                points[seg_idx] = (points[seg_idx][0], new_y)
                points[seg_idx + 1] = (points[seg_idx + 1][0], new_y)
                self._draw_single_axis_guide(new_y, "y")
                seg_dx, seg_dy = 0, new_y - old_a[1]
            else:
                new_x = self._snap_to_step(event.x - self._drag_wire["offset"], self.MID_STEP)
                points[seg_idx] = (new_x, points[seg_idx][1])
                points[seg_idx + 1] = (new_x, points[seg_idx + 1][1])
                self._draw_single_axis_guide(new_x, "x")
                seg_dx, seg_dy = new_x - old_a[0], 0
            connection.waypoints = list(points[1:-1])
            coords = [c for p in points for c in p]
            self.canvas.coords(connection.line_id, *coords)
            if connection.label_id:
                self._update_label(connection, coords)
            # Move PORT junctions pre-identified at drag start
            if seg_dx != 0 or seg_dy != 0:
                seg_junctions = self._drag_wire.get("seg_junctions", [])
                for jname in seg_junctions:
                    jnode = self.nodes.get(jname)
                    if not jnode:
                        continue
                    self.canvas.move(f"node:{jname}", seg_dx, seg_dy)
                    jnode.x += seg_dx
                    jnode.y += seg_dy
                    for jp in jnode.inputs + jnode.outputs:
                        if jp.manual_y is not None:
                            jp.manual_y += seg_dy
            self._update_connections()
            return

    def _on_wire_release(self, _event):
        # Multi-select drag release is handled by _on_canvas_release
        if self._multi_select["dragging"]:
            return
        if self._drag_wire["connection"]:
            self._simplify_waypoints(self._drag_wire["connection"])
            self._update_connections()
            self._snap_junctions_to_wires()
            self._update_connections()
            self._record_history()
        self._drag_wire["connection"] = None
        self._drag_wire["mode"] = None
        self._drag_wire["port"] = None
        self._drag_wire["node"] = None
        self._drag_wire.pop("seg_index", None)
        self._drag_wire.pop("points", None)
        self._drag_wire.pop("seg_dir", None)
        self._drag_wire.pop("seg_junctions", None)
        self._drag_wire.pop("src_node", None)
        self._drag_wire.pop("src_port", None)
        self._drag_wire.pop("dst_node", None)
        self._drag_wire.pop("dst_port", None)
        self._clear_alignment_guides()

    def _on_wire_double_click(self, event):
        if self._mode != "normal":
            return
        item = self.canvas.find_withtag("current")
        if not item:
            return
        line_id = item[0]
        connection = next((c for c in self.connections if c.line_id == line_id), None)
        if not connection:
            return
        if self._selected_wire is connection:
            self._deselect_wire()
            return
        self._deselect_wire()
        self._selected_wire = connection
        self.canvas.itemconfigure(line_id, width=4)

    def _deselect_wire(self):
        if self._selected_wire and self._selected_wire.line_id:
            self.canvas.itemconfigure(
                self._selected_wire.line_id, width=self._wire_width(self._selected_wire)
            )
        self._selected_wire = None

    def _deselect_label(self):
        if self._selected_label_border:
            self.canvas.delete(self._selected_label_border)
            self._selected_label_border = None
        self._selected_label_conn = None

    def _schedule_status_update(self):
        self._update_status_bar()
        self.root.after(150, self._schedule_status_update)

    def _update_status_bar(self):
        mode_map = {
            "normal": "normal",
            "connect": "connect",
            "create_port": "create port",
            "delete_port": "delete port",
            "move_port": "move port",
            "create_wire": "create wire",
            "wire_port": "wire port",
        }
        mode_text = mode_map.get(self._mode, self._mode)
        if self._delete_mode:
            mode_text = "delete"
        if self._active_node_name and self._mode == "normal":
            node = self.nodes.get(self._active_node_name)
            if node and node.resize_enabled:
                mode_text = "resize"
        if getattr(self, "_save_flash", False):
            mode_text = "save"
        self._status_mode_label.config(text=f"Mode: {mode_text}")
        sel_text = ""
        ms = self._multi_select
        if ms["nodes"] or ms["wires"] or ms["labels"]:
            items = []
            for name in ms["nodes"]:
                node = self.nodes.get(name)
                if node:
                    items.append(node.name if node.kind == "BLOCK" else node.kind)
            for _conn in ms["wires"]:
                items.append("wire")
            for conn in ms["labels"]:
                items.append(f"label({conn.label})" if conn.label else "label")
            sel_text = "| Selected: " + ", ".join(items)
        elif self._selected_wire:
            sel_text = "| Selected: wire"
        elif self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node:
                if node.kind == "BLOCK":
                    sel_text = f"| Selected: {node.name}"
                else:
                    sel_text = f"| Selected: {node.kind}"
        self._status_selection_label.config(text=sel_text)

    def _on_label_press(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        if self._delete_mode:
            item = self.canvas.find_withtag("current")
            if not item:
                return
            label_id = item[0]
            connection = next((c for c in self.connections if c.label_id == label_id), None)
            if not connection:
                return
            self._remove_connection(connection)
            return
        if self._mode != "normal":
            return
        # Check if clicking on a multi-selected label → start multi-drag
        if self._multi_select["nodes"] or self._multi_select["wires"] or self._multi_select["labels"]:
            item = self.canvas.find_withtag("current")
            if item:
                label_id = item[0]
                clicked_conn = next((c for c in self.connections if c.label_id == label_id), None)
                if clicked_conn and (clicked_conn in self._multi_select["labels"] or clicked_conn in self._multi_select["wires"]):
                    self._multi_select["dragging"] = True
                    self._multi_select["active"] = True
                    self._multi_select["drag_x"] = event.x
                    self._multi_select["drag_y"] = event.y
                    return
            self._clear_multi_select()
        item = self.canvas.find_withtag("current")
        if not item:
            return
        label_id = item[0]
        connection = next((c for c in self.connections if c.label_id == label_id), None)
        if not connection:
            return
        self._deselect_wire()
        self._deselect_label()
        self._selected_label_conn = connection
        bbox = self.canvas.bbox(label_id)
        if bbox:
            pad = 3
            self._selected_label_border = self.canvas.create_rectangle(
                bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
                outline="black", width=2,
            )
        self._label_drag_data["connection"] = connection
        self._label_drag_data["x"] = event.x
        self._label_drag_data["y"] = event.y

    def _on_label_motion(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        # Multi-select drag is handled by _on_canvas_drag
        if self._multi_select["dragging"]:
            return
        connection = self._label_drag_data.get("connection")
        if not connection or not connection.label_id:
            return
        dx = event.x - self._label_drag_data["x"]
        dy = event.y - self._label_drag_data["y"]
        self._label_drag_data["x"] = event.x
        self._label_drag_data["y"] = event.y
        self.canvas.move(connection.label_id, dx, dy)
        if self._selected_label_border:
            self.canvas.move(self._selected_label_border, dx, dy)
        lx, ly = self.canvas.coords(connection.label_id)
        connection.label_x = lx
        connection.label_y = ly
        # Use label bbox for alignment guides (left/center/right, top/center/bottom)
        bbox = self.canvas.bbox(connection.label_id)
        if bbox:
            self._draw_label_alignment_guides(bbox)
        else:
            self._draw_point_alignment_guides(lx, ly)

    def _on_label_release(self, _event):
        # Multi-select drag release is handled by _on_canvas_release
        if self._multi_select["dragging"]:
            return
        if self._label_drag_data.get("connection"):
            self._record_history()
        self._label_drag_data["connection"] = None
        self._clear_alignment_guides()

    def _clear_alignment_guides(self):
        for gid in self._align_guides:
            self.canvas.delete(gid)
        self._align_guides.clear()

    def _calc_alignment(self, moving_node: Node, sx: int, sy: int) -> tuple[int, int]:
        threshold = self._align_threshold
        best_x, best_dx = sx, threshold + 1
        best_y, best_dy = sy, threshold + 1
        mx_left = sx
        mx_cx = sx + moving_node.width / 2
        mx_right = sx + moving_node.width
        my_top = sy
        my_cy = sy + moving_node.height / 2
        my_bottom = sy + moving_node.height
        for other in self.nodes.values():
            if other.name == moving_node.name:
                continue
            ref_xs = [other.x, other.x + other.width / 2, other.x + other.width]
            ref_ys = [other.y, other.y + other.height / 2, other.y + other.height]
            for rx in ref_xs:
                for mx in [mx_left, mx_cx, mx_right]:
                    d = abs(mx - rx)
                    if d < threshold and d < best_dx:
                        best_dx = d
                        best_x = sx + int(rx - mx)
            for ry in ref_ys:
                for my in [my_top, my_cy, my_bottom]:
                    d = abs(my - ry)
                    if d < threshold and d < best_dy:
                        best_dy = d
                        best_y = sy + int(ry - my)
        return best_x, best_y

    def _collect_guide_refs(self, exclude_node: str | None = None) -> tuple[list[float], list[float]]:
        """Collect all reference X and Y positions for alignment guides."""
        ref_xs: list[float] = []
        ref_ys: list[float] = []
        for node in self.nodes.values():
            if node.name == exclude_node:
                continue
            if node.kind == "PORT":
                cx, cy = self._junction_port_xy(node)
                ref_xs.append(cx)
                ref_ys.append(cy)
            else:
                ref_xs.extend([node.x, node.x + node.width / 2, node.x + node.width])
                ref_ys.extend([node.y, node.y + node.height / 2, node.y + node.height])
                for port in node.inputs + node.outputs:
                    ppx, ppy = self._port_position(node, port)
                    ref_xs.append(ppx)
                    ref_ys.append(ppy)
        for conn in self.connections:
            coords = self._connection_line_coords(conn)
            if coords:
                for i in range(0, len(coords), 2):
                    ref_xs.append(coords[i])
                    ref_ys.append(coords[i + 1])
            # Add label bbox edges/center as reference positions
            if conn.label_id:
                bbox = self.canvas.bbox(conn.label_id)
                if bbox:
                    lx1, ly1, lx2, ly2 = bbox
                    ref_xs.extend([lx1, (lx1 + lx2) / 2, lx2])
                    ref_ys.extend([ly1, (ly1 + ly2) / 2, ly2])
        return ref_xs, ref_ys

    def _draw_alignment_guides(self, moving_node: Node):
        self._clear_alignment_guides()
        if moving_node.kind == "PORT":
            cx, cy = self._junction_port_xy(moving_node)
            moving_xs = [cx]
            moving_ys = [cy]
        else:
            moving_xs = [moving_node.x, moving_node.x + moving_node.width / 2, moving_node.x + moving_node.width]
            moving_ys = [moving_node.y, moving_node.y + moving_node.height / 2, moving_node.y + moving_node.height]
        guide_color = "#4A90D9"
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        drawn_x: set[float] = set()
        drawn_y: set[float] = set()
        all_rx, all_ry = self._collect_guide_refs(exclude_node=moving_node.name)
        for rx in all_rx:
            for mx in moving_xs:
                if abs(mx - rx) < 1 and rx not in drawn_x:
                    drawn_x.add(rx)
                    gid = self.canvas.create_line(rx, 0, rx, canvas_h, fill=guide_color, dash=(4, 4), width=1)
                    self._align_guides.append(gid)
        for ry in all_ry:
            for my in moving_ys:
                if abs(my - ry) < 1 and ry not in drawn_y:
                    drawn_y.add(ry)
                    gid = self.canvas.create_line(0, ry, canvas_w, ry, fill=guide_color, dash=(4, 4), width=1)
                    self._align_guides.append(gid)

    def _draw_point_alignment_guides(self, px: float, py: float):
        self._clear_alignment_guides()
        threshold = self._align_threshold
        guide_color = "#4A90D9"
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        drawn_x: set[float] = set()
        drawn_y: set[float] = set()
        all_rx, all_ry = self._collect_guide_refs()
        for rx in all_rx:
            if abs(px - rx) < threshold and rx not in drawn_x:
                drawn_x.add(rx)
                gid = self.canvas.create_line(rx, 0, rx, canvas_h, fill=guide_color, dash=(4, 4), width=1)
                self._align_guides.append(gid)
        for ry in all_ry:
            if abs(py - ry) < threshold and ry not in drawn_y:
                drawn_y.add(ry)
                gid = self.canvas.create_line(0, ry, canvas_w, ry, fill=guide_color, dash=(4, 4), width=1)
                self._align_guides.append(gid)

    def _draw_single_axis_guide(self, value: float, axis: str):
        """Draw alignment guide for a single axis: 'x' for vertical line, 'y' for horizontal line."""
        self._clear_alignment_guides()
        threshold = self._align_threshold
        guide_color = "#4A90D9"
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        drawn: set[float] = set()
        all_rx, all_ry = self._collect_guide_refs()
        refs = all_ry if axis == "y" else all_rx
        for r in refs:
            if abs(value - r) < threshold and r not in drawn:
                drawn.add(r)
                if axis == "y":
                    gid = self.canvas.create_line(0, r, canvas_w, r, fill=guide_color, dash=(4, 4), width=1)
                else:
                    gid = self.canvas.create_line(r, 0, r, canvas_h, fill=guide_color, dash=(4, 4), width=1)
                self._align_guides.append(gid)

    def _draw_label_alignment_guides(self, bbox: tuple[int, int, int, int]):
        """Draw alignment guides using label bbox edges and center."""
        self._clear_alignment_guides()
        lx1, ly1, lx2, ly2 = bbox
        lcx = (lx1 + lx2) / 2
        lcy = (ly1 + ly2) / 2
        moving_xs = [lx1, lcx, lx2]
        moving_ys = [ly1, lcy, ly2]
        guide_color = "#4A90D9"
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        drawn_x: set[float] = set()
        drawn_y: set[float] = set()
        all_rx, all_ry = self._collect_guide_refs()
        for rx in all_rx:
            for mx in moving_xs:
                if abs(mx - rx) < self._align_threshold and rx not in drawn_x:
                    drawn_x.add(rx)
                    gid = self.canvas.create_line(rx, 0, rx, canvas_h, fill=guide_color, dash=(4, 4), width=1)
                    self._align_guides.append(gid)
        for ry in all_ry:
            for my in moving_ys:
                if abs(my - ry) < self._align_threshold and ry not in drawn_y:
                    drawn_y.add(ry)
                    gid = self.canvas.create_line(0, ry, canvas_w, ry, fill=guide_color, dash=(4, 4), width=1)
                    self._align_guides.append(gid)

    def _handle_escape(self):
        if self._multi_select["nodes"] or self._multi_select["wires"] or self._multi_select["labels"]:
            self._clear_multi_select()
            return
        if self._delete_mode:
            self._toggle_delete_mode()
            return
        if self._mode in ("connect", "create_port", "delete_port", "move_port"):
            self._reset_port_mode()
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
        if self._mode == "wire_port":
            self._exit_wire_port_mode()
        if self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node and node.resize_enabled:
                node.resize_enabled = False
                self._redraw_node(node)
                self._update_connections()
        self._deselect_wire()
        self._deselect_label()

    def _copy_selection(self):
        if self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node:
                ports = {}
                for port in node.inputs + node.outputs:
                    ports[port.name] = {
                        "side": port.side,
                        "offset": port.offset,
                        "manual_y": port.manual_y,
                    }
                self._clipboard = {
                    "type": "node",
                    "kind": node.kind,
                    "width": node.width,
                    "height": node.height,
                    "ports": ports,
                    "fill_color": node.fill_color,
                    "outline_color": node.outline_color,
                    "outline_enabled": node.outline_enabled,
                    "outline_style": node.outline_style,
                    "outline_scale": node.outline_scale,
                    "label_font_size": node.label_font_size,
                    "label_font_family": node.label_font_family,
                    "label_font_weight": node.label_font_weight,
                    "rotation": node.rotation,
                    "name": node.name,
                }
                return
        if self._selected_wire:
            conn = self._selected_wire
            self._clipboard = {
                "type": "wire",
                "free_points": list(conn.free_points) if conn.free_points else [],
                "line_color": conn.line_color,
                "line_thickness": conn.line_thickness,
                "show_arrow": conn.show_arrow,
                "label": conn.label,
                "label_font_family": conn.label_font_family,
                "label_font_size": conn.label_font_size,
                "label_font_weight": conn.label_font_weight,
                "label_angle": conn.label_angle,
            }
            return
        if self._selected_label_conn:
            conn = self._selected_label_conn
            self._clipboard = {
                "type": "label",
                "label": conn.label,
                "label_font_family": conn.label_font_family,
                "label_font_size": conn.label_font_size,
                "label_font_weight": conn.label_font_weight,
                "label_angle": conn.label_angle,
                "label_x": conn.label_x,
                "label_y": conn.label_y,
            }
            return

    def _paste_selection(self):
        if not self._clipboard:
            return
        cb = self._clipboard
        paste_offset = 30

        if cb["type"] == "node":
            kind = cb["kind"]
            if kind == "BLOCK":
                base = cb["name"]
            else:
                base = kind
            name = self._unique_node_name(base)
            inputs = []
            outputs = []
            for pname, pdata in cb["ports"].items():
                side = pdata["side"]
                port = Port(name=pname, kind="in" if side in ("left", "top") else "out",
                            side=side, offset=pdata["offset"])
                if port.kind == "in":
                    inputs.append(port)
                else:
                    outputs.append(port)
            x, y = self._next_block_position()
            new_node = Node(
                name=name,
                kind=kind,
                inputs=inputs,
                outputs=outputs,
                x=x,
                y=y,
                width=cb["width"],
                height=cb["height"],
                base_height=cb["height"],
                fill_color=cb["fill_color"],
                outline_color=cb["outline_color"],
                outline_enabled=cb["outline_enabled"],
                outline_style=cb["outline_style"],
                outline_scale=cb["outline_scale"],
                label_font_size=cb["label_font_size"],
                label_font_family=cb["label_font_family"],
                label_font_weight=cb["label_font_weight"],
                level=self._next_level(),
                rotation=cb["rotation"],
            )
            self._align_gate_ports_to_grid(new_node)
            self.nodes[name] = new_node
            self._draw_node(new_node)
            self._apply_z_order(active_node_name=new_node.name)
            self._active_node_name = name
            self._record_history()
            return

        if cb["type"] == "wire" and cb["free_points"]:
            new_points = [(px + paste_offset, py + paste_offset) for px, py in cb["free_points"]]
            new_conn = Connection(
                src=None,
                dst=None,
                line_color=cb["line_color"],
                line_thickness=cb["line_thickness"],
                show_arrow=cb["show_arrow"],
            )
            new_conn.free_points = new_points
            self.connections.append(new_conn)
            self._draw_connection(new_conn)
            self._record_history()
            return

        if cb["type"] == "label":
            lx = (cb["label_x"] or 200) + paste_offset
            ly = (cb["label_y"] or 200) + paste_offset
            new_conn = Connection(src=None, dst=None)
            new_conn.label = cb["label"]
            new_conn.label_font_family = cb["label_font_family"]
            new_conn.label_font_size = cb["label_font_size"]
            new_conn.label_font_weight = cb["label_font_weight"]
            new_conn.label_angle = cb["label_angle"]
            new_conn.label_x = lx
            new_conn.label_y = ly
            self.connections.append(new_conn)
            self._draw_connection(new_conn)
            self._record_history()
            return

    def _handle_edit_key(self):
        if self._selected_label_conn:
            self._open_label_dialog(self._selected_label_conn)
            return
        if self._selected_wire and self._selected_wire.free_points:
            self._open_wire_style_editor(self._selected_wire)
            return
        self._open_edit_block()

    def _handle_s_key(self):
        if self._selected_wire and self._selected_wire.free_points:
            if self._mode == "wire_port":
                self._exit_wire_port_mode()
                return
            if self._mode in ("connect", "create_port", "delete_port", "move_port"):
                self._reset_port_mode()
            if self._mode == "create_wire":
                self._reset_create_wire_mode()
            self._enter_wire_port_mode()
            return
        self._toggle_resize_active_node()

    def _open_label_dialog(self, connection: Connection, is_new: bool = False):
        dialog = tk.Toplevel(self.root)
        dialog.title("LABEL")
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Text:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        text_var = tk.StringVar(value=connection.label or "")
        text_entry = tk.Entry(dialog, textvariable=text_var, width=30)
        text_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        text_entry.focus_set()

        tk.Label(dialog, text="Font:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        font_families = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia"]
        font_var = tk.StringVar(value=connection.label_font_family)
        font_combo = ttk.Combobox(dialog, textvariable=font_var, values=font_families, width=18)
        font_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

        tk.Label(dialog, text="Size:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        size_var = tk.IntVar(value=connection.label_font_size)
        size_spin = tk.Spinbox(dialog, from_=6, to=72, textvariable=size_var, width=5)
        size_spin.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        bold_var = tk.BooleanVar(value=connection.label_font_weight == "bold")
        bold_check = tk.Checkbutton(dialog, text="Bold", variable=bold_var)
        bold_check.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        result = {"ok": False}

        def on_ok(_event=None):
            result["ok"] = True
            dialog.destroy()

        def on_cancel(_event=None):
            dialog.destroy()

        text_entry.bind("<Return>", on_ok)
        dialog.bind("<Escape>", on_cancel)
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        tk.Button(btn_frame, text="OK", width=8, command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=8, command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()
        if not result["ok"]:
            return
        new_text = text_var.get()
        if not new_text and is_new:
            return
        connection.label = new_text if new_text else None
        connection.label_font_family = font_var.get() or "Arial"
        try:
            connection.label_font_size = int(size_var.get())
        except (ValueError, tk.TclError):
            connection.label_font_size = 12
        connection.label_font_weight = "bold" if bold_var.get() else "normal"
        font = (connection.label_font_family, connection.label_font_size, connection.label_font_weight)
        if connection.label:
            if connection.label_id:
                self.canvas.itemconfig(
                    connection.label_id,
                    text=connection.label,
                    font=font,
                    angle=connection.label_angle,
                )
            else:
                coords = self._connection_line_coords(connection)
                if coords:
                    if connection.label_x is not None and connection.label_y is not None:
                        lx, ly = connection.label_x, connection.label_y
                    else:
                        lx, ly = self._label_position(coords)
                    connection.label_id = self.canvas.create_text(
                        lx, ly, text=connection.label, font=font, anchor="s", angle=connection.label_angle,
                    )
                    self.canvas.addtag_withtag("label", connection.label_id)
        else:
            if connection.label_id:
                self.canvas.delete(connection.label_id)
                connection.label_id = None
                connection.label_x = None
                connection.label_y = None
        self._deselect_label()
        if self._selected_label_conn is connection and connection.label_id:
            bbox = self.canvas.bbox(connection.label_id)
            if bbox:
                pad = 3
                self._selected_label_border = self.canvas.create_rectangle(
                    bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
                    outline="black", width=2,
                )
        self._record_history()

    def _near_vertical_segment(
        self,
        px: float,
        py: float,
        x: float,
        y1: float,
        y2: float,
        threshold: float = 6.0,
    ) -> bool:
        if abs(px - x) > threshold:
            return False
        return min(y1, y2) - threshold <= py <= max(y1, y2) + threshold

    def _near_horizontal_segment(
        self,
        px: float,
        py: float,
        x1: float,
        x2: float,
        y: float,
        threshold: float = 6.0,
    ) -> bool:
        if abs(py - y) > threshold:
            return False
        return min(x1, x2) - threshold <= px <= max(x1, x2) + threshold

    @staticmethod
    def _distance_squared(x1: float, y1: float, x2: float, y2: float) -> float:
        return (x1 - x2) ** 2 + (y1 - y2) ** 2

    @classmethod
    def _nearest_point_on_segment(
        cls,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        px: float,
        py: float,
    ) -> tuple[float, float]:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return (x1, y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return (x1 + t * dx, y1 + t * dy)

    @classmethod
    def _nearest_point_on_polyline(
        cls,
        coords: list[float],
        px: float,
        py: float,
    ) -> tuple[float, float]:
        best_point = (coords[0], coords[1])
        best_dist = float("inf")
        for idx in range(0, len(coords) - 2, 2):
            x1, y1 = coords[idx], coords[idx + 1]
            x2, y2 = coords[idx + 2], coords[idx + 3]
            cx, cy = cls._nearest_point_on_segment(x1, y1, x2, y2, px, py)
            dist = cls._distance_squared(cx, cy, px, py)
            if dist < best_dist:
                best_dist = dist
                best_point = (cx, cy)
        return best_point

    @classmethod
    def _point_ratio_on_polyline(cls, coords: list[float], px: float, py: float) -> float:
        """Compute the ratio [0..1] of point (px, py) along the polyline."""
        import math
        total_len = 0.0
        seg_lengths = []
        for i in range(0, len(coords) - 2, 2):
            x1, y1 = coords[i], coords[i + 1]
            x2, y2 = coords[i + 2], coords[i + 3]
            seg_len = math.hypot(x2 - x1, y2 - y1)
            seg_lengths.append(seg_len)
            total_len += seg_len
        if total_len == 0:
            return 0.0
        cum = 0.0
        best_ratio = 0.0
        best_dist = float("inf")
        for i, seg_len in enumerate(seg_lengths):
            x1, y1 = coords[i * 2], coords[i * 2 + 1]
            x2, y2 = coords[i * 2 + 2], coords[i * 2 + 3]
            cx, cy = cls._nearest_point_on_segment(x1, y1, x2, y2, px, py)
            dist = cls._distance_squared(cx, cy, px, py)
            if dist < best_dist:
                best_dist = dist
                d = math.hypot(cx - x1, cy - y1)
                best_ratio = (cum + d) / total_len
            cum += seg_len
        return max(0.0, min(1.0, best_ratio))

    @classmethod
    def _point_from_ratio_on_polyline(cls, coords: list[float], ratio: float) -> tuple[float, float]:
        """Compute the point at given ratio [0..1] along the polyline."""
        import math
        total_len = 0.0
        seg_lengths = []
        for i in range(0, len(coords) - 2, 2):
            x1, y1 = coords[i], coords[i + 1]
            x2, y2 = coords[i + 2], coords[i + 3]
            seg_lengths.append(math.hypot(x2 - x1, y2 - y1))
            total_len += seg_lengths[-1]
        if total_len == 0:
            return coords[0], coords[1]
        target = ratio * total_len
        cum = 0.0
        for i, seg_len in enumerate(seg_lengths):
            if cum + seg_len >= target or i == len(seg_lengths) - 1:
                x1, y1 = coords[i * 2], coords[i * 2 + 1]
                x2, y2 = coords[i * 2 + 2], coords[i * 2 + 3]
                t = (target - cum) / seg_len if seg_len > 0 else 0
                return x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            cum += seg_len
        return coords[-2], coords[-1]

    @staticmethod
    def _orthogonal_segments(
        coords: list[float],
    ) -> tuple[float, float, float, float, float, float]:
        x1, y1, x2, y2, x3, y3 = coords
        if y1 == y2:
            h_x1, h_x2, h_y = x1, x2, y1
            v_x, v_y1, v_y2 = x2, y2, y3
        else:
            h_x1, h_x2, h_y = x2, x3, y2
            v_x, v_y1, v_y2 = x1, y1, y2
        return h_x1, h_x2, h_y, v_x, v_y1, v_y2

    def _move_port(self, node: Node, port: Port, target_x: float, target_y: float):
        if port.canvas_id is None:
            return
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        radius = self.PORT_RADIUS
        if port.side in ("left", "right"):
            min_y = y1 + radius
            max_y = y2 - radius
            new_y = max(min_y, min(target_y, max_y))
            new_y = self._snap_value(new_y, int(min_y))
            port.offset = 0 if y2 == y1 else (new_y - y1) / (y2 - y1)
            port.manual_y = new_y
            x = x1 if port.side == "left" else x2
            self.canvas.coords(port.canvas_id, x - radius, new_y - radius, x + radius, new_y + radius)
        else:
            min_x = x1 + radius
            max_x = x2 - radius
            new_x = max(min_x, min(target_x, max_x))
            new_x = self._snap_value(new_x, int(min_x))
            port.offset = 0 if x2 == x1 else (new_x - x1) / (x2 - x1)
            port.manual_y = None
            y = y1 if port.side == "top" else y2
            self.canvas.coords(port.canvas_id, new_x - radius, y - radius, new_x + radius, y + radius)
        self._update_connections()

    def _on_port_motion(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        node = self._port_drag_data.get("node")
        port = self._port_drag_data.get("port")
        if not node or not port:
            return
        self._move_port(node, port, event.x, event.y)
        if port.canvas_id:
            px, py = self._port_center(port.canvas_id)
            self._draw_point_alignment_guides(px, py)

    def _on_port_release(self, _event):
        if self._port_drag_data.get("node"):
            self._record_history()
        self._port_drag_data = {"node": None, "port": None, "x": 0, "y": 0}
        self._clear_alignment_guides()

    def _on_port_press(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        if self._mode == "delete_port":
            self._handle_delete_port_click(event)
            return
        if self._mode == "move_port":
            item = self.canvas.find_withtag("current")
            if not item:
                return
            port_info = self._port_items.get(item[0])
            if not port_info:
                return
            node_name, port_name = port_info
            node = self.nodes.get(node_name)
            if not node:
                return
            for port in node.inputs + node.outputs:
                if port.name == port_name:
                    self._port_drag_data = {
                        "node": node,
                        "port": port,
                        "x": event.x,
                        "y": event.y,
                    }
                    return
            return
        if self._mode != "connect":
            return
        item = self.canvas.find_withtag("current")
        if not item:
            return
        port_info = self._port_items.get(item[0])
        if not port_info:
            return
        node_name, port_name = port_info
        port_data = self._find_port(node_name, port_name, "in") or self._find_port(node_name, port_name, "out")
        if not port_data:
            return
        node, port = port_data
        if not self._selected_ports:
            self._selected_ports.append((node_name, port_name))
            self._set_port_color(port, "blue")
            self._pending_midpoints = []
            self._wire_direction = "horizontal" if port.side in ("left", "right") else "vertical"
            self._update_wire_preview(event.x, event.y)
            return
        if len(self._selected_ports) == 1:
            first_node, first_port = self._selected_ports[0]
            if first_node == node_name:
                self._reset_connect_mode()
                return
            first_port_data = self._find_port(first_node, first_port, "in") or self._find_port(first_node, first_port, "out")
            if not first_port_data:
                self._reset_connect_mode()
                return
            src = (first_node, first_port)
            dst = (node_name, port_name)
            connection = Connection(src=src, dst=dst)
            waypoints = list(self._pending_midpoints)
            dst_port_id = self._get_port_canvas_id(node_name, port_name)
            if dst_port_id:
                dest_x, dest_y = self._port_center(dst_port_id)
                src_port_id = self._get_port_canvas_id(first_node, first_port)
                if src_port_id:
                    if waypoints:
                        last_x, last_y = waypoints[-1]
                        cur_dir = self._current_wire_direction()
                        if cur_dir == "vertical":
                            if last_x != dest_x:
                                waypoints.append((last_x, dest_y))
            if waypoints:
                connection.waypoints = waypoints
            self.connections.append(connection)
            self._draw_connection(connection)
            self._record_history()
            self._reset_connect_mode()
            return

    def _open_new_block(self):
        self._open_block_dialog(mode="create")

    def _open_edit_block(self):
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node or node.kind == "PORT":
            return
        self._open_block_dialog(mode="edit", node=node)

    def _open_block_dialog(self, mode: str, node: Node | None = None):
        window = tk.Toplevel(self.root)
        window.title("Edit" if mode == "edit" else "New")
        window.bind("<Escape>", lambda _e: window.destroy())
        mode_var = tk.StringVar(value="block")
        if mode == "create":
            tk.Radiobutton(window, text="Block", variable=mode_var, value="block").grid(
                row=0, column=0, padx=6, pady=6, sticky="w"
            )
            tk.Radiobutton(window, text="Diagram", variable=mode_var, value="gate").grid(
                row=0, column=1, padx=6, pady=6, sticky="w"
            )

        color_options = list(self.COLOR_NAME_TO_HEX.keys())
        color_hex_map = self.COLOR_NAME_TO_HEX

        def _make_color_bar(parent, var, row):
            """Create a row of color swatch buttons that update *var* on click."""
            bar = tk.Frame(parent)
            bar.grid(row=row, column=1, padx=6, pady=3, sticky="w")
            btns = {}
            def _select(name):
                var.set(name)
                for n, b in btns.items():
                    b.configure(relief="sunken" if n == name else "raised",
                                bd=2 if n == name else 1)
            for cname in color_options:
                hex_val = color_hex_map[cname]
                b = tk.Button(bar, width=2, height=1, bg=hex_val,
                              activebackground=hex_val,
                              relief="raised", bd=1,
                              command=lambda n=cname: _select(n))
                b.pack(side="left", padx=1)
                btns[cname] = b
            # Sync initial selection
            def _sync(*_a):
                cur = var.get()
                for n, b in btns.items():
                    b.configure(relief="sunken" if n == cur else "raised",
                                bd=2 if n == cur else 1)
            var.trace_add("write", _sync)
            _sync()
            return bar

        # --- Helper to build common UI fields on a frame starting at given row ---
        def _build_style_fields(frame, start_row, name_height=5,
                                default_h_align="Left", default_v_align="Top"):
            fields = {}
            r = start_row
            tk.Label(frame, text="Name").grid(row=r, column=0, padx=6, pady=6, sticky="nw")
            fields["name_entry"] = tk.Text(frame, height=name_height, width=24)
            fields["name_entry"].grid(row=r, column=1, padx=6, pady=6, sticky="w")
            r += 1
            tk.Label(frame, text="Font Size").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["font_size_var"] = tk.IntVar(value=12)
            tk.Spinbox(frame, from_=6, to=72, textvariable=fields["font_size_var"], width=6).grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Font").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["font_family_var"] = tk.StringVar(value="Arial")
            tk.OptionMenu(frame, fields["font_family_var"], "Arial", "Malgun Gothic").grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Bold").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["bold_var"] = tk.BooleanVar(value=True)
            tk.Checkbutton(frame, variable=fields["bold_var"]).grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Fill Color").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["fill_var"] = tk.StringVar(value="WHITE")
            _make_color_bar(frame, fields["fill_var"], r)
            r += 1
            tk.Label(frame, text="Outline").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["outline_enabled_var"] = tk.BooleanVar(value=True)
            tk.Checkbutton(frame, variable=fields["outline_enabled_var"]).grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Outline Color").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["outline_var"] = tk.StringVar(value="BLACK")
            fields["outline_color_bar"] = _make_color_bar(frame, fields["outline_var"], r)
            r += 1
            tk.Label(frame, text="Outline Thickness").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["outline_thickness_var"] = tk.StringVar(value="Normal")
            fields["outline_thickness_menu"] = tk.OptionMenu(
                frame, fields["outline_thickness_var"], "Thin", "Normal", "Thick")
            fields["outline_thickness_menu"].grid(row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Outline Style").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["outline_style_var"] = tk.StringVar(value="Solid")
            fields["outline_style_menu"] = tk.OptionMenu(
                frame, fields["outline_style_var"], "Solid", "Dashed")
            fields["outline_style_menu"].grid(row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Name H-Align").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["h_align_var"] = tk.StringVar(value=default_h_align)
            tk.OptionMenu(frame, fields["h_align_var"], "Left", "Center", "Right").grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            r += 1
            tk.Label(frame, text="Name V-Align").grid(row=r, column=0, padx=6, pady=3, sticky="w")
            fields["v_align_var"] = tk.StringVar(value=default_v_align)
            tk.OptionMenu(frame, fields["v_align_var"], "Top", "Center", "Bottom").grid(
                row=r, column=1, padx=6, pady=3, sticky="w")
            # Outline toggle
            def _toggle_outline(*_a):
                st = "normal" if fields["outline_enabled_var"].get() else "disabled"
                for child in fields["outline_color_bar"].winfo_children():
                    child.configure(state=st)
                fields["outline_thickness_menu"].configure(state=st)
                fields["outline_style_menu"].configure(state=st)
            fields["outline_enabled_var"].trace_add("write", _toggle_outline)
            _toggle_outline()
            return fields

        # --- Block frame ---
        block_frame = tk.Frame(window)
        block_frame.grid(row=1, column=0, columnspan=2, sticky="w")
        bf = _build_style_fields(block_frame, 0)

        # --- Diagram (gate) frame ---
        gate_frame = tk.Frame(window)
        gate_frame.grid(row=1, column=0, columnspan=2, sticky="w")

        tk.Label(gate_frame, text="Diagram Type").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        gate_var = tk.StringVar(value="AND2")
        gate_menu = tk.OptionMenu(gate_frame, gate_var, *self._gate_types())
        gate_menu.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        # Build same style fields for diagram frame, starting at row 1
        gf = _build_style_fields(gate_frame, 1, name_height=2,
                                 default_h_align="Center", default_v_align="Center")

        # Shorthand references for block frame (used by edit mode and block create)
        name_entry = bf["name_entry"]
        font_size_var = bf["font_size_var"]
        font_family_var = bf["font_family_var"]
        bold_var = bf["bold_var"]
        fill_var = bf["fill_var"]
        outline_enabled_var = bf["outline_enabled_var"]
        outline_var = bf["outline_var"]
        outline_thickness_var = bf["outline_thickness_var"]
        outline_style_var = bf["outline_style_var"]
        h_align_var = bf["h_align_var"]
        v_align_var = bf["v_align_var"]

        def _toggle_fields(*_args):
            is_gate = mode_var.get() == "gate"
            if is_gate:
                block_frame.grid_remove()
                gate_frame.grid()
            else:
                gate_frame.grid_remove()
                block_frame.grid()

        # Track whether we're editing a gate/diagram (non-BLOCK)
        _editing_gate = False

        if mode == "create":
            mode_var.trace_add("write", _toggle_fields)
            _toggle_fields()
        else:
            # Edit mode: show the right frame based on node kind
            if node and node.kind != "BLOCK":
                block_frame.grid_remove()
                gate_frame.grid()
                _editing_gate = True
            else:
                gate_frame.grid_remove()

        def _unique_gate_name(kind: str) -> str:
            index = 1
            while True:
                candidate = f"{kind}{index}"
                if candidate not in self.nodes:
                    return candidate
                index += 1

        def _align_gate_to_grid(target: Node):
            self._align_gate_ports_to_grid(target)

        def _populate_fields(fields_dict, src_node):
            """Populate a set of style fields from a node."""
            fields_dict["name_entry"].insert("1.0", src_node.name)
            fields_dict["font_size_var"].set(src_node.label_font_size)
            fields_dict["font_family_var"].set(src_node.label_font_family)
            fields_dict["bold_var"].set(src_node.label_font_weight == "bold")
            fields_dict["fill_var"].set(self._color_to_name(src_node.fill_color))
            fields_dict["outline_var"].set(self._color_to_name(src_node.outline_color))
            fields_dict["outline_enabled_var"].set(src_node.outline_enabled)
            thickness_map = {0.5: "Thin", 1.0: "Normal", 2.0: "Thick"}
            fields_dict["outline_thickness_var"].set(thickness_map.get(src_node.outline_scale, "Normal"))
            fields_dict["outline_style_var"].set("Dashed" if src_node.outline_style == "dashed" else "Solid")
            fields_dict["h_align_var"].set(getattr(src_node, "label_h_align", "left").capitalize())
            fields_dict["v_align_var"].set(getattr(src_node, "label_v_align", "top").capitalize())

        if node:
            if _editing_gate:
                _populate_fields(gf, node)
                gate_var.set(node.kind)
            else:
                _populate_fields(bf, node)

        def _apply_block_changes(target: Node, new_name: str):
            target.name = new_name
            target.label_font_size = font_size_var.get()
            target.label_font_family = font_family_var.get()
            target.label_font_weight = "bold" if bold_var.get() else "normal"
            target.fill_color = self._color_to_hex(fill_var.get())
            target.outline_color = self._color_to_hex(outline_var.get())
            thickness_map = {"Thin": 0.5, "Normal": 1.0, "Thick": 2.0}
            target.outline_scale = thickness_map.get(outline_thickness_var.get(), 1.0)
            target.outline_style = "dashed" if outline_style_var.get() == "Dashed" else "solid"
            target.outline_enabled = outline_enabled_var.get()
            target.label_h_align = h_align_var.get().lower()
            target.label_v_align = v_align_var.get().lower()
            self._redraw_node(target)

        def _apply_gate_style(target: Node):
            """Apply style fields from the diagram (gate) frame to a node."""
            target.label_font_size = gf["font_size_var"].get()
            target.label_font_family = gf["font_family_var"].get()
            target.label_font_weight = "bold" if gf["bold_var"].get() else "normal"
            target.fill_color = self._color_to_hex(gf["fill_var"].get())
            target.outline_color = self._color_to_hex(gf["outline_var"].get())
            thickness_map = {"Thin": 0.5, "Normal": 1.0, "Thick": 2.0}
            target.outline_scale = thickness_map.get(gf["outline_thickness_var"].get(), 1.0)
            target.outline_style = "dashed" if gf["outline_style_var"].get() == "Dashed" else "solid"
            target.outline_enabled = gf["outline_enabled_var"].get()
            target.label_h_align = gf["h_align_var"].get().lower()
            target.label_v_align = gf["v_align_var"].get().lower()

        def _create_or_edit():
            if mode == "create" and mode_var.get() == "gate":
                gate_kind = gate_var.get()
                # Use name from diagram name field, or auto-generate
                custom_name = gf["name_entry"].get("1.0", "end-1c").strip()
                if custom_name and custom_name in self.nodes:
                    messagebox.showerror("Error", f"Name '{custom_name}' already exists.", parent=window)
                    return
                name = custom_name if custom_name else _unique_gate_name(gate_kind)
                gate_def = self._gate_definitions()[gate_kind]
                # Diagram shapes get 1 port on each side (top/bottom/left/right)
                if gate_kind in self._DIAGRAM_SHAPES:
                    inputs = [
                        Port(name="left", kind="in", side="left", offset=0.5),
                        Port(name="top", kind="in", side="top", offset=0.5),
                    ]
                    outputs = [
                        Port(name="right", kind="out", side="right", offset=0.5),
                        Port(name="bottom", kind="out", side="bottom", offset=0.5),
                    ]
                else:
                    inputs = [Port(name=f"in{idx}", kind="in") for idx in range(1, gate_def["inputs"] + 1)]
                    outputs = [Port(name=f"out{idx}", kind="out") for idx in range(1, gate_def["outputs"] + 1)]
                    _assign_port_offsets(inputs, "left")
                    _assign_port_offsets(outputs, "right")
                width = gate_def["width"]
                height = gate_def["height"]
                x, y = self._next_block_position()
                new_node = Node(
                    name=name,
                    kind=gate_kind,
                    inputs=inputs,
                    outputs=outputs,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    base_height=height,
                    fill_color="#e0e0e0",
                    outline_color=self._color_to_hex("GRAY"),
                    outline_enabled=True,
                    outline_style="solid",
                    outline_scale=1.0,
                    label_font_size=12,
                    label_font_family="Arial",
                    label_font_weight="bold",
                    level=self._next_level(),
                )
                _apply_gate_style(new_node)
                _align_gate_to_grid(new_node)
                self.nodes[name] = new_node
                self._draw_node(new_node)
                self._apply_z_order(active_node_name=new_node.name)
                self._record_history()
                window.destroy()
                return

            # Editing a diagram shape
            if _editing_gate and node:
                new_name = gf["name_entry"].get("1.0", "end-1c").strip()
                if not new_name:
                    return
                if new_name != node.name and new_name in self.nodes:
                    messagebox.showerror("Error", f"Name '{new_name}' already exists.", parent=window)
                    return
                old_name = node.name
                node.name = new_name
                _apply_gate_style(node)
                self._redraw_node(node)
                if new_name != old_name:
                    self._rename_node(old_name, new_name)
                self._apply_z_order(active_node_name=node.name)
                self._record_history()
                window.destroy()
                return

            new_name = name_entry.get("1.0", "end-1c").strip()
            if not new_name:
                return
            if mode == "create":
                if new_name in self.nodes:
                    messagebox.showerror("Error", f"Name '{new_name}' already exists.", parent=window)
                    return
                x, y = self._next_block_position()
                new_node = Node(
                    name=new_name,
                    kind="BLOCK",
                    inputs=[],
                    outputs=[],
                    x=x,
                    y=y,
                    width=160,
                    height=100,
                    base_height=100,
                    level=self._next_level(),
                )
                self.nodes[new_name] = new_node
                _apply_block_changes(new_node, new_name)
                self._apply_z_order(active_node_name=new_node.name)
                self._record_history()
                window.destroy()
                return
            if node and new_name != node.name and new_name in self.nodes:
                messagebox.showerror("Error", f"Name '{new_name}' already exists.", parent=window)
                return
            if node:
                old_name = node.name
                _apply_block_changes(node, new_name)
                if new_name != old_name:
                    self._rename_node(old_name, new_name)
                self._apply_z_order(active_node_name=node.name)
                self._record_history()
                window.destroy()

        tk.Button(window, text="Create", command=_create_or_edit).grid(row=2, column=0, columnspan=3, pady=8)

    def _rename_node(self, old_name: str, new_name: str):
        node = self.nodes.pop(old_name)
        node.name = new_name
        self.nodes[new_name] = node
        for connection in self.connections:
            if connection.src and connection.src[0] == old_name:
                connection.src = (new_name, connection.src[1])
            if connection.dst and connection.dst[0] == old_name:
                connection.dst = (new_name, connection.dst[1])
        self._redraw_node(node)

    def _align_gate_ports_to_grid(self, node: Node):
        node.x = self._snap_value(node.x)
        node.y = self._snap_value(node.y)
        for port in node.inputs + node.outputs:
            if port.side != "right":
                continue
            y = node.y + port.offset * node.height
            port.manual_y = self._snap_value(y)

    def _next_block_position(self) -> tuple[int, int]:
        if not self.nodes:
            return (80, 80)
        max_y = max(node.y + node.height for node in self.nodes.values())
        x = 80
        y = max_y + 60
        if y > 600:
            y = 80
            x = max(node.x + node.width for node in self.nodes.values()) + 60
        return x, y

    def _toggle_connect_mode(self):
        if self._mode == "connect":
            self._reset_connect_mode()
            return
        if self._mode in ("create_port", "delete_port", "move_port"):
            self._reset_port_mode()
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
        self._mode = "connect"
        self._selected_ports = []
        self._pending_midpoints = []
        self._wire_direction = None
        self._set_all_port_colors("yellow")

    def _reset_connect_mode(self):
        self._selected_ports = []
        self._pending_midpoints = []
        self._wire_direction = None
        self._clear_wire_preview()
        self._set_all_port_colors("black")
        self._mode = "normal"

    def _toggle_create_wire_mode(self):
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
            return
        if self._mode in ("connect", "create_port", "delete_port", "move_port"):
            self._reset_port_mode()
        wire_style = self._open_wire_style_dialog(
            "CREATE WIRE",
            self._create_wire_data["color"],
            self._create_wire_data["thickness"],
        )
        if not wire_style:
            return
        self._create_wire_data["color"], self._create_wire_data["thickness"] = wire_style
        self._mode = "create_wire"
        self._create_wire_data["start"] = None
        self._clear_create_wire_preview()

    def _open_wire_style_dialog(
        self,
        title: str,
        initial_color: str,
        initial_thickness: float,
    ) -> tuple[str, float] | None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.grab_set()

        color_options = list(self.COLOR_NAME_TO_HEX.keys())
        tk.Label(dialog, text="Color").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        color_name = self._color_to_name(initial_color)
        if color_name not in color_options:
            color_name = "BLACK"
        color_var = tk.StringVar(value=color_name)
        color_bar = tk.Frame(dialog)
        color_bar.grid(row=0, column=1, padx=6, pady=3, sticky="w")
        _wire_btns = {}
        def _wire_sel(name):
            color_var.set(name)
            for n, b in _wire_btns.items():
                b.configure(relief="sunken" if n == name else "raised",
                            bd=2 if n == name else 1)
        for cname in color_options:
            hex_val = self.COLOR_NAME_TO_HEX[cname]
            b = tk.Button(color_bar, width=2, height=1, bg=hex_val,
                          activebackground=hex_val, relief="raised", bd=1,
                          command=lambda n=cname: _wire_sel(n))
            b.pack(side="left", padx=1)
            _wire_btns[cname] = b
        _wire_sel(color_name)

        tk.Label(dialog, text="Thickness").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        thickness_lookup = {0.5: "Thin", 1.0: "Normal", 2.0: "Thick"}
        thickness_var = tk.StringVar(value=thickness_lookup.get(initial_thickness, "Normal"))
        thickness_menu = tk.OptionMenu(dialog, thickness_var, "Thin", "Normal", "Thick")
        thickness_menu.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        result = {"ok": False}

        def on_ok(_event=None):
            result["ok"] = True
            dialog.destroy()

        def on_cancel(_event=None):
            dialog.destroy()

        dialog.bind("<Escape>", on_cancel)
        dialog.bind("<Return>", on_ok)
        tk.Button(dialog, text="OK", width=8, command=on_ok).grid(row=2, column=0, padx=6, pady=8)
        tk.Button(dialog, text="Cancel", width=8, command=on_cancel).grid(row=2, column=1, padx=6, pady=8)

        dialog.wait_window()
        if not result["ok"]:
            return None
        thickness_map = {"Thin": 0.5, "Normal": 1.0, "Thick": 2.0}
        color = self._color_to_hex(color_var.get())
        thickness = thickness_map.get(thickness_var.get(), 1.0)
        return (color, thickness)

    def _open_wire_style_editor(self, connection: Connection):
        wire_style = self._open_wire_style_dialog(
            "EDIT WIRE",
            connection.line_color,
            connection.line_thickness,
        )
        if not wire_style:
            return
        connection.line_color, connection.line_thickness = wire_style
        if connection.line_id:
            width = self._wire_selected_width(connection) if self._selected_wire is connection else self._wire_width(connection)
            self.canvas.itemconfig(connection.line_id, fill=connection.line_color, width=width)
        self._record_history()

    def _handle_create_wire_press(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        start = self._create_wire_data.get("start")
        if start is None:
            start_x = self._snap_value(event.x)
            start_y = self._snap_value(event.y)
            self._create_wire_data["start"] = (start_x, start_y)
            self._update_create_wire_preview(event.x, event.y)
            return
        start_x, start_y = start
        end_x, end_y = self._constrain_wire_end(start_x, start_y, event.x, event.y)
        if (start_x, start_y) == (end_x, end_y):
            return
        connection = Connection(src=None, dst=None)
        connection.free_points = [(start_x, start_y), (end_x, end_y)]
        connection.line_color = self._create_wire_data["color"]
        connection.line_thickness = self._create_wire_data["thickness"]
        connection.show_arrow = False
        self.connections.append(connection)
        self._draw_connection(connection)
        self._record_history()
        self._create_wire_data["start"] = None
        self._clear_create_wire_preview()

    def _update_create_wire_preview(self, x: float, y: float):
        start = self._create_wire_data.get("start")
        if start is None:
            self._clear_create_wire_preview()
            return
        start_x, start_y = start
        end_x, end_y = self._constrain_wire_end(start_x, start_y, x, y)
        coords = [start_x, start_y, end_x, end_y]
        preview_id = self._create_wire_data.get("preview_id")
        width = max(1, int(round(self._create_wire_data["thickness"] * 2)))
        if preview_id is None:
            preview_id = self.canvas.create_line(*coords, width=width, fill="#999999")
            self._create_wire_data["preview_id"] = preview_id
        else:
            self.canvas.coords(preview_id, *coords)

    def _clear_create_wire_preview(self):
        preview_id = self._create_wire_data.get("preview_id")
        if preview_id:
            self.canvas.delete(preview_id)
        self._create_wire_data["preview_id"] = None

    def _reset_create_wire_mode(self):
        self._create_wire_data["start"] = None
        self._clear_create_wire_preview()
        self._mode = "normal"

    def _constrain_wire_end(self, start_x: int, start_y: int, raw_x: float, raw_y: float) -> tuple[int, int]:
        end_x = self._snap_value(raw_x)
        end_y = self._snap_value(raw_y)
        dx = end_x - start_x
        dy = end_y - start_y
        if dx == 0 and dy == 0:
            return end_x, end_y
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx >= abs_dy * 2:
            return end_x, start_y
        if abs_dy >= abs_dx * 2:
            return start_x, end_y
        length = max(abs_dx, abs_dy)
        return (
            start_x + (length if dx >= 0 else -length),
            start_y + (length if dy >= 0 else -length),
        )


    def _current_wire_direction(self) -> str:
        direction = self._wire_direction or "horizontal"
        if len(self._pending_midpoints) % 2 == 1:
            direction = "vertical" if direction == "horizontal" else "horizontal"
        return direction

    def _update_wire_preview(self, x: float, y: float):
        if len(self._selected_ports) != 1:
            self._clear_wire_preview()
            return
        node_name, port_name = self._selected_ports[0]
        port_id = self._get_port_canvas_id(node_name, port_name)
        if not port_id:
            self._clear_wire_preview()
            return
        start_x, start_y = self._port_center(port_id)
        end_x, end_y = self._snap_value(x), self._snap_value(y)
        points = [(start_x, start_y)]
        for mx, my in self._pending_midpoints:
            points.append((mx, my))
        last_x, last_y = points[-1]
        cur_dir = self._current_wire_direction()
        if cur_dir == "horizontal":
            points.append((end_x, last_y))
        else:
            points.append((last_x, end_y))
        coords = [c for p in points for c in p]
        if len(coords) < 4:
            coords = [start_x, start_y, end_x, end_y]
        if self._wire_preview_id is None:
            self._wire_preview_id = self.canvas.create_line(*coords, width=2, fill="#999999")
        else:
            self.canvas.coords(self._wire_preview_id, *coords)

    def _clear_wire_preview(self):
        if self._wire_preview_id is not None:
            self.canvas.delete(self._wire_preview_id)
        self._wire_preview_id = None

    def _toggle_delete_mode(self):
        # Exit delete blink mode if active
        if self._delete_mode:
            self._stop_delete_blink()
            self._delete_mode = False
            self._mode = "normal"
            self._update_status_bar()
            return
        # Exit any special mode first → go to normal
        if self._mode in ("connect", "create_port", "delete_port", "move_port"):
            self._reset_port_mode()
            self._update_status_bar()
            return
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
            self._update_status_bar()
            return
        if self._mode == "wire_port":
            self._exit_wire_port_mode()
            self._update_status_bar()
            return
        # Multi-select delete: delete all selected items immediately
        if self._multi_select["nodes"] or self._multi_select["wires"] or self._multi_select["labels"]:
            for hid in self._multi_select["highlights"]:
                self.canvas.delete(hid)
            self._multi_select["highlights"] = []
            for conn in list(self._multi_select["wires"]):
                self._remove_connection(conn, record=False)
            for conn in list(self._multi_select["labels"]):
                self._remove_connection(conn, record=False)
            for name in list(self._multi_select["nodes"]):
                node = self.nodes.get(name)
                if node:
                    self._remove_node(node)
            self._multi_select = {
                "active": False, "rect_id": None,
                "start_x": 0, "start_y": 0,
                "nodes": [], "wires": [], "labels": [],
                "dragging": False, "drag_x": 0, "drag_y": 0,
                "highlights": [],
            }
            self._record_history()
            self._update_status_bar()
            return
        # Single selected node delete
        if self._active_node_name and not self._delete_mode:
            node = self.nodes.get(self._active_node_name)
            if node:
                self._unhighlight_node()
                self._remove_node(node)
                self._active_node_name = None
                self._update_status_bar()
                return
        # Single selected wire delete
        if self._selected_wire and not self._delete_mode:
            conn = self._selected_wire
            self._deselect_wire()
            self._remove_connection(conn)
            self._update_status_bar()
            return
        # Nothing selected: enter delete blink mode
        self._delete_mode = True
        self._delete_blink_on = False
        self._capture_delete_colors()
        self._schedule_delete_blink()

    def _capture_delete_colors(self):
        self._wire_color_backup = {}
        self._node_color_backup = {}
        for node in self.nodes.values():
            if node.kind == "BLOCK" and node.items:
                rect_id = node.items[0]
                fill = self.canvas.itemcget(rect_id, "fill")
                outline = self.canvas.itemcget(rect_id, "outline")
                self._node_color_backup[node.name] = (fill, outline)
        for connection in self.connections:
            if connection.line_id:
                self._wire_color_backup[connection.line_id] = self.canvas.itemcget(connection.line_id, "fill")

    def _schedule_delete_blink(self):
        self._apply_delete_blink()
        self._delete_blink_job = self.root.after(1000, self._schedule_delete_blink)

    def _apply_delete_blink(self):
        self._delete_blink_on = not self._delete_blink_on
        if self._delete_blink_on:
            for node in self.nodes.values():
                if node.kind == "BLOCK":
                    if node.items:
                        fill, _outline = self._node_color_backup.get(node.name, (node.fill_color, node.outline_color))
                        self.canvas.itemconfig(node.items[0], fill=fill, outline="red")
                else:
                    overlay_id = self._delete_overlays.get(node.name)
                    if not overlay_id:
                        overlay_id = self.canvas.create_rectangle(
                            node.x,
                            node.y,
                            node.x + node.width,
                            node.y + node.height,
                            outline="red",
                            width=3,
                        )
                        self._delete_overlays[node.name] = overlay_id
                    else:
                        self.canvas.coords(
                            overlay_id,
                            node.x,
                            node.y,
                            node.x + node.width,
                            node.y + node.height,
                        )
                        self.canvas.itemconfig(overlay_id, outline="red")
            for connection in self.connections:
                if connection.line_id:
                    self.canvas.itemconfig(connection.line_id, fill="red")
        else:
            for node in self.nodes.values():
                if node.kind == "BLOCK" and node.items:
                    fill, outline = self._node_color_backup.get(node.name, (node.fill_color, node.outline_color))
                    self.canvas.itemconfig(node.items[0], fill=fill, outline=outline)
            for overlay_id in self._delete_overlays.values():
                self.canvas.delete(overlay_id)
            self._delete_overlays.clear()
            for connection in self.connections:
                if connection.line_id:
                    original = self._wire_color_backup.get(connection.line_id, "#333333")
                    self.canvas.itemconfig(connection.line_id, fill=original)

    def _stop_delete_blink(self):
        if self._delete_blink_job:
            self.root.after_cancel(self._delete_blink_job)
        self._delete_blink_job = None
        self._delete_blink_on = False
        for node in self.nodes.values():
            if node.kind == "BLOCK" and node.items:
                fill, outline = self._node_color_backup.get(node.name, (node.fill_color, node.outline_color))
                self.canvas.itemconfig(node.items[0], fill=fill, outline=outline)
        for overlay_id in self._delete_overlays.values():
            self.canvas.delete(overlay_id)
        self._delete_overlays.clear()
        for connection in self.connections:
            if connection.line_id:
                original = self._wire_color_backup.get(connection.line_id, "#333333")
                self.canvas.itemconfig(connection.line_id, fill=original)

    def _set_all_port_colors(self, color: str):
        for node in self.nodes.values():
            for port in node.inputs + node.outputs:
                self._set_port_color(port, color)

    def _set_port_color(self, port: Port, color: str):
        port.color = color
        if port.canvas_id:
            hidden = not self._show_ports and color == "black"
            fill = "" if hidden else color
            outline = "" if hidden else color
            width = 0 if hidden else 1
            self.canvas.itemconfig(port.canvas_id, fill=fill, outline=outline, width=width)

    def _set_all_wire_colors(self, color: str):
        for connection in self.connections:
            if connection.line_id:
                self.canvas.itemconfig(connection.line_id, fill=color)
            connection.line_color = color

    def _set_all_wire_widths(self, width: int):
        for connection in self.connections:
            if connection.line_id:
                self.canvas.itemconfig(connection.line_id, width=width)
            connection.line_thickness = max(0.5, width / 2)

    def _remove_active_node(self):
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node:
            return
        self._remove_node(node)

    def _remove_node(self, node: Node):
        to_remove = [
            conn
            for conn in self.connections
            if (conn.src and conn.src[0] == node.name) or (conn.dst and conn.dst[0] == node.name)
        ]
        for conn in to_remove:
            self._remove_connection(conn, record=False)
        for item in node.items:
            self.canvas.delete(item)
        overlay_id = self._delete_overlays.pop(node.name, None)
        if overlay_id:
            self.canvas.delete(overlay_id)
        self._node_color_backup.pop(node.name, None)
        self._port_items = {key: value for key, value in self._port_items.items() if value[0] != node.name}
        self._outline_backup.pop(node.name, None)
        # Remove from junction_ports of any parent wire
        for conn in self.connections:
            conn.junction_ports = [jp for jp in conn.junction_ports if jp.get("node") != node.name]
        self.nodes.pop(node.name, None)
        if self._active_node_name == node.name:
            self._active_node_name = None
        self._record_history()

    def _remove_connection(self, connection: Connection, record: bool = True):
        if self._selected_wire is connection:
            self._selected_wire = None
        if self._selected_label_conn is connection:
            self._deselect_label()
        # Remove junction PORT nodes owned by this connection
        for jp in connection.junction_ports:
            jname = jp.get("node")
            jnode = self.nodes.get(jname)
            if jnode and jnode.kind == "PORT":
                # Remove wires connected from/to this junction
                child_conns = [
                    c for c in self.connections
                    if c is not connection and (
                        (c.src and c.src[0] == jname) or (c.dst and c.dst[0] == jname)
                    )
                ]
                for cc in child_conns:
                    if cc.line_id:
                        self.canvas.delete(cc.line_id)
                        self._wire_color_backup.pop(cc.line_id, None)
                    if cc.label_id:
                        self.canvas.delete(cc.label_id)
                self.connections = [c for c in self.connections if c not in child_conns]
                for item in jnode.items:
                    self.canvas.delete(item)
                self._port_items = {k: v for k, v in self._port_items.items() if v[0] != jname}
                self.nodes.pop(jname, None)
        if connection.line_id:
            self.canvas.delete(connection.line_id)
            self._wire_color_backup.pop(connection.line_id, None)
        if connection.label_id:
            self.canvas.delete(connection.label_id)
        self.connections = [conn for conn in self.connections if conn is not connection]
        if record:
            self._record_history()

    def _remove_port(self, node: Node, port: Port):
        if port.canvas_id:
            self.canvas.delete(port.canvas_id)
            self._port_items.pop(port.canvas_id, None)
        node.inputs = [p for p in node.inputs if p is not port]
        node.outputs = [p for p in node.outputs if p is not port]
        to_remove = [conn for conn in self.connections if conn.src == (node.name, port.name) or conn.dst == (node.name, port.name)]
        for conn in to_remove:
            self._remove_connection(conn, record=False)
        self._update_connections()
        self._record_history()

    def _toggle_ports(self):
        self._show_ports = not self._show_ports
        self._draw_grid()
        for node in self.nodes.values():
            for port in node.inputs + node.outputs:
                self._set_port_color(port, port.color)

    def _toggle_create_port_mode(self):
        if self._mode == "create_port":
            self._reset_port_mode()
            return
        if self._selected_wire and (self._selected_wire.free_points or self._selected_wire.line_id):
            if self._mode == "wire_port":
                self._exit_wire_port_mode()
                return
            if self._mode in ("connect", "create_port", "delete_port", "move_port"):
                self._reset_port_mode()
            if self._mode == "create_wire":
                self._reset_create_wire_mode()
            self._enter_wire_port_mode()
            return
        if not self._active_node_name and not self._selected_wire:
            return
        if self._mode in ("connect", "delete_port", "move_port"):
            self._reset_port_mode()
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
        self._mode = "create_port"
        self._pending_port_node_select = self._active_node_name is None
        node = self.nodes.get(self._active_node_name)
        if node and node.kind == "BLOCK":
            for port in node.inputs + node.outputs:
                if port.canvas_id:
                    _, current_y = self._port_center(port.canvas_id)
                    if port.side in ("left", "right"):
                        port.manual_y = current_y
            self._outline_backup.setdefault(node.name, node.outline_color)
            node.outline_color = "blue"
            node.resize_enabled = True
            self._redraw_node(node)
        else:
            self._mode = "normal"

    def _unique_node_name(self, base: str) -> str:
        index = 1
        while True:
            candidate = f"{base}{index}"
            if candidate not in self.nodes:
                return candidate
            index += 1

    def _toggle_delete_port_mode(self):
        if self._mode == "delete_port":
            self._reset_port_mode()
            return
        if not self._active_node_name:
            return
        if self._mode in ("connect", "create_port", "move_port"):
            self._reset_port_mode()
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
        self._mode = "delete_port"
        node = self.nodes.get(self._active_node_name)
        if node and node.kind == "BLOCK":
            self._outline_backup.setdefault(node.name, node.outline_color)
            node.resize_enabled = True
            for port in node.inputs + node.outputs:
                self._set_port_color(port, "red")
        else:
            self._mode = "normal"

    def _toggle_move_port_mode(self):
        if self._mode == "move_port":
            self._reset_port_mode()
            return
        if not self._active_node_name:
            return
        if self._mode in ("connect", "create_port", "delete_port"):
            self._reset_port_mode()
        if self._mode == "create_wire":
            self._reset_create_wire_mode()
        self._mode = "move_port"
        node = self.nodes.get(self._active_node_name)
        if node and node.kind == "BLOCK":
            self._outline_backup.setdefault(node.name, node.outline_color)
            node.resize_enabled = True
            for port in node.inputs + node.outputs:
                if port.canvas_id:
                    _, current_y = self._port_center(port.canvas_id)
                    if port.side in ("left", "right"):
                        port.manual_y = current_y
                self._set_port_color(port, "blue")
            self._redraw_node(node)
        else:
            self._mode = "normal"

    def _rotate_active_selection(self):
        if self._selected_label_conn and self._selected_label_conn.label_id:
            self._rotate_label(self._selected_label_conn)
            return
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node:
            return
        self._rotate_node(node)

    def _rotate_label(self, connection: Connection):
        connection.label_angle = (connection.label_angle + 90) % 360
        if connection.label_id:
            self.canvas.itemconfig(connection.label_id, angle=connection.label_angle)
        self._record_history()

    def _rotate_node(self, node: Node):
        cx = node.x + node.width / 2
        cy = node.y + node.height / 2
        old_positions = [(port, self._port_position(node, port)) for port in node.inputs + node.outputs]
        new_width, new_height = node.height, node.width
        node.rotation = (node.rotation + 90) % 360
        node.width = new_width
        node.height = new_height
        node.x = self._snap_value(cx - new_width / 2)
        node.y = self._snap_value(cy - new_height / 2)
        new_cx = node.x + node.width / 2
        new_cy = node.y + node.height / 2
        shift_x = new_cx - cx
        shift_y = new_cy - cy
        left, right = node.x, node.x + node.width
        top, bottom = node.y, node.y + node.height
        for port, (px, py) in old_positions:
            # Clockwise 90°: (x,y) relative to center -> (-y, x)
            rx = cx - (py - cy) + shift_x
            ry = cy + (px - cx) + shift_y
            distances = {
                "left": abs(rx - left),
                "right": abs(rx - right),
                "top": abs(ry - top),
                "bottom": abs(ry - bottom),
            }
            side = min(distances, key=distances.get)
            port.side = side
            if side in ("left", "right"):
                port.manual_y = ry
                port.offset = 0 if node.height == 0 else (ry - top) / node.height
            else:
                port.manual_y = None
                port.offset = 0 if node.width == 0 else (rx - left) / node.width
        self._clamp_ports_to_node(node)
        self._redraw_node(node)
        self._update_connections()
        self._record_history()

    def _toggle_wire_name_mode(self):
        if self._selected_wire:
            self._open_label_dialog(self._selected_wire, is_new=(self._selected_wire.label is None))
            return
        self._create_free_label()

    def _create_free_label(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("LABEL")
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Text:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        text_var = tk.StringVar()
        text_entry = tk.Entry(dialog, textvariable=text_var, width=30)
        text_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        text_entry.focus_set()

        tk.Label(dialog, text="Font:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        font_families = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia"]
        font_var = tk.StringVar(value="Arial")
        font_combo = ttk.Combobox(dialog, textvariable=font_var, values=font_families, width=18)
        font_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

        tk.Label(dialog, text="Size:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        size_var = tk.IntVar(value=12)
        size_spin = tk.Spinbox(dialog, from_=6, to=72, textvariable=size_var, width=5)
        size_spin.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        bold_var = tk.BooleanVar(value=False)
        bold_check = tk.Checkbutton(dialog, text="Bold", variable=bold_var)
        bold_check.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        result = {"ok": False}

        def on_ok(_event=None):
            result["ok"] = True
            dialog.destroy()

        def on_cancel(_event=None):
            dialog.destroy()

        text_entry.bind("<Return>", on_ok)
        dialog.bind("<Escape>", on_cancel)
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        tk.Button(btn_frame, text="OK", width=8, command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=8, command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()
        if not result["ok"]:
            return
        new_text = text_var.get()
        if not new_text:
            return
        font_family = font_var.get() or "Arial"
        try:
            font_size = int(size_var.get())
        except (ValueError, tk.TclError):
            font_size = 12
        cx = self.canvas.canvasx(self.canvas.winfo_width() / 2)
        cy = self.canvas.canvasy(self.canvas.winfo_height() / 2)
        connection = Connection(src=None, dst=None, label=new_text)
        connection.label_font_family = font_family
        connection.label_font_size = font_size
        connection.label_font_weight = "bold" if bold_var.get() else "normal"
        connection.label_x = cx
        connection.label_y = cy
        font = (font_family, font_size, connection.label_font_weight)
        connection.label_id = self.canvas.create_text(
            cx, cy, text=new_text, font=font, anchor="s", angle=connection.label_angle,
        )
        self.canvas.addtag_withtag("label", connection.label_id)
        self.connections.append(connection)
        self._record_history()

    def _reset_port_mode(self):
        if self._mode == "connect":
            self._reset_connect_mode()
        if self._mode == "create_port" and self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node:
                node.outline_color = self._outline_backup.pop(node.name, node.outline_color)
                node.resize_enabled = False
                self._redraw_node(node)
        if self._mode == "delete_port" and self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node:
                for port in node.inputs + node.outputs:
                    self._set_port_color(port, "black")
                node.resize_enabled = False
                node.outline_color = self._outline_backup.pop(node.name, node.outline_color)
                self._redraw_node(node)
        if self._mode == "move_port" and self._active_node_name:
            node = self.nodes.get(self._active_node_name)
            if node:
                for port in node.inputs + node.outputs:
                    self._set_port_color(port, "black")
                node.resize_enabled = False
                node.outline_color = self._outline_backup.pop(node.name, node.outline_color)
                self._redraw_node(node)
        self._pending_port_node_select = False
        self._mode = "normal"

    def _handle_create_port_click(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        if not self._active_node_name and self._pending_port_node_select:
            item = self.canvas.find_withtag("current")
            if item:
                tags = self.canvas.gettags(item[0])
                node_tag = next((tag for tag in tags if tag.startswith("node:")), None)
                if node_tag:
                    self._active_node_name = node_tag.split(":", 1)[1]
            self._pending_port_node_select = False
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node or node.kind != "BLOCK":
            return
        edge = self._edge_for_point(node, event.x, event.y)
        if not edge:
            return
        port_name = f"p{len(node.inputs) + len(node.outputs) + 1}"
        offset = self._edge_offset(node, edge, event.x, event.y)
        port = Port(name=port_name, kind="io", side=edge, offset=offset)
        node.inputs.append(port)
        node.outline_color = self._outline_backup.pop(node.name, node.outline_color)
        node.resize_enabled = False
        self._redraw_node(node)
        self._mode = "normal"
        self._record_history()

    def _handle_wire_port_click(self, event):
        event.x, event.y = self._cx(event), self._cy(event)
        connection = self._selected_wire
        if not connection or not connection.line_id:
            self._exit_wire_port_mode()
            return
        coords = self._connection_line_coords(connection)
        if not coords or len(coords) < 4:
            self._exit_wire_port_mode()
            return
        px, py = self._nearest_point_on_polyline(coords, event.x, event.y)
        if self._distance_squared(px, py, event.x, event.y) > (6.0 ** 2):
            return
        seg_dir = self._segment_direction_at(coords, px, py)
        # Port side perpendicular to the wire segment
        if seg_dir == "horizontal":
            port_side = "top"
        else:
            port_side = "left"
        jname = self._create_junction_at(px, py, port_side=port_side)
        # Register junction in parent wire's junction_ports
        if jname:
            ratio = self._point_ratio_on_polyline(coords, px, py)
            connection.junction_ports.append({"node": jname, "ratio": ratio})
        self._exit_wire_port_mode()

    def _junction_port_xy(self, node: Node) -> tuple[float, float]:
        """Return the port circle center position of a PORT (junction) node."""
        ports = node.inputs + node.outputs
        if ports:
            return self._port_position(node, ports[0])
        return node.x + node.width / 2, node.y + node.height / 2

    def _find_parent_wire(self, node: Node) -> Connection | None:
        """Find the wire (free-point or connected) that a PORT node sits on."""
        if node.kind != "PORT":
            return None
        # First check junction_ports for definitive match
        for conn in self.connections:
            for jp in conn.junction_ports:
                if jp.get("node") == node.name:
                    return conn
        # Fallback to proximity search
        ref_x, ref_y = self._junction_port_xy(node)
        best_conn = None
        best_dist = float("inf")
        for conn in self.connections:
            # Skip connections FROM or TO this junction node
            if conn.src and conn.src[0] == node.name:
                continue
            if conn.dst and conn.dst[0] == node.name:
                continue
            coords = self._connection_line_coords(conn)
            if not coords or len(coords) < 4:
                continue
            px, py = self._nearest_point_on_polyline(coords, ref_x, ref_y)
            dist = self._distance_squared(px, py, ref_x, ref_y)
            if dist < best_dist:
                best_dist = dist
                best_conn = conn
        if best_dist < 20 ** 2:
            return best_conn
        return None

    def _segment_direction_at(self, coords: list[float], px: float, py: float) -> str:
        """Return 'horizontal' or 'vertical' for the segment nearest to (px, py)."""
        best_dir = "horizontal"
        best_dist = float("inf")
        for i in range(0, len(coords) - 2, 2):
            ax, ay = coords[i], coords[i + 1]
            bx, by = coords[i + 2], coords[i + 3]
            cx, cy = self._nearest_point_on_segment(ax, ay, bx, by, px, py)
            d = self._distance_squared(cx, cy, px, py)
            if d < best_dist:
                best_dist = d
                if abs(ax - bx) < 1:
                    best_dir = "vertical"
                else:
                    best_dir = "horizontal"
        return best_dir

    def _junction_node_pos(self, px: float, py: float, port_side: str, size: int = 12) -> tuple[int, int]:
        """Compute junction node (x, y) so that the port circle center is at (px, py)."""
        half = size / 2
        if port_side == "top":
            return int(px - half), int(py)
        elif port_side == "bottom":
            return int(px - half), int(py - size)
        elif port_side == "left":
            return int(px), int(py - half)
        else:  # right
            return int(px - size), int(py - half)

    def _create_junction_at(self, x: float, y: float, port_side: str = "left",
                            name: str | None = None) -> str:
        if not name or name in self.nodes:
            name = self._unique_node_name("Junction")
        size = 12
        nx, ny = self._junction_node_pos(x, y, port_side, size)
        node = Node(
            name=name,
            kind="PORT",
            inputs=[],
            outputs=[],
            x=nx,
            y=ny,
            width=size,
            height=size,
            base_height=size,
            level=self._next_level(),
            fill_color="white",
            outline_color="black",
            outline_enabled=True,
            outline_style="solid",
            outline_scale=1.0,
            label_font_size=1,
            label_font_family="Arial",
            label_font_weight="normal",
        )
        port = Port(name="p1", kind="io", side=port_side, offset=0.5)
        if port_side in ("left", "right"):
            port.manual_y = y
        node.inputs = [port]
        self.nodes[name] = node
        self._draw_node(node)
        self._apply_z_order(active_node_name=node.name)
        self._record_history()
        return name

    def _enter_wire_port_mode(self):
        connection = self._selected_wire
        if not connection or not connection.line_id:
            return
        if connection.line_id not in self._wire_port_backup:
            current_width = int(float(self.canvas.itemcget(connection.line_id, "width") or 0))
            current_color = self.canvas.itemcget(connection.line_id, "fill") or connection.line_color
            self._wire_port_backup[connection.line_id] = (current_width, current_color)
        self.canvas.itemconfig(connection.line_id, width=max(6, self._wire_width(connection) + 3), fill="blue")
        self._mode = "wire_port"

    def _exit_wire_port_mode(self):
        connection = self._selected_wire
        if connection and connection.line_id:
            backup = self._wire_port_backup.pop(connection.line_id, None)
            if backup is not None:
                orig_width, orig_color = backup
                self.canvas.itemconfig(connection.line_id, width=orig_width, fill=orig_color)
        self._mode = "normal"

    def _handle_delete_port_click(self, event):
        if not self._active_node_name:
            return
        item = self.canvas.find_withtag("current")
        if not item:
            return
        port_info = self._port_items.get(item[0])
        if not port_info:
            return
        node_name, port_name = port_info
        if node_name != self._active_node_name:
            return
        node = self.nodes.get(node_name)
        if not node:
            return
        port = next((p for p in node.inputs + node.outputs if p.name == port_name), None)
        if not port:
            return
        self._remove_port(node, port)
        self._reset_port_mode()

    def _bring_active_front(self):
        if self._selected_wire and self._selected_wire.line_id:
            self.canvas.tag_raise(self._selected_wire.line_id)
            if self._selected_wire.label_id:
                self.canvas.tag_raise(self._selected_wire.label_id)
            return
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node:
            return
        neighbor = next((other for other in self.nodes.values() if other.level == node.level + 1), None)
        if not neighbor:
            return
        node.level, neighbor.level = neighbor.level, node.level
        self._apply_z_order(active_node_name=node.name)
        self._record_history()

    def _send_active_back(self):
        if self._selected_wire and self._selected_wire.line_id:
            self.canvas.tag_lower(self._selected_wire.line_id)
            if self._selected_wire.label_id:
                self.canvas.tag_lower(self._selected_wire.label_id)
            self.canvas.tag_lower("grid")
            return
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node:
            return
        neighbor = next((other for other in self.nodes.values() if other.level == node.level - 1), None)
        if not neighbor:
            return
        node.level, neighbor.level = neighbor.level, node.level
        self._apply_z_order(active_node_name=node.name)
        self._record_history()

    def _apply_zoom(self, factor: float):
        if factor == 1.0:
            return
        self._zoom_scale *= factor
        for node in self.nodes.values():
            node.x *= factor
            node.y *= factor
            if node.kind == "BLOCK" or node.kind in self._CUSTOM_GATE_KINDS:
                node.width *= factor
                node.height *= factor
                node.base_height *= factor
            else:
                node.image_subsample = max(1, int(round(node.image_subsample / factor)))
                base_image = self._gate_base_image(node.kind)
                if base_image:
                    node.width = base_image.width() / node.image_subsample
                    node.height = base_image.height() / node.image_subsample
                    node.base_height = node.height
            for port in node.inputs + node.outputs:
                if port.manual_y is not None:
                    port.manual_y *= factor
            self._clamp_ports_to_node(node)
        for connection in self.connections:
            if connection.manual_mid_x is not None:
                connection.manual_mid_x *= factor
            if connection.manual_mid_y is not None:
                connection.manual_mid_y *= factor
            if connection.waypoints:
                connection.waypoints = [(wx * factor, wy * factor) for wx, wy in connection.waypoints]
            if connection.free_points:
                connection.free_points = [(px * factor, py * factor) for px, py in connection.free_points]
            if connection.label_x is not None:
                connection.label_x *= factor
            if connection.label_y is not None:
                connection.label_y *= factor
        self._draw_grid()
        for connection in self.connections:
            if connection.line_id:
                self.canvas.delete(connection.line_id)
                connection.line_id = None
            if connection.label_id:
                self.canvas.delete(connection.label_id)
                connection.label_id = None
        for node in self.nodes.values():
            self._redraw_node(node)
        for connection in self.connections:
            self._draw_connection(connection)
        self._apply_z_order()
        self._update_scroll_region()

    def _zoom_in(self):
        self._apply_zoom(1.1)
        self._record_history()

    def _zoom_out(self):
        self._apply_zoom(0.9)
        self._record_history()

    def _on_zoom_wheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self._apply_zoom(1.1)
        elif getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            self._apply_zoom(0.9)
        else:
            return
        self._record_history()

    def _on_pan_start(self, event):
        self._pan_data["active"] = True
        self._pan_data["x"] = event.x
        self._pan_data["y"] = event.y

    def _on_pan_motion(self, event):
        if not self._pan_data["active"]:
            return
        dx = event.x - self._pan_data["x"]
        dy = event.y - self._pan_data["y"]
        self._pan_data["x"] = event.x
        self._pan_data["y"] = event.y
        self.canvas.move("all", dx, dy)
        for node in self.nodes.values():
            node.x += dx
            node.y += dy
            for port in node.inputs + node.outputs:
                if port.manual_y is not None:
                    port.manual_y += dy
        for conn in self.connections:
            if conn.manual_mid_x is not None:
                conn.manual_mid_x += dx
            if conn.manual_mid_y is not None:
                conn.manual_mid_y += dy
            if conn.waypoints:
                conn.waypoints = [(wx + dx, wy + dy) for wx, wy in conn.waypoints]
            if conn.free_points:
                conn.free_points = [(px + dx, py + dy) for px, py in conn.free_points]
            if conn.label_x is not None:
                conn.label_x += dx
            if conn.label_y is not None:
                conn.label_y += dy

    def _on_pan_release(self, _event):
        if self._pan_data["active"]:
            self._draw_grid()
            self._record_history()
        self._pan_data["active"] = False

    def _build_payload(self, unscale: bool) -> dict[str, object]:
        def _unscale(value: float | None) -> float | None:
            if value is None:
                return None
            if not unscale:
                return value
            return round(value / self._zoom_scale, 2)

        # Collect junction PORT node names to exclude from blocks
        junction_node_names: set[str] = set()
        for connection in self.connections:
            for jp in connection.junction_ports:
                node_name = jp.get("node")
                if node_name:
                    junction_node_names.add(node_name)

        blocks = []
        for node in self.nodes.values():
            if node.name in junction_node_names:
                continue
            ports = {}
            for port in node.inputs + node.outputs:
                ports[port.name] = {
                    "side": port.side,
                    "offset": port.offset,
                    "manual_y": _unscale(port.manual_y),
                }
            blocks.append(
                {
                    "name": node.name,
                    "kind": node.kind,
                    "ports": ports,
                    "x": _unscale(node.x),
                    "y": _unscale(node.y),
                    "width": _unscale(node.width),
                    "height": _unscale(node.height),
                    "level": node.level,
                    "fill_color": self._color_to_name(node.fill_color),
                    "outline_color": self._color_to_name(node.outline_color),
                    "outline_enabled": node.outline_enabled,
                    "outline_thickness": node.outline_scale,
                    "outline_style": node.outline_style,
                    "font_size": node.label_font_size,
                    "font_family": node.label_font_family,
                    "font_weight": node.label_font_weight,
                    "rotation": node.rotation,
                    "label_h_align": getattr(node, "label_h_align", "left"),
                    "label_v_align": getattr(node, "label_v_align", "top"),
                }
            )
        blocks.sort(key=lambda block: block["level"])
        connections = []
        wires = []
        for connection in self.connections:
            conn_entry = {
                "src": f"{connection.src[0]}.{connection.src[1]}" if connection.src else None,
                "dst": f"{connection.dst[0]}.{connection.dst[1]}" if connection.dst else None,
                "label": connection.label,
            }
            if not connection.src and not connection.dst:
                if connection.free_points:
                    conn_entry["points"] = [(_unscale(px), _unscale(py)) for px, py in connection.free_points]
                if connection.label_x is not None:
                    conn_entry["label_x"] = _unscale(connection.label_x)
                if connection.label_y is not None:
                    conn_entry["label_y"] = _unscale(connection.label_y)
                if connection.label_font_family != "Arial":
                    conn_entry["label_font_family"] = connection.label_font_family
                if connection.label_font_size != 12:
                    conn_entry["label_font_size"] = connection.label_font_size
                if connection.label_font_weight != "normal":
                    conn_entry["label_font_weight"] = connection.label_font_weight
                if connection.label_angle:
                    conn_entry["label_angle"] = connection.label_angle
                if connection.line_color != "#333333":
                    conn_entry["line_color"] = self._color_to_name(connection.line_color)
                if connection.line_thickness != 1.0:
                    conn_entry["line_thickness"] = connection.line_thickness
                if not connection.show_arrow:
                    conn_entry["show_arrow"] = False
                # Save junction ports inline as WIRE_BAR
                if connection.junction_ports:
                    conn_entry["kind"] = "WIRE_BAR"
                    jp_list = []
                    coords = self._connection_line_coords(connection)
                    for jp in connection.junction_ports:
                        jnode = self.nodes.get(jp.get("node"))
                        if jnode and coords and len(coords) >= 4:
                            jx, jy = self._junction_port_xy(jnode)
                            ratio = self._point_ratio_on_polyline(coords, jx, jy)
                            jp_list.append({"name": jp["node"], "ratio": round(ratio, 6)})
                    if jp_list:
                        conn_entry["ports"] = jp_list
            connections.append(conn_entry)
            if not connection.src and not connection.dst:
                continue
            wire_data = {
                "src": f"{connection.src[0]}.{connection.src[1]}" if connection.src else None,
                "dst": f"{connection.dst[0]}.{connection.dst[1]}" if connection.dst else None,
                "manual_mid_x": _unscale(connection.manual_mid_x),
                "manual_mid_y": _unscale(connection.manual_mid_y),
            }
            if connection.waypoints:
                wire_data["waypoints"] = [(_unscale(wx), _unscale(wy)) for wx, wy in connection.waypoints]
            if connection.line_color != "#333333":
                wire_data["line_color"] = self._color_to_name(connection.line_color)
            if connection.line_thickness != 1.0:
                wire_data["line_thickness"] = connection.line_thickness
            if connection.label_font_family != "Arial":
                wire_data["label_font_family"] = connection.label_font_family
            if connection.label_font_size != 12:
                wire_data["label_font_size"] = connection.label_font_size
            if connection.label_font_weight != "normal":
                wire_data["label_font_weight"] = connection.label_font_weight
            if connection.label_angle:
                wire_data["label_angle"] = connection.label_angle
            if connection.label_x is not None:
                wire_data["label_x"] = _unscale(connection.label_x)
            if connection.label_y is not None:
                wire_data["label_y"] = _unscale(connection.label_y)
            if not connection.show_arrow:
                wire_data["show_arrow"] = False
            # Save junction ports inline in wire data
            if connection.junction_ports:
                jp_list = []
                coords = self._connection_line_coords(connection)
                for jp in connection.junction_ports:
                    jnode = self.nodes.get(jp.get("node"))
                    if jnode and coords and len(coords) >= 4:
                        jx, jy = self._junction_port_xy(jnode)
                        ratio = self._point_ratio_on_polyline(coords, jx, jy)
                        jp_list.append({"name": jp["node"], "ratio": round(ratio, 6)})
                if jp_list:
                    wire_data["ports"] = jp_list
            wires.append(wire_data)
        return {"blocks": blocks, "connections": connections, "wires": wires}

    def _serialize_state(self) -> dict[str, object]:
        payload = self._build_payload(unscale=False)
        payload["zoom_scale"] = self._zoom_scale
        return payload

    def _record_history(self, initial: bool = False):
        if self._suspend_history:
            return
        state = self._serialize_state()
        if initial:
            self._history = [state]
            self._redo_stack = []
            self._update_scroll_region()
            return
        if self._history and self._history[-1] == state:
            return
        self._history.append(state)
        self._redo_stack = []
        self._update_scroll_region()

    def _load_state(self, state: dict[str, object]):
        self._suspend_history = True
        if self._delete_mode:
            self._stop_delete_blink()
            self._delete_mode = False
        payload = {
            "blocks": state.get("blocks", []),
            "connections": state.get("connections", []),
            "wires": state.get("wires", []),
        }
        self.nodes, self.connections = parse_data(payload)
        self._zoom_scale = float(state.get("zoom_scale", 1.0))
        self.canvas.delete("all")
        self._grid_items.clear()
        self._port_items.clear()
        self._selected_ports = []
        self._pending_midpoints = []
        self._active_node_name = None
        self._outline_backup.clear()
        self._clear_wire_preview()
        self._clear_create_wire_preview()
        self._create_wire_data["start"] = None
        self._selected_wire = None
        self._selected_label_conn = None
        self._selected_label_border = None
        self._mode = "normal"
        self._draw_grid()
        for node in self.nodes.values():
            self._draw_node(node)
        for connection in self.connections:
            self._draw_connection(connection)
        self._materialize_pending_ports()
        self._apply_z_order()
        self._update_connections()
        self._update_scroll_region()
        self._suspend_history = False

    def _undo(self):
        if len(self._history) <= 1:
            return
        current = self._history.pop()
        self._redo_stack.append(current)
        self._load_state(self._history[-1])

    def _redo(self):
        if not self._redo_stack:
            return
        state = self._redo_stack.pop()
        self._history.append(state)
        self._load_state(state)

    def _open_guide(self):
        window = tk.Toplevel(self.root)
        window.title("Guide")
        window.configure(bg="white")
        text = (
            "Buttons & Shortcuts\n"
            "- NEW (I): create a new block or gate.\n"
            "- EDIT (E): edit the selected block.\n"
            "- ROTATE (R): rotate the selected block/gate/label 90° clockwise.\n"
            "- DELETE (Del): toggle delete mode (items blink red, click to remove, Del to exit).\n"
            "- SAVE (Ctrl+S): save to input.json.\n"
            "- CONNECT (W): connect ports (click empty space to add a bend).\n"
            "- DISCONNECT: click a wire to remove it.\n"
            "- LABEL (L): click a wire to add/edit a label.\n"
            "- CREATE WIRE (Ctrl+W): draw a straight wire by clicking two points.\n"
            "- CREATE PORT (A): add a port on the selected block edge.\n"
            "- DELETE PORT (Ctrl+A): remove a port on the selected block.\n"
            "- MOVE PORT (Shift+A): drag ports to reposition on the selected block.\n"
            "- SHOW/HIDE PORT (`): toggle port visibility.\n"
            "- BRING FRONT (F): move block forward.\n"
            "- SEND BACK (B): move block backward.\n"
            "- ZOOM IN/OUT (Ctrl+Wheel): zoom with the mouse wheel.\n"
            "- COPY/PASTE (Ctrl+C / Ctrl+V): copy and paste blocks, gates, wires.\n"
            "- UNDO/REDO: Ctrl+Z / Ctrl+Y.\n"
            "- Auto-alignment guides appear when dragging elements.\n"
            "- PAN: hold middle mouse button (wheel) and drag to move the view.\n"
            "\n"
            "Tips\n"
            "- Hover a block/gate edge to highlight it, press S to resize (border turns yellow), click to finish.\n"
            "- Select a free wire, press A, then click a point on the wire to place a junction port.\n"
            "- In CONNECT mode, click empty space to add orthogonal bends. Multiple bends supported.\n"
        )
        label = tk.Label(window, text=text, justify="left", bg="white", font=("Arial", 10))
        label.pack(padx=12, pady=12)

    def _save_json(self):
        payload = self._build_payload(unscale=True)
        self.input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._save_flash = True
        if hasattr(self, "_save_flash_job") and self._save_flash_job:
            self.root.after_cancel(self._save_flash_job)
        self._save_flash_job = self.root.after(1500, self._clear_save_flash)

    def _clear_save_flash(self):
        self._save_flash = False
        self._save_flash_job = None

    def _save_png(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="Save PNG",
        )
        if path:
            self.save_diagram(Path(path))

    def _toggle_wire_arrow(self):
        if not self._selected_wire:
            return
        connection = self._selected_wire
        connection.show_arrow = not connection.show_arrow
        if connection.line_id:
            self.canvas.itemconfigure(
                connection.line_id,
                arrow=tk.LAST if connection.show_arrow else tk.NONE,
            )
        self._record_history()

    def _gate_types(self) -> list[str]:
        return list(self._gate_definitions().keys())

    def _gate_definitions(self) -> dict[str, dict[str, int]]:
        return self._gate_definitions_static()

    def _gate_base_image(self, gate_kind: str) -> tk.PhotoImage | None:
        if gate_kind in self._gate_source_images:
            return self._gate_source_images[gate_kind]
        image_path = Path(__file__).resolve().parent / "gate_image" / f"{gate_kind}.png"
        if not image_path.exists():
            return None
        image = tk.PhotoImage(file=str(image_path))
        self._gate_source_images[gate_kind] = image
        return image

    def _load_gate_image(self, gate_kind: str, subsample: int) -> tk.PhotoImage | None:
        key = (gate_kind, subsample)
        if key in self._gate_images:
            return self._gate_images[key]
        base_image = self._gate_base_image(gate_kind)
        if not base_image:
            return None
        image = base_image.subsample(subsample, subsample)
        self._gate_images[key] = image
        return image

    @staticmethod
    def _gate_definitions_static() -> dict[str, dict[str, int]]:
        return {
            "AND2": {"inputs": 2, "outputs": 1, "width": 60, "height": 50},
            "AND4": {"inputs": 4, "outputs": 1, "width": 60, "height": 50},
            "OR2": {"inputs": 2, "outputs": 1, "width": 60, "height": 50},
            "OR4": {"inputs": 4, "outputs": 1, "width": 60, "height": 50},
            "XOR2": {"inputs": 2, "outputs": 1, "width": 60, "height": 50},
            "XOR4": {"inputs": 4, "outputs": 1, "width": 60, "height": 50},
            "MUX_2x1": {"inputs": 2, "outputs": 1, "width": 60, "height": 60},
            "MUX_4x1": {"inputs": 4, "outputs": 1, "width": 60, "height": 90},
            "DEMUX_1x2": {"inputs": 1, "outputs": 2, "width": 60, "height": 60},
            "DEMUX_1x4": {"inputs": 1, "outputs": 4, "width": 60, "height": 90},
            "DFF": {"inputs": 2, "outputs": 1, "width": 60, "height": 60},
            "INV": {"inputs": 1, "outputs": 1, "width": 60, "height": 50},
            "CIRCLE": {"inputs": 0, "outputs": 0, "width": 80, "height": 80},
            "RECTANGLE": {"inputs": 0, "outputs": 0, "width": 120, "height": 80},
            "ROUNDED_RECT": {"inputs": 0, "outputs": 0, "width": 120, "height": 80},
            "CLOUD": {"inputs": 0, "outputs": 0, "width": 120, "height": 80},
        }

    def _content_bbox(self):
        all_ids = self.canvas.find_all()
        content_ids = [i for i in all_ids if "grid" not in self.canvas.gettags(i)]
        if not content_ids:
            return None
        x1 = y1 = float("inf")
        x2 = y2 = float("-inf")
        for cid in content_ids:
            b = self.canvas.bbox(cid)
            if b:
                x1 = min(x1, b[0])
                y1 = min(y1, b[1])
                x2 = max(x2, b[2])
                y2 = max(y2, b[3])
        if x1 == float("inf"):
            return None
        return (x1, y1, x2, y2)

    def save_diagram(self, path: Path):
        self.root.update()
        try:
            from PIL import Image, ImageDraw, ImageFont

            bbox = self._content_bbox()
            if not bbox:
                return
            margin = 30
            ox, oy = int(bbox[0] - margin), int(bbox[1] - margin)
            w = int(bbox[2] - bbox[0] + 2 * margin)
            h = int(bbox[3] - bbox[1] + 2 * margin)
            img = Image.new("RGB", (w, h), "white")
            draw = ImageDraw.Draw(img)

            def _color(c: str) -> str | None:
                if not c or c == "":
                    return None
                try:
                    r, g, b = self.canvas.winfo_rgb(c)
                except tk.TclError:
                    return c
                return f"#{r // 256:02x}{g // 256:02x}{b // 256:02x}"

            image_lookup = {
                node.image_id: node.image
                for node in self.nodes.values()
                if node.image_id and node.image
            }

            for item_id in self.canvas.find_all():
                tags = self.canvas.gettags(item_id)
                if "grid" in tags:
                    continue
                item_type = self.canvas.type(item_id)
                coords = self.canvas.coords(item_id)
                if not coords:
                    continue
                tc = []
                for i, c in enumerate(coords):
                    tc.append(c - (ox if i % 2 == 0 else oy))
                state = self.canvas.itemcget(item_id, "state")
                if state == "hidden":
                    continue
                if item_type == "rectangle":
                    fill = _color(self.canvas.itemcget(item_id, "fill"))
                    outline = _color(self.canvas.itemcget(item_id, "outline")) or "black"
                    lw = max(1, int(float(self.canvas.itemcget(item_id, "width") or 1)))
                    draw.rectangle([tc[0], tc[1], tc[2], tc[3]], fill=fill, outline=outline, width=lw)
                elif item_type == "line":
                    fill = _color(self.canvas.itemcget(item_id, "fill")) or "black"
                    lw = max(1, int(float(self.canvas.itemcget(item_id, "width") or 1)))
                    points = [(tc[i], tc[i + 1]) for i in range(0, len(tc), 2)]
                    if len(points) >= 2:
                        draw.line(points, fill=fill, width=lw)
                        arrow = self.canvas.itemcget(item_id, "arrow")
                        if arrow in ("last", "both") and len(points) >= 2:
                            ex, ey = points[-1]
                            px, py = points[-2]
                            self._draw_arrowhead(draw, px, py, ex, ey, fill, lw)
                elif item_type == "polygon":
                    fill = _color(self.canvas.itemcget(item_id, "fill"))
                    outline = _color(self.canvas.itemcget(item_id, "outline")) or "black"
                    lw = max(1, int(float(self.canvas.itemcget(item_id, "width") or 1)))
                    points = [(tc[i], tc[i + 1]) for i in range(0, len(tc), 2)]
                    if len(points) >= 3:
                        draw.polygon(points, fill=fill, outline=outline, width=lw)
                elif item_type == "oval":
                    fill = _color(self.canvas.itemcget(item_id, "fill"))
                    outline = _color(self.canvas.itemcget(item_id, "outline")) or "black"
                    draw.ellipse([tc[0], tc[1], tc[2], tc[3]], fill=fill, outline=outline)
                elif item_type == "text":
                    fill = _color(self.canvas.itemcget(item_id, "fill")) or "black"
                    text = self.canvas.itemcget(item_id, "text")
                    if text:
                        font_str = self.canvas.itemcget(item_id, "font")
                        pil_font = self._parse_tk_font(font_str)
                        anchor = self.canvas.itemcget(item_id, "anchor") or "center"
                        pil_anchor = {"s": "ms", "n": "mt", "center": "mm", "w": "lm", "e": "rm", "nw": "lt", "sw": "lb"}.get(anchor, "mm")
                        angle_str = self.canvas.itemcget(item_id, "angle") or "0"
                        try:
                            angle = float(angle_str)
                        except ValueError:
                            angle = 0.0
                        if angle:
                            bbox = draw.textbbox((0, 0), text, font=pil_font, anchor="lt")
                            text_w = max(1, bbox[2] - bbox[0])
                            text_h = max(1, bbox[3] - bbox[1])
                            text_img = Image.new("RGBA", (text_w, text_h), (255, 255, 255, 0))
                            text_draw = ImageDraw.Draw(text_img)
                            text_draw.text((0, 0), text, fill=fill, font=pil_font, anchor="lt")
                            rotated = text_img.rotate(-angle, expand=True)
                            rx = int(tc[0] - rotated.width / 2)
                            ry = int(tc[1] - rotated.height / 2)
                            img.paste(rotated, (rx, ry), rotated)
                        else:
                            draw.text((tc[0], tc[1]), text, fill=fill, font=pil_font, anchor=pil_anchor)
                elif item_type == "image":
                    photo = image_lookup.get(item_id)
                    if photo:
                        from PIL import ImageTk

                        pil_img = ImageTk.getimage(photo)
                        if pil_img.mode != "RGBA":
                            pil_img = pil_img.convert("RGBA")
                        px, py = int(tc[0]), int(tc[1])
                        img.paste(pil_img, (px, py), pil_img)
            img.save(path)
        except Exception as exc:
            print(f"PNG 저장 실패: {exc}")

    @staticmethod
    def _draw_arrowhead(draw, px, py, ex, ey, fill, lw):
        import math
        dx, dy = ex - px, ey - py
        length = math.hypot(dx, dy)
        if length < 1:
            return
        udx, udy = dx / length, dy / length
        size = max(8, lw * 3)
        bx, by = ex - udx * size, ey - udy * size
        nx, ny = -udy * size * 0.5, udx * size * 0.5
        p1 = (bx + nx, by + ny)
        p2 = (bx - nx, by - ny)
        draw.polygon([(ex, ey), p1, p2], fill=fill)

    @staticmethod
    def _parse_tk_font(font_str: str):
        from PIL import ImageFont
        parts = font_str.replace("{", "").replace("}", "").split()
        size = 12
        is_bold = any(part.lower() == "bold" for part in parts)
        for p in parts:
            try:
                s = int(p)
                if s > 0:
                    size = s
                    break
            except ValueError:
                continue
        if is_bold:
            try:
                return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
            except Exception:
                pass
            try:
                return ImageFont.truetype("arialbd.ttf", size)
            except Exception:
                pass
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            pass
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            pass
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

    def run(self):
        self.root.mainloop()


def _assign_port_offsets(ports: list[Port], side: str):
    total = len(ports)
    if total == 0:
        return
    for idx, port in enumerate(ports, start=1):
        port.side = side
        port.offset = idx / (total + 1)


def _parse_port_specs(
    specs: dict[str, dict[str, object]] | None,
    count: int,
    prefix: str,
    default_side: str,
) -> list[Port]:
    if specs:
        ports = []
        for name, spec in specs.items():
            side = str(spec.get("side") or default_side)
            offset = float(spec.get("offset", 0.5))
            manual_y = spec.get("manual_y")
            port = Port(name=name, kind=prefix, side=side, offset=offset)
            if manual_y is not None:
                port.manual_y = float(manual_y)
            ports.append(port)
        return ports
    ports = [Port(name=f"{prefix}{idx}", kind=prefix) for idx in range(1, count + 1)]
    _assign_port_offsets(ports, default_side)
    return ports


def _segment_direction_at_ratio(coords: list[float], ratio: float) -> str:
    """Determine segment direction (horizontal/vertical) at a given ratio along a polyline."""
    import math
    total_len = 0.0
    seg_lengths = []
    for i in range(0, len(coords) - 2, 2):
        x1, y1 = coords[i], coords[i + 1]
        x2, y2 = coords[i + 2], coords[i + 3]
        seg_lengths.append(math.hypot(x2 - x1, y2 - y1))
        total_len += seg_lengths[-1]
    if total_len == 0:
        return "horizontal"
    target = ratio * total_len
    cum = 0.0
    for i, seg_len in enumerate(seg_lengths):
        if cum + seg_len >= target or i == len(seg_lengths) - 1:
            x1, y1 = coords[i * 2], coords[i * 2 + 1]
            x2, y2 = coords[i * 2 + 2], coords[i * 2 + 3]
            if abs(y2 - y1) < abs(x2 - x1):
                return "horizontal"
            return "vertical"
        cum += seg_len
    return "horizontal"


def _create_junction_node_data(nodes: dict, px: float, py: float, port_side: str,
                               name: str | None = None) -> str:
    """Create a PORT junction node in the nodes dict and return its name."""
    if not name or name in nodes:
        idx = 1
        while f"Junction{idx}" in nodes:
            idx += 1
        name = f"Junction{idx}"
    size = 12
    half = size / 2
    if port_side == "top":
        nx, ny = int(px - half), int(py)
    elif port_side == "bottom":
        nx, ny = int(px - half), int(py - size)
    elif port_side == "left":
        nx, ny = int(px), int(py - half)
    else:
        nx, ny = int(px - size), int(py - half)
    max_level = max((n.level for n in nodes.values()), default=-1) + 1
    node = Node(
        name=name, kind="PORT", inputs=[], outputs=[],
        x=nx, y=ny, width=size, height=size, base_height=size,
        level=max_level, fill_color="white", outline_color="black",
        outline_enabled=True, outline_style="solid", outline_scale=1.0,
        label_font_size=1, label_font_family="Arial", label_font_weight="normal",
    )
    port = Port(name="p1", kind="io", side=port_side, offset=0.5)
    if port_side in ("left", "right"):
        port.manual_y = py
    node.inputs = [port]
    nodes[name] = node
    return name


def _parse_endpoint(value: object | None) -> tuple[str, str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        node_name, port_name = value.split(".", 1)
        return (node_name, port_name)
    if isinstance(value, dict):
        node_name = value.get("node")
        port_name = value.get("port")
        if node_name and port_name:
            return (str(node_name), str(port_name))
    raise ValueError(f"연결 포트를 파싱할 수 없습니다: {value}")


def _normalize_levels(nodes: dict[str, Node], order: list[str]):
    levels = [nodes[name].level for name in order if name in nodes]
    if len(set(levels)) != len(levels) or any(level is None for level in levels):
        for idx, name in enumerate(order):
            nodes[name].level = idx
        return
    ranked = sorted(order, key=lambda name: nodes[name].level)
    for idx, name in enumerate(ranked):
        nodes[name].level = idx


def parse_data(data: dict[str, object]) -> tuple[dict[str, Node], list[Connection]]:
    blocks = data.get("blocks", [])
    connections_data = data.get("connections", [])
    wires_data = data.get("wires", [])
    nodes: dict[str, Node] = {}
    order: list[str] = []

    for block in blocks:
        name = block.get("name")
        if not name:
            raise ValueError("블록 name이 필요합니다.")
        name = str(name)
        kind = str(block.get("kind", "BLOCK"))
        inputs_count = int(block.get("inputs", 0))
        outputs_count = int(block.get("outputs", 0))
        if kind != "BLOCK":
            gate_def = DiagramApp._gate_definitions_static().get(kind)
            if gate_def:
                inputs_count = inputs_count or gate_def["inputs"]
                outputs_count = outputs_count or gate_def["outputs"]
        ports_info = block.get("ports")
        ports_info = ports_info if isinstance(ports_info, dict) else {}
        if ports_info:
            ports = _parse_port_specs(ports_info, 0, "io", "left")
        else:
            ports = _parse_port_specs(None, inputs_count, "in", "left")
            ports.extend(_parse_port_specs(None, outputs_count, "out", "right"))
        x = int(block.get("x", 80))
        y = int(block.get("y", 80))
        width = int(block.get("width", 160))
        height = int(block.get("height", max(100, 40 + 20 * max(inputs_count, outputs_count, 1))))
        level = block.get("level")
        fill_raw = block.get("fill_color", block.get("color", "#e0e0e0"))
        outline_raw = block.get("outline_color", block.get("color", "GRAY"))
        fill_color = DiagramApp._color_to_hex(str(fill_raw))
        outline_color = DiagramApp._color_to_hex(str(outline_raw))
        outline_enabled = bool(block.get("outline_enabled", True))
        outline_scale = float(block.get("outline_thickness", 1.0))
        outline_style = str(block.get("outline_style", "solid"))
        font_size = int(block.get("font_size", 12))
        font_family = str(block.get("font_family", "Arial"))
        font_weight = str(block.get("font_weight", "bold"))
        rotation = int(block.get("rotation", 0) or 0)
        label_h_align = str(block.get("label_h_align", "left"))
        label_v_align = str(block.get("label_v_align", "top"))
        node = Node(
            name=name,
            kind=kind,
            inputs=ports,
            outputs=[],
            x=x,
            y=y,
            width=width,
            height=height,
            base_height=height,
            outline_color=outline_color,
            fill_color=fill_color,
            outline_enabled=outline_enabled,
            outline_style=outline_style,
            outline_scale=outline_scale,
            label_font_size=font_size,
            label_font_family=font_family,
            label_font_weight=font_weight,
            label_h_align=label_h_align,
            label_v_align=label_v_align,
            level=int(level) if level is not None else 0,
            rotation=rotation,
        )
        if node.kind != "BLOCK":
            node.image_subsample = 0
            snap = lambda value: int(round(value / DiagramApp.GRID_STEP) * DiagramApp.GRID_STEP)
            node.x = snap(node.x)
            node.y = snap(node.y)
            for port in node.inputs + node.outputs:
                if port.side != "right":
                    continue
                y = node.y + port.offset * node.height
                port.manual_y = snap(y)
        nodes[name] = node
        order.append(name)

    _normalize_levels(nodes, order)

    connections: list[Connection] = []
    for entry in connections_data:
        src = _parse_endpoint(entry.get("src"))
        dst = _parse_endpoint(entry.get("dst"))
        label = entry.get("label")
        connection = Connection(
            src=src,
            dst=dst,
            label=str(label) if label is not None else None,
            manual_mid_x=entry.get("manual_mid_x"),
            manual_mid_y=entry.get("manual_mid_y"),
        )
        if "line_color" in entry and entry["line_color"] is not None:
            connection.line_color = DiagramApp._color_to_hex(str(entry["line_color"]))
        if "line_thickness" in entry and entry["line_thickness"] is not None:
            connection.line_thickness = float(entry["line_thickness"])
        if not src and not dst:
            points = entry.get("points")
            if points:
                connection.free_points = [(float(px), float(py)) for px, py in points]
            if "show_arrow" in entry:
                connection.show_arrow = bool(entry["show_arrow"])
            if "label_x" in entry and entry["label_x"] is not None:
                connection.label_x = float(entry["label_x"])
            if "label_y" in entry and entry["label_y"] is not None:
                connection.label_y = float(entry["label_y"])
            if "label_font_family" in entry:
                connection.label_font_family = str(entry["label_font_family"])
            if "label_font_size" in entry:
                connection.label_font_size = int(entry["label_font_size"])
            if "label_font_weight" in entry:
                connection.label_font_weight = str(entry["label_font_weight"])
            if "label_angle" in entry and entry["label_angle"] is not None:
                connection.label_angle = int(entry["label_angle"])
            # New WIRE_BAR format: ports with ratio (and optional name)
            if "ports" in entry and entry.get("kind") == "WIRE_BAR":
                # Create PORT nodes from ratios using free_points
                if connection.free_points:
                    coords = [c for pt in connection.free_points for c in pt]
                    for p in entry["ports"]:
                        ratio = float(p["ratio"])
                        pname = p.get("name")
                        px, py = DiagramApp._point_from_ratio_on_polyline(coords, ratio)
                        seg_dir = _segment_direction_at_ratio(coords, ratio)
                        port_side = "top" if seg_dir == "horizontal" else "left"
                        jname = _create_junction_node_data(nodes, px, py, port_side, name=pname)
                        connection.junction_ports.append({"node": jname, "ratio": ratio})
            # Legacy format: junction_ports with node references
            elif "junction_ports" in entry:
                connection.junction_ports = [
                    {"node": str(jp["node"]), "ratio": float(jp["ratio"])}
                    for jp in entry["junction_ports"]
                ]
        connections.append(connection)

    if wires_data:
        for wire in wires_data:
            src = _parse_endpoint(wire.get("src"))
            dst = _parse_endpoint(wire.get("dst"))
            for connection in connections:
                if connection.src == src and connection.dst == dst:
                    if "manual_mid_x" in wire:
                        connection.manual_mid_x = wire.get("manual_mid_x")
                    if "manual_mid_y" in wire:
                        connection.manual_mid_y = wire.get("manual_mid_y")
                    if "label" in wire and wire.get("label") is not None:
                        connection.label = str(wire.get("label"))
                    waypoints = wire.get("waypoints")
                    if waypoints:
                        connection.waypoints = [(float(wp[0]), float(wp[1])) for wp in waypoints]
                    if "line_color" in wire and wire["line_color"] is not None:
                        connection.line_color = DiagramApp._color_to_hex(str(wire["line_color"]))
                    if "line_thickness" in wire and wire["line_thickness"] is not None:
                        connection.line_thickness = float(wire["line_thickness"])
                    if "label_font_family" in wire:
                        connection.label_font_family = str(wire["label_font_family"])
                    if "label_font_size" in wire:
                        connection.label_font_size = int(wire["label_font_size"])
                    if "label_font_weight" in wire:
                        connection.label_font_weight = str(wire["label_font_weight"])
                    if "label_angle" in wire and wire["label_angle"] is not None:
                        connection.label_angle = int(wire["label_angle"])
                    if "label_x" in wire and wire["label_x"] is not None:
                        connection.label_x = float(wire["label_x"])
                    if "label_y" in wire and wire["label_y"] is not None:
                        connection.label_y = float(wire["label_y"])
                    if "show_arrow" in wire:
                        connection.show_arrow = bool(wire["show_arrow"])
                    # New format: ports with ratio (and optional name)
                    if "ports" in wire:
                        connection.pending_wire_ports = [
                            {"ratio": float(p["ratio"]), "name": p.get("name")}
                            for p in wire["ports"]
                        ]
                    # Legacy format: junction_ports with node references
                    elif "junction_ports" in wire:
                        connection.junction_ports = [
                            {"node": str(jp["node"]), "ratio": float(jp["ratio"])}
                            for jp in wire["junction_ports"]
                        ]
                    break

    return nodes, connections


def parse_json(path: Path) -> tuple[dict[str, Node], list[Connection]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_data(data)


def validate_connections(nodes: dict[str, Node], connections: list[Connection], log_path: Path) -> bool:
    used_ports: set[tuple[str, str]] = set()
    for connection in connections:
        if connection.src:
            used_ports.add(connection.src)
        if connection.dst:
            used_ports.add(connection.dst)

    errors: list[str] = []
    for node in nodes.values():
        for port in node.inputs + node.outputs:
            if (node.name, port.name) not in used_ports:
                errors.append(f"[WARN] 포트 미연결: {node.name}.{port.name}")
                port.connected = False

    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
        print(f"미연결 포트가 있습니다. {log_path}를 확인하세요.")
        return True
    if log_path.exists():
        log_path.unlink()
    return True


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("input.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("diagram.png")
    if not input_path.exists():
        print("input.json 파일이 없습니다.")
        sys.exit(1)
    nodes, connections = parse_json(input_path)
    validate_connections(nodes, connections, Path("error.log"))
    app = DiagramApp(nodes, connections, input_path, output_path)
    app.run()


if __name__ == "__main__":
    main()
