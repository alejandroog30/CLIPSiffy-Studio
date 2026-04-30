from matplotlib import pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QDockWidget, QWidget,
    QVBoxLayout, QTabWidget, QLabel, QComboBox,
)

from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSignal

class Surface3DThread(QThread):
    """
    A background worker thread responsible for calculating the 3D control surface 
    of a Fuzzy System. It iteratively runs the CLIPS engine across a 2D grid 
    of input combinations to compute the corresponding Z-axis output values 
    without freezing the main graphical interface.

    Attributes:
        signal_finished (pyqtSignal): Signal emitted when the computation is complete, 
                                      carrying a list of dictionaries with the plotting data.
        temp_path (str): File path to a temporary CLIPS environment save state.
        facts_str (list of str): String representations of the base CLIPS facts to re-assert.
        sys_id (str): The identifier of the fuzzy system being evaluated.
        var_x (str): The name of the first input variable (X-axis).
        var_y (str): The name of the second input variable (Y-axis).
        var_z (str): The name of the output variable (Z-axis).
        x_bounds (tuple of float): A tuple (min, max) defining the evaluation range for X.
        y_bounds (tuple of float): A tuple (min, max) defining the evaluation range for Y.
        dark_mode (bool): Indicates if the UI is currently in dark mode (used for styling).
    """
    
    signal_finished = pyqtSignal(list)

    def __init__(self, temp_path, facts_str, sys_id, var_x, var_y, var_z, x_bounds, y_bounds, dark_mode=True):
        """
        Initializes the thread with the parameters required to run the grid evaluation.

        Args:
            temp_path (str): Path to the temporary `.clp` file containing the environment's rules.
            facts_str (list of str): Static facts (system configs, variables) to load in each iteration.
            sys_id (str): ID of the system to simulate.
            var_x (str): Variable mapped to the X-axis.
            var_y (str): Variable mapped to the Y-axis.
            var_z (str): Output variable mapped to the Z-axis.
            x_bounds (tuple): (min, max) limits for the X variable.
            y_bounds (tuple): (min, max) limits for the Y variable.
            dark_mode (bool, optional): Theme flag. Defaults to True.
        """
        super().__init__()
        self.temp_path = temp_path
        self.facts_str = facts_str
        self.sys_id = sys_id
        self.var_x = var_x
        self.var_y = var_y
        self.var_z = var_z
        self.x_bounds = x_bounds
        self.y_bounds = y_bounds
        self.dark_mode = dark_mode 

    def run(self):
        """
        Executes the main loop of the thread.
        It creates an isolated temporary CLIPS environment, parses the input ranges into 
        a 2D grid, and executes the engine for every (X, Y) coordinate pair to extract 
        the defuzzified Z output. Once finished, it emits the results back to the GUI.
        """
        import clips
        import numpy as np
        import os
        from matplotlib.figure import Figure
        import mpl_toolkits.mplot3d 

        # Create an isolated engine instance for the thread
        env_temp = clips.Environment()

        try:
            env_temp.load(self.temp_path)
        except Exception:
            pass
        finally:
            if os.path.exists(self.temp_path):
                try: os.remove(self.temp_path)
                except: pass

        # Filter out dynamic execution facts to only keep structural definitions
        base_facts = [
            h for h in self.facts_str 
            if "CrispInput" not in h 
            and "SystemOutput" not in h 
            and "FuzzyRuleOutput" not in h 
            and "FuzzyInput" not in h
            and "CurrentState" not in h 
            and "initial-fact" not in h
        ]

        # Define grid resolution
        res = 20
        X = np.linspace(self.x_bounds[0], self.x_bounds[1], res)
        Y = np.linspace(self.y_bounds[0], self.y_bounds[1], res)
        X_grid, Y_grid = np.meshgrid(X, Y)
        Z_grid = np.zeros_like(X_grid)

        # Iterate through the grid
        for i in range(res):
            for j in range(res):
                env_temp.reset()
                
                # Re-assert the structural facts
                for h in base_facts:
                    try:
                        env_temp.assert_string(h)
                    except Exception:
                        pass

                # Assert the current (X, Y) coordinate as crisp inputs
                env_temp.assert_string(f"(CrispInput (var-name {self.var_x}) (value {X_grid[i, j]}))")
                env_temp.assert_string(f"(CrispInput (var-name {self.var_y}) (value {Y_grid[i, j]}))")
                
                # Run the fuzzy inference engine
                env_temp.run()

                # Extract the defuzzified output (Z)
                z_val = 0.0
                for f in env_temp.facts():
                    if f.template.name == "SystemOutput" and str(f["var-name"]) == self.var_z:
                        z_val = float(f["value"])
                        break
                Z_grid[i, j] = z_val

        # Pack the computed matrices and emit them to the main GUI thread
        self.signal_finished.emit([{
            "sys_id": self.sys_id,
            "var_x": self.var_x,
            "var_y": self.var_y,
            "var_z": self.var_z,
            "X": X_grid,
            "Y": Y_grid,
            "Z": Z_grid
        }])

        # Free engine memory
        try:
            env_temp.clear()
        except Exception:
            pass

