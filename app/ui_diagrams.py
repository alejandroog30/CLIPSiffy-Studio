import qtvscodestyle as qtvsc

from PyQt6.QtWidgets import (
    QGraphicsLineItem, QPushButton, QGraphicsView,
    QGraphicsScene, QGraphicsPathItem, QGraphicsItem,
    QGraphicsTextItem, QGraphicsRectItem, QGraphicsPixmapItem
)

from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtSvg import QSvgRenderer

from PyQt6.QtCore import Qt, QSize, QPointF, QTimer, QByteArray

from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush

class DiagramView(QGraphicsView):
    """
    The interactive canvas view displaying the graphical architecture of the CLIPS
    Fuzzy Systems and Environments. Supports zoom, drag, and multi-level drill-down.

    Attributes:
        scene_obj (QGraphicsScene): The logical scene holding the graphical items.
        view_mode (str): Current zoom level ("global", "detalle_sistema", "detalle_entorno").
        current_id (str): The ID of the currently inspected system or environment.
        last_env (clips.Environment): Reference to the last processed CLIPS environment.
        btn_return (QPushButton): UI button to return to the global macro view.
    """

    def __init__(self, parent=None):
        """
        Initializes the canvas, sets rendering parameters, and adds navigation UI.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        self.setStyleSheet("border: none;")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) 
        
        self.view_mode = "global"
        self.current_id = None
        self.last_env = None
        
        self.btn_return = QPushButton("Return to Global View", self)
        self.btn_return.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        self.btn_return.move(15, 15)
        self.btn_return.hide()
        self.btn_return.clicked.connect(self.return_global_view)

    def drawBackground(self, painter, rect):
        """
        Renders a dotted grid pattern in the background of the canvas.

        Args:
            painter (QPainter): The painter object used for drawing.
            rect (QRectF): The exposed rectangle of the viewport needing an update.
        """
        painter.fillRect(rect, QColor("#1a1a1a"))
        spacing = 20
        left = int(rect.left()) - (int(rect.left()) % spacing)
        top = int(rect.top()) - (int(rect.top()) % spacing)
        points = []
        for x in range(left, int(rect.right()), spacing):
            for y in range(top, int(rect.bottom()), spacing):
                points.append(QPointF(x, y))
        painter.setPen(QPen(QColor("#3d3d3d"), 1))
        painter.drawPoints(points)

    def return_global_view(self):
        """
        Restores the view mode to the macro-level architecture and updates the diagram.
        """
        self.view_mode = "global"
        self.current_id = None
        self.btn_return.hide()
        if self.last_env:
            self.update_diagram(self.last_env)

    def on_node_double_click(self, node_type, ref_id):
        """
        Callback executed when a macro block is double-clicked. 
        It transitions the view mode to drill-down into the specific system or environment.

        Args:
            node_type (str): Type of the clicked node ("sistema" or "entorno").
            ref_id (str): ID of the target system or environment to inspect.
        """
        if node_type in ["sistema", "entorno"]:
            self.view_mode = f"detalle_{node_type}"
            self.current_id = ref_id
            self.btn_return.show()
            if self.last_env:
                QTimer.singleShot(0, lambda: self.update_diagram(self.last_env))

    def update_diagram(self, env):
        """
        Parses the CLIPS environment memory to extract relationships and routes 
        the drawing logic based on the current active view mode.

        Args:
            env (clips.Environment): The active CLIPS environment containing the current facts.
        """
        self.last_env = env
        self.scene_obj.clear()
        
        systems = []; variables = []; connections = []; fuzzy_sets = {}
        env_configs = []; env_vars = []; env_links = []; env_eqs = []
        
        for fact in env.facts():
            t = fact.template.name
            if t == "FuzzySystemConfig": systems.append(fact)
            elif t == "FuzzyVar": variables.append(fact)
            elif t == "Connection": connections.append(fact)
            elif t == "FuzzySet":
                vname = str(fact["var-name"])
                if vname not in fuzzy_sets: fuzzy_sets[vname] = []
                fuzzy_sets[vname].append(fact)
            elif t == "EnvConfig": env_configs.append(fact)
            elif t == "EnvVar": env_vars.append(fact)
            elif t == "EnvEquation": env_eqs.append(fact)
            elif t == "EnvLink": env_links.append(fact)
                
        if not systems and not env_configs:
            self.scene_obj.addText("No systems or environments loaded.", QFont("Segoe UI", 12)).setDefaultTextColor(QColor("#858585"))
            return

        if self.view_mode == "global":
            self._draw_global_view(systems, env_configs, variables, connections, env_eqs, env_links)
        elif self.view_mode == "detalle_sistema":
            self._draw_system_detail(self.current_id, variables, fuzzy_sets)
        elif self.view_mode == "detalle_entorno":
            self._draw_environment_detail(self.current_id, variables, env_vars, env_eqs)
    
    def _draw_global_view(self, systems, env_configs, variables, connections, env_eqs, env_links):
        """
        Renders the macro block diagram showing major systems, environments, and their data pipelines.

        Args:
            systems (list): List of FuzzySystemConfig facts.
            env_configs (list): List of EnvConfig facts.
            variables (list): List of FuzzyVar facts.
            connections (list): List of inter-system Connection facts.
            env_eqs (list): List of EnvEquation facts (System to Environment links).
            env_links (list): List of EnvLink facts (Environment to System links).
        """
        import qtvscodestyle as qtvsc
        adj = {}
        for sys in systems: adj[f"SYS_{sys['id']}"] = []
        for ec in env_configs: adj[f"ENV_{ec['id']}"] = []
            
        out_vars = {str(v["name"]): str(v["system-id"]) for v in variables if str(v["type"]) == "output"}
        in_vars = {str(v["name"]): str(v["system-id"]) for v in variables if str(v["type"]) == "input"}

        macro_connections = []

        for conn in connections:
            try:
                from_sys = str(conn["from-system"])
                to_sys = in_vars.get(str(conn["to-var"]))
                if to_sys:
                    adj[f"SYS_{from_sys}"].append(f"SYS_{to_sys}")
                    macro_connections.append((f"SYS_{from_sys}", f"SYS_{to_sys}", "#a855f7"))
            except Exception: pass

        for eq in env_eqs:
            try:
                eid = f"ENV_{eq['env-id']}"
                for arg in str(eq["args"]).split():
                    if arg in out_vars:
                        sid = f"SYS_{out_vars[arg]}"
                        adj[sid].append(eid)
                        macro_connections.append((sid, eid, "#10b981"))
            except Exception: pass

        for link in env_links:
            try:
                eid = f"ENV_{link['env-id']}"
                fin = str(link["fuzzy-input"])
                if fin in in_vars:
                    sid = f"SYS_{in_vars[fin]}"
                    adj[eid].append(sid)
                    macro_connections.append((eid, sid, "#3b82f6"))
            except Exception: pass

        depth = {k: 0 for k in adj}
        change = True
        limit = 0
        while change and limit < 50:
            change = False
            for u in adj:
                for v in adj[u]:
                    if depth[v] < depth[u] + 1:
                        depth[v] = depth[u] + 1
                        change = True
            limit += 1

        graphic_nodes = {}
        y_counters = {}

        for sys in systems:
            sid = str(sys["id"])
            nid = f"SYS_{sid}"
            lvl = depth.get(nid, 0)
            if lvl not in y_counters: y_counters[lvl] = 50
            
            x = lvl * 350 + 50
            y = y_counters[lvl]
            
            node = NodeItem(x, y, f"System: {sid}", "#2d1b2e", "#a855f7", is_system=True, 
                            node_type="sistema", ref_id=sid, click_callback=self.on_node_double_click,
                            vsc_icon=qtvsc.Vsc.SETTINGS_GEAR)
            self.scene_obj.addItem(node)
            graphic_nodes[nid] = node
            y_counters[lvl] += 80

        for ec in env_configs:
            eid = str(ec["id"])
            nid = f"ENV_{eid}"
            lvl = depth.get(nid, 0)
            if lvl not in y_counters: y_counters[lvl] = 50
            
            x = lvl * 350 + 50
            y = y_counters[lvl]
            
            node = NodeItem(x, y, f"Environment: {eid}", "#064e3b", "#10b981", is_system=True, 
                            node_type="entorno", ref_id=eid, click_callback=self.on_node_double_click,
                            vsc_icon=qtvsc.Vsc.GLOBE)
            self.scene_obj.addItem(node)
            graphic_nodes[nid] = node
            y_counters[lvl] += 80

        drawn_edges = set()
        for from_id, to_id, color in macro_connections:
            if (from_id, to_id) not in drawn_edges and from_id in graphic_nodes and to_id in graphic_nodes:
                drawn_edges.add((from_id, to_id))
                n_ori = graphic_nodes[from_id]
                n_des = graphic_nodes[to_id]
                c = ConnectionItem(n_ori, n_des)
                c.setPen(QPen(QColor(color), 3, Qt.PenStyle.SolidLine))
                n_ori.output_connections.append(c)
                n_des.input_connections.append(c)
                self.scene_obj.addItem(c)

    def _draw_system_detail(self, sys_id, variables, fuzzy_sets):
        """
        Renders the detailed internal view of a specific Fuzzy System, showing 
        all its input and output variables along with their membership functions.

        Args:
            sys_id (str): The unique identifier of the system to inspect.
            variables (list): List of all FuzzyVar facts to filter.
            fuzzy_sets (dict): Dictionary grouping fuzzy sets by variable name.
        """
        import qtvscodestyle as qtvsc
        inputs_vars = [v for v in variables if str(v["system-id"]) == sys_id and str(v["type"]) == "input"]
        outputs_vars = [v for v in variables if str(v["system-id"]) == sys_id and str(v["type"]) == "output"]
        
        center_y = 50 + max(len(inputs_vars), len(outputs_vars)) * 40
        node_sys = NodeItem(300, center_y, f"Central System: {sys_id}", "#2d1b2e", "#a855f7", is_system=True, vsc_icon=qtvsc.Vsc.SETTINGS_GEAR)
        self.scene_obj.addItem(node_sys)
        
        y_in = 50
        for var in inputs_vars:
            vname = str(var['name'])
            fsets = fuzzy_sets.get(vname, [])
            vmin = float(var['min']) if var['min'] is not None else 0.0
            vmax = float(var['max']) if var['max'] is not None else 100.0
            
            node = NodeItem(50, y_in, f"{vname}", "#1e293b", "#3b82f6", False, vmin, vmax, fsets, vsc_icon=qtvsc.Vsc.SIGN_IN)
            self.scene_obj.addItem(node)
            
            c = ConnectionItem(node, node_sys)
            node.output_connections.append(c)
            node_sys.input_connections.append(c)
            self.scene_obj.addItem(c)
            y_in += 95
            
        y_out = 50
        for var in outputs_vars:
            vname = str(var['name'])
            fsets = fuzzy_sets.get(vname, [])
            vmin = float(var['min']) if var['min'] is not None else 0.0
            vmax = float(var['max']) if var['max'] is not None else 100.0
            
            node = NodeItem(600, y_out, f"{vname}", "#3f201d", "#f97316", False, vmin, vmax, fsets, vsc_icon=qtvsc.Vsc.DASH)
            self.scene_obj.addItem(node)
            
            c = ConnectionItem(node_sys, node)
            node_sys.output_connections.append(c)
            node.input_connections.append(c)
            self.scene_obj.addItem(c)
            y_out += 95

    def _draw_environment_detail(self, env_id, variables, env_vars, env_eqs):
        """
        Renders the detailed internal view of a simulated Environment, displaying 
        the expected inputs from fuzzy systems and its own internally tracked state variables.

        Args:
            env_id (str): The unique identifier of the environment to inspect.
            variables (list): List of all FuzzyVar facts to filter external inputs.
            env_vars (list): List of internally tracked environment variables.
            env_eqs (list): List of update equations applied within this environment.
        """
        import qtvscodestyle as qtvsc
        env_vars_list = [v for v in env_vars if str(v["env-id"]) == env_id]
        env_eqs_list = [eq for eq in env_eqs if str(eq["env-id"]) == env_id]
        out_vars = {str(v["name"]): str(v["system-id"]) for v in variables if str(v["type"]) == "output"}
        
        expected_inputs = set()
        for eq in env_eqs_list:
            args = str(eq["args"]).split()
            for arg in args:
                if arg in out_vars: expected_inputs.add(arg)
                
        center_y = 50 + max(len(expected_inputs), len(env_vars_list)) * 40
        node_env = NodeItem(300, center_y, f"Environment Engine: {env_id}", "#064e3b", "#10b981", is_system=True, vsc_icon=qtvsc.Vsc.GLOBE)
        self.scene_obj.addItem(node_env)
        
        y_in = 50
        for vname in expected_inputs:
            node = NodeItem(50, y_in, f"{vname} (Fuzzy)", "#1e293b", "#10b981", is_system=True, vsc_icon=qtvsc.Vsc.SIGN_IN)
            self.scene_obj.addItem(node)
            c = ConnectionItem(node, node_env)
            node.output_connections.append(c)
            node_env.input_connections.append(c)
            self.scene_obj.addItem(c)
            y_in += 60
            
        y_out = 50
        for var in env_vars_list:
            vname = str(var["name"])
            node = NodeItem(600, y_out, f"{vname} (EnvVar)", "#1e293b", "#10b981", is_system=True, vsc_icon=qtvsc.Vsc.SIGN_OUT)
            self.scene_obj.addItem(node)
            c = ConnectionItem(node_env, node)
            node_env.output_connections.append(c)
            node.input_connections.append(c)
            self.scene_obj.addItem(c)
            y_out += 60

class InteractiveSVGViewer(QGraphicsView):
    """
    A custom interactive view for displaying Scalable Vector Graphics (SVG).
    It provides built-in support for panning (click and drag) and zooming (mouse wheel).

    Attributes:
        scene_obj (QGraphicsScene): The logical scene holding the SVG item.
        renderer (QSvgRenderer): The engine responsible for parsing and rendering the SVG byte data.
        svg_item (QGraphicsSvgItem): The graphical item that displays the rendered SVG on the canvas.
    """

    def __init__(self, svg_bytes, parent=None):
        """
        Initializes the SVG viewer, sets up the scene, and configures interactive modes.

        Args:
            svg_bytes (bytes): The raw byte data of the SVG image to be rendered.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        # Initialize the SVG renderer with the provided byte array
        self.renderer = QSvgRenderer(QByteArray(svg_bytes))
        self.svg_item = QGraphicsSvgItem()
        self.svg_item.setSharedRenderer(self.renderer)
        self.scene_obj.addItem(self.svg_item)
        
        # Adjust the scene boundaries to match the loaded SVG size
        self.scene_obj.setSceneRect(self.svg_item.boundingRect())
        
        # Visual styling and rendering quality
        self.setStyleSheet("background-color: #1a1a1a; border: none;")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Enable panning with a hand cursor and zooming towards the mouse pointer
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event):
        """
        Overrides the default mouse wheel event to implement zooming capabilities.
        Scrolling up zooms in, scrolling down zooms out.

        Args:
            event (QWheelEvent): The wheel event containing the rotation delta.
        """
        if event.angleDelta().y() > 0:
            zoom_factor = 1.15
        else:
            zoom_factor = 1 / 1.15
            
        # Apply the scaling transformation
        self.scale(zoom_factor, zoom_factor)

