import configparser
import re
import sys
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Port:
    name: str
    kind: str
    canvas_id: int | None = None
    connected: bool = True
    manual_y: float | None = None


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


@dataclass
class Connection:
    src: tuple[str, str]
    dst: tuple[str, str]
    line_id: int | None = None
    manual_mid_x: float | None = None
    label: str | None = None
    label_id: int | None = None


class DiagramApp:
    def __init__(
        self,
        nodes: dict[str, Node],
        connections: list[Connection],
        output_path: Path,
    ):
        self.nodes = nodes
        self.connections = connections
        self.output_path = output_path
        self.root = tk.Tk()
        self.root.title("Block Diagram")
        self.canvas = tk.Canvas(self.root, width=1200, height=800, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._drag_data = {"node": None, "x": 0, "y": 0}
        self._drag_wire = {"connection": None, "offset": 0.0, "mode": None, "port": None, "node": None}
        self._build_ui()

    def _build_ui(self):
        for node in self.nodes.values():
            self._draw_node(node)
        for connection in self.connections:
            self._draw_connection(connection)
        self.canvas.tag_bind("node", "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind("node", "<ButtonRelease-1>", self._on_release)
        self.canvas.tag_bind("node", "<B1-Motion>", self._on_motion)
        self.canvas.tag_bind("wire", "<ButtonPress-1>", self._on_wire_press)
        self.canvas.tag_bind("wire", "<B1-Motion>", self._on_wire_motion)
        self.canvas.tag_bind("wire", "<ButtonRelease-1>", self._on_wire_release)
        self.root.bind("s", lambda _event: self.save_diagram(self.output_path))
        self.root.after(300, lambda: self.save_diagram(self.output_path))

    def _draw_node(self, node: Node):
        x1, y1 = node.x, node.y
        x2, y2 = node.x + node.width, node.y + node.height
        if node.kind == "AND":
            mid_x = (x1 + x2) / 2
            rect = self.canvas.create_rectangle(
                x1,
                y1,
                mid_x,
                y2,
                fill="#e0e0e0",
                outline="",
                width=0,
            )
            arc = self.canvas.create_arc(
                mid_x - (x2 - x1) / 2,
                y1,
                x2,
                y2,
                start=-90,
                extent=180,
                style=tk.PIESLICE,
                fill="#e0e0e0",
                outline="",
                width=0,
            )
            left = self.canvas.create_line(x1, y1, x1, y2, fill="#666666", width=2)
            top = self.canvas.create_line(x1, y1, mid_x, y1, fill="#666666", width=2)
            bottom = self.canvas.create_line(x1, y2, mid_x, y2, fill="#666666", width=2)
            outline_arc = self.canvas.create_arc(
                mid_x - (x2 - x1) / 2,
                y1,
                x2,
                y2,
                start=-90,
                extent=180,
                style=tk.ARC,
                outline="#666666",
                width=2,
            )
            node.items.extend([rect, arc, left, top, bottom, outline_arc])
        else:
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="#e0e0e0", outline="#666666", width=2)
            node.items.append(rect)
        if node.kind == "BLOCK":
            label = self.canvas.create_text(
                x1 + 6,
                y1 + 6,
                text=node.name,
                font=("Arial", 12, "bold"),
                anchor="nw",
            )
            node.items.append(label)

        port_gap = max(node.base_height - 60, 40)
        connected_inputs = [port for port in node.inputs if port.connected]
        if connected_inputs:
            input_step = port_gap // max(len(connected_inputs), 1)
            center_y = (y1 + y2) / 2
            for idx, port in enumerate(connected_inputs, start=1):
                if node.kind == "AND" and len(connected_inputs) >= 2:
                    spacing = 20
                    offset = spacing * (idx - (len(connected_inputs) + 1) / 2)
                    px, py = x1, center_y + offset
                else:
                    px, py = x1, y1 + 50 + idx * input_step
                if port.manual_y is not None:
                    py = port.manual_y
                port_id = self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill="black", outline="black")
                port.canvas_id = port_id
                node.items.append(port_id)

        connected_outputs = [port for port in node.outputs if port.connected]
        if connected_outputs:
            output_step = port_gap // max(len(connected_outputs), 1)
            center_y = (y1 + y2) / 2
            for idx, port in enumerate(connected_outputs, start=1):
                if node.kind == "AND":
                    px, py = x2, center_y
                else:
                    px, py = x2, y1 + 50 + idx * output_step
                if port.manual_y is not None:
                    py = port.manual_y
                port_id = self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill="black", outline="black")
                port.canvas_id = port_id
                node.items.append(port_id)

        for item in node.items:
            self.canvas.addtag_withtag("node", item)
            self.canvas.addtag_withtag(f"node:{node.name}", item)

    def _draw_connection(self, connection: Connection):
        src_node, src_port = connection.src
        dst_node, dst_port = connection.dst
        src_port_id = self._get_port_canvas_id(src_node, src_port, "out")
        dst_port_id = self._get_port_canvas_id(dst_node, dst_port, "in")
        if not src_port_id or not dst_port_id:
            return
        x1, y1 = self._port_center(src_port_id)
        x2, y2 = self._port_center(dst_port_id)
        coords = self._connection_coords(
            (x1, y1),
            (x2, y2),
            connection.manual_mid_x,
        )
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
                font=("Arial", 6),
                anchor="s",
            )
            connection.label_id = label_id

    def _get_port_canvas_id(self, node_name: str, port_name: str, kind: str) -> int | None:
        node = self.nodes.get(node_name)
        if not node:
            return None
        ports = node.outputs if kind == "out" else node.inputs
        for port in ports:
            if port.name == port_name:
                return port.canvas_id
        return None

    def _port_center(self, canvas_id: int) -> tuple[float, float]:
        x1, y1, x2, y2 = self.canvas.coords(canvas_id)
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _on_press(self, event):
        item = self.canvas.find_withtag("current")
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        node_tag = next((tag for tag in tags if tag.startswith("node:")), None)
        if not node_tag:
            return
        node_name = node_tag.split(":", 1)[1]
        self._drag_data["node"] = self.nodes[node_name]
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_release(self, _event):
        self._drag_data["node"] = None

    def _on_motion(self, event):
        node = self._drag_data["node"]
        if not node:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.canvas.move(f"node:{node.name}", dx, dy)
        node.x += dx
        node.y += dy
        for port in node.inputs + node.outputs:
            if port.manual_y is not None:
                port.manual_y += dy
        for connection in self.connections:
            connection.manual_mid_x = None
        self._update_connections()

    def _update_connections(self):
        for connection in self.connections:
            if not connection.line_id:
                continue
            src_id = self._get_port_canvas_id(connection.src[0], connection.src[1], "out")
            dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1], "in")
            if not src_id or not dst_id:
                continue
            x1, y1 = self._port_center(src_id)
            x2, y2 = self._port_center(dst_id)
            coords = self._connection_coords(
                (x1, y1),
                (x2, y2),
                connection.manual_mid_x,
            )
            self.canvas.coords(
                connection.line_id,
                *coords,
            )
            self._update_label(connection, coords)

    def _connection_coords(
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

    def _find_port(self, node_name: str, port_name: str, kind: str) -> tuple[Node, Port] | None:
        node = self.nodes.get(node_name)
        if not node:
            return None
        ports = node.outputs if kind == "out" else node.inputs
        for port in ports:
            if port.name == port_name:
                return node, port
        return None

    def _on_wire_press(self, event):
        item = self.canvas.find_withtag("current")
        if not item:
            return
        line_id = item[0]
        connection = next((conn for conn in self.connections if conn.line_id == line_id), None)
        if not connection:
            return
        src_id = self._get_port_canvas_id(connection.src[0], connection.src[1], "out")
        dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1], "in")
        if not src_id or not dst_id:
            return
        start = self._port_center(src_id)
        end = self._port_center(dst_id)
        coords = self._connection_coords(start, end, connection.manual_mid_x)
        if len(coords) < 8:
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
            port_info = self._find_port(connection.src[0], connection.src[1], "out")
            if not port_info:
                return
            node, port = port_info
            self._reset_mid_for_port(node.name, port.name)
            self._drag_wire["connection"] = connection
            self._drag_wire["mode"] = "src_port"
            self._drag_wire["node"] = node
            self._drag_wire["port"] = port
            return
        if self._near_horizontal_segment(event.x, event.y, mid_x, coords[6], y2a):
            port_info = self._find_port(connection.dst[0], connection.dst[1], "in")
            if not port_info:
                return
            node, port = port_info
            self._reset_mid_for_port(node.name, port.name)
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
            connection.manual_mid_x = event.x - self._drag_wire["offset"]
            src_id = self._get_port_canvas_id(connection.src[0], connection.src[1], "out")
            dst_id = self._get_port_canvas_id(connection.dst[0], connection.dst[1], "in")
            if not src_id or not dst_id:
                return
            x1, y1 = self._port_center(src_id)
            x2, y2 = self._port_center(dst_id)
            coords = self._connection_coords(
                (x1, y1),
                (x2, y2),
                connection.manual_mid_x,
            )
            self.canvas.coords(connection.line_id, *coords)
            return
        if mode in ("src_port", "dst_port"):
            node = self._drag_wire["node"]
            port = self._drag_wire["port"]
            if not node or not port:
                return
            kind = "out" if mode == "src_port" else "in"
            self._move_port(node, port, kind, event.y)
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

    def _move_port(self, node: Node, port: Port, kind: str, target_y: float):
        if port.canvas_id is None:
            return
        radius = 6
        min_y = node.y + 10
        max_y = node.y + node.height - 10
        new_y = max(min_y, min(target_y, max_y))
        x = node.x if kind == "in" else node.x + node.width
        self.canvas.coords(port.canvas_id, x - radius, new_y - radius, x + radius, new_y + radius)
        port.manual_y = new_y
        self._update_connections()

    def _reset_mid_for_port(self, node_name: str, port_name: str):
        for connection in self.connections:
            if connection.src == (node_name, port_name) or connection.dst == (node_name, port_name):
                connection.manual_mid_x = None

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


