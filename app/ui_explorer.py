import os

from PyQt6.QtWidgets import (
    QTreeView, QDockWidget,
    QFileDialog, QWidget,
    QVBoxLayout, QPushButton,
    QMessageBox,
    QMenu,
    QInputDialog
)

from PyQt6.QtCore import (
    Qt, QDir, pyqtSignal, pyqtSignal
)

from PyQt6.QtGui import (
    QFileSystemModel, QAction
)

class FileExplorer(QDockWidget):
    """
    A dockable side panel providing a tree view of the local file system. 
    It allows users to open project directories, select files for batch loading, 
    and manage files (create, rename, delete) via context menus.

    Attributes:
        signal_file_double_click (pyqtSignal): Emitted with the file path when a file is double-clicked.
        signal_folder_changed (pyqtSignal): Emitted with the new directory path when the root folder changes.
        signal_rename_request (pyqtSignal): Emitted when a file/folder rename is requested.
        signal_delete_request (pyqtSignal): Emitted when a file/folder deletion is requested.
        file_model (CheckableFileSystemModel): The underlying data model supporting the tree view.
        tree_view (QTreeView): The visual widget rendering the file tree.
    """
    
    signal_file_double_click = pyqtSignal(str) 
    signal_folder_changed = pyqtSignal(str)
    signal_rename_request = pyqtSignal(str, str) 
    signal_delete_request = pyqtSignal(str, bool) 

    def __init__(self, title, parent=None):
        """
        Initializes the File Explorer dock widget and sets up its tree view.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_change_folder = QPushButton("Open Folder...")
        self.btn_change_folder.setStyleSheet("background-color: #007acc; color: white; padding: 5px;")
        self.btn_change_folder.clicked.connect(self._select_folder)
        
        self.file_model = CheckableFileSystemModel() 
        self.file_model.setRootPath(QDir.rootPath())
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(QDir.currentPath()))
        
        self.tree_view.doubleClicked.connect(self._on_double_click)

        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Hide standard filesystem columns (Size, Type, Date Modified)
        for i in range(1, 4):
            self.tree_view.setColumnHidden(i, True)
            
        layout.addWidget(self.btn_change_folder)
        layout.addWidget(self.tree_view)
        content_widget.setLayout(layout)
        self.setWidget(content_widget)

    def _select_folder(self):
        """
        Opens an OS-level dialog prompting the user to select a new root directory,
        updating the tree view to point to the newly chosen path.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder_path:
            os.chdir(folder_path)
            QDir.setCurrent(folder_path)
            
            new_path_index = self.file_model.index(folder_path)
            self.tree_view.setRootIndex(new_path_index)
            
            self.signal_folder_changed.emit(folder_path)

    def _on_double_click(self, index):
        """
        Intercepts double clicks on items. If the item is a file, it emits a signal 
        to open it in the editor.

        Args:
            index (QModelIndex): The index of the item clicked.
        """
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            if file_path.endswith('.clpx'):
                QMessageBox.information(
                    self, 
                    "Encrypted Environment", 
                    "This file is encrypted and cannot be viewed in the editor.\n\n"
                    "Use 'Run -> Load Environment' (F4) to load it directly into the engine."
                )
                return
            self.signal_file_double_click.emit(file_path)

    def _show_context_menu(self, position):
        """
        Constructs and displays a right-click context menu for file operations.

        Args:
            position (QPoint): The location of the cursor within the tree view.
        """
        index = self.tree_view.indexAt(position)
        menu = QMenu(self)
        
        if not index.isValid():
            base_path = self.file_model.filePath(self.tree_view.rootIndex())
            is_folder = True
        else:
            base_path = self.file_model.filePath(index)
            is_folder = self.file_model.isDir(index)
            
        parent_dir = base_path if is_folder else os.path.dirname(base_path)

        action_new_file = QAction("New File", self)
        action_new_file.triggered.connect(lambda: self._create_file(parent_dir))
        menu.addAction(action_new_file)
        
        action_new_folder = QAction("New Folder", self)
        action_new_folder.triggered.connect(lambda: self._create_folder(parent_dir))
        menu.addAction(action_new_folder)
        
        menu.addSeparator()

        if index.isValid():
            action_rename = QAction("Rename", self)
            action_rename.triggered.connect(lambda: self._rename(base_path))
            menu.addAction(action_rename)
            
            action_delete = QAction("Delete", self)
            action_delete.triggered.connect(lambda: self._delete(base_path, is_folder))
            menu.addAction(action_delete)
            
            menu.addSeparator()
            
        action_reload = QAction("Reload", self)
        action_reload.triggered.connect(self._reload)
        menu.addAction(action_reload)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def _create_file(self, directory):
        """
        Prompts the user for a filename and creates a blank file on the disk.

        Args:
            directory (str): The absolute path of the directory where the file will be created.
        """
        name, ok = QInputDialog.getText(self, "New File", "File name (e.g. rules.clp):")
        if ok and name:
            path = os.path.join(directory, name)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    pass 
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file:\n{e}")

    def _create_folder(self, directory):
        """
        Prompts the user for a folder name and creates the directory on the disk.

        Args:
            directory (str): The absolute path where the new folder will be placed.
        """
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            path = os.path.join(directory, name)
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{e}")

    def _rename(self, current_path):
        """
        Prompts the user for a new name and emits the rename request signal.

        Args:
            current_path (str): The current absolute path of the item to rename.
        """
        directory = os.path.dirname(current_path)
        old_name = os.path.basename(current_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(directory, new_name)
            self.signal_rename_request.emit(current_path, new_path)

    def _delete(self, path, is_folder):
        """
        Asks for confirmation and emits the deletion request signal.

        Args:
            path (str): The absolute path to be permanently deleted.
            is_folder (bool): True if the target is a directory.
        """
        item_type = "the folder and all its contents" if is_folder else "the file"
        response = QMessageBox.warning(
            self, "Confirm deletion", 
            f"Are you sure you want to permanently delete {item_type} '{os.path.basename(path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.Yes:
            self.signal_delete_request.emit(path, is_folder)

    def _reload(self):
        """
        Forces a visual refresh of the underlying filesystem model.
        """
        current_path = self.file_model.filePath(self.tree_view.rootIndex())
        self.tree_view.setRootIndex(self.file_model.index(""))
        self.tree_view.setRootIndex(self.file_model.index(current_path))

    def get_selected(self):
        """
        Returns all paths currently selected via the UI checkboxes.

        Returns:
            list of str: Absolute file paths.
        """
        return self.file_model.get_checked_paths()

class CheckableFileSystemModel(QFileSystemModel):
    """
    A specialized QFileSystemModel that adds native checkbox support to file tree items,
    allowing users to multi-select files for loading into the CLIPS environment.

    Attributes:
        check_states (dict): A dictionary mapping file paths to their checked states.
    """

    def __init__(self, parent=None):
        """
        Initializes the model and the dictionary for state tracking.

        Args:
            parent (QObject, optional): The parent object. Defaults to None.
        """
        super().__init__(parent)
        self.check_states = {} 

    def flags(self, index):
        """
        Extends the default item flags to include the checkable attribute.

        Args:
            index (QModelIndex): The index of the item.

        Returns:
            Qt.ItemFlags: The combined flags for the item.
        """
        original_flags = super().flags(index)
        if index.column() == 0:
            original_flags |= Qt.ItemFlag.ItemIsUserCheckable
        return original_flags

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Intercepts data requests to supply the correct checkbox state (Checked/Unchecked).

        Args:
            index (QModelIndex): The index being queried.
            role (Qt.ItemDataRole): The specific role of data being requested.

        Returns:
            Any: The requested data or the check state.
        """
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            return self.check_states.get(path, Qt.CheckState.Unchecked.value)
            
        return super().data(index, role)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Captures the event when a user clicks a checkbox and saves the state to the dictionary.

        Args:
            index (QModelIndex): The index being modified.
            value (Any): The new value (check state).
            role (Qt.ItemDataRole): The data role being modified.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            self.check_states[path] = value 
            self.dataChanged.emit(index, index, [role]) 
            return True
            
        return super().setData(index, value, role)

    def get_checked_paths(self):
        """
        Retrieves a list of all file paths that currently have their checkboxes ticked.
        Folders are explicitly ignored, returning only concrete files.

        Returns:
            list of str: Absolute file paths of selected files.
        """
        files = []
        for path, state in self.check_states.items():
            if state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked:
                if not self.isDir(self.index(path)):
                    files.append(path)
        return files
