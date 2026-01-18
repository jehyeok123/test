import json
import sys
import tkinter as tk
from tkinter import simpledialog
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
    level: int = 0
    image: tk.PhotoImage | None = None
    image_id: int | None = None


@dataclass
class Connection:
    src: tuple[str, str] | None
    dst: tuple[str, str] | None
    line_id: int | None = None
    manual_mid_x: float | None = None
    manual_mid_y: float | None = None
    label: str | None = None
    label_id: int | None = None


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
        self.toolbar = tk.Frame(self.root)
        self.toolbar.pack(fill=tk.X)
        self.new_button = tk.Button(self.toolbar, text="NEW", command=self._open_new_block)
        self.new_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.edit_button = tk.Button(self.toolbar, text="EDIT", command=self._open_edit_block)
        self.edit_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.save_button = tk.Button(self.toolbar, text="JSON SAVE", command=self._save_json)
        self.save_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.connect_button = tk.Button(self.toolbar, text="CONNECT", command=self._toggle_connect_mode)
        self.connect_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.disconnect_button = tk.Button(self.toolbar, text="DISCONNECT", command=self._toggle_disconnect_mode)
        self.disconnect_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.create_port_button = tk.Button(self.toolbar, text="CREATE PORT", command=self._toggle_create_port_mode)
        self.create_port_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.delete_port_button = tk.Button(self.toolbar, text="DELETE PORT", command=self._toggle_delete_port_mode)
        self.delete_port_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.port_toggle_button = tk.Button(self.toolbar, text="SHOW/HIDE PORT", command=self._toggle_ports)
        self.port_toggle_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.wire_name_button = tk.Button(self.toolbar, text="WIRE NAME", command=self._toggle_wire_name_mode)
        self.wire_name_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.bring_front_button = tk.Button(self.toolbar, text="BRING FRONT", command=self._bring_active_front)
        self.bring_front_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.send_back_button = tk.Button(self.toolbar, text="SEND BACK", command=self._send_active_back)
        self.send_back_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.zoom_in_button = tk.Button(self.toolbar, text="ZOOM IN", command=self._zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.zoom_out_button = tk.Button(self.toolbar, text="ZOOM OUT", command=self._zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.canvas = tk.Canvas(self.root, width=1200, height=800, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._drag_data = {"node": None, "x": 0, "y": 0}
        self._drag_wire = {"connection": None, "offset": 0.0, "mode": None, "port": None, "node": None}
        self._resize_data = {"node": None, "mode": None, "x": 0, "y": 0, "orig": None}
        self._mode = "normal"
        self._show_ports = True
        self._port_items: dict[int, tuple[str, str]] = {}
        self._selected_ports: list[tuple[str, str]] = []
        self._active_node_name: str | None = None
        self._gate_images: dict[str, tk.PhotoImage] = {}
        self._zoom_scale = 1.0
        self._outline_backup: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self):
        for node in self.nodes.values():
            self._draw_node(node)
        for connection in self.connections:
            self._draw_connection(connection)
        self.canvas.tag_bind("node", "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind("node", "<ButtonRelease-1>", self._on_release)
        self.canvas.tag_bind("node", "<B1-Motion>", self._on_motion)
        self.canvas.tag_bind("node", "<Double-Button-1>", self._on_toggle_resize)
        self.canvas.tag_bind("port", "<ButtonPress-1>", self._on_port_press)
        self.canvas.tag_bind("wire", "<ButtonPress-1>", self._on_wire_press)
        self.canvas.tag_bind("wire", "<B1-Motion>", self._on_wire_motion)
        self.canvas.tag_bind("wire", "<ButtonRelease-1>", self._on_wire_release)
        self.root.bind("s", lambda _event: self.save_diagram(self.output_path))
        self.root.after(300, lambda: self.save_diagram(self.output_path))

    def _draw_node(self, node: Node):
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        if node.kind != "BLOCK":
            image = self._load_gate_image(node.kind)
            if image:
                node.image = image
                node.width = image.width()
                node.height = image.height()
                node.base_height = node.height
                x2, y2 = node.x + node.width, node.y + node.height
                node.image_id = self.canvas.create_image(x1, y1, image=image, anchor="nw")
                node.items.append(node.image_id)
            else:
                node.items.extend(self._draw_gate_shape(node, x1, y1, x2, y2))
        else:
            base_width = 4 if node.resize_enabled else 2
            outline_width = max(1, base_width * node.outline_scale)
            dash = (4, 2) if node.outline_style == "dashed" else None
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
        if node.kind == "BLOCK":
            label = self.canvas.create_text(
                x1 + 6,
                y1 + 6,
                text=node.name,
                font=(node.label_font_family, node.label_font_size, node.label_font_weight),
                anchor="nw",
            )
            node.items.append(label)

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
            return
        line = self.canvas.create_line(
            *coords,
            smooth=False,
            arrow=tk.LAST,
            width=2,
            fill="#333333",
        )
        self.canvas.addtag_withtag("wire", line)
        connection.line_id = line
        if connection.label:
            label_x, label_y = self._label_position(coords)
            label_id = self.canvas.create_text(
                label_x,
                label_y,
                text=connection.label,
                font=("Arial", 12),
                anchor="s",
            )
            connection.label_id = label_id

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

    def _on_press(self, event):
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
        self._active_node_name = node.name
        self._apply_z_order(active_node_name=node.name)
        if node.resize_enabled:
            resize_mode = self._hit_test_edge(node, event.x, event.y)
            if resize_mode:
                self._resize_data["node"] = node
                self._resize_data["mode"] = resize_mode
                self._resize_data["x"] = event.x
                self._resize_data["y"] = event.y
                self._resize_data["orig"] = (node.x, node.y, node.width, node.height)
                self.canvas.bind("<B1-Motion>", self._on_resize_motion)
                self.canvas.bind("<ButtonRelease-1>", self._on_resize_release)
            return
        resize_mode = self._hit_test_edge(node, event.x, event.y)
        if resize_mode:
            self._resize_data["node"] = node
            self._resize_data["mode"] = resize_mode
            self._resize_data["x"] = event.x
            self._resize_data["y"] = event.y
            self._resize_data["orig"] = (node.x, node.y, node.width, node.height)
            return
        self._drag_data["node"] = node
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_release(self, _event):
        self._drag_data["node"] = None
        self._resize_data["node"] = None
        self._resize_data["mode"] = None
        self._resize_data["orig"] = None

    def _on_motion(self, event):
        if self._mode != "normal":
            return
        if self._resize_data["node"] is not None:
            self._on_resize_motion(event)
            return
        node = self._drag_data["node"]
        if not node:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        target_x = node.x + dx
        target_y = node.y + dy
        snapped_x = self._snap_value(target_x)
        snapped_y = self._snap_value(target_y)
        dx = snapped_x - node.x
        dy = snapped_y - node.y
        if dx == 0 and dy == 0:
            return
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.canvas.move(f"node:{node.name}", dx, dy)
        node.x += dx
        node.y += dy
        self._update_connections()

    def _hit_test_edge(self, node: Node, x: float, y: float, threshold: float = 6.0) -> str | None:
        if node.kind != "BLOCK" or not node.resize_enabled:
            return None
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

    def _on_toggle_resize(self, event):
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
        self._active_node_name = node.name
        if node.kind != "BLOCK":
            return
        node.resize_enabled = not node.resize_enabled
        self._redraw_node(node)
        self._update_connections()

    def _on_resize_motion(self, event):
        node = self._resize_data["node"]
        mode = self._resize_data["mode"]
        orig = self._resize_data["orig"]
        if not node or not mode or not orig:
            return
        orig_x, orig_y, orig_width, orig_height = orig
        dx = event.x - self._resize_data["x"]
        dy = event.y - self._resize_data["y"]
        min_width = 80
        min_height = 60
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
            for port, prev in old_port_positions:
                port.manual_y = prev[1]
        elif mode == "bottom":
            node.height = self._snap_value(max(min_height, orig_height + dy), min_height)
        self._redraw_node(node)
        self._update_connections()

    def _on_resize_release(self, _event):
        self._resize_data["node"] = None
        self._resize_data["mode"] = None
        self._resize_data["orig"] = None
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
        for node in nodes:
            self.canvas.tag_raise(f"node:{node.name}")
        for connection in self.connections:
            self._raise_connection(connection)

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
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        if port.side == "left":
            py = port.manual_y if port.manual_y is not None else y1 + port.offset * (y2 - y1)
            return (x1, py)
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

    @staticmethod
    def _connection_coords_orthogonal(
        start: tuple[float, float],
        end: tuple[float, float],
        prefer_vertical_end: bool,
    ) -> list[float]:
        x1, y1 = start
        x2, y2 = end
        if prefer_vertical_end:
            return [x1, y1, x2, y1, x2, y2]
        return [x1, y1, x1, y2, x2, y2]

    def _connection_orientation(self, connection: Connection) -> str | None:
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
        return self._connection_orientation(connection) == "orthogonal"

    def _connection_line_coords(self, connection: Connection) -> list[float] | None:
        if connection.src and connection.dst:
            src_node, src_port = connection.src
            dst_node, dst_port = connection.dst
            src_port_id = self._get_port_canvas_id(src_node, src_port, "out")
            dst_port_id = self._get_port_canvas_id(dst_node, dst_port, "in")
            if not src_port_id or not dst_port_id:
                return None
            x1, y1 = self._port_center(src_port_id)
            x2, y2 = self._port_center(dst_port_id)
            orientation = self._connection_orientation(connection)
            if orientation == "horizontal":
                return self._connection_coords_horizontal((x1, y1), (x2, y2), connection.manual_mid_x)
            if orientation == "vertical":
                return self._connection_coords_vertical((x1, y1), (x2, y2), connection.manual_mid_y)
            if orientation == "orthogonal":
                dst_side = self._port_side((dst_node, dst_port))
                prefer_vertical_end = dst_side in ("top", "bottom") if dst_side else False
                return self._connection_coords_orthogonal((x1, y1), (x2, y2), prefer_vertical_end)
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
        label_x, label_y = self._label_position(coords)
        self.canvas.coords(connection.label_id, label_x, label_y)

    def _find_port(self, node_name: str, port_name: str, kind: str | None = None) -> tuple[Node, Port] | None:
        node = self.nodes.get(node_name)
        if not node:
            return None
        for port in node.inputs + node.outputs:
            if port.name == port_name:
                return node, port
        return None

    def _on_wire_press(self, event):
        if self._mode == "wire_name":
            item = self.canvas.find_withtag("current")
            if not item:
                return
            line_id = item[0]
            connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
            if not connection:
                return
            label = simpledialog.askstring("WIRE NAME", "Wire name:")
            if label is not None:
                connection.label = label
                if connection.label_id is None:
                    coords = self._connection_line_coords(connection)
                    if coords:
                        label_x, label_y = self._label_position(coords)
                        connection.label_id = self.canvas.create_text(
                            label_x,
                            label_y,
                            text=label,
                            font=("Arial", 12),
                            anchor="s",
                        )
                else:
                    self.canvas.itemconfig(connection.label_id, text=label)
                if connection.label_id:
                    coords = self._connection_line_coords(connection)
                    if coords:
                        self._update_label(connection, coords)
            self._toggle_wire_name_mode()
            return
        if self._mode == "disconnect":
            item = self.canvas.find_withtag("current")
            if not item:
                return
            line_id = item[0]
            connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
            if not connection:
                return
            self._remove_connection(connection)
            self._toggle_disconnect_mode()
            return
        if self._mode != "normal":
            return
        item = self.canvas.find_withtag("current")
        if not item:
            return
        line_id = item[0]
        connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
        if not connection:
            return
        coords = self._connection_line_coords(connection)
        if not coords:
            return
        if len(coords) == 4:
            if not self._near_horizontal_segment(event.x, event.y, coords[0], coords[2], coords[1]):
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
        orientation = self._connection_orientation(connection)
        if orientation == "orthogonal":
            if not connection.src or not connection.dst:
                return
            src_node, src_port = connection.src
            dst_node, dst_port = connection.dst
            src_side = self._port_side((src_node, src_port))
            dst_side = self._port_side((dst_node, dst_port))
            if not src_side or not dst_side:
                return
            if src_side in ("left", "right"):
                lr_target = self._find_port(src_node, src_port)
                tb_target = self._find_port(dst_node, dst_port)
            else:
                lr_target = self._find_port(dst_node, dst_port)
                tb_target = self._find_port(src_node, src_port)
            if not lr_target or not tb_target:
                return
            h_x1, h_x2, h_y, v_x, v_y1, v_y2 = self._orthogonal_segments(coords)
            if self._near_horizontal_segment(event.x, event.y, h_x1, h_x2, h_y):
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "orth_move_lr"
                self._drag_wire["node"], self._drag_wire["port"] = lr_target
                return
            if self._near_vertical_segment(event.x, event.y, v_x, v_y1, v_y2):
                self._drag_wire["connection"] = connection
                self._drag_wire["mode"] = "orth_move_tb"
                self._drag_wire["node"], self._drag_wire["port"] = tb_target
                return
            return
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
        connection: Connection | None = self._drag_wire["connection"]
        if not connection:
            return
        mode = self._drag_wire["mode"]
        if mode == "mid":
            if self._connection_manual_locked(connection):
                return
            raw_mid = event.x - self._drag_wire["offset"]
            connection.manual_mid_x = self._snap_to_step(raw_mid, self.MID_STEP)
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
            return
        if mode == "mid_y":
            if self._connection_manual_locked(connection):
                return
            raw_mid = event.y - self._drag_wire["offset"]
            connection.manual_mid_y = self._snap_to_step(raw_mid, self.MID_STEP)
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
            return
        if mode in ("orth_move_lr", "orth_move_tb"):
            if self._mode != "normal":
                return
            node = self._drag_wire["node"]
            port = self._drag_wire["port"]
            if not node or not port:
                return
            self._move_port(node, port, event.x, event.y)
            return
        if mode in ("src_port", "dst_port"):
            if self._mode != "normal":
                return
            node = self._drag_wire["node"]
            port = self._drag_wire["port"]
            if not node or not port:
                return
            self._move_port(node, port, event.x, event.y)
            return

    def _on_wire_release(self, _event):
        self._drag_wire["connection"] = None
        self._drag_wire["mode"] = None
        self._drag_wire["port"] = None
        self._drag_wire["node"] = None

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
        if node.kind != "BLOCK":
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

    def _on_port_press(self, event):
        if self._mode == "delete_port":
            self._handle_delete_port_click(event)
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
            self.connections.append(connection)
            self._draw_connection(connection)
            self._reset_connect_mode()
            return

    def _open_new_block(self):
        self._open_block_dialog(mode="create")

    def _open_edit_block(self):
        if not self._active_node_name:
            return
        node = self.nodes.get(self._active_node_name)
        if not node or node.kind != "BLOCK":
            return
        self._open_block_dialog(mode="edit", node=node)

    def _open_block_dialog(self, mode: str, node: Node | None = None):
        window = tk.Toplevel(self.root)
        window.title("Edit" if mode == "edit" else "New")
        mode_var = tk.StringVar(value="block")
        if mode == "create":
            tk.Radiobutton(window, text="Block", variable=mode_var, value="block").grid(
                row=0, column=0, padx=6, pady=6, sticky="w"
            )
            tk.Radiobutton(window, text="Gate", variable=mode_var, value="gate").grid(
                row=0, column=1, padx=6, pady=6, sticky="w"
            )

        block_frame = tk.Frame(window)
        block_frame.grid(row=1, column=0, columnspan=2, sticky="w")
        gate_frame = tk.Frame(window)
        gate_frame.grid(row=1, column=0, columnspan=2, sticky="w")

        tk.Label(block_frame, text="Name").grid(row=0, column=0, padx=6, pady=6, sticky="nw")
        name_entry = tk.Text(block_frame, height=5, width=24)
        name_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        tk.Label(block_frame, text="Font Size").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        font_size_var = tk.IntVar(value=12)
        font_size_spin = tk.Spinbox(block_frame, from_=6, to=72, textvariable=font_size_var, width=6)
        font_size_spin.grid(row=1, column=1, padx=6, pady=6, sticky="w")
        tk.Label(block_frame, text="Font").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        font_family_var = tk.StringVar(value="Arial")
        font_menu = tk.OptionMenu(block_frame, font_family_var, "Arial", "Malgun Gothic")
        font_menu.grid(row=2, column=1, padx=6, pady=6, sticky="w")
        bold_var = tk.BooleanVar(value=True)
        bold_check = tk.Checkbutton(block_frame, text="Bold", variable=bold_var)
        bold_check.grid(row=3, column=1, padx=6, pady=6, sticky="w")
        color_options = list(self.COLOR_NAME_TO_HEX.keys())
        fill_var = tk.StringVar(value="GRAY")
        tk.Label(block_frame, text="Fill Color").grid(row=4, column=0, padx=6, pady=6, sticky="w")
        fill_menu = tk.OptionMenu(block_frame, fill_var, *color_options)
        fill_menu.grid(row=4, column=1, padx=6, pady=6, sticky="w")

        outline_enabled_var = tk.BooleanVar(value=True)
        tk.Label(block_frame, text="Outline").grid(row=5, column=0, padx=6, pady=6, sticky="w")
        outline_check = tk.Checkbutton(block_frame, variable=outline_enabled_var)
        outline_check.grid(row=5, column=1, padx=6, pady=6, sticky="w")
        tk.Label(block_frame, text="Outline Color").grid(row=6, column=0, padx=6, pady=6, sticky="w")
        outline_var = tk.StringVar(value="GRAY")
        outline_menu = tk.OptionMenu(block_frame, outline_var, *color_options)
        outline_menu.grid(row=6, column=1, padx=6, pady=6, sticky="w")
        tk.Label(block_frame, text="Outline Thickness").grid(row=7, column=0, padx=6, pady=6, sticky="w")
        outline_thickness_var = tk.StringVar(value="Normal")
        outline_thickness_menu = tk.OptionMenu(block_frame, outline_thickness_var, "Thin", "Normal", "Thick")
        outline_thickness_menu.grid(row=7, column=1, padx=6, pady=6, sticky="w")
        tk.Label(block_frame, text="Outline Style").grid(row=8, column=0, padx=6, pady=6, sticky="w")
        outline_style_var = tk.StringVar(value="Solid")
        outline_style_menu = tk.OptionMenu(block_frame, outline_style_var, "Solid", "Dashed")
        outline_style_menu.grid(row=8, column=1, padx=6, pady=6, sticky="w")

        tk.Label(gate_frame, text="Gate Type").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        gate_var = tk.StringVar(value="AND2")
        gate_menu = tk.OptionMenu(gate_frame, gate_var, *self._gate_types())
        gate_menu.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        def _toggle_outline_fields(*_args):
            state = "normal" if outline_enabled_var.get() else "disabled"
            outline_menu.configure(state=state)
            outline_thickness_menu.configure(state=state)
            outline_style_menu.configure(state=state)

        def _toggle_fields(*_args):
            is_gate = mode_var.get() == "gate"
            if is_gate:
                block_frame.grid_remove()
                gate_frame.grid()
            else:
                gate_frame.grid_remove()
                block_frame.grid()

        if mode == "create":
            mode_var.trace_add("write", _toggle_fields)
            _toggle_fields()
        else:
            gate_frame.grid_remove()

        outline_enabled_var.trace_add("write", _toggle_outline_fields)
        _toggle_outline_fields()

        def _unique_gate_name(kind: str) -> str:
            index = 1
            while True:
                candidate = f"{kind}{index}"
                if candidate not in self.nodes:
                    return candidate
                index += 1

        if node:
            name_entry.insert("1.0", node.name)
            font_size_var.set(node.label_font_size)
            font_family_var.set(node.label_font_family)
            bold_var.set(node.label_font_weight == "bold")
            fill_var.set(self._color_to_name(node.fill_color))
            outline_var.set(self._color_to_name(node.outline_color))
            outline_enabled_var.set(node.outline_enabled)
            thickness_map = {0.5: "Thin", 1.0: "Normal", 2.0: "Thick"}
            outline_thickness_var.set(thickness_map.get(node.outline_scale, "Normal"))
            outline_style_var.set("Dashed" if node.outline_style == "dashed" else "Solid")

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
            self._redraw_node(target)

        def _create_or_edit():
            if mode == "create" and mode_var.get() == "gate":
                gate_kind = gate_var.get()
                name = _unique_gate_name(gate_kind)
                gate_def = self._gate_definitions()[gate_kind]
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
                self.nodes[name] = new_node
                self._draw_node(new_node)
                self._apply_z_order(active_node_name=new_node.name)
                window.destroy()
                return

            new_name = name_entry.get("1.0", "end-1c").strip()
            if not new_name:
                return
            if mode == "create":
                if new_name in self.nodes:
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
                window.destroy()
                return
            if node and new_name != node.name and new_name in self.nodes:
                return
            if node:
                old_name = node.name
                _apply_block_changes(node, new_name)
                if new_name != old_name:
                    self._rename_node(old_name, new_name)
                self._apply_z_order(active_node_name=node.name)
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
        if self._mode == "disconnect":
            self._toggle_disconnect_mode()
        if self._mode in ("create_port", "delete_port", "wire_name"):
            self._reset_port_mode()
        self._mode = "connect"
        self._selected_ports = []
        self._set_all_port_colors("yellow")

    def _reset_connect_mode(self):
        self._selected_ports = []
        self._set_all_port_colors("black")
        self._mode = "normal"

    def _toggle_disconnect_mode(self):
        if self._mode == "disconnect":
            self._set_all_wire_colors("#333333")
            self._mode = "normal"
            return
        if self._mode == "connect":
            self._reset_connect_mode()
        if self._mode in ("create_port", "delete_port", "wire_name"):
            self._reset_port_mode()
        self._mode = "disconnect"
        self._set_all_wire_colors("red")

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

    def _remove_connection(self, connection: Connection):
        if connection.line_id:
            self.canvas.delete(connection.line_id)
        if connection.label_id:
            self.canvas.delete(connection.label_id)
        self.connections = [conn for conn in self.connections if conn is not connection]

    def _remove_port(self, node: Node, port: Port):
        if port.canvas_id:
            self.canvas.delete(port.canvas_id)
            self._port_items.pop(port.canvas_id, None)
        node.inputs = [p for p in node.inputs if p is not port]
        node.outputs = [p for p in node.outputs if p is not port]
        to_remove = [conn for conn in self.connections if conn.src == (node.name, port.name) or conn.dst == (node.name, port.name)]
        for conn in to_remove:
            self._remove_connection(conn)
        self._update_connections()

    def _toggle_ports(self):
        self._show_ports = not self._show_ports
        for node in self.nodes.values():
            for port in node.inputs + node.outputs:
                self._set_port_color(port, port.color)

    def _toggle_create_port_mode(self):
        if self._mode == "create_port":
            self._reset_port_mode()
            return
        if not self._active_node_name:
            return
        if self._mode in ("connect", "disconnect", "delete_port", "wire_name"):
            self._reset_port_mode()
        self._mode = "create_port"
        node = self.nodes.get(self._active_node_name)
        if node and node.kind == "BLOCK":
            self._outline_backup.setdefault(node.name, node.outline_color)
            node.outline_color = "green"
            node.resize_enabled = True
            self._redraw_node(node)
        else:
            self._mode = "normal"

    def _toggle_delete_port_mode(self):
        if self._mode == "delete_port":
            self._reset_port_mode()
            return
        if not self._active_node_name:
            return
        if self._mode in ("connect", "disconnect", "create_port", "wire_name"):
            self._reset_port_mode()
        self._mode = "delete_port"
        node = self.nodes.get(self._active_node_name)
        if node and node.kind == "BLOCK":
            self._outline_backup.setdefault(node.name, node.outline_color)
            node.resize_enabled = True
            for port in node.inputs + node.outputs:
                self._set_port_color(port, "red")
        else:
            self._mode = "normal"

    def _toggle_wire_name_mode(self):
        if self._mode == "wire_name":
            self._set_all_wire_colors("#333333")
            self._mode = "normal"
            return
        if self._mode in ("connect", "disconnect", "create_port", "delete_port"):
            self._reset_port_mode()
        self._mode = "wire_name"
        self._set_all_wire_colors("blue")

    def _reset_port_mode(self):
        if self._mode == "connect":
            self._reset_connect_mode()
        if self._mode == "disconnect":
            self._set_all_wire_colors("#333333")
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
        if self._mode == "wire_name":
            self._set_all_wire_colors("#333333")
        self._mode = "normal"

    def _handle_create_port_click(self, event):
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

    def _send_active_back(self):
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

    def _apply_zoom(self, factor: float):
        if factor == 1.0:
            return
        self._zoom_scale *= factor
        for node in self.nodes.values():
            node.x *= factor
            node.y *= factor
            node.width *= factor
            node.height *= factor
            node.base_height *= factor
            for port in node.inputs + node.outputs:
                if port.manual_y is not None:
                    port.manual_y *= factor
        for connection in self.connections:
            if connection.manual_mid_x is not None:
                connection.manual_mid_x *= factor
            if connection.manual_mid_y is not None:
                connection.manual_mid_y *= factor
        for node in self.nodes.values():
            self._redraw_node(node)
        self._update_connections()

    def _zoom_in(self):
        self._apply_zoom(1.1)

    def _zoom_out(self):
        self._apply_zoom(0.9)

    def _save_json(self):
        def _unscale(value: float | None) -> float | None:
            if value is None:
                return None
            return round(value / self._zoom_scale, 2)

        blocks = []
        for node in self.nodes.values():
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
            }
        )
        blocks.sort(key=lambda block: block["level"])
        connections = []
        wires = []
        for connection in self.connections:
            connections.append(
                {
                    "src": f"{connection.src[0]}.{connection.src[1]}" if connection.src else None,
                    "dst": f"{connection.dst[0]}.{connection.dst[1]}" if connection.dst else None,
                    "label": connection.label,
                }
            )
            wires.append(
                {
                    "src": f"{connection.src[0]}.{connection.src[1]}" if connection.src else None,
                    "dst": f"{connection.dst[0]}.{connection.dst[1]}" if connection.dst else None,
                    "manual_mid_x": _unscale(connection.manual_mid_x),
                    "manual_mid_y": _unscale(connection.manual_mid_y),
                }
            )
        payload = {"blocks": blocks, "connections": connections, "wires": wires}
        self.input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _gate_types(self) -> list[str]:
        return list(self._gate_definitions().keys())

    def _gate_definitions(self) -> dict[str, dict[str, int]]:
        return self._gate_definitions_static()

    def _load_gate_image(self, gate_kind: str) -> tk.PhotoImage | None:
        if gate_kind in self._gate_images:
            return self._gate_images[gate_kind]
        image_path = Path(__file__).resolve().parent / "gate_image" / f"{gate_kind}.png"
        if not image_path.exists():
            return None
        image = tk.PhotoImage(file=str(image_path))
        image = image.subsample(10, 10)
        self._gate_images[gate_kind] = image
        return image

    @staticmethod
    def _gate_definitions_static() -> dict[str, dict[str, int]]:
        return {
            "AND2": {"inputs": 2, "outputs": 1, "width": 60, "height": 40},
            "AND4": {"inputs": 4, "outputs": 1, "width": 60, "height": 40},
            "OR2": {"inputs": 2, "outputs": 1, "width": 60, "height": 40},
            "OR4": {"inputs": 4, "outputs": 1, "width": 60, "height": 40},
            "XOR2": {"inputs": 2, "outputs": 1, "width": 60, "height": 40},
            "XOR4": {"inputs": 4, "outputs": 1, "width": 60, "height": 40},
            "MUX_2x1": {"inputs": 2, "outputs": 1, "width": 60, "height": 40},
            "MUX_4x1": {"inputs": 4, "outputs": 1, "width": 60, "height": 40},
            "DEMUX_1x2": {"inputs": 1, "outputs": 2, "width": 60, "height": 40},
            "DEMUX_1x4": {"inputs": 1, "outputs": 4, "width": 60, "height": 40},
            "DFF": {"inputs": 2, "outputs": 1, "width": 60, "height": 40},
            "INV": {"inputs": 1, "outputs": 1, "width": 60, "height": 40},
        }

    def _draw_gate_shape(self, node: Node, x1: float, y1: float, x2: float, y2: float) -> list[int]:
        kind = node.kind
        items: list[int] = []
        outline = node.outline_color
        fill = node.fill_color
        if kind.startswith("AND"):
            mid_x = (x1 + x2) / 2
            rect = self.canvas.create_rectangle(x1, y1, mid_x, y2, fill=fill, outline="", width=0)
            arc = self.canvas.create_arc(
                mid_x - (x2 - x1) / 2,
                y1,
                x2,
                y2,
                start=-90,
                extent=180,
                style=tk.PIESLICE,
                fill=fill,
                outline="",
                width=0,
            )
            left = self.canvas.create_line(x1, y1, x1, y2, fill=outline, width=2)
            top = self.canvas.create_line(x1, y1, mid_x, y1, fill=outline, width=2)
            bottom = self.canvas.create_line(x1, y2, mid_x, y2, fill=outline, width=2)
            outline_arc = self.canvas.create_arc(
                mid_x - (x2 - x1) / 2,
                y1,
                x2,
                y2,
                start=-90,
                extent=180,
                style=tk.ARC,
                outline=outline,
                width=2,
            )
            items.extend([rect, arc, left, top, bottom, outline_arc])
            return items
        if kind.startswith("OR"):
            back = self.canvas.create_line(
                x1,
                y1,
                x1 + (x2 - x1) * 0.3,
                y2,
                smooth=True,
                fill=outline,
                width=2,
            )
            front = self.canvas.create_line(
                x1 + (x2 - x1) * 0.3,
                y1,
                x2,
                (y1 + y2) / 2,
                x1 + (x2 - x1) * 0.3,
                y2,
                smooth=True,
                fill=outline,
                width=2,
            )
            fill_poly = self.canvas.create_polygon(
                x1 + (x2 - x1) * 0.25,
                y1 + 1,
                x2 - 1,
                (y1 + y2) / 2,
                x1 + (x2 - x1) * 0.25,
                y2 - 1,
                x1 + (x2 - x1) * 0.1,
                y2 - 1,
                x1 + (x2 - x1) * 0.1,
                y1 + 1,
                fill=fill,
                outline="",
                smooth=True,
            )
            items.extend([fill_poly, back, front])
            return items
        if kind.startswith("MUX"):
            poly = self.canvas.create_polygon(
                x1,
                y1,
                x2,
                y1 + (y2 - y1) * 0.2,
                x2,
                y2 - (y2 - y1) * 0.2,
                x1,
                y2,
                fill=fill,
                outline=outline,
                width=2,
            )
            items.append(poly)
            return items
        if kind.startswith("DEMUX"):
            poly = self.canvas.create_polygon(
                x1,
                y1 + (y2 - y1) * 0.2,
                x2,
                y1,
                x2,
                y2,
                x1,
                y2 - (y2 - y1) * 0.2,
                fill=fill,
                outline=outline,
                width=2,
            )
            items.append(poly)
            return items
        if kind == "DFF":
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
            clock = self.canvas.create_polygon(
                x1,
                (y1 + y2) / 2 - 6,
                x1 + 8,
                (y1 + y2) / 2,
                x1,
                (y1 + y2) / 2 + 6,
                fill=outline,
                outline=outline,
            )
            items.extend([rect, clock])
            return items
        rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
        items.append(rect)
        return items

    def save_diagram(self, path: Path):
        self.root.update()
        ps_path = path.with_suffix(".ps")
        self.canvas.postscript(file=ps_path, colormode="color")
        try:
            from PIL import Image

            img = Image.open(ps_path)
            img.save(path)
        except Exception as exc:
            print(f"PNG 저장 실패: {exc}. PostScript 파일로 저장합니다: {ps_path}")

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


def parse_json(path: Path) -> tuple[dict[str, Node], list[Connection]]:
    data = json.loads(path.read_text(encoding="utf-8"))
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
            level=int(level) if level is not None else 0,
        )
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
                    break

    return nodes, connections


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