def _build_ports(value: str, prefix: str) -> list[str]:
    text = value.strip()
    if not text:
        return []
    try:
        count = int(text)
    except ValueError:
        raise ValueError(f"포트 개수는 숫자로 입력해야 합니다: {value}")
    if count < 0:
        raise ValueError(f"포트 개수는 0 이상이어야 합니다: {value}")
    return [f"{prefix}{idx}" for idx in range(1, count + 1)]


def parse_blocks(path: Path) -> dict[str, Node]:
    config = configparser.ConfigParser()
    config.read(path)
    nodes: dict[str, Node] = {}
    x, y = 80, 80
    for section in config.sections():
        inputs = _build_ports(config.get(section, "in", fallback=""), "in")
        outputs = _build_ports(config.get(section, "out", fallback=""), "out")
        base_height = max(100, 40 + 20 * max(len(inputs), len(outputs), 1))
        width = config.getint(section, "width", fallback=160)
        height = config.getint(section, "height", fallback=base_height)
        node = Node(
            name=section,
            kind="BLOCK",
            inputs=[Port(name=p, kind="in") for p in inputs],
            outputs=[Port(name=p, kind="out") for p in outputs],
            x=x,
            y=y,
            width=width,
            height=height,
            base_height=base_height,
        )
        nodes[section] = node
        y += 160
        if y > 600:
            y = 80
            x += 260
    return nodes