class ConnectionItem(QGraphicsPathItem):
    """
    Represents a visual connection line (Bézier curve) between two nodes in the diagram scene.

    Attributes:
        source_node (NodeItem): The node where the connection starts.
        target_node (NodeItem): The node where the connection ends.
    """

    def __init__(self, source_node, target_node):
        """
        Initializes the connection item.

        Args:
            source_node (NodeItem): The origin node.
            target_node (NodeItem): The destination node.
        """
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.setPen(QPen(QColor("#858585"), 2))
        self.setZValue(-1)
        self.update_path()
        
    def update_path(self):
        """
        Calculates and draws a cubic Bézier curve between the right anchor of the 
        source node and the left anchor of the target node.
        """
        p_start = self.source_node.right_anchor_point()
        p_end = self.target_node.left_anchor_point()
        
        path = QPainterPath(p_start)
        distance = abs(p_end.x() - p_start.x()) * 0.5
        ctrl1 = QPointF(p_start.x() + distance, p_start.y())
        ctrl2 = QPointF(p_end.x() - distance, p_end.y())
        path.cubicTo(ctrl1, ctrl2, p_end)
        self.setPath(path)

class NodeItem(QGraphicsRectItem):
    """
    Represents a graphical block/node in the diagram. It can act as a macro system block
    or a detailed variable block displaying miniature fuzzy sets.

    Attributes:
        input_connections (list): List of incoming ConnectionItems.
        output_connections (list): List of outgoing ConnectionItems.
        node_type (str): Specifies if the node is a "sistema" (system) or "entorno" (environment).
        ref_id (str): The unique identifier of the system/environment this node represents.
        click_callback (callable): Function to trigger upon double-clicking the node.
    """

    def __init__(self, x, y, text, bg_color, border_color, is_system=False, vmin=0.0, vmax=1.0, fsets=None, node_type=None, ref_id=None, click_callback=None, vsc_icon=None):
        """
        Initializes the NodeItem and constructs its visual layout.

        Args:
            x (float): X-coordinate position in the scene.
            y (float): Y-coordinate position in the scene.
            text (str): The display text or title of the node.
            bg_color (str): Hex color code for the background.
            border_color (str): Hex color code for the border.
            is_system (bool): If True, it renders as a compact box. If False, it may expand to draw graphs.
            vmin (float): Minimum range value for the fuzzy variable (used for graphs).
            vmax (float): Maximum range value for the fuzzy variable (used for graphs).
            fsets (list of dict, optional): Fuzzy sets configuration to draw the mini-graphs.
            node_type (str, optional): The type of macro block ('sistema' or 'entorno').
            ref_id (str, optional): Identifier for drill-down mapping.
            click_callback (callable, optional): The callback to execute on double-click.
            vsc_icon (str, optional): VSCode theme icon constant to render next to the text.
        """
        super().__init__()
        self.input_connections = []
        self.output_connections = []
        
        self.node_type = node_type
        self.ref_id = ref_id
        self.click_callback = click_callback
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        if self.click_callback:
            self.setToolTip("Double click to inspect internal components")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setDefaultTextColor(QColor("#d4d4d4"))
        self.text_item.setFont(QFont("Segoe UI", 10))

        offset_x = 0
        if vsc_icon:
            icon = qtvsc.theme_icon(vsc_icon, "icon.foreground")
            pixmap = icon.pixmap(QSize(16, 16))
            self.icon_item = QGraphicsPixmapItem(pixmap, self)
            offset_x = 22 # 16px icon + 6px gap
            
        if is_system or not fsets:
            width = self.text_item.boundingRect().width() + offset_x + 40
            height = 40
            if vsc_icon:
                self.icon_item.setPos(20, 12) 
                self.text_item.setPos(20 + offset_x, 8)
            else:
                self.text_item.setPos(20, 8)
        else:
            width = max(self.text_item.boundingRect().width() + offset_x + 40, 140)
            height = 85
            
            total_width = self.text_item.boundingRect().width() + offset_x
            start_x = (width - total_width) / 2
            
            if vsc_icon:
                self.icon_item.setPos(start_x, 9)
                self.text_item.setPos(start_x + offset_x, 5)
            else:
                self.text_item.setPos(start_x, 5)
                
            self._draw_mini_graph(vmin, vmax, fsets, width, height, border_color)
            
        self.setRect(0, 0, width, height)
        self.setPos(x, y)
        self.setPen(QPen(QColor(border_color), 2))
        self.setBrush(QBrush(QColor(bg_color)))

    def mouseDoubleClickEvent(self, event):
        """
        Catches double-click events to trigger drill-down navigation.

        Args:
            event (QGraphicsSceneMouseEvent): The mouse event object.
        """
        if event.button() == Qt.MouseButton.LeftButton and self.click_callback:
            self.click_callback(self.node_type, self.ref_id)
        super().mouseDoubleClickEvent(event)
        
    def _draw_mini_graph(self, vmin, vmax, fsets, width, height, line_color):
        """
        Internally renders mathematical approximations of fuzzy membership functions 
        (Type-1 and Type-2) within the node's visual boundary.

        Args:
            vmin (float): Minimum x-axis value.
            vmax (float): Maximum x-axis value.
            fsets (list of dict): Configuration data of the fuzzy sets.
            width (float): Width of the node.
            height (float): Height of the node.
            line_color (str): Color of the lines to be plotted.
        """
        import numpy as np
        
        pad_x = 10
        top_y = 25
        bottom_y = height - 10
        w_graph = width - 2 * pad_x
        h_graph = bottom_y - top_y
        
        axis = QGraphicsLineItem(pad_x, bottom_y, width - pad_x, bottom_y, self)
        axis.setPen(QPen(QColor("#555555"), 1))
        
        range_val = vmax - vmin if vmax > vmin else 1.0
        x = np.linspace(vmin, vmax, 50)
        
        def trace_curve(y_vals, is_dashed=False):
            if y_vals is None: return
            path = QPainterPath()
            for i in range(len(x)):
                px = pad_x + ((x[i] - vmin) / range_val) * w_graph
                py = bottom_y - (y_vals[i] * h_graph)
                if i == 0: path.moveTo(px, py)
                else: path.lineTo(px, py)
                
            path_item = QGraphicsPathItem(path, self)
            pen = QPen(QColor(line_color), 1.5)
            if is_dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setWidthF(1.0) 
            path_item.setPen(pen)

        for fset in fsets:
            def calculate_y(mf_name, parameters):
                if not mf_name or mf_name == "nil": return None
                try:
                    p = [float(v) for v in parameters]
                except Exception: return None
                
                y = np.zeros_like(x)
                if mf_name == "mf-triangular" and len(p) >= 3:
                    a, b, c = p[:3]
                    idx1 = (x > a) & (x < b); y[idx1] = (x[idx1] - a) / (b - a) if b > a else 0
                    y[x == b] = 1.0
                    idx2 = (x > b) & (x < c); y[idx2] = (c - x[idx2]) / (c - b) if c > b else 0
                elif mf_name == "mf-trapezoidal" and len(p) >= 4:
                    a, b, c, d = p[:4]
                    idx1 = (x > a) & (x < b); y[idx1] = (x[idx1] - a) / (b - a) if b > a else 0
                    y[(x >= b) & (x <= c)] = 1.0
                    idx2 = (x > c) & (x < d); y[idx2] = (d - x[idx2]) / (d - c) if d > c else 0
                elif mf_name == "mf-gaussian" and len(p) >= 2:
                    m, k = p[:2]
                    y = np.exp(-((x-m)**2) / (2 * k**2 + 1e-9))
                elif mf_name == "mf-gamma" and len(p) >= 2:
                    a, m = p[:2]
                    y[x >= m] = 1.0
                    idx = (x > a) & (x < m); y[idx] = (x[idx] - a) / (m - a) if m > a else 0
                elif mf_name in ["mf-z", "mf-l"] and len(p) >= 2:
                    a, c = p[:2]
                    y[x <= a] = 1.0
                    idx = (x > a) & (x < c); y[idx] = (c - x[idx]) / (c - a) if c > a else 0
                elif mf_name in ["mf-s"] and len(p) >= 2:
                    a, c = p[:2]
                    y[x >= c] = 1.0
                    idx = (x > a) & (x < c); y[idx] = (x[idx] - a) / (c - a) if c > a else 0
                else:
                    return None
                return y

            try:
                mf_val = str(fset["mf"]) if fset["mf"] is not None else "nil"
                params_val = fset["params"] if fset["params"] is not None else []
                l_mf_val = str(fset["l-mf"]) if fset["l-mf"] is not None else "nil"
                l_params_val = fset["l-params"] if fset["l-params"] is not None else []
                u_mf_val = str(fset["u-mf"]) if fset["u-mf"] is not None else "nil"
                u_params_val = fset["u-params"] if fset["u-params"] is not None else []
            except Exception:
                continue

            # Type 1 Evaluation
            if mf_val != "nil" and len(params_val) > 0:
                y_mf = calculate_y(mf_val, params_val)
                trace_curve(y_mf, is_dashed=False)
            
            # Type 2 Evaluation
            if l_mf_val != "nil" and len(l_params_val) > 0:
                y_l = calculate_y(l_mf_val, l_params_val)
                trace_curve(y_l, is_dashed=False) 
            
            if u_mf_val != "nil" and len(u_params_val) > 0:
                y_u = calculate_y(u_mf_val, u_params_val)
                trace_curve(y_u, is_dashed=True)  

    def left_anchor_point(self):
        """
        Calculates the center-left point of the node for incoming connections.
        
        Returns:
            QPointF: The coordinate point.
        """
        rect = self.sceneBoundingRect()
        return QPointF(rect.left(), rect.center().y())
        
    def right_anchor_point(self):
        """
        Calculates the center-right point of the node for outgoing connections.
        
        Returns:
            QPointF: The coordinate point.
        """
        rect = self.sceneBoundingRect()
        return QPointF(rect.right(), rect.center().y())
        
    def itemChange(self, change, value):
        """
        Listens to node movements to dynamically update the paths of connected lines.

        Args:
            change (QGraphicsItem.GraphicsItemChange): The state change type.
            value (Any): The new value associated with the change.

        Returns:
            Any: The propagated return value from the parent class.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for conn in self.input_connections + self.output_connections:
                conn.update_path()
        return super().itemChange(change, value)
