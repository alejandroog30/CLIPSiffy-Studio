import sys
import os
os.environ["QT_API"] = "pyqt6"
import clips
import shutil
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
import ctypes

import qtvscodestyle as qtvsc

from PyQt6.QtWidgets import (
    QApplication, QLineEdit, QMainWindow, QDockWidget, QFileDialog,
    QTabWidget, QMessageBox, QInputDialog, QLabel,
    QToolBar
)

from PyQt6.QtCore import Qt, QDir, QTimer, QSettings

from PyQt6.QtGui import QAction, QTextCursor, QIcon

from app.ui_menu import MainMenu
from app.ui_editor import CLIPSEditor
from app.ui_console import CLIPSConsole, CLIPSRouter
from app.ui_explorer import FileExplorer
from app.ui_panels import FuzzyFactsPanel, CLIPSFactsPanel, CLIPSRulesPanel, CLIPSAgendaPanel
from app.ui_builders import FuzzyBuilderPanel, EnvironmentBuilderPanel
from app.ui_diagrams import DiagramView
from app.ui_plots import InferenceView, Surface3DView, SimulationGraphView, StateSpaceView
from app.core_threads import CLIPSRunThread

import tempfile
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ClipsIDE(QMainWindow):
    """
    The main window and central orchestrator of the CLIPS IDE application.
    It integrates the code editor, CLIPS engine environment, graphical viewers,
    side panels, and system menus into a cohesive PyQt6 application.

    Attributes:
        env (clips.Environment): The active CLIPS expert system engine instance.
        router (CLIPSRouter): The router redirecting CLIPS prints to the IDE console.
    """

    def __init__(self):
        """Initializes the main window, instantiates all dockable panels, and configures signal routing."""
        super().__init__()
        self.setWindowTitle("CLIPSiffy Studio")

        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.icon_path = os.path.join(base_dir, "images", "icon.svg")
        self.setWindowIcon(QIcon(self.icon_path))
        
        self.last_search = ""
        self.run_thread = None

        self.dock_editor = QDockWidget("CODE VIEW", self)
        self.dock_editor.setObjectName("DockEditor")
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)
        self.dock_editor.setWidget(self.editor_tabs)
        
        self.dock_diagram = QDockWidget("BLOCK VIEW", self)
        self.dock_diagram.setObjectName("DockDiagram")
        self.diagram_view = DiagramView()
        self.dock_diagram.setWidget(self.diagram_view)

        self.dock_inference = QDockWidget("FUZZY INFERENCE", self)
        self.dock_inference.setObjectName("DockInference")
        self.inference_view = InferenceView()
        self.dock_inference.setWidget(self.inference_view)

        self.dock_surface = QDockWidget("3D CONTROL SURFACE", self)
        self.dock_surface.setObjectName("DockSurface")
        self.surface_view = Surface3DView()
        self.dock_surface.setWidget(self.surface_view)
        self.dock_surface.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_surface)
        self.dock_surface.setFloating(True)
        self.dock_surface.hide()

        self.dock_sim_graph = SimulationGraphView("SIMULATION DASHBOARD", self)
        self.dock_sim_graph.setObjectName("DockSimGraph")
        self.dock_sim_graph.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_sim_graph)
        self.dock_sim_graph.setFloating(False)
        self.dock_sim_graph.hide()

        self.dock_state_space = StateSpaceView("STATE SPACE", self)
        self.dock_state_space.setObjectName("DockStateSpace")
        self.dock_state_space.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_state_space)
        self.dock_state_space.setFloating(False)
        self.dock_state_space.hide()
        
        self.dock_inference.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inference)
        self.dock_inference.setFloating(True)
        self.dock_inference.hide()

        self.explorer = FileExplorer("EXPLORER", self)
        self.explorer.setObjectName("PanelExplorer")

        self.panel_fuzzy = FuzzyFactsPanel("FUZZY FACTS", self)
        self.panel_fuzzy.setObjectName("PanelFuzzyFacts")

        self.panel_facts = CLIPSFactsPanel("FACTS", self)
        self.panel_facts.setObjectName("PanelFacts")

        self.panel_rules = CLIPSRulesPanel("RULES", self)
        self.panel_rules.setObjectName("PanelRules")

        self.panel_agenda = CLIPSAgendaPanel("AGENDA", self)
        self.panel_agenda.setObjectName("PanelAgenda")

        self.panel_builder = FuzzyBuilderPanel("FUZZY BUILDER", self)
        self.panel_builder.setObjectName("PanelFuzzyBuilder")

        self.panel_environment = EnvironmentBuilderPanel("ENVIRONMENT BUILDER", self)
        self.panel_environment.setObjectName("PanelEnvBuilder")
        
        self.console = CLIPSConsole("TERMINAL / CLIPS OUTPUT", self)
        self.console.setObjectName("PanelConsole")

        self._create_activity_bar()

        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
        self.apply_default_layout()
        
        QTimer.singleShot(100, self._adjust_initial_sizes)

        self.main_menu = MainMenu()
        self.setMenuBar(self.main_menu)
        
        view_actions = [
            self.explorer.toggleViewAction(),
            self.panel_fuzzy.toggleViewAction(),
            self.console.toggleViewAction(),
            self.dock_editor.toggleViewAction(),
            self.dock_diagram.toggleViewAction(),
            self.panel_builder.toggleViewAction(),
            self.panel_environment.toggleViewAction(),
            self.dock_inference.toggleViewAction(),
            self.dock_surface.toggleViewAction(),
            self.panel_agenda.toggleViewAction(),
            self.dock_sim_graph.toggleViewAction(),
            self.dock_state_space.toggleViewAction()
        ]
        self.main_menu.add_view_actions(view_actions)

        self.statusBar().setStyleSheet("background-color: #007acc; color: white; font-weight: bold;")
        self.statusBar().setSizeGripEnabled(True)
        
        self.lbl_memory_status = QLabel(" Facts: 0 | Rules: 0 ")
        self.lbl_memory_status.setStyleSheet("color: white; padding-right: 10px;")
        
        self.statusBar().addPermanentWidget(self.lbl_memory_status)

        self.env = clips.Environment()
        self.router = CLIPSRouter(self.console)
        self.env.add_router(self.router)

        self.panel_builder.signal_insert_fact.connect(self.logic_live_command)
        self.panel_environment.signal_insert_fact.connect(self.logic_live_command)
        
        self.console_font_size = 14 
        
        self.main_menu.signal_zoom_in.connect(self.logic_zoom_in)
        self.main_menu.signal_zoom_out.connect(self.logic_zoom_out)
        self.main_menu.signal_toggle_theme.connect(self.logic_toggle_theme)

        self.main_menu.signal_default_layout.connect(self.apply_default_layout)
        self.main_menu.signal_simple_layout.connect(self.apply_simple_layout)

        self.main_menu.signal_docs_fuzzy.connect(self.logic_docs_fuzzy)
        self.main_menu.signal_docs_ide.connect(self.logic_docs_ide)

        self.main_menu.signal_toggle_fuzzy_mode.connect(self.logic_toggle_fuzzy_mode)
        self.main_menu.signal_toggle_diagram.connect(self.logic_toggle_diagram)
        self.main_menu.signal_toggle_graphs.connect(self.logic_toggle_graphs)
        self.main_menu.signal_toggle_3d_surface.connect(self.logic_toggle_3d_surface)
        self.main_menu.signal_toggle_sim_graph.connect(self.logic_toggle_sim_graph)
        self.main_menu.signal_toggle_state_space.connect(self.logic_toggle_state_space)

        self.main_menu.signal_undo.connect(self.logic_undo)
        self.main_menu.signal_redo.connect(self.logic_redo)
        self.main_menu.signal_cut.connect(self.logic_cut)
        self.main_menu.signal_copy.connect(self.logic_copy)
        self.main_menu.signal_paste.connect(self.logic_paste)
        self.main_menu.signal_find.connect(self.logic_find)
        self.main_menu.signal_find_next.connect(self.logic_find_next)
        self.main_menu.signal_toggle_comment.connect(self.logic_toggle_comment)

        self.main_menu.signal_new_file.connect(self.logic_new_file)
        self.main_menu.signal_load_example.connect(self.logic_load_example)
        self.main_menu.signal_export_fuzzy.connect(self.logic_export_fuzzy)
        self.main_menu.signal_encrypt_file.connect(self.logic_encrypt_file)
        self.main_menu.signal_open_file.connect(self.logic_open_file)
        
        self.main_menu.signal_open_folder.connect(self.explorer._select_folder) 
        
        self.main_menu.signal_save.connect(self.logic_save)
        self.main_menu.signal_save_as.connect(self.logic_save_as)
        
        self.main_menu.signal_exit.connect(self.close)

        self.main_menu.signal_watch_facts.connect(self.logic_watch_facts)
        self.main_menu.signal_watch_rules.connect(self.logic_watch_rules)
        self.main_menu.signal_watch_activations.connect(self.logic_watch_activations)

        self.main_menu.signal_load.connect(self.logic_load)
        self.main_menu.signal_load_files.connect(self.logic_load_files)
        self.main_menu.signal_reset.connect(self.logic_reset)
        self.main_menu.signal_run.connect(self.logic_run)
        self.main_menu.signal_step.connect(self.logic_step)
        self.main_menu.signal_clear.connect(self.logic_clear)
        self.main_menu.signal_stop.connect(self.logic_stop)

        self.console.signal_command.connect(self.logic_live_command)
        
        self.explorer.signal_file_double_click.connect(self.open_file_in_tab)
        self.explorer.signal_folder_changed.connect(self.notify_directory_change)
        self.explorer.signal_rename_request.connect(self.logic_rename)
        self.explorer.signal_delete_request.connect(self.logic_delete)


        self.docs_port = self._start_docs_server()

        self._load_workspace()

    def _create_activity_bar(self):
        """Creates the vertical icon activity bar on the left to switch side panels."""
        self.activity_bar = QToolBar("Activity Bar")
        self.activity_bar.setObjectName("ToolBarActivity")
        self.activity_bar.setMovable(False) 
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.activity_bar)
        
        self.activity_bar.setStyleSheet("""
            QToolBar { background-color: #252526; border-right: 1px solid #333333; spacing: 5px; padding-top: 10px; }
            QToolButton { color: #858585; font-size: 20px; padding: 12px; border: none; }
            QToolButton:hover { color: #ffffff; background-color: #333333; }
        """)

        self.side_panels = [self.explorer, self.panel_builder, self.panel_environment, self.panel_fuzzy, self.panel_facts, self.panel_rules, self.panel_agenda]
        self.panel_widths = {}

        act_explorer = QAction("", self)
        act_explorer.setToolTip("Explorer")
        act_explorer.setIcon(qtvsc.theme_icon(qtvsc.Vsc.FILE, "icon.foreground"))
        act_explorer.triggered.connect(lambda: self.show_side_panel(self.explorer))
        self.activity_bar.addAction(act_explorer)

        self.act_builder = QAction("", self)
        self.act_builder.setToolTip("Fuzzy Builder")
        self.act_builder.setIcon(qtvsc.theme_icon(qtvsc.Vsc.EXTENSIONS, "icon.foreground"))
        self.act_builder.triggered.connect(lambda: self.show_side_panel(self.panel_builder))
        self.activity_bar.addAction(self.act_builder)

        self.act_environment = QAction("", self)
        self.act_environment.setToolTip("Environment Builder")
        self.act_environment.setIcon(qtvsc.theme_icon(qtvsc.Vsc.GLOBE, "icon.foreground")) 
        self.act_environment.triggered.connect(lambda: self.show_side_panel(self.panel_environment))
        self.activity_bar.addAction(self.act_environment)

        self.act_fuzzy = QAction("", self)
        self.act_fuzzy.setToolTip("Fuzzy Facts")
        self.act_fuzzy.setIcon(qtvsc.theme_icon(qtvsc.Vsc.GRAPH, "icon.foreground"))
        self.act_fuzzy.triggered.connect(lambda: self.show_side_panel(self.panel_fuzzy))
        self.activity_bar.addAction(self.act_fuzzy)

        act_facts = QAction("", self)
        act_facts.setToolTip("Facts")
        act_facts.setIcon(qtvsc.theme_icon(qtvsc.Vsc.HISTORY, "icon.foreground"))
        act_facts.triggered.connect(lambda: self.show_side_panel(self.panel_facts))
        self.activity_bar.addAction(act_facts)

        act_rules = QAction("", self)
        act_rules.setToolTip("Rules")
        act_rules.setIcon(qtvsc.theme_icon(qtvsc.Vsc.ARROW_RIGHT, "icon.foreground"))
        act_rules.triggered.connect(lambda: self.show_side_panel(self.panel_rules))
        self.activity_bar.addAction(act_rules)

        act_agenda = QAction("", self)
        act_agenda.setToolTip("Agenda")
        act_agenda.setIcon(qtvsc.theme_icon(qtvsc.Vsc.LIST_SELECTION, "icon.foreground"))
        act_agenda.triggered.connect(lambda: self.show_side_panel(self.panel_agenda))
        self.activity_bar.addAction(act_agenda)

    def show_side_panel(self, panel_to_show):
        """Shows the selected panel and hides others in the same dock area."""
        current_visible_panel = None
        for panel in self.side_panels:
            if panel.isVisible() and not panel.isFloating() and self.dockWidgetArea(panel) == Qt.DockWidgetArea.LeftDockWidgetArea:
                current_visible_panel = panel
                if panel.width() > 50:
                    self.panel_widths[panel] = panel.width()
                panel.hide()

        if panel_to_show.isFloating() or self.dockWidgetArea(panel_to_show) != Qt.DockWidgetArea.LeftDockWidgetArea:
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, panel_to_show)
            panel_to_show.setFloating(False)
            current_visible_panel = None 

        if current_visible_panel == panel_to_show: return

        panel_to_show.show()
        panel_to_show.raise_()
        restore_width = self.panel_widths.get(panel_to_show, 250)
        panel_to_show.setMinimumWidth(restore_width)
        panel_to_show.setMaximumWidth(restore_width)
        QTimer.singleShot(50, lambda: self._free_panel_width(panel_to_show))

    def _free_panel_width(self, panel):
        """Releases the rigid sizing limits applied to the dock panel."""
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(16777215) 

    def logic_zoom_in(self):
        """Increases text size across editors and console."""
        for i in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(i)
            if isinstance(widget, CLIPSEditor):
                widget.zoomIn(2) 
                widget.update_margin_width(0) 
        self.console.text_area.zoomIn(2)

    def logic_zoom_out(self):
        """Decreases text size across editors and console."""
        for i in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(i)
            if isinstance(widget, CLIPSEditor):
                widget.zoomOut(2) 
                widget.update_margin_width(0) 
        self.console.text_area.zoomOut(2)

    def _start_docs_server(self):
        """Spawns an internal HTTP server on a separate thread to serve static documentation pages."""
        if self.main_menu.action_toggle_fuzzy.isChecked():
            if getattr(sys, 'frozen', False): base_dir = sys._MEIPASS 
            else: base_dir = os.path.dirname(os.path.abspath(__file__))
        
        class SilentHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=base_dir, **kwargs)
            def log_message(self, format, *args): pass
        
        server = ThreadingTCPServer(('127.0.0.1', 0), SilentHandler)
        port = server.server_address[1] 
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return port

    def _manage_affected_tabs(self, target_path, is_folder):
        """Checks and potentially closes tabs corresponding to a deleted or renamed file/folder."""
        norm_target = os.path.normpath(target_path)
        for i in range(self.editor_tabs.count() - 1, -1, -1):
            tab_path = self.editor_tabs.tabToolTip(i)
            if not tab_path: continue
            norm_tab = os.path.normpath(tab_path)
            affected = False
            if is_folder:
                if norm_tab.startswith(norm_target + os.sep) or norm_tab == norm_target: affected = True
            else:
                if norm_tab == norm_target: affected = True
            if affected:
                self.editor_tabs.setCurrentIndex(i)
                if not self.close_tab(i): return False
        return True

    def logic_rename(self, old_path, new_path):
        """Handles renaming a file/folder physically and updating the IDE."""
        is_folder = os.path.isdir(old_path)
        if self._manage_affected_tabs(old_path, is_folder):
            try:
                os.rename(old_path, new_path)
                self.console.write(f"\n> Renamed: '{os.path.basename(old_path)}' to '{os.path.basename(new_path)}'")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename:\n{e}")

    def logic_delete(self, path, is_folder):
        """Handles physically deleting a file/folder and updating the IDE."""
        if self._manage_affected_tabs(path, is_folder):
            try:
                if is_folder: shutil.rmtree(path)
                else: os.remove(path)
                self.console.write(f"\n> Permanently deleted: '{os.path.basename(path)}'")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete:\n{e}")

    def notify_directory_change(self, new_path):
        """Logs the user directory change to the console."""
        self.console.write(f"\n> Working directory changed to: {new_path}")

    def apply_default_layout(self):
        """Resets all dock panels to the standard developer arrangement."""
        panels = [self.dock_editor, self.dock_diagram, self.explorer, 
                   self.panel_fuzzy, self.panel_facts, self.panel_rules, self.console,
                   self.panel_builder, self.panel_environment, self.panel_agenda]
        for dock in panels: self.removeDockWidget(dock)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_builder)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_environment)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_fuzzy)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_facts)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_rules)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_agenda)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_editor)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.console)
        self.splitDockWidget(self.dock_editor, self.console, Qt.Orientation.Vertical)
        self.splitDockWidget(self.dock_editor, self.dock_diagram, Qt.Orientation.Horizontal)
        
        self.show_side_panel(self.explorer)
        self.dock_editor.show()
        self.console.show()
        self.dock_diagram.show()
        self.dock_editor.raise_()
        self.resizeDocks([self.explorer, self.dock_editor, self.dock_diagram], [250, 900, 450], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dock_editor, self.console], [650, 200], Qt.Orientation.Vertical)

    def _adjust_initial_sizes(self):
        """Initial resizing of elements after layout population."""
        self.resizeDocks([self.explorer, self.dock_editor, self.dock_diagram], [180, 900, 450], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dock_editor, self.console], [650, 200], Qt.Orientation.Vertical)

    def apply_simple_layout(self):
        """Applies a minimalist layout (only code editor, console, facts, and rules)."""
        panels = [self.dock_editor, self.dock_diagram, self.explorer, 
                   self.panel_fuzzy, self.panel_facts, self.panel_rules, self.console]
        for dock in panels: self.removeDockWidget(dock)

        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dock_editor)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.panel_facts)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.panel_rules)
        self.tabifyDockWidget(self.console, self.panel_facts)
        self.tabifyDockWidget(self.panel_facts, self.panel_rules)
        
        active_panels = [self.dock_editor, self.console, self.panel_facts, self.panel_rules]
        for dock in active_panels: dock.show()
            
        self.explorer.hide()
        self.panel_fuzzy.hide()
        self.dock_diagram.hide()
        
        self.console.raise_() 
        self.resizeDocks([self.dock_editor, self.console], [800, 200], Qt.Orientation.Vertical)

    def logic_toggle_diagram(self, is_active):
        """Displays or hides the block architecture diagram."""
        if is_active:
            if self.main_menu.action_toggle_fuzzy.isChecked():
                self.diagram_view.update_diagram(self.env)
                self.dock_diagram.show()
        else:
            self.diagram_view.scene_obj.clear() 
            self.dock_diagram.hide()

    def logic_toggle_graphs(self, is_active):
        """Displays or hides the 2D fuzzy inference viewer."""
        if is_active:
            if self.main_menu.action_toggle_fuzzy.isChecked(): self.show_graphs_if_available()
        else:
            if hasattr(self, 'dock_inference'): self.dock_inference.hide()

    def logic_toggle_fuzzy_mode(self, is_active):
        """Enables or disables fuzzy-specific UI elements."""
        self.main_menu.action_toggle_graphs.setEnabled(is_active)
        self.main_menu.action_toggle_diagram.setEnabled(is_active)
        
        if hasattr(self.main_menu, 'action_toggle_3d'): 
            self.main_menu.action_toggle_3d.setEnabled(is_active)
            
        if hasattr(self.main_menu, 'action_toggle_sim_graph'):
            self.main_menu.action_toggle_sim_graph.setEnabled(is_active)
        if hasattr(self.main_menu, 'action_toggle_state_space'):
            self.main_menu.action_toggle_state_space.setEnabled(is_active)

        self.act_builder.setVisible(is_active)
        self.act_fuzzy.setVisible(is_active)
        self.act_environment.setVisible(is_active)

        if is_active:
            if self.main_menu.action_toggle_diagram.isChecked(): self.dock_diagram.show()
            if self.main_menu.action_toggle_graphs.isChecked(): self.show_graphs_if_available()
        else:
            self.panel_fuzzy.hide()
            self.panel_builder.hide()
            self.panel_environment.hide()
            self.dock_diagram.hide()
            
            if hasattr(self, 'dock_inference') and self.dock_inference.isVisible(): self.dock_inference.hide()
            if hasattr(self, 'dock_surface') and self.dock_surface.isVisible(): self.dock_surface.hide()
            
            if hasattr(self, 'dock_sim_graph') and self.dock_sim_graph.isVisible(): self.dock_sim_graph.hide()
            if hasattr(self, 'dock_state_space') and self.dock_state_space.isVisible(): self.dock_state_space.hide()

    def show_graphs_if_available(self):
        """Pops up the 2D or 3D views if inference outputs exist in memory."""
        if not self.main_menu.action_toggle_graphs.isChecked(): pass 
        else:
            has_data = False
            for f in self.env.facts():
                if f.template.name == "FuzzyRuleOutput":
                    has_data = True; break
            if has_data:
                self.inference_view.update_diagram(self.env)
                if not self.dock_inference.isVisible():
                    self.dock_inference.setFloating(True)
                    self.dock_inference.resize(1100, 800)
                self.dock_inference.show()
                self.dock_inference.raise_()
        
        if self.main_menu.action_toggle_3d.isChecked():
            self.surface_view.update_diagram(self.env)
            if not self.dock_surface.isVisible():
                self.dock_surface.setFloating(True)
                self.dock_surface.resize(800, 700)
            self.dock_surface.show()
            self.dock_surface.raise_()

        if hasattr(self.main_menu, 'action_toggle_sim_graph') and self.main_menu.action_toggle_sim_graph.isChecked():
            has_history = False
            for f in self.env.facts():
                if f.template.name == "EnvHistory":
                    has_history = True
                    break
            if has_history:
                self.dock_sim_graph.update_plot(self.env)
                if not self.dock_sim_graph.isVisible():
                    self.dock_sim_graph.show()
                    self.dock_sim_graph.raise_()

    def update_memory_views(self):
        """Triggers a data refresh on all memory-monitoring side panels and diagrams."""
        self.panel_fuzzy.update_facts(self.env)
        self.panel_facts.update(self.env)
        self.panel_rules.update(self.env)
        self.panel_agenda.update(self.env)
        
        if self.main_menu.action_toggle_diagram.isChecked(): 
            self.diagram_view.update_diagram(self.env)
            
        if hasattr(self, 'dock_inference') and self.dock_inference.isVisible():
            if self.main_menu.action_toggle_graphs.isChecked(): 
                self.inference_view.update_diagram(self.env)
                
        if hasattr(self, 'dock_sim_graph') and self.dock_sim_graph.isVisible():
            self.dock_sim_graph.update_plot(self.env)

        if hasattr(self, 'dock_state_space') and self.dock_state_space.isVisible():
            self.dock_state_space.update_plot(self.env)
            
        self.update_status_bar()
        self.panel_builder.update_data(self.env)

        if hasattr(self.panel_environment, 'update_data'):
            self.panel_environment.update_data(self.env)

    def update_status_bar(self):
        """Recalculates counts and state machine phase to display in the bottom status bar."""
        try:
            num_facts = 0
            current_state = "STOPPED" 
            for fact in self.env.facts():
                num_facts += 1
                if "CurrentState" in fact.template.name: current_state = str(fact["state"]).upper()
            all_rules = self.env.eval("(get-defrule-list *)")
            num_rules = len(all_rules)
            status_text = f"PHASE: {current_state}  |  Facts: {num_facts}  |  Rules: {num_rules} "
            self.lbl_memory_status.setText(status_text)
        except Exception: pass

    def _mark_modified(self, editor, is_modified):
        """Appends an asterisk (*) to the tab name if the document contains unsaved changes."""
        index = self.editor_tabs.indexOf(editor)
        if index != -1:
            title = self.editor_tabs.tabText(index)
            if is_modified and not title.endswith("*"): self.editor_tabs.setTabText(index, title + "*")
            elif not is_modified and title.endswith("*"): self.editor_tabs.setTabText(index, title[:-1])

    def logic_new_file(self):
        """Creates a new empty editor tab."""
        new_editor = CLIPSEditor()
        new_editor.set_theme(self.main_menu.action_theme.isChecked())
        new_editor.document().modificationChanged.connect(lambda modified, ed=new_editor: self._mark_modified(ed, modified))
        index = self.editor_tabs.addTab(new_editor, "Untitled")
        self.editor_tabs.setTabToolTip(index, "") 
        self.editor_tabs.setCurrentIndex(index)

    def _get_active_editor(self):
        """Returns the currently active text editor widget."""
        current_index = self.editor_tabs.currentIndex()
        if current_index != -1: return self.editor_tabs.widget(current_index)
        return None

    def logic_undo(self):
        editor = self._get_active_editor()
        if editor: editor.undo()

    def logic_redo(self):
        editor = self._get_active_editor()
        if editor: editor.redo()

    def logic_cut(self):
        editor = self._get_active_editor()
        if editor: editor.cut()

    def logic_copy(self):
        editor = self._get_active_editor()
        if editor: editor.copy()

    def logic_paste(self):
        editor = self._get_active_editor()
        if editor: editor.paste()

    def logic_find(self):
        """Opens a prompt dialog to search for text within the current document."""
        editor = self._get_active_editor()
        if not editor: return
        text, ok = QInputDialog.getText(self, "Find", "Search for:", text=self.last_search)
        if ok and text:
            self.last_search = text
            self.execute_search(text)

    def logic_find_next(self):
        """Continues searching for the last queried string."""
        if self.last_search: self.execute_search(self.last_search)
        else: self.logic_find()

    def execute_search(self, text):
        """Locates and highlights the specified text in the editor."""
        editor = self._get_active_editor()
        if not editor: return
        found = editor.find(text)
        if not found:
            response = QMessageBox.question(self, "Find", f"No more matches for '{text}'. Start from the beginning?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if response == QMessageBox.StandardButton.Yes:
                cursor = editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(cursor)
                if not editor.find(text): QMessageBox.information(self, "Find", f"No matches found for '{text}'.")

    def logic_toggle_comment(self):
        """Adds or removes the semicolon (;) comment character to the selected lines."""
        editor = self._get_active_editor()
        if not editor: return
        cursor = editor.textCursor()
        if not cursor.hasSelection(): cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        selected_text = cursor.selectedText()
        lines = selected_text.split('\u2029')
        all_commented = all(line.lstrip().startswith(';') or not line.strip() for line in lines)
        new_lines = []
        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue
            if all_commented: new_lines.append(line.replace(';', '', 1))
            else: new_lines.append(';' + line)
        new_text = '\u2029'.join(new_lines)
        cursor.insertText(new_text)

    def logic_export_fuzzy(self):
        """Extracts fuzzy constructs and rules from memory and writes them into a new file tab."""
        allowed_templates = ["FuzzySystemConfig", "FuzzyVar", "FuzzySet", "CrispInput", "Connection", "LinguisticModifier"]
        exported_text = ";; =========================================\n;; EXPORTED FUZZY CONFIGURATION\n;; =========================================\n\n(deffacts exported-fuzzy-facts\n"
        has_facts = False
        for fact in self.env.facts():
            if fact.template.name in allowed_templates:
                exported_text += f"    {str(fact)}\n"
                has_facts = True
        if not has_facts: exported_text += "    ;; (No facts of the indicated templates were found)\n"
        exported_text += ")\n\n;; =========================================\n;; INFER MODULE RULES\n;; =========================================\n\n"
        try:
            prev_module = str(self.env.eval("(set-current-module INFER)"))
            has_rules = False
            for rule in self.env.rules():
                exported_text += str(rule) + "\n\n"
                has_rules = True
            if not has_rules: exported_text += ";; (No rules found within the INFER module)\n"
            self.env.eval(f"(set-current-module {prev_module})")
        except Exception as e:
            exported_text += f";; (Error accessing the INFER module: {str(e)})\n"
            try: self.env.eval("(set-current-module MAIN)")
            except: pass

        new_editor = CLIPSEditor()
        new_editor.setPlainText(exported_text)
        new_editor.document().setModified(True) 
        new_editor.document().modificationChanged.connect(lambda modified, ed=new_editor: self._mark_modified(ed, modified))
        index = self.editor_tabs.addTab(new_editor, "Fuzzy_Export*")
        self.editor_tabs.setTabToolTip(index, "") 
        self.editor_tabs.setCurrentIndex(index)
        self.console.write("\n> [OK] Configuration successfully exported to a new tab.")

    def _get_encryption_key(self, password: str, salt: bytes) -> bytes:
        """Derives a secure encryption key from a password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def logic_encrypt_file(self):
        """Encrypts a .clp file into a .clpx 'black box' for students."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file to encrypt", "", "CLIPS Files (*.clp)")
        if not file_path: return

        password, ok = QInputDialog.getText(self, "Encrypt", "Set password:", QLineEdit.EchoMode.Password)
        if ok and password:
            try:
                with open(file_path, 'rb') as f: data = f.read()
                salt = os.urandom(16)
                fernet = Fernet(self._get_encryption_key(password, salt))
                encrypted = salt + fernet.encrypt(data)
                
                save_path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Encrypted (*.clpx)")
                if save_path:
                    if not save_path.endswith(".clpx"): save_path += ".clpx"
                    with open(save_path, 'wb') as f: f.write(encrypted)
                    self.console.write(f"\n> [OK] Encrypted: {os.path.basename(save_path)}")
            except Exception as e:
                self.console.write_error(f"\n> [ERROR] Encryption failed: {str(e)}")

    def logic_load_files(self):
        """Loads only selected files (or active tab) without reloading the fuzzy library."""
        file_paths = self.explorer.get_selected()
        if not file_paths:
            current = self._get_active_editor()
            path = self.editor_tabs.tabToolTip(self.editor_tabs.currentIndex()) if current else None
            if path: file_paths = [path]
            else:
                self.console.write("\n> [WARNING] No files selected or saved.")
                return

        self.console.write("\n> Injecting selected files...")
        self._internal_loader(file_paths)
        self.update_memory_views()

    def _internal_loader(self, file_paths):
        """Shared logic to load standard or encrypted files into the engine."""
        for path in file_paths:
            if path.endswith(".clpx"):
                pwd, ok = QInputDialog.getText(self, "Unlock", f"Password for {os.path.basename(path)}:", QLineEdit.EchoMode.Password)
                if not ok or not pwd: continue
                try:
                    with open(path, 'rb') as f: content = f.read()
                    salt, encrypted = content[:16], content[16:]
                    fernet = Fernet(self._get_encryption_key(pwd, salt))
                    decrypted = fernet.decrypt(encrypted)
                    
                    fd, temp_p = tempfile.mkstemp(suffix=".clp")
                    try:
                        with os.fdopen(fd, 'wb') as tmp: tmp.write(decrypted)
                        self.env.load(temp_p)
                        self.console.write(f"  [OK] Encrypted file loaded: {os.path.basename(path)}")
                    finally:
                        if os.path.exists(temp_p): os.remove(temp_p)
                except InvalidToken:
                    self.console.write_error(f"  [ERROR] Wrong password for {os.path.basename(path)}")
                except Exception as e:
                    self.console.write_error(f"  [ERROR] Failed to load {path}: {e}")
            else:
                try:
                    self.env.load(path)
                    self.console.write(f"  [OK] {os.path.basename(path)} loaded.")
                except Exception as e:
                    self.console.write_error(f"  [ERROR] Failed to load {path}: {e}")

    def logic_save(self):
        """Saves the current document to its active disk path."""
        current_index = self.editor_tabs.currentIndex()
        if current_index == -1: return
        file_path = self.editor_tabs.tabToolTip(current_index)
        if not file_path: self.logic_save_as()
        else: self._save_to_path(file_path, current_index)

    def logic_save_as(self):
        """Prompts the user to save the document under a new file path."""
        current_index = self.editor_tabs.currentIndex()
        if current_index == -1: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CLIPS File", "", "CLIPS Files (*.clp);;All Files (*)")
        if file_path:
            if not file_path.endswith(".clp"): file_path += ".clp"
            self._save_to_path(file_path, current_index)

    def _save_to_path(self, path, index):
        """Performs the disk write operation. Returns True on success, False on failure."""
        editor = self.editor_tabs.widget(index)
        code = editor.toPlainText()
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(code)
            editor.document().setModified(False)
            file_name = os.path.basename(path)
            self.editor_tabs.setTabText(index, file_name)
            self.editor_tabs.setTabToolTip(index, path)
            self.console.write(f"> File saved successfully: {path}")
            return True
        except Exception as e:
            self.console.write(f"> [ERROR] Could not save the file: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Could not save the file:\n{str(e)}")
            return False

    def open_file_in_tab(self, file_path):
        """Opens a disk file and loads its contents into a new editor tab."""
        for i in range(self.editor_tabs.count()):
            if self.editor_tabs.tabToolTip(i) == file_path:
                self.editor_tabs.setCurrentIndex(i) 
                return
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            new_editor = CLIPSEditor()
            new_editor.set_theme(self.main_menu.action_theme.isChecked())
            new_editor.setPlainText(content)
            new_editor.document().setModified(False)
            new_editor.document().modificationChanged.connect(lambda modified, ed=new_editor: self._mark_modified(ed, modified))
            file_name = os.path.basename(file_path)
            index = self.editor_tabs.addTab(new_editor, file_name)
            self.editor_tabs.setTabToolTip(index, file_path) 
            self.editor_tabs.setCurrentIndex(index)
            self.console.write(f"\n> File opened: {file_name}")
        except Exception as e:
            self.console.write(f"\n> [ERROR] Could not open file: {str(e)}")

    def close_tab(self, index, is_shutting_down=False):
        """
        Attempts to close an editor tab. Warns if unsaved.
        If is_shutting_down is True, it evaluates the save state but DOES NOT physically remove the tab.
        """
        editor = self.editor_tabs.widget(index)
        if editor.document().isModified():
            file_name = self.editor_tabs.tabText(index).replace("*", "")
            response = QMessageBox.warning(
                self, "Unsaved changes", 
                f"The file '{file_name}' has unsaved changes.\nDo you want to save them before closing?", 
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if response == QMessageBox.StandardButton.Save:
                path = self.editor_tabs.tabToolTip(index)
                if not path: 
                    path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "CLIPS Files (*.clp);;All Files (*)")
                    if not path: return False # User cancelled the dialog
                    if not path.endswith(".clp"): path += ".clp"
                
                # If the save operation fails, abort the tab closure!
                if not self._save_to_path(path, index):
                    return False 
                    
            elif response == QMessageBox.StandardButton.Cancel:
                return False 
        
        # Only remove the tab from the UI if we aren't shutting down the whole app
        if not is_shutting_down:
            self.editor_tabs.removeTab(index)
            
        return True
    
    def _save_workspace(self):
        """
        Saves the current IDE state using QSettings. Includes geometry, open tabs, explorer path, and menu toggles.
        """
        # Updated to match the strings used in _save_workspace
        settings = QSettings("CLIPSiffyTeam", "CLIPSiffy") 
        
        # Load the save toggle preference (True by default on first run).
        save_state_pref = settings.value("save_state_pref", type=bool, defaultValue=True)
        self.main_menu.action_save_state.setChecked(save_state_pref)

        # If the user does NOT want to save, clear the history.
        if not save_state_pref:
            claves_a_borrar = [
                "geometry", "windowState", "explorer_path", "open_tabs", "current_tab_index",
                "toggle_fuzzy", "toggle_graphs", "toggle_diagram", "toggle_3d", 
                "toggle_sim_graph", "toggle_state_space", "watch_facts", "watch_rules", "watch_activations"
            ]
            for key in claves_a_borrar:
                settings.remove(key)
                
            # The theme is saved regardless, as it is a global preference.
            settings.setValue("theme_dark", self.main_menu.action_theme.isChecked())
            return
        
        # Standard save: Window layout and theme.
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("theme_dark", self.main_menu.action_theme.isChecked())
        
        # Save menu toggles state.
        settings.setValue("toggle_fuzzy", self.main_menu.action_toggle_fuzzy.isChecked())
        settings.setValue("toggle_graphs", self.main_menu.action_toggle_graphs.isChecked())
        settings.setValue("toggle_diagram", self.main_menu.action_toggle_diagram.isChecked())
        settings.setValue("toggle_3d", self.main_menu.action_toggle_3d.isChecked())
        settings.setValue("toggle_sim_graph", self.main_menu.action_toggle_sim_graph.isChecked())
        settings.setValue("toggle_state_space", self.main_menu.action_toggle_state_space.isChecked())
        
        settings.setValue("watch_facts", self.main_menu.action_watch_facts.isChecked())
        settings.setValue("watch_rules", self.main_menu.action_watch_rules.isChecked())
        settings.setValue("watch_activations", self.main_menu.action_watch_activations.isChecked())
       
        # Save explorer path.
        current_explorer_path = self.explorer.file_model.filePath(self.explorer.tree_view.rootIndex())
        settings.setValue("explorer_path", current_explorer_path)
        
        # Save open tabs.
        open_files = []
        for i in range(self.editor_tabs.count()):
            path = self.editor_tabs.tabToolTip(i)
            if path and os.path.exists(path):
                open_files.append(path)
                
        settings.setValue("open_tabs", open_files)
        settings.setValue("current_tab_index", self.editor_tabs.currentIndex())

    def _load_workspace(self):
        """
        Restores the IDE state from the system registry on startup.
        """
        # Make sure this strictly matches the names in _save_workspace!
        settings = QSettings("CLIPSiffyTeam", "CLIPSiffy")
        
        # Robust Boolean Parser for PyQt6 (Put this at the very top)
        def get_bool(key, default_val):
            val = settings.value(key)
            if val is None: return default_val
            if isinstance(val, str): return val.lower() == 'true'
            return bool(val)
        
        # Safely load the Master Save Switch
        save_state_pref = get_bool("save_state_pref", True)
        self.main_menu.action_save_state.setChecked(save_state_pref)

        # If the user unchecked "Save Workspace", start clean.
        if not save_state_pref:
            is_dark = get_bool("theme_dark", True)
            self.main_menu.action_theme.setChecked(is_dark)
            self.logic_toggle_theme(is_dark)
            self.logic_new_file()
            return

        # --- RESTORE WORKSPACE ---
        geom = settings.value("geometry")
        if geom: self.restoreGeometry(geom)
            
        state = settings.value("windowState")
        if state: self.restoreState(state)
            
        is_dark = get_bool("theme_dark", True)
        self.main_menu.action_theme.setChecked(is_dark)
        self.logic_toggle_theme(is_dark)
        
        # Safely load the menu checkboxes
        self.main_menu.action_toggle_fuzzy.setChecked(get_bool("toggle_fuzzy", False))
        self.main_menu.action_toggle_graphs.setChecked(get_bool("toggle_graphs", False))
        self.main_menu.action_toggle_diagram.setChecked(get_bool("toggle_diagram", False))
        self.main_menu.action_toggle_3d.setChecked(get_bool("toggle_3d", False))
        self.main_menu.action_toggle_sim_graph.setChecked(get_bool("toggle_sim_graph", False))
        self.main_menu.action_toggle_state_space.setChecked(get_bool("toggle_state_space", False))
        
        self.main_menu.action_watch_facts.setChecked(get_bool("watch_facts", False))
        self.main_menu.action_watch_rules.setChecked(get_bool("watch_rules", False))
        self.main_menu.action_watch_activations.setChecked(get_bool("watch_activations", False))

        # Explicitly enforce the loaded menu states into the UI and Engine
        self.logic_toggle_fuzzy_mode(self.main_menu.action_toggle_fuzzy.isChecked())
        self.logic_toggle_diagram(self.main_menu.action_toggle_diagram.isChecked())
        self.logic_toggle_graphs(self.main_menu.action_toggle_graphs.isChecked())
        self.logic_toggle_3d_surface(self.main_menu.action_toggle_3d.isChecked())
        self.logic_toggle_sim_graph(self.main_menu.action_toggle_sim_graph.isChecked())
        self.logic_toggle_state_space(self.main_menu.action_toggle_state_space.isChecked())
        
        self.logic_watch_facts(self.main_menu.action_watch_facts.isChecked())
        self.logic_watch_rules(self.main_menu.action_watch_rules.isChecked())
        self.logic_watch_activations(self.main_menu.action_watch_activations.isChecked())
        
        # Restore explorer path
        exp_path = settings.value("explorer_path", type=str, defaultValue="")
        if exp_path and os.path.exists(exp_path):
            os.chdir(exp_path)
            QDir.setCurrent(exp_path)
            self.explorer.tree_view.setRootIndex(self.explorer.file_model.index(exp_path))
            
        # Restore open tabs
        open_tabs = settings.value("open_tabs", type=list, defaultValue=[])
        if open_tabs:
            while self.editor_tabs.count() > 0:
                self.editor_tabs.removeTab(0)
                
            for path in open_tabs:
                if os.path.exists(path):
                    self.open_file_in_tab(path)
            
            saved_index = settings.value("current_tab_index", type=int, defaultValue=0)
            if 0 <= saved_index < self.editor_tabs.count():
                self.editor_tabs.setCurrentIndex(saved_index)
        else:
            self.logic_new_file()

        # Restore the active Activity Bar side panel
        active_panel_name = settings.value("active_side_panel", type=str, defaultValue="PanelExplorer")
        for panel in self.side_panels:
            if panel.objectName() == active_panel_name:
                self.show_side_panel(panel)
                break

    def closeEvent(self, event):
        """Safely shuts down the IDE, saving state and halting threads."""
        # Check all tabs for unsaved changes without destroying the tabs yet
        for i in range(self.editor_tabs.count() - 1, -1, -1):
            self.editor_tabs.setCurrentIndex(i) 
            # Pass is_shutting_down=True so tabs remain in the UI for state saving
            if not self.close_tab(i, is_shutting_down=True):
                event.ignore()
                return
        
        # Halt any running async CLIPS execution safely
        if self.run_thread and self.run_thread.isRunning():
            self.run_thread.stop()
            self.run_thread.wait(2000) # Give it 2 seconds to gracefully shut down
        
        # Save the workspace. The tabs still exist, so they will be saved correctly!
        self._save_workspace()
        
        event.accept()

    def logic_open_file(self):
        """File dialog prompt to load a single file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CLIPS file", "", "CLIPS Files (*.clp);;All Files (*)")
        if file_path: self.open_file_in_tab(file_path)

    def logic_load_example(self, filename):
        """Loads a pre-existing example file as a NEW, unsaved template to protect the original."""
        
        # Figure out where the app is currently running from
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # Construct the full path to the examples folder
        examples_dir = os.path.join(base_dir, "fuzzy_lib", "fuzzy_lib", "tests")
        file_path = os.path.join(examples_dir, filename)
        
        # Check if the file actually exists
        if not os.path.exists(file_path):
            self.console.write_error(f"\n> [ERROR] Could not find the example file at:\n  {file_path}")
            return
            
        # Read the file content manually
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Create a brand new, detached editor
            new_editor = CLIPSEditor()
            new_editor.set_theme(self.main_menu.action_theme.isChecked())
            new_editor.setPlainText(content)
            
            # Force the editor to think it has unsaved changes. 
            # This forces Ctrl+S to trigger "Save As..."
            new_editor.document().setModified(True) 
            new_editor.document().modificationChanged.connect(
                lambda modified, ed=new_editor: self._mark_modified(ed, modified)
            )
            
            # Add the tab with an asterisk, but leave the ToolTip EMPTY.
            # An empty ToolTip breaks the link to the original file path.
            tab_name = f"{filename}*"
            index = self.editor_tabs.addTab(new_editor, tab_name)
            self.editor_tabs.setTabToolTip(index, "") 
            self.editor_tabs.setCurrentIndex(index)
            
            self.console.write(f"\n> Example loaded as a new template: {filename}")
            
        except Exception as e:
            self.console.write_error(f"\n> [ERROR] Could not read example file: {str(e)}")

    def logic_load(self):
        """
        Batch loads the fuzzy library (if enabled) and then loads 
        the selected user files or active tab using the internal loader.
        This corresponds to the full 'F4' command.
        """
        # Identify which user files to load
        file_paths = self.explorer.get_selected()
        if not file_paths:
            current_index = self.editor_tabs.currentIndex()
            if current_index != -1: 
                active_path = self.editor_tabs.tabToolTip(current_index)
                if active_path: file_paths = [active_path]
                else: self.console.write("\n> [WARNING] The current file has not been saved. Only the base library will be loaded.")
            else: self.console.write("\n> [WARNING] No user files selected or open. Only the base library will be loaded.")
                
        self.console.clear_console()
        self.console.write("> Starting full load into the environment...")
        
        library_loaded = False
        
        # Load the Fuzzy Library if the mode is enabled in Settings
        if hasattr(self, 'main_menu') and self.main_menu.action_toggle_fuzzy.isChecked():
            if getattr(sys, 'frozen', False): base_path = sys._MEIPASS
            else: base_path = os.path.dirname(os.path.abspath(__file__))
            
            # The exact sequential order is critical for CLIPS to resolve dependencies
            fuzzy_files = [
                "modules.clp",
                "templates.clp",
                "utilities.clp",
                "membership_functions.clp",
                "linguistic_modifiers.clp",
                "norms.clp",
                "main.clp",
                "setup.clp",
                "fuzzification.clp",
                "defuzzification.clp",
                "connections.clp",
                "environment.clp"
            ]
            
            library_loaded = True
            for f_name in fuzzy_files:
                file_path = os.path.join(base_path, "fuzzy_lib", "fuzzy_lib", "src", f_name)
                if os.path.exists(file_path):
                    try:
                        self.env.load(file_path)
                        self.console.write(f"  [OK] {f_name} successfully injected.")
                    except Exception as e:
                        self.console.write_error(f"  [ERROR] Loading {f_name}: {str(e)}\n")
                        library_loaded = False
                else:
                    self.console.write_error(f"  [WARNING] '{f_name}' not found at:\n  {file_path}\n")
                    library_loaded = False
            
            if not library_loaded:
                self.console.write("  [WARNING] Fuzzy library loading incomplete. Fuzzy mode may fail.")
        
        # Load user files (normal or encrypted) using the shared internal loader logic
        self._internal_loader(file_paths)
            
        # Refresh UI panels to reflect the new state of memory
        self.update_memory_views()

    def logic_reset(self):
        """Sends the (reset) command to initialize rules and facts."""
        self.console.write("\n> Initializing facts (Reset)...")
        try:
            self.env.reset()
            self.console.write("> [OK] Reset completed.")
            self.update_memory_views()
        except Exception as e:
            self.console.write_error(f"> [ERROR] During reset: {str(e)}\n")

    def logic_run(self):
        """Executes the rule engine asynchronously to prevent GUI freezing."""
        if self.run_thread and self.run_thread.isRunning():
            return
            
        self.console.write("\n> Executing asynchronously (Run)...\n")
        self._toggle_run_state(True)
        
        self.router.enable_buffering(True)
        
        self.run_thread = CLIPSRunThread(self.env)
        self.run_thread.signal_finished.connect(self._on_run_finished)
        self.run_thread.signal_error.connect(self._on_run_error)
        self.run_thread.start()

    def logic_step(self):
        """Steps through a single activation sequence asynchronously."""
        if self.run_thread and self.run_thread.isRunning():
            return
            
        self.console.write("\n> Executing step by step (Step 1)...")
        self._toggle_run_state(True)
        
        self.router.enable_buffering(True)
        
        self.run_thread = CLIPSRunThread(self.env, steps=1)
        self.run_thread.signal_finished.connect(self._on_run_finished)
        self.run_thread.signal_error.connect(self._on_run_error)
        self.run_thread.start()

    def logic_stop(self):
        """Safely halts the asynchronous execution thread."""
        if self.run_thread and self.run_thread.isRunning():
            self.console.write("\n> Halting execution (Waiting for next chunk boundary)...")
            self.run_thread.stop()

    def _on_run_finished(self):
        """Callback triggered when async execution completes naturally or is halted."""
        self.router.flush()
        self.router.enable_buffering(False)
        
        self._toggle_run_state(False)
        self.console.write("> [OK] Execution stopped/completed.")
        self.update_memory_views()
        self.show_graphs_if_available()
        
        if hasattr(self, 'dock_sim_graph') and self.dock_sim_graph.isVisible():
            self.dock_sim_graph.update_plot(self.env)

    def _on_run_error(self, err_msg):
        """Callback triggered if the async thread encounters an exception."""
        self.router.flush()
        self.router.enable_buffering(False)
        
        self._toggle_run_state(False)
        self.console.write_error(f"\n> [ERROR] During execution: {err_msg}\n")

    def _toggle_run_state(self, is_running):
        """Locks or unlocks the UI elements during execution to prevent conflicts."""
        self.console.input_line.setEnabled(not is_running)
        if hasattr(self.main_menu, 'action_stop'):
            self.main_menu.action_stop.setEnabled(is_running)
            
        if hasattr(self.main_menu, 'action_run'):
            self.main_menu.action_run.setEnabled(not is_running)
            self.main_menu.action_step.setEnabled(not is_running)
            self.main_menu.action_reset.setEnabled(not is_running)
            self.main_menu.action_clear.setEnabled(not is_running)
            self.main_menu.action_load.setEnabled(not is_running)

    def logic_clear(self):
        """Sends the (clear) command to completely wipe engine memory."""
        self.console.write("\n> Clearing the engine (Clear)...")
        try:
            self.env.clear()
            self.console.write("> [OK] CLIPS engine cleared.")
            self.update_memory_views()
        except Exception as e:
            self.console.write_error(f"> [ERROR] During clear: {str(e)}\n")

    def logic_live_command(self, command):
        """Parses inputs from the console command line and pipes them into CLIPS."""
        clean_command = command.strip()
        if clean_command.lower() in ['clear', 'cls', 'limpiar']:
            self.console.clear_console()
            return
        self.console.write_base(f"\nCLIPS> {command}\n")
        try:
            if clean_command.startswith("(def"):
                self.env.build(command) 
                self.console.write_base("> [Construct added to memory]\n")
                self.update_memory_views()
            else:
                result = self.env.eval(command)
                if result is not None: self.console.write_base(f"{str(result)}\n")
                self.update_memory_views()
        except Exception as e:
            self.console.write_error(f"[SYNTAX ERROR] {str(e)}\n")

    def _open_docs_browser(self, relative_html_path):
        """Opens internal static web documentation on the user's default browser."""
        clean_path = relative_html_path.replace("\\", "/")
        url = f"http://127.0.0.1:{self.docs_port}/{clean_path}"
        webbrowser.open_new_tab(url)
        self.console.write("\n> Opening documentation in the web browser...")

    def logic_docs_fuzzy(self):
        """Opens the documentation for the Fuzzy Library."""
        self._open_docs_browser("fuzzy_lib/docs_lib/site/index.html")

    def logic_docs_ide(self):
        """Opens the documentation for the IDE."""
        self._open_docs_browser("docs_ide/site/index.html")

    def logic_toggle_3d_surface(self, is_active):
        """Displays or hides the 3D control surface viewer."""
        if is_active:
            self.surface_view.update_diagram(self.env)
            self.dock_surface.show()
        else: self.dock_surface.hide()

    def logic_toggle_sim_graph(self, is_active):
        """Displays or hides the simulation dashboard."""
        if is_active:
            self.dock_sim_graph.update_plot(self.env)
            self.dock_sim_graph.show()
        else: 
            self.dock_sim_graph.hide()

    def logic_toggle_state_space(self, is_active):
        """Displays or hides the State Space phase portrait."""
        if is_active:
            self.dock_state_space.update_plot(self.env)
            self.dock_state_space.show()
        else: 
            self.dock_state_space.hide()

    def logic_watch_facts(self, is_active):
        """Toggles the CLIPS engine's internal tracker for Facts."""
        if is_active:
            self.env.eval("(watch facts)")
            self.console.write("\n> [DEBUG] Watch Facts: ON")
        else:
            self.env.eval("(unwatch facts)")
            self.console.write("\n> [DEBUG] Watch Facts: OFF")

    def logic_watch_rules(self, is_active):
        """Toggles the CLIPS engine's internal tracker for Rules."""
        if is_active:
            self.env.eval("(watch rules)")
            self.console.write("\n> [DEBUG] Watch Rules: ON")
        else:
            self.env.eval("(unwatch rules)")
            self.console.write("\n> [DEBUG] Watch Rules: OFF")

    def logic_watch_activations(self, is_active):
        """Toggles the CLIPS engine's internal tracker for Activations."""
        if is_active:
            self.env.eval("(watch activations)")
            self.console.write("\n> [DEBUG] Watch Activations: ON")
        else:
            self.env.eval("(unwatch activations)")
            self.console.write("\n> [DEBUG] Watch Activations: OFF")

    def logic_toggle_theme(self, is_dark):
        """
        Dynamically swaps the visual application theme and forces a redraw on child components.

        Args:
            is_dark (bool): True for Dark Mode, False for Light Mode.
        """
        app = QApplication.instance()
        
        if is_dark:
            style_sheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
            self.main_menu.action_theme.setText("Dark Theme")
            bg_toolbar = "#252526"; border_toolbar = "#333333"; color_btn = "#858585"; hover_btn = "#ffffff"; hover_bg = "#333333"
        else:
            style_sheet = qtvsc.load_stylesheet(qtvsc.Theme.LIGHT_VS)
            self.main_menu.action_theme.setText("Light Theme")
            bg_toolbar = "#f3f3f3"; border_toolbar = "#cccccc"; color_btn = "#666666"; hover_btn = "#000000"; hover_bg = "#e5e5e5"

        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.apply_theme(is_dark)
            
        app.setStyleSheet(style_sheet)
        self.activity_bar.setStyleSheet(f"""
            QToolBar {{ background-color: {bg_toolbar}; border-right: 1px solid {border_toolbar}; spacing: 5px; padding-top: 10px; }}
            QToolButton {{ color: {color_btn}; font-size: 20px; padding: 12px; border: none; }}
            QToolButton:hover {{ color: {hover_btn}; background-color: {hover_bg}; }}
        """)

        self.console.set_theme(is_dark)
        
        for i in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(i)
            if isinstance(widget, CLIPSEditor):
                widget.set_theme(is_dark)

        if self.main_menu.action_toggle_diagram.isChecked() and self.dock_diagram.isVisible():
            self.diagram_view.update_diagram(self.env)
            
        if self.main_menu.action_toggle_graphs.isChecked() and hasattr(self, 'dock_inference') and self.dock_inference.isVisible():
            self.inference_view.update_diagram(self.env)
            
        if hasattr(self, 'dock_surface') and self.dock_surface.isVisible():
            self.surface_view.update_diagram(self.env)

if __name__ == '__main__':
    import ctypes
    try:
        myappid = 'clipsiffy.studio.version_1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    os.environ["QT_SCALE_FACTOR"] = "1.2"
    app = QApplication(sys.argv)
    style_sheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    app.setStyleSheet(style_sheet)
    ide = ClipsIDE()
    ide.showMaximized()
    sys.exit(app.exec())