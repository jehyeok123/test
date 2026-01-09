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
    items: list[int] = field(default_factory=list)


@dataclass
class Connection:
    src: tuple[str, str]
    dst: tuple[str, str]
    line_id: int | None = None
    manual_mid_x: float | None = None
    manual_y1: float | None = None
    manual_y2: float | None = None


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
        self._drag_wire = {"connection": None, "offset": 0.0, "mode": None}
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
                fill="#f0f5ff",
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
                fill="#f0f5ff",
                outline="",
                width=0,
            )
            left = self.canvas.create_line(x1, y1, x1, y2, fill="#1f3b74", width=2)
            top = self.canvas.create_line(x1, y1, mid_x, y1, fill="#1f3b74", width=2)
            bottom = self.canvas.create_line(x1, y2, mid_x, y2, fill="#1f3b74", width=2)
            outline_arc = self.canvas.create_arc(
                mid_x - (x2 - x1) / 2,
                y1,
                x2,
                y2,
                start=-90,
                extent=180,
                style=tk.ARC,
                outline="#1f3b74",
                width=2,
            )
            node.items.extend([rect, arc, left, top, bottom, outline_arc])
        else:
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="#f0f5ff", outline="#1f3b74", width=2)
            node.items.append(rect)
        if node.kind == "BLOCK":
            label = self.canvas.create_text((x1 + x2) / 2, y1 + 16, text=node.name, font=("Arial", 12, "bold"))
            node.items.append(label)

        port_gap = max(node.height - 60, 40)
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
                port_id = self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill="#6c7ae0")
                text_id = self.canvas.create_text(px + 12, py, text=port.name, anchor="w", font=("Arial", 9))
                port.canvas_id = port_id
                node.items.extend([port_id, text_id])

        connected_outputs = [port for port in node.outputs if port.connected]
        if connected_outputs:
            output_step = port_gap // max(len(connected_outputs), 1)
            center_y = (y1 + y2) / 2
            for idx, port in enumerate(connected_outputs, start=1):
                if node.kind == "AND":
                    px, py = x2, center_y
                else:
                    px, py = x2, y1 + 50 + idx * output_step
                port_id = self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill="#28a745")
                text_id = self.canvas.create_text(px - 12, py, text=port.name, anchor="e", font=("Arial", 9))
                port.canvas_id = port_id
                node.items.extend([port_id, text_id])

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
            connection.manual_y1,
            connection.manual_y2,
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
        for connection in self.connections:
            connection.manual_mid_x = None
            connection.manual_y1 = None
            connection.manual_y2 = None
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
            connection.manual_y1,
            connection.manual_y2,
        )
            self.canvas.coords(
                connection.line_id,
                *coords,
            )

    def _connection_coords(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        manual_mid_x: float | None = None,
        manual_y1: float | None = None,
        manual_y2: float | None = None,
    ) -> list[float]:
        x1, y1 = start
        x2, y2 = end
        if x1 == x2 or y1 == y2:
            return [x1, y1, x2, y2]
        mid_x = manual_mid_x if manual_mid_x is not None else (x1 + x2) / 2
        y1a = manual_y1 if manual_y1 is not None else y1
        y2a = manual_y2 if manual_y2 is not None else y2
        coords = [x1, y1]
        if y1a != y1:
            coords.extend([x1, y1a])
        coords.extend([mid_x, y1a, mid_x, y2a])
        if y2a != y2:
            coords.extend([x2, y2a])
        coords.extend([x2, y2])
        return coords


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
        coords = self._connection_coords(start, end, connection.manual_mid_x, connection.manual_y1, connection.manual_y2)
        if len(coords) < 8:
            return
        mid_x = coords[2]
        y1a = coords[3]
        y2a = coords[5]
        if self._near_vertical_segment(event.x, event.y, mid_x, y1a, y2a):
            self._drag_wire["connection"] = connection
            self._drag_wire["offset"] = event.x - mid_x
            self._drag_wire["mode"] = "vertical"
            return
        if self._near_horizontal_segment(event.x, event.y, start[0], mid_x, y1a):
            self._drag_wire["connection"] = connection
            self._drag_wire["offset"] = event.y - y1a
            self._drag_wire["mode"] = "top"
            return
        if self._near_horizontal_segment(event.x, event.y, mid_x, end[0], y2a):
            self._drag_wire["connection"] = connection
            self._drag_wire["offset"] = event.y - y2a
            self._drag_wire["mode"] = "bottom"
            return

    def _on_wire_motion(self, event):
        connection: Connection | None = self._drag_wire["connection"]
        if not connection:
            return
        mode = self._drag_wire["mode"]
        if mode == "vertical":
            connection.manual_mid_x = event.x - self._drag_wire["offset"]
        elif mode == "top":
            connection.manual_y1 = event.y - self._drag_wire["offset"]
        elif mode == "bottom":
            connection.manual_y2 = event.y - self._drag_wire["offset"]
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
            connection.manual_y1,
            connection.manual_y2,
        )
        self.canvas.coords(connection.line_id, *coords)

    def _on_wire_release(self, _event):
        self._drag_wire["connection"] = None
        self._drag_wire["mode"] = None

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


def parse_blocks(path: Path) -> dict[str, Node]:
    config = configparser.ConfigParser()
    config.read(path)
    nodes: dict[str, Node] = {}
    x, y = 80, 80
    for section in config.sections():
        inputs = [p.strip() for p in config.get(section, "in", fallback="").split(",") if p.strip()]
        outputs = [p.strip() for p in config.get(section, "out", fallback="").split(",") if p.strip()]
        node = Node(
            name=section,
            kind="BLOCK",
            inputs=[Port(name=p, kind="in") for p in inputs],
            outputs=[Port(name=p, kind="out") for p in outputs],
            x=x,
            y=y,
            height=max(100, 40 + 20 * max(len(inputs), len(outputs), 1)),
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
            )
            nodes[gate_name] = gate_node
            gate_index += 1
            for idx, source in enumerate(inputs):
                src_node, src_port = source.split(".", 1)
                connections.append(Connection(src=(src_node, src_port), dst=(gate_name, f"in{idx+1}")))
            dst_node, dst_port = output.split(".", 1)
            connections.append(Connection(src=(gate_name, "out"), dst=(dst_node, dst_port)))
            continue

        direct_match = re.match(r"^(\S+)\s*->\s*(\S+)$", line)
        if direct_match:
            src, dst = direct_match.groups()
            src_node, src_port = src.split(".", 1)
            dst_node, dst_port = dst.split(".", 1)
            connections.append(Connection(src=(src_node, src_port), dst=(dst_node, dst_port)))
            continue

        raise ValueError(f"연결 형식을 파싱할 수 없습니다: {line}")
    return connections


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