def parse_connections(
    path: Path,
    nodes: dict[str, Node],
) -> list[Connection]:
    connections: list[Connection] = []
    gate_index = 1
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line, label = _split_label(line)
        gate_match = re.match(r"^(AND|OR|MUX)\s+(\w+)\s*:\s*(.+?)\s*->\s*(\S+)$", line)
        if gate_match:
            gate_type, gate_name, inputs_raw, output_raw = gate_match.groups()
            inputs = [item.strip() for item in inputs_raw.split(",") if item.strip()]
            output = output_raw.strip()
            gate_node = Node(
                name=gate_name,
                kind=gate_type,
                inputs=[Port(name=f"in{idx+1}", kind="in") for idx in range(len(inputs))],
                outputs=[Port(name="out", kind="out")],
                x=400 + gate_index * 40,
                y=120 + gate_index * 40,
                width=120,
                height=80,
                base_height=80,
            )
            nodes[gate_name] = gate_node
            gate_index += 1
            for idx, source in enumerate(inputs):
                src_node, src_port = source.split(".", 1)
                connections.append(
                    Connection(src=(src_node, src_port), dst=(gate_name, f"in{idx+1}"), label=label)
                )
            dst_node, dst_port = output.split(".", 1)
            connections.append(Connection(src=(gate_name, "out"), dst=(dst_node, dst_port), label=label))
            continue

        direct_match = re.match(r"^(\S+)\s*->\s*(\S+)$", line)
        if direct_match:
            src, dst = direct_match.groups()
            src_node, src_port = src.split(".", 1)
            dst_node, dst_port = dst.split(".", 1)
            connections.append(Connection(src=(src_node, src_port), dst=(dst_node, dst_port), label=label))
            continue

        raise ValueError(f"연결 형식을 파싱할 수 없습니다: {line}")
    return connections


def _split_label(line: str) -> tuple[str, str | None]:
    if "|" not in line:
        return line, None
    base, raw_label = line.split("|", 1)
    label = raw_label.strip()
    label = label.replace("\\n", "\n")
    return base.strip(), label if label else None


def validate_connections(nodes: dict[str, Node], connections: list[Connection], log_path: Path) -> bool:
    used_inputs: set[tuple[str, str]] = set()
    used_outputs: set[tuple[str, str]] = set()
    for connection in connections:
        used_outputs.add(connection.src)
        used_inputs.add(connection.dst)

    errors: list[str] = []
    for node in nodes.values():
        if node.kind != "BLOCK":
            continue
        for port in node.inputs:
            if (node.name, port.name) not in used_inputs:
                errors.append(f"[WARN] 입력 포트 미연결: {node.name}.{port.name}")
                port.connected = False
        for port in node.outputs:
            if (node.name, port.name) not in used_outputs:
                errors.append(f"[WARN] 출력 포트 미연결: {node.name}.{port.name}")
                port.connected = False

    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
        print(f"미연결 포트가 있습니다. {log_path}를 확인하세요.")
        return True
    if log_path.exists():
        log_path.unlink()
    return True


def main():
    blocks_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("input.txt")
    connections_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("connections.txt")
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("diagram.png")
    if not blocks_path.exists() or not connections_path.exists():
        print("input.txt 또는 connections.txt 파일이 없습니다.")
        sys.exit(1)
    nodes = parse_blocks(blocks_path)
    connections = parse_connections(connections_path, nodes)
    validate_connections(nodes, connections, Path("error.log"))
    app = DiagramApp(nodes, connections, output_path)
    app.run()


if __name__ == "__main__":
    main()
