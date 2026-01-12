Fix connection drawing error and update sample connections to avoid unconnected port warnings.
Fix connection line coordinate usage and log warnings with [WARN] prefix.
Add straight wires with double-click bends, snap-to-90 guidance, and AND gate shape.
Remove bend editing and add gate_symbol.txt plus orthogonal auto-routing.
Rename gate_symbol.json and allow dragging the vertical elbow; reset on node move.
Remove gate_symbol.json and draw AND gate directly on the canvas.
Refine AND gate outline and allow dragging horizontal wire segments.
Fix indentation bug when updating wire coordinates.
Remove horizontal wire dragging and switch block ports to count-based definitions.
Enable dragging port positions via horizontal wire segments and update port/block styling.
Allow block sizing overrides and wire labels from connections.txt.
Hide port dots and allow one-sided connections with fixed-length stubs.
Add edge drag resizing for blocks and remove width/height config.
Require double-click resize mode to edit block size and disable moves while active.
Ensure edge resize continues until mouse release even when leaving the edge.
Snap block move/resize to 10-unit grid steps.
Raise selected block and its wires to the front.
Snap block moves/resizes and port moves to 10-unit steps.
Snap elbow drag to 5-unit steps and keep elbows when moving ports.
Add NEW/CONNECT/DISCONNECT UI with port dots and interactive wiring modes.
Add SHOW/HIDE PORT toggle and gate creation options.
