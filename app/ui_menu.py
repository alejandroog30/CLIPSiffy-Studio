from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal

class MainMenu(QMenuBar):
    """
    The main application menu bar for the CLIPS IDE.
    It constructs the standard application menus (File, Edit, View, Run, Debug, Settings, Help) 
    and acts as a central hub, routing user UI interactions to the main application via PyQt signals.

    Attributes:
        signal_new_file (pyqtSignal): Emitted to create a new empty file tab.
        signal_export_fuzzy (pyqtSignal): Emitted to export the fuzzy configuration to a file.
        signal_open_file (pyqtSignal): Emitted to open an existing .clp file.
        signal_open_folder (pyqtSignal): Emitted to change the explorer's root directory.
        signal_save (pyqtSignal): Emitted to save the currently active editor tab.
        signal_save_as (pyqtSignal): Emitted to prompt for a new save location.
        signal_exit (pyqtSignal): Emitted to close the application.
        signal_load_example (pyqtSignal): Emitted to show examples.
        signal_undo (pyqtSignal): Emitted to undo the last text action.
        signal_redo (pyqtSignal): Emitted to redo the last text action.
        signal_cut (pyqtSignal): Emitted to cut text.
        signal_copy (pyqtSignal): Emitted to copy text.
        signal_paste (pyqtSignal): Emitted to paste text.
        signal_find (pyqtSignal): Emitted to open the find dialog.
        signal_find_next (pyqtSignal): Emitted to search for the next occurrence.
        signal_toggle_comment (pyqtSignal): Emitted to comment/uncomment the selected lines.
        signal_load (pyqtSignal): Emitted to load files into the CLIPS environment.
        signal_reset (pyqtSignal): Emitted to execute a CLIPS (reset) command.
        signal_run (pyqtSignal): Emitted to execute a CLIPS (run) command.
        signal_step (pyqtSignal): Emitted to execute a single CLIPS step.
        signal_clear (pyqtSignal): Emitted to execute a CLIPS (clear) command.
        signal_stop (pyqtSignal): Emmitted to stop CLIPS.
        signal_default_layout (pyqtSignal): Emitted to restore the default window layout.
        signal_simple_layout (pyqtSignal): Emitted to switch to a simplified layout.
        signal_zoom_in (pyqtSignal): Emitted to increase UI text size.
        signal_zoom_out (pyqtSignal): Emitted to decrease UI text size.
        signal_toggle_theme (pyqtSignal): Emitted with a bool indicating if dark mode is active.
        signal_docs_fuzzy (pyqtSignal): Emitted to open the fuzzy library documentation.
        signal_docs_ide (pyqtSignal): Emitted to open the IDE documentation.
        signal_toggle_fuzzy_mode (pyqtSignal): Emitted when fuzzy mode is enabled/disabled.
        signal_toggle_diagram (pyqtSignal): Emitted when the block diagram view is toggled.
        signal_toggle_graphs (pyqtSignal): Emitted when the 2D inference graphs are toggled.
        signal_toggle_3d_surface (pyqtSignal): Emitted when the 3D surface view is toggled.
        signal_toggle_sim_graph (pyqtSignal): Emitted when the simlation graphic view is toggled.
        signal_watch_facts (pyqtSignal): Emitted to toggle the CLIPS watch facts flag.
        signal_watch_rules (pyqtSignal): Emitted to toggle the CLIPS watch rules flag.
        signal_watch_activations (pyqtSignal): Emitted to toggle the CLIPS watch activations flag.
    """

    # --- Signals Definition ---
    signal_new_file = pyqtSignal()
    signal_export_fuzzy = pyqtSignal()
    signal_encrypt_file = pyqtSignal()
    signal_open_file = pyqtSignal()
    signal_open_folder = pyqtSignal()
    signal_save = pyqtSignal()
    signal_save_as = pyqtSignal()
    signal_exit = pyqtSignal()
    signal_load_example = pyqtSignal(str)

    signal_undo = pyqtSignal()
    signal_redo = pyqtSignal()
    signal_cut = pyqtSignal()
    signal_copy = pyqtSignal()
    signal_paste = pyqtSignal()
    signal_find = pyqtSignal()
    signal_find_next = pyqtSignal()
    signal_toggle_comment = pyqtSignal()

    signal_load = pyqtSignal()
    signal_load_files = pyqtSignal()
    signal_reset = pyqtSignal()
    signal_run = pyqtSignal()
    signal_step = pyqtSignal()
    signal_clear = pyqtSignal()
    signal_stop = pyqtSignal()

    signal_default_layout = pyqtSignal()
    signal_simple_layout = pyqtSignal()

    signal_zoom_in = pyqtSignal()
    signal_zoom_out = pyqtSignal()

    signal_toggle_theme = pyqtSignal(bool)

    signal_docs_fuzzy = pyqtSignal()
    signal_docs_ide = pyqtSignal()

    signal_toggle_fuzzy_mode = pyqtSignal(bool)
    signal_toggle_diagram = pyqtSignal(bool)
    signal_toggle_graphs = pyqtSignal(bool)
    signal_toggle_3d_surface = pyqtSignal(bool)
    signal_toggle_sim_graph = pyqtSignal(bool)
    signal_toggle_state_space = pyqtSignal(bool)

    signal_watch_facts = pyqtSignal(bool)
    signal_watch_rules = pyqtSignal(bool)
    signal_watch_activations = pyqtSignal(bool)

    def __init__(self, parent=None):
        """
        Initializes the menu bar and constructs its hierarchical structure.

        Args:
            parent (QWidget, optional): The parent widget (typically the QMainWindow). Defaults to None.
        """
        super().__init__(parent)
        self._setup_menu()
    
    def _setup_menu(self):
        """
        Internally constructs the sub-menus (File, Edit, View, Run, Debug, Settings, Help)
        and binds their respective QActions to the class signals.
        """
        # --- File Menu ---
        menu_file = self.addMenu("File")

        action_new = QAction("New File", self)
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self.signal_new_file.emit)
        menu_file.addAction(action_new)

        menu_examples = menu_file.addMenu("Load Example...")
        action_clips_hello_world = QAction("CLIPS Hello World", self)
        action_clips_hello_world.triggered.connect(lambda: self.signal_load_example.emit("clips_hello_world.clp"))
        menu_examples.addAction(action_clips_hello_world)
        action_wenv_car = QAction("Car environment", self)
        action_wenv_car.triggered.connect(lambda: self.signal_load_example.emit("wenv_car.clp"))
        menu_examples.addAction(action_wenv_car)
        action_wenv_drone = QAction("Drone environment", self)
        action_wenv_drone.triggered.connect(lambda: self.signal_load_example.emit("wenv_drone.clp"))
        menu_examples.addAction(action_wenv_drone)
        action_wenv_pendulum = QAction("Pendulum environment", self)
        action_wenv_pendulum.triggered.connect(lambda: self.signal_load_example.emit("wenv_pendulum.clp"))
        menu_examples.addAction(action_wenv_pendulum)
        
        action_export = QAction("Export Fuzzy Configuration...", self)
        action_export.setShortcut("Ctrl+E")
        action_export.triggered.connect(self.signal_export_fuzzy.emit)
        menu_file.addAction(action_export)

        action_encrypt = QAction("Encrypt File...", self)
        action_encrypt.triggered.connect(self.signal_encrypt_file.emit)
        menu_file.addAction(action_encrypt)

        action_open = QAction("Open File...", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self.signal_open_file.emit) 
        menu_file.addAction(action_open)
        
        action_open_folder = QAction("Open Folder...", self)
        action_open_folder.setShortcut("Ctrl+K, Ctrl+O")
        action_open_folder.triggered.connect(self.signal_open_folder.emit)
        menu_file.addAction(action_open_folder)
        
        menu_file.addSeparator() 
        
        action_save = QAction("Save", self)
        action_save.setShortcut("Ctrl+S")
        action_save.triggered.connect(self.signal_save.emit)
        menu_file.addAction(action_save)
        
        action_save_as = QAction("Save as...", self)
        action_save_as.setShortcut("Ctrl+Shift+S")
        action_save_as.triggered.connect(self.signal_save_as.emit)
        menu_file.addAction(action_save_as)
        
        menu_file.addSeparator() 
        
        action_exit = QAction("Exit", self)
        action_exit.setShortcut("Ctrl+F4")
        action_exit.triggered.connect(self.signal_exit.emit)
        menu_file.addAction(action_exit)

        # --- Edit Menu ---
        menu_edit = self.addMenu("Edit")

        action_undo = QAction("Undo", self)
        action_undo.setShortcut("Ctrl+Z")
        action_undo.triggered.connect(self.signal_undo.emit)
        menu_edit.addAction(action_undo)

        action_redo = QAction("Redo", self)
        action_redo.setShortcut("Ctrl+Y")
        action_redo.triggered.connect(self.signal_redo.emit)
        menu_edit.addAction(action_redo)

        menu_edit.addSeparator()

        action_cut = QAction("Cut", self)
        action_cut.setShortcut("Ctrl+X")
        action_cut.triggered.connect(self.signal_cut.emit)
        menu_edit.addAction(action_cut)

        action_copy = QAction("Copy", self)
        action_copy.setShortcut("Ctrl+C")
        action_copy.triggered.connect(self.signal_copy.emit)
        menu_edit.addAction(action_copy)

        action_paste = QAction("Paste", self)
        action_paste.setShortcut("Ctrl+V")
        action_paste.triggered.connect(self.signal_paste.emit)
        menu_edit.addAction(action_paste)

        menu_edit.addSeparator()

        action_find = QAction("Find...", self)
        action_find.setShortcut("Ctrl+F")
        action_find.triggered.connect(self.signal_find.emit)
        menu_edit.addAction(action_find)

        action_find_next = QAction("Find Next", self)
        action_find_next.setShortcut("F3") 
        action_find_next.triggered.connect(self.signal_find_next.emit)
        menu_edit.addAction(action_find_next)

        action_comment = QAction("Toggle Comment", self)
        action_comment.setShortcut("Ctrl+/") 
        action_comment.triggered.connect(self.signal_toggle_comment.emit)
        menu_edit.addAction(action_comment)

        # --- View Menu ---
        self.menu_view = self.addMenu("View")

        self.action_theme = QAction("Dark Theme", self)
        self.action_theme.setCheckable(True)
        self.action_theme.setChecked(True) 
        self.action_theme.toggled.connect(self.signal_toggle_theme.emit)
        self.menu_view.addAction(self.action_theme)

        self.menu_view.addSeparator()

        self.menu_layouts = self.menu_view.addMenu("Layouts")
        
        action_default_layout = QAction("Default Layout", self)
        action_default_layout.triggered.connect(self.signal_default_layout.emit)
        self.menu_layouts.addAction(action_default_layout)
        
        action_simple_layout = QAction("Simple (Editor + Console/Facts/Rules)", self)
        action_simple_layout.triggered.connect(self.signal_simple_layout.emit)
        self.menu_layouts.addAction(action_simple_layout)

        action_zoom_in = QAction("Zoom In", self)
        action_zoom_in.setShortcut("Ctrl++")
        action_zoom_in.triggered.connect(self.signal_zoom_in.emit)
        self.menu_view.addAction(action_zoom_in)

        action_zoom_out = QAction("Zoom Out", self)
        action_zoom_out.setShortcut("Ctrl+-")
        action_zoom_out.triggered.connect(self.signal_zoom_out.emit)
        self.menu_view.addAction(action_zoom_out)
        
        self.menu_view.addSeparator()

        # --- Run Menu ---
        menu_run = self.addMenu("Run")
        
        self.action_load = QAction("Load Environment (Full)", self)
        self.action_load.setShortcut("F4")
        self.action_load.triggered.connect(self.signal_load.emit)
        menu_run.addAction(self.action_load)

        self.action_load_files = QAction("Load Selected Files Only", self)
        self.action_load_files.setShortcut("Shift+F4")
        self.action_load_files.triggered.connect(self.signal_load_files.emit)
        menu_run.addAction(self.action_load_files)
        
        self.action_reset = QAction("Reset", self)
        self.action_reset.setShortcut("F5")
        self.action_reset.triggered.connect(self.signal_reset.emit)
        menu_run.addAction(self.action_reset)
        
        self.action_run = QAction("Run", self)
        self.action_run.setShortcut("F6")
        self.action_run.triggered.connect(self.signal_run.emit)
        menu_run.addAction(self.action_run)
        
        self.action_step = QAction("Step", self)
        self.action_step.setShortcut("F7")
        self.action_step.triggered.connect(self.signal_step.emit)
        menu_run.addAction(self.action_step)

        menu_run.addSeparator() 

        self.action_stop = QAction("Stop Execution", self)
        self.action_stop.setShortcut("Shift+F6")
        self.action_stop.setEnabled(False) # Deshabilitado por defecto
        self.action_stop.triggered.connect(self.signal_stop.emit)
        menu_run.addAction(self.action_stop)
        
        menu_run.addSeparator() 
        
        self.action_clear = QAction("Clear Environment", self)
        self.action_clear.setShortcut("Ctrl+Shift+L")
        self.action_clear.triggered.connect(self.signal_clear.emit)
        menu_run.addAction(self.action_clear)

        # --- Debug Menu ---
        menu_debug = self.addMenu("Debug")

        self.action_watch_facts = QAction("Watch Facts", self)
        self.action_watch_facts.setCheckable(True)
        self.action_watch_facts.toggled.connect(self.signal_watch_facts.emit)
        menu_debug.addAction(self.action_watch_facts)

        self.action_watch_rules = QAction("Watch Rules", self)
        self.action_watch_rules.setCheckable(True)
        self.action_watch_rules.toggled.connect(self.signal_watch_rules.emit)
        menu_debug.addAction(self.action_watch_rules)

        self.action_watch_activations = QAction("Watch Activations", self)
        self.action_watch_activations.setCheckable(True)
        self.action_watch_activations.toggled.connect(self.signal_watch_activations.emit)
        menu_debug.addAction(self.action_watch_activations)

        # --- Settings Menu ---
        menu_settings = self.addMenu("Settings")
        
        self.action_save_state = QAction("Save Workspace on Exit", self)
        self.action_save_state.setCheckable(True)
        self.action_save_state.setChecked(True)
        self.action_save_state.setToolTip("Saves open tabs, window layout, and explorer path.")
        menu_settings.addAction(self.action_save_state)

        menu_settings.addSeparator()

        self.action_toggle_fuzzy = QAction("Enable Fuzzy Logic Mode", self)
        self.action_toggle_fuzzy.setCheckable(True)
        self.action_toggle_fuzzy.setChecked(True) 
        self.action_toggle_fuzzy.toggled.connect(self.signal_toggle_fuzzy_mode.emit)
        menu_settings.addAction(self.action_toggle_fuzzy)

        menu_settings.addSeparator() 

        self.action_toggle_graphs = QAction("Generate Inference Graphs", self)
        self.action_toggle_graphs.setCheckable(True) 
        self.action_toggle_graphs.setChecked(True)   
        self.action_toggle_graphs.setToolTip("Disable this to speed up execution if you don't need to see the graphs.")
        self.action_toggle_graphs.toggled.connect(self.signal_toggle_graphs.emit)
        menu_settings.addAction(self.action_toggle_graphs)

        self.action_toggle_diagram = QAction("Generate Block Diagrams", self)
        self.action_toggle_diagram.setCheckable(True)
        self.action_toggle_diagram.setChecked(True) 
        self.action_toggle_diagram.toggled.connect(self.signal_toggle_diagram.emit)
        menu_settings.addAction(self.action_toggle_diagram)

        self.action_toggle_3d = QAction("Generate 3D Control Surface", self)
        self.action_toggle_3d.setCheckable(True)
        self.action_toggle_3d.setChecked(False) 
        self.action_toggle_3d.toggled.connect(self.signal_toggle_3d_surface.emit)
        menu_settings.addAction(self.action_toggle_3d)

        self.action_toggle_sim_graph = QAction("Generate Simulation Dashboard", self)
        self.action_toggle_sim_graph.setCheckable(True)
        self.action_toggle_sim_graph.setChecked(False)
        self.action_toggle_sim_graph.toggled.connect(self.signal_toggle_sim_graph.emit)
        menu_settings.addAction(self.action_toggle_sim_graph)

        self.action_toggle_state_space = QAction("Generate State Space Graph", self)
        self.action_toggle_state_space.setCheckable(True)
        self.action_toggle_state_space.setChecked(False)
        self.action_toggle_state_space.toggled.connect(self.signal_toggle_state_space.emit) 
        menu_settings.addAction(self.action_toggle_state_space)

        # --- Help Menu ---
        menu_help = self.addMenu("Help")
        
        action_docs_fuzzy = QAction("Fuzzy Library Documentation", self)
        action_docs_fuzzy.setShortcut("F1") 
        action_docs_fuzzy.triggered.connect(self.signal_docs_fuzzy.emit)
        menu_help.addAction(action_docs_fuzzy)
        
        action_docs_ide = QAction("IDE Documentation", self)
        action_docs_ide.setShortcut("F2") 
        action_docs_ide.triggered.connect(self.signal_docs_ide.emit)
        menu_help.addAction(action_docs_ide)

    def add_view_actions(self, actions):
        """
        Dynamically appends a list of QActions to the View menu. Usually used to 
        add toggle visibility actions for the various dock widgets.

        Args:
            actions (list of QAction): The actions to append.
        """
        for action in actions:
            self.menu_view.addAction(action)