class Matplotlib3DViewer(QWidget):
    """
    A custom PyQt widget that embeds a Matplotlib 3D figure canvas.
    It provides an interactive view of the generated fuzzy control surface,
    including a navigation toolbar for rotating, panning, and zooming.

    Attributes:
        layout (QVBoxLayout): The main vertical layout containing the canvas and toolbar.
        fig (matplotlib.figure.Figure): The Matplotlib figure instance holding the plot.
        canvas (FigureCanvas): The PyQt-compatible canvas that renders the Matplotlib figure.
        toolbar (NavigationToolbar): The interactive toolbar provided by Matplotlib.
    """

    def __init__(self, data, parent=None):
        """
        Initializes the 3D viewer, sets up the Matplotlib canvas, and triggers the drawing routine.

        Args:
            data (dict): A dictionary containing the computed surface data and metadata.
                         Expected keys: 'X', 'Y', 'Z' (numpy arrays), 'var_x', 'var_y', 
                         'var_z' (strings), and 'sys_id' (string).
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Initialize the Matplotlib figure with a dark background
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')
        self.canvas = FigureCanvas(self.fig)
        
        # Add the standard Matplotlib navigation toolbar and style it
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #2d2d2d; color: white;")

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        # Render the 3D surface plot
        self._draw_surface(data)

    def _draw_surface(self, d):
        """
        Configures the 3D axes, plots the surface data, and applies visual styling 
        (colors, labels, and grid properties) to match the IDE's dark theme.

        Args:
            d (dict): The data dictionary containing the matrices and labels needed for plotting.
        """
        ax = self.fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#1a1a1a')

        # Plot the mathematical surface using the plasma colormap
        ax.plot_surface(d["X"], d["Y"], d["Z"], cmap='plasma', edgecolor='none', alpha=0.9)

        # Set axis labels and title with custom colors
        ax.set_xlabel(d["var_x"], color='#d4d4d4')
        ax.set_ylabel(d["var_y"], color='#d4d4d4')
        ax.set_zlabel(d["var_z"], color='#f97316')
        ax.set_title(f"Control Surface 3D: {d['sys_id']}", color="#a855f7", fontweight='bold')

        # Style the ticks and axis spines for the dark theme
        ax.tick_params(colors='#858585')
        for spine in ax.spines.values():
            spine.set_color('#3d3d3d')
        
        # Remove the solid background fill from the 3D panes
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False

        # Adjust the layout to prevent clipping and force a canvas redraw
        self.fig.tight_layout()
        self.canvas.draw()

class Surface3DView(QWidget):
    """
    A container widget that orchestrates the generation and display of 3D control 
    surfaces for Fuzzy Systems. It evaluates the current CLIPS memory to find 
    systems with at least 2 inputs and 1 output, dispatches a background computing 
    thread, and manages the UI tabs to display the results.

    Attributes:
        layout (QVBoxLayout): The main vertical layout of the widget.
        tabs (QTabWidget): The tab container used to display multiple 3D viewers or status messages.
        render_thread (Surface3DThread): The background worker thread used to calculate the surface.
    """

    def __init__(self, parent=None):
        """
        Initializes the view, sets up the layout, and applies custom styling to the tabs.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0px; }
            QTabBar::tab { background: #2d2d2d; color: #858585; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;}
            QTabBar::tab:selected { background: #007acc; color: white; font-weight: bold; }
        """)
        self.layout.addWidget(self.tabs)
        self.setStyleSheet("background-color: #1a1a1a; color: #d4d4d4;")
        self.render_thread = None 

    def update_diagram(self, env):
        """
        Analyzes the current CLIPS environment to identify candidate fuzzy systems 
        (requiring >= 2 inputs and >= 1 output). If a valid system is found, it 
        saves the environment state to a temporary file and starts a background 
        thread to compute the 3D surface data.

        Args:
            env (clips.Environment): The active CLIPS environment containing the fuzzy logic definitions.
        """
        systems = {}
        # Parse memory to extract variables grouped by system ID
        for f in env.facts():
            if f.template.name == "FuzzyVar":
                sid = str(f["system-id"])
                if sid not in systems: systems[sid] = {'in': [], 'out': []}
                
                vdata = (str(f["name"]), float(f["min"]), float(f["max"]))
                if str(f["type"]) == "input": systems[sid]['in'].append(vdata)
                elif str(f["type"]) == "output": systems[sid]['out'].append(vdata)

        # Find the first valid candidate system (2 inputs, 1 output)
        candidate_sys = None
        for sid, vars in systems.items():
            if len(vars['in']) >= 2 and len(vars['out']) >= 1:
                candidate_sys = sid
                break
                
        if not candidate_sys:
            self.tabs.clear()
            self.tabs.addTab(QWidget(), "Requires a system with at least 2 inputs and 1 output.")
            return

        self.tabs.clear()
        self.tabs.addTab(QWidget(), "Calculating 3D Surface (400 iterations)...")

        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "clips_clone_env.clp").replace("\\", "/")
        
        # Save current state to a temp file for the background thread to use safely
        try:
            env.eval(f'(save "{temp_path}")')
        except Exception as e:
            print(f"Error saving temp environment: {e}")

        # Stringify facts to bypass memory pointer issues across threads
        facts_str = [str(f) for f in env.facts()]
        
        # Extract metadata and limits for the axes
        var_x = systems[candidate_sys]['in'][0][0]
        xb = (systems[candidate_sys]['in'][0][1], systems[candidate_sys]['in'][0][2])
        
        var_y = systems[candidate_sys]['in'][1][0]
        yb = (systems[candidate_sys]['in'][1][1], systems[candidate_sys]['in'][1][2])
        
        var_z = systems[candidate_sys]['out'][0][0]

        # Attempt to retrieve IDE dark mode preference
        main_ide = self.parent().parent() if self.parent() else None
        is_dark = main_ide.main_menu.action_theme.isChecked() if hasattr(main_ide, 'main_menu') else True

        # Initialize and dispatch the computing thread
        self.render_thread = Surface3DThread(temp_path, facts_str, candidate_sys, var_x, var_y, var_z, xb, yb, is_dark)
        self.render_thread.signal_finished.connect(self._show_svg_tabs)
        self.render_thread.start()

    def _show_svg_tabs(self, results):
        """
        Callback triggered when the background thread completes its computations.
        It clears the loading tab and spawns Matplotlib3DViewer widgets for each result.

        Args:
            results (list of dict): A list containing data dictionaries with X, Y, Z matrices 
                                    and metadata for rendering.
        """
        self.tabs.clear()
        
        for data in results:
            sys_id = data["sys_id"]
            interactive_viewer = Matplotlib3DViewer(data)
            self.tabs.addTab(interactive_viewer, f"3D Surface: {sys_id}")

class SimulationGraphView(QDockWidget):
    """
    A dockable panel that renders time-series graphs of environment variables.
    It scans the CLIPS memory for 'EnvHistory' facts and plots the evolution 
    of each variable over time (or simulation steps) using Matplotlib.

    Attributes:
        figure (Figure): The Matplotlib figure container.
        canvas (FigureCanvas): The PyQt widget rendering the figure.
        toolbar (NavigationToolbar): Matplotlib's interactive navigation bar.
        ax (Axes): The main axes for the plot.
    """

    def __init__(self, title, parent=None):
        """Initializes the simulation graph panel and its Matplotlib canvas."""
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(dpi=100)
        self.figure.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        
        self.toolbar = NavigationToolbar(self.canvas, main_widget)
        self.toolbar.setStyleSheet("background-color: #2d2d2d; color: white;")

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self._setup_axes()

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setWidget(main_widget)

    def _setup_axes(self):
        """Configures the aesthetic properties of the plot axes for dark mode."""
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='#d4d4d4')
        for spine in self.ax.spines.values():
            spine.set_color('#3d3d3d')
        self.ax.set_xlabel("Time / Steps", color="#858585", fontweight='bold')
        self.ax.set_ylabel("Variable Value", color="#858585", fontweight='bold')
        self.ax.grid(True, color='#3d3d3d', linestyle='--', alpha=0.7)

    def update_plot(self, env):
        """
        Scrapes 'EnvHistory' facts from the CLIPS engine, organizes them by variable,
        and redraws the time-series plot.

        Args:
            env (clips.Environment): The active CLIPS environment.
        """
        self._setup_axes()
        
        history_data = {}

        for f in env.facts():
            if f.template.name == "EnvHistory":
                try:
                    time_val = float(f["time"])
                    var_name = str(f["var-name"])
                    value = float(f["value"])
                    
                    if var_name not in history_data:
                        history_data[var_name] = []
                    history_data[var_name].append((time_val, value))
                except Exception:
                    pass

        if not history_data:
            self.ax.text(0.5, 0.5, "No 'EnvHistory' facts found in memory.", 
                         color="#858585", ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        color_idx = 0

        for var_name, points in history_data.items():
            points.sort(key=lambda x: x[0])
            times = [p[0] for p in points]
            values = [p[1] for p in points]
            
            color = colors[color_idx % len(colors)]
            self.ax.plot(times, values, label=var_name, color=color, linewidth=2, marker='o', markersize=4)
            color_idx += 1

        self.ax.legend(facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#d4d4d4')
        self.figure.tight_layout()
        self.canvas.draw()

class StateSpaceView(QDockWidget):
    """
    A dockable panel that renders a Phase Portrait (State Space) diagram.
    It plots one environment variable against another (e.g., Angle vs Velocity)
    to visualize the dynamical trajectory of the system over time.
    """
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        lbl_x = QLabel("X-Axis:")
        lbl_x.setStyleSheet("color: #d4d4d4; font-weight: bold;")
        self.combo_x = QComboBox()
        self.combo_x.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #555;")
        self.combo_x.currentIndexChanged.connect(self._force_redraw)
        
        lbl_y = QLabel("Y-Axis:")
        lbl_y.setStyleSheet("color: #d4d4d4; font-weight: bold;")
        self.combo_y = QComboBox()
        self.combo_y.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #555;")
        self.combo_y.currentIndexChanged.connect(self._force_redraw)
        
        control_layout.addWidget(lbl_x)
        control_layout.addWidget(self.combo_x)
        control_layout.addSpacing(20)
        control_layout.addWidget(lbl_y)
        control_layout.addWidget(self.combo_y)
        control_layout.addStretch()

        self.figure = Figure(dpi=100)
        self.figure.patch.set_facecolor('#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        
        self.toolbar = NavigationToolbar(self.canvas, main_widget)
        self.toolbar.setStyleSheet("background-color: #2d2d2d; color: white;")

        self.ax = self.figure.add_subplot(111)
        self._setup_axes()

        layout.addWidget(self.toolbar)
        layout.addLayout(control_layout)
        layout.addWidget(self.canvas)
        self.setWidget(main_widget)
        
        self.current_env = None

    def _setup_axes(self):
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='#d4d4d4')
        for spine in self.ax.spines.values():
            spine.set_color('#3d3d3d')
        self.ax.grid(True, color='#3d3d3d', linestyle='--', alpha=0.7)
        
        self.ax.axhline(0, color='#555555', linewidth=1.5, zorder=1)
        self.ax.axvline(0, color='#555555', linewidth=1.5, zorder=1)

    def _force_redraw(self):
        if self.current_env:
            self.update_plot(self.current_env)

    def update_plot(self, env):
        self.current_env = env
        
        history_data = {}
        for f in env.facts():
            if f.template.name == "EnvHistory":
                try:
                    t = float(f["time"])
                    vname = str(f["var-name"])
                    val = float(f["value"])
                    if vname not in history_data: history_data[vname] = []
                    history_data[vname].append((t, val))
                except Exception: pass

        if not history_data:
            self._setup_axes()
            self.ax.text(0.5, 0.5, "No 'EnvHistory' facts found.", color="#858585", ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        vars_available = sorted(list(history_data.keys()))
        
        self.combo_x.blockSignals(True)
        self.combo_y.blockSignals(True)
        
        current_x = self.combo_x.currentText()
        current_y = self.combo_y.currentText()
        
        self.combo_x.clear(); self.combo_x.addItems(vars_available)
        self.combo_y.clear(); self.combo_y.addItems(vars_available)
        
        if current_x in vars_available: self.combo_x.setCurrentText(current_x)
        elif len(vars_available) > 0: self.combo_x.setCurrentIndex(0)
            
        if current_y in vars_available: self.combo_y.setCurrentText(current_y)
        elif len(vars_available) > 1: self.combo_y.setCurrentIndex(1)
        else: self.combo_y.setCurrentIndex(0)
            
        self.combo_x.blockSignals(False)
        self.combo_y.blockSignals(False)

        var_x = self.combo_x.currentText()
        var_y = self.combo_y.currentText()

        if not var_x or not var_y: return
        
        pts_x = sorted(history_data[var_x], key=lambda i: i[0])
        pts_y = sorted(history_data[var_y], key=lambda i: i[0])
        
        dict_x = {t: v for t, v in pts_x}
        dict_y = {t: v for t, v in pts_y}
        common_times = sorted(list(set(dict_x.keys()).intersection(set(dict_y.keys()))))
        
        if not common_times: return
        
        X = [dict_x[t] for t in common_times]
        Y = [dict_y[t] for t in common_times]

        self._setup_axes()
        self.ax.set_xlabel(var_x, color="#a855f7", fontweight='bold')
        self.ax.set_ylabel(var_y, color="#3b82f6", fontweight='bold')
        self.ax.set_title(f"State Space: {var_y} vs {var_x}", color="#d4d4d4")

        import numpy as np
        points = np.array([X, Y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        norm = plt.Normalize(0, len(common_times))
        lc = LineCollection(segments, cmap='plasma', norm=norm, linewidth=2, alpha=0.8, zorder=2)
        lc.set_array(np.arange(len(common_times)))
        self.ax.add_collection(lc)
        
        self.ax.scatter(X[0], Y[0], color='#22c55e', s=80, zorder=3, label='Start', edgecolors='white')
        self.ax.scatter(X[-1], Y[-1], color='#ef4444', s=80, zorder=3, label='End', edgecolors='white')

        margin_x = (max(X) - min(X)) * 0.1 if max(X) != min(X) else 1
        margin_y = (max(Y) - min(Y)) * 0.1 if max(Y) != min(Y) else 1
        self.ax.set_xlim(min(X) - margin_x, max(X) + margin_x)
        self.ax.set_ylim(min(Y) - margin_y, max(Y) + margin_y)
        
        self.ax.legend(facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#d4d4d4')
        self.figure.tight_layout()
        self.canvas.draw()

class Matplotlib2DViewer(QWidget):
    """
    A custom PyQt widget that embeds a 2D Matplotlib figure canvas.
    It is specifically designed to display the detailed fuzzy inference process 
    (rule evaluations, cuts, and final aggregation) generated by the `FuzzyRenderThread`.
    It also includes a built-in navigation toolbar for zooming and panning.

    Attributes:
        layout (QVBoxLayout): The main vertical layout containing the toolbar and canvas.
        canvas (FigureCanvas): The PyQt-compatible canvas that renders the provided Matplotlib figure.
        toolbar (NavigationToolbar): The interactive toolbar provided by Matplotlib.
    """

    def __init__(self, fig, parent=None):
        """
        Initializes the 2D viewer, configures the Matplotlib canvas with the given figure, 
        and sets up the user interface layout.

        Args:
            fig (matplotlib.figure.Figure): The pre-rendered Matplotlib figure containing 
                                            the fuzzy inference subplots.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Initialize the canvas with the pre-constructed figure
        self.canvas = FigureCanvas(fig)
        
        # Add and style the Matplotlib navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #2d2d2d; color: white;")

        # Assemble the layout
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
        # Force an initial draw to render the graphs
        self.canvas.draw()

class FuzzyRenderThread(QThread):
    """
    A background worker thread that computes and generates 2D Matplotlib figures 
    representing the step-by-step fuzzy inference process. It handles both Type-1 
    and Type-2 fuzzy sets, evaluating Mamdani and Sugeno inference methods.

    Attributes:
        signal_finished (pyqtSignal): Signal emitted when the computation is complete, 
                                      carrying a list of tuples containing the system ID 
                                      and its corresponding Matplotlib Figure.
        data (dict): A dictionary containing all the parsed CLIPS facts needed for 
                     rendering (rule outputs, configurations, variables, sets, etc.).
    """
    
    signal_finished = pyqtSignal(list) 

    def __init__(self, data):
        """
        Initializes the rendering thread with the necessary fuzzy engine data.

        Args:
            data (dict): Dictionary containing the memory state of the fuzzy engine.
        """
        super().__init__()
        self.data = data

    def _eval_mf(self, mf_func, x, params):
        """
        Mathematically evaluates a fuzzy membership function over a given numerical domain.

        Args:
            mf_func (str): The name of the membership function (e.g., 'mf-triangular').
            x (numpy.ndarray): The x-axis array representing the variable's universe of discourse.
            params (list of float): The mathematical parameters defining the shape of the function.

        Returns:
            numpy.ndarray: An array of truth values (y-axis) corresponding to the x-axis domain,
                           or None if the function type is not supported.
        """
        p = [float(v) for v in params]
        y = np.zeros_like(x)
        if mf_func == "mf-triangular" and len(p) >= 3:
            a, b, c = p[:3]
            idx1 = (x > a) & (x < b); y[idx1] = (x[idx1] - a) / (b - a) if b > a else 0
            y[x == b] = 1.0
            idx2 = (x > b) & (x < c); y[idx2] = (c - x[idx2]) / (c - b) if c > b else 0
        elif mf_func == "mf-trapezoidal" and len(p) >= 4:
            a, b, c, d = p[:4]
            idx1 = (x > a) & (x < b); y[idx1] = (x[idx1] - a) / (b - a) if b > a else 0
            y[(x >= b) & (x <= c)] = 1.0
            idx2 = (x > c) & (x < d); y[idx2] = (d - x[idx2]) / (d - c) if d > c else 0
        elif mf_func == "mf-gaussian" and len(p) >= 2:
            m, k = p[:2]
            y = np.exp(-((x-m)**2) / (2 * k**2 + 1e-9))
        elif mf_func == "mf-gamma" and len(p) >= 2:
            a, m = p[:2]
            y[x >= m] = 1.0
            idx = (x > a) & (x < m); y[idx] = (x[idx] - a) / (m - a) if m > a else 0
        elif mf_func in ["mf-z", "mf-l"] and len(p) >= 2:
            a, c = p[:2]
            y[x <= a] = 1.0
            idx = (x > a) & (x < c); y[idx] = (c - x[idx]) / (c - a) if c > a else 0
        elif mf_func in ["mf-s"] and len(p) >= 2:
            a, c = p[:2]
            y[x >= c] = 1.0
            idx = (x > a) & (x < c); y[idx] = (x[idx] - a) / (c - a) if c > a else 0
        else:
            return None
        return y

    def run(self):
        """
        Executes the main routine of the thread. It parses the active rules, applies 
        the crisp inputs to the antecedent plots, calculates the degree of fulfillment 
        (strength) for the consequents, and builds the final aggregation plot.
        Emits the generated matplotlib figures once completed.
        """
        is_dark = self.data.get('modo_oscuro', True)
        bg_fig = '#1a1a1a' if is_dark else '#ffffff'
        bg_ax = '#1e1e1e' if is_dark else '#f9fafb'
        fg_text = '#d4d4d4' if is_dark else '#374151'
        grid_color = '#3d3d3d' if is_dark else '#e5e7eb'

        rule_outputs = self.data['rule_outputs']
        sys_configs = self.data['sys_configs']
        fuzzy_vars = self.data['fuzzy_vars']
        fuzzy_sets = self.data['fuzzy_sets']
        crisp_inputs = self.data['crisp_inputs']
        sys_outputs = self.data['sys_outputs']
        
        rules_by_sys = {}
        for r in rule_outputs:
            sid = r["system-id"]
            if sid not in rules_by_sys: rules_by_sys[sid] = []
            rules_by_sys[sid].append(r)
            
        figure_results = []

        for sys_id, sys_rules in rules_by_sys.items():
            config = sys_configs.get(sys_id)
            if not config: continue
            
            is_sugeno = (config["method-type"] == "sugeno")
            is_type2 = (config["mf-type"] == 2)
            
            inputs_used = []
            for r in sys_rules:
                ants = r["antecedents"]
                for i in range(0, len(ants), 2):
                    if ants[i] not in inputs_used: inputs_used.append(ants[i])
                        
            out_var = sys_rules[0]["var-name"]
            
            fvar_out_global = fuzzy_vars.get(out_var)
            if fvar_out_global:
                vmin_g, vmax_g = fvar_out_global["min"], fvar_out_global["max"]
                x_agg_axis = np.linspace(vmin_g, vmax_g, 200)
                y_agg = np.zeros_like(x_agg_axis)
                y_agg_l = np.zeros_like(x_agg_axis)
                y_agg_u = np.zeros_like(x_agg_axis)
            else:
                x_agg_axis = None
            
            n_rows = len(sys_rules) + 1 
            n_cols = len(inputs_used) + 1  
            
            fig = Figure(figsize=(max(10, n_cols * 3.5), max(8, n_rows * 2.5)), dpi=100)
            fig.patch.set_facecolor('#1a1a1a')
            axes = fig.subplots(n_rows, n_cols, squeeze=False)
            fig.subplots_adjust(hspace=0.6, wspace=0.4, left=0.05, right=0.95, top=0.92, bottom=0.08)
            
            # title_text = f"Fuzzy Inference: {sys_id} ({config['method-type'].upper()} Type {config['mf-type']})"
            fig.suptitle("", color="#a855f7", fontsize=14, fontweight='bold')
            
            for ax in axes.flat:
                ax.set_facecolor('#1e1e1e')
                ax.tick_params(colors='#858585', labelsize=8)
                for spine in ax.spines.values(): spine.set_color('#3d3d3d')
            
            for r_idx, rule in enumerate(sys_rules):
                ants = rule["antecedents"]
                pairs = {ants[k]: ants[k+1] for k in range(0, len(ants), 2)}
                
                for c_idx, var_in in enumerate(inputs_used):
                    ax = axes[r_idx, c_idx]
                    if r_idx == 0: ax.set_title(var_in, color="#d4d4d4", fontsize=10)
                    
                    if var_in in pairs:
                        lbl = pairs[var_in]
                        fvar = fuzzy_vars.get(var_in)
                        fset = fuzzy_sets.get(var_in, {}).get(lbl)
                        
                        if fvar and fset:
                            vmin, vmax = fvar["min"], fvar["max"]
                            x = np.linspace(vmin, vmax, 200)
                            input_val = crisp_inputs.get(var_in, None)
                            
                            if not is_type2:
                                y = self._eval_mf(fset["mf"], x, fset["params"])

                                if y is None:
                                    ax.text(0.5, 0.5, "[Custom MF]", color="#ef4444", 
                                            ha='center', va='center', transform=ax.transAxes, fontsize=8)
                                    continue 

                                ax.plot(x, y, color="#3b82f6", lw=1.5)
                                if input_val is not None:
                                    ax.axvline(input_val, color="#ef4444", lw=2)
                                    mu_cut = np.interp(input_val, x, y)
                                    ax.fill_between(x, 0, np.minimum(y, mu_cut), color="#1d4ed8", alpha=0.5)
                            else:
                                y_l = self._eval_mf(fset["l-mf"], x, fset["l-params"])
                                y_u = self._eval_mf(fset["u-mf"], x, fset["u-params"])
                                ax.plot(x, y_u, color="#3b82f6", lw=1, linestyle='--')
                                ax.plot(x, y_l, color="#3b82f6", lw=1.5)
                                ax.fill_between(x, y_l, y_u, color="#3b82f6", alpha=0.2)
                                
                                if input_val is not None:
                                    ax.axvline(input_val, color="#ef4444", lw=2)
                                    mu_u = np.interp(input_val, x, y_u)
                                    y_top = np.minimum(y_u, mu_u)
                                    ax.fill_between(x, y_l, y_top, where=(y_top > y_l), color="#1d4ed8", alpha=0.6)
                            
                            ax.set_ylim(0, 1.05); ax.set_xlim(vmin, vmax)
                            ax.text(0.05, 0.85, f"'{lbl}'", transform=ax.transAxes, color="#d4d4d4", fontsize=9, 
                                    bbox=dict(facecolor='#1e1e1e', alpha=0.8, edgecolor='none', pad=2))
                    else:
                        ax.axis('off')
                        
                ax_out = axes[r_idx, -1]
                if r_idx == 0: ax_out.set_title(f"{out_var} (Output)", color="#f97316", fontsize=10, fontweight='bold')
                
                lbl_out = rule["label"]
                ax_out.text(0.95, 0.85, f"R: {rule['rule-name']}", transform=ax_out.transAxes, 
                            color="#d4d4d4", fontsize=9, ha='right', 
                            bbox=dict(facecolor='#1e1e1e', alpha=0.8, edgecolor='none', pad=2))
                
                if fvar_out_global:
                    vmin, vmax = fvar_out_global["min"], fvar_out_global["max"]
                    x = np.linspace(vmin, vmax, 200)
                    ax_out.set_xlim(vmin, vmax)
                    
                    if is_sugeno:
                        y_val = rule.get("y-value", 0.0)
                        if not is_type2:
                            w = rule.get("strength", 0.0)
                            ax_out.stem([y_val], [w], linefmt="#f97316", markerfmt="o", basefmt=" ")
                            ax_out.text(y_val, min(w + 0.12, 1.15), f"y={y_val:.2f}", 
                                        color="#f97316", ha='center', fontsize=9, fontweight='bold',
                                        bbox=dict(facecolor='#1e1e1e', alpha=0.8, edgecolor='none', pad=1))
                        else:
                            w_l = rule.get("l-strength", 0.0)
                            w_u = rule.get("u-strength", 0.0)
                            ax_out.vlines(y_val, 0, w_u, color="#f97316", lw=2, linestyle='--')
                            ax_out.vlines(y_val, 0, w_l, color="#f97316", lw=4)
                            ax_out.text(y_val, min(w_u + 0.12, 1.15), f"y={y_val:.2f}", 
                                        color="#f97316", ha='center', fontsize=9, fontweight='bold',
                                        bbox=dict(facecolor='#1e1e1e', alpha=0.8, edgecolor='none', pad=1))
                        ax_out.set_ylim(0, 1.25) 
                        
                    else:
                        fset_out = fuzzy_sets.get(out_var, {}).get(lbl_out)
                        if fset_out:
                            if not is_type2:
                                y = self._eval_mf(fset_out["mf"], x, fset_out["params"])
                                w = rule.get("strength", 0.0)
                                ax_out.plot(x, y, color="#f97316", lw=1, linestyle=':')
                                y_cut = np.minimum(y, w)
                                ax_out.fill_between(x, 0, y_cut, color="#c2410c", alpha=0.7)
                                if x_agg_axis is not None: y_agg = np.maximum(y_agg, y_cut)
                            else:
                                y_l = self._eval_mf(fset_out["l-mf"], x, fset_out["l-params"])
                                y_u = self._eval_mf(fset_out["u-mf"], x, fset_out["u-params"])
                                w_u = rule.get("u-strength", 0.0)
                                w_l = rule.get("l-strength", 0.0)
                                ax_out.plot(x, y_u, color="#f97316", lw=1, linestyle='--')
                                ax_out.plot(x, y_l, color="#f97316", lw=1.5)
                                ax_out.fill_between(x, y_l, y_u, color="#f97316", alpha=0.1)
                                
                                y_top = np.minimum(y_u, w_u)
                                y_bot = np.minimum(y_l, w_l)
                                ax_out.fill_between(x, y_l, y_top, where=(y_top > y_l), color="#c2410c", alpha=0.7)
                                
                                if x_agg_axis is not None:
                                    y_agg_l = np.maximum(y_agg_l, y_bot)
                                    y_agg_u = np.maximum(y_agg_u, y_top)
                            ax_out.set_ylim(0, 1.05)

            for c_idx in range(n_cols - 1): axes[-1, c_idx].axis('off')
            ax_agg = axes[-1, -1]
            ax_agg.spines['bottom'].set_color('#22c55e')
            
            final_val = sys_outputs.get(out_var)
            if final_val is not None and fvar_out_global:
                ax_agg.set_title(f"Result: {final_val:.3f}", color="#22c55e", fontsize=11, fontweight='bold')
                vmin, vmax = fvar_out_global["min"], fvar_out_global["max"]
                ax_agg.set_xlim(vmin, vmax); ax_agg.set_ylim(0, 1.05)
                
                if not is_sugeno and x_agg_axis is not None:
                    if not is_type2:
                        ax_agg.fill_between(x_agg_axis, 0, y_agg, color="#c2410c", alpha=0.7)
                        ax_agg.plot(x_agg_axis, y_agg, color="#f97316", lw=1.5)
                    else:
                        ax_agg.fill_between(x_agg_axis, y_agg_l, y_agg_u, where=(y_agg_u > y_agg_l), color="#c2410c", alpha=0.7)
                        ax_agg.plot(x_agg_axis, y_agg_u, color="#f97316", lw=1.5, linestyle='--')
                        ax_agg.plot(x_agg_axis, y_agg_l, color="#f97316", lw=1.5)
                
                ax_agg.axvline(final_val, color="#22c55e", lw=4)
            else:
                ax_agg.set_title("Defuzzified Result", color="#22c55e", fontsize=10, fontweight='bold')
            
            figure_results.append((sys_id, fig))

        self.signal_finished.emit(figure_results)

class InferenceView(QWidget):
    """
    A UI container widget that manages the generation and display of 2D fuzzy inference graphs.
    It scrapes the CLIPS memory for executed rule outputs and dispatches a background
    thread to process the complex Matplotlib drawings, displaying the results in interactive tabs.

    Attributes:
        layout (QVBoxLayout): The main layout of the widget.
        tabs (QTabWidget): The tab container holding the generated 2D viewer instances.
        render_thread (FuzzyRenderThread): The background worker thread used to plot the graphs.
    """

    def __init__(self, parent=None):
        """
        Initializes the inference view, configuring the layout and custom tab styling.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0px; }
            QTabBar::tab { background: #2d2d2d; color: #858585; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;}
            QTabBar::tab:selected { background: #007acc; color: white; font-weight: bold; }
            QTabBar::tab:hover:!selected { background: #3d3d3d; }
        """)
        
        self.layout.addWidget(self.tabs)
        self.setStyleSheet("background-color: #1a1a1a; color: #d4d4d4;")
        self.render_thread = None 

    def _get_slot(self, fact, slot_name, default=0.0):
        """
        Safely retrieves and converts a specific slot's value from a CLIPS fact to a float.

        Args:
            fact (clips.Fact): The CLIPS fact to query.
            slot_name (str): The name of the slot to retrieve.
            default (float, optional): The fallback value if extraction fails. Defaults to 0.0.

        Returns:
            float: The extracted numerical value, or the default value on error.
        """
        try: return float(fact[slot_name]) if fact[slot_name] is not None else default
        except: return default

    def update_diagram(self, env):
        """
        Gathers all required facts (systems, variables, fuzzy sets, inputs, and rule outputs)
        from the CLIPS environment, packages them into a structured dictionary, and starts
        the background rendering thread to generate the inference plots.

        Args:
            env (clips.Environment): The active CLIPS environment containing the execution facts.
        """
        # Clear existing tabs to free up memory before generating new graphs
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()
            
        self.tabs.addTab(QWidget(), "⏳ Generating inference graphs...")
            
        data = {
            'rule_outputs': [], 'sys_configs': {}, 'fuzzy_vars': {},
            'fuzzy_sets': {}, 'crisp_inputs': {}, 'sys_outputs': {}
        }

        # Check parent IDE settings for dark mode toggle
        main_ide = self.parent().parent() if self.parent() else None
        if hasattr(main_ide, 'main_menu'):
            data['modo_oscuro'] = main_ide.main_menu.action_theme.isChecked()
        else:
            data['modo_oscuro'] = True
        
        # Scrape facts from memory
        for f in env.facts():
            t = f.template.name
            if t == "FuzzyRuleOutput": 
                data['rule_outputs'].append({
                    "system-id": str(f["system-id"]),
                    "var-name": str(f["var-name"]),
                    "rule-name": str(f["rule-name"]),
                    "label": str(f["label"]),
                    "antecedents": [str(x) for x in f["antecedents"]],
                    "strength": self._get_slot(f, "strength"),
                    "l-strength": self._get_slot(f, "l-strength"),
                    "u-strength": self._get_slot(f, "u-strength"),
                    "y-value": self._get_slot(f, "y-value")
                })
            elif t == "FuzzySystemConfig": 
                data['sys_configs'][str(f["id"])] = {
                    "method-type": str(f["method-type"]),
                    "mf-type": int(f["mf-type"])
                }
            elif t == "FuzzyVar": 
                data['fuzzy_vars'][str(f["name"])] = {
                    "min": float(f["min"]), "max": float(f["max"])
                }
            elif t == "FuzzySet": 
                vname = str(f["var-name"])
                if vname not in data['fuzzy_sets']: data['fuzzy_sets'][vname] = {}
                data['fuzzy_sets'][vname][str(f["label"])] = {
                    "mf": str(f["mf"]),
                    "params": [float(x) for x in f["params"]] if f["params"] else [],
                    "l-mf": str(f["l-mf"]) if f["l-mf"] else "",
                    "l-params": [float(x) for x in f["l-params"]] if f["l-params"] else [],
                    "u-mf": str(f["u-mf"]) if f["u-mf"] else "",
                    "u-params": [float(x) for x in f["u-params"]] if f["u-params"] else []
                }
            elif t in ["CrispInput", "FuzzyInput"]: 
                val = f["value"]
                data['crisp_inputs'][str(f["var-name"])] = float(val) if val is not None else 0.0
            elif t == "SystemOutput": 
                data['sys_outputs'][str(f["var-name"])] = float(f["value"])
                
        if not data['rule_outputs']:
            self.tabs.clear()
            return
            
        # Dispatch the background thread
        self.render_thread = FuzzyRenderThread(data)
        self.render_thread.signal_finished.connect(self._show_2d_tabs)
        self.render_thread.start()
        
    def _show_2d_tabs(self, results):
        """
        Callback invoked when the background render thread finishes. It instantiates
        a Matplotlib2DViewer for each generated figure and adds it to the tab widget.

        Args:
            results (list of tuple): A list of (sys_id, figure) pairs.
        """
        self.tabs.clear() 
        
        for sys_id, fig in results:
            viewer = Matplotlib2DViewer(fig)
            self.tabs.addTab(viewer, f"System: {sys_id}")
