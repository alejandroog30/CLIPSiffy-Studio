import clips
import re

from PyQt6.QtWidgets import QTextEdit, QDockWidget, QWidget, QVBoxLayout, QLineEdit, QTabWidget, QCompleter

from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QObject, pyqtSignal

from PyQt6.QtGui import QFont, QAction, QTextCharFormat, QColor, QTextCursor

class CLIPSConsole(QDockWidget):
    """
    A dockable console widget that acts as the terminal for the CLIPS engine.
    It features a dual-tab system: 'Terminal' for general execution outputs and inputs,
    and 'Problems' to isolate and track execution or syntax errors.

    Attributes:
        signal_command (pyqtSignal): Emitted when the user presses Enter in the command line.
        tabs_console (QTabWidget): The container for the Terminal and Problems views.
        text_area (QTextEdit): The read-only text display area for standard output.
        error_area (QTextEdit): The read-only text display area specifically for errors.
        input_line (CommandLine): The interactive text field for user input.
        is_dark_mode (bool): State tracker for the current UI theme.
        error_count (int): Counter tracking the number of captured errors.
    """
    
    signal_command = pyqtSignal(str) 

    def __init__(self, title, parent=None):
        """
        Initializes the CLIPS Console with its tabs and layout.

        Args:
            title (str): The text title displayed on the dock tab.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.is_dark_mode = True
        self.error_count = 0
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab configuration and styling
        self.tabs_console = QTabWidget()
        self._apply_tab_style()
        
        console_font = QFont("Courier", 12)
        console_font.setStyleHint(QFont.StyleHint.Monospace)

        # TERMINAL
        self.tab_terminal = QWidget()
        term_layout = QVBoxLayout(self.tab_terminal)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(0)

        self.text_area = QTextEdit()
        self.text_area.setFont(console_font) 
        self.text_area.setReadOnly(True)
        self.text_area.setMinimumHeight(50)
        self.text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_area.customContextMenuRequested.connect(self._show_context_menu_terminal)
        
        self.input_line = CommandLine(self)
        self.input_line.setFont(console_font)
        self.input_line.setPlaceholderText("CLIPS> (Write and press Enter)")
        self.input_line.returnPressed.connect(self._process_enter)

        term_layout.addWidget(self.text_area)
        term_layout.addWidget(self.input_line)

        # PROBLEMS / ERRORS
        self.tab_errors = QWidget()
        err_layout = QVBoxLayout(self.tab_errors)
        err_layout.setContentsMargins(0, 0, 0, 0)
        err_layout.setSpacing(0)

        self.error_area = QTextEdit()
        self.error_area.setFont(console_font)
        self.error_area.setReadOnly(True)
        self.error_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.error_area.customContextMenuRequested.connect(self._show_context_menu_errors)

        err_layout.addWidget(self.error_area)

        # Build tabs
        self.tabs_console.addTab(self.tab_terminal, "Terminal")
        self.tabs_console.addTab(self.tab_errors, "Problems")

        self.action_clear_screen = QAction(self)
        self.action_clear_screen.setShortcut("Ctrl+L")
        self.action_clear_screen.triggered.connect(self.clear_console)
        self.addAction(self.action_clear_screen)
        
        layout.addWidget(self.tabs_console)
        content_widget.setLayout(layout)
        self.setWidget(content_widget)

    def _apply_tab_style(self):
        """Applies dynamic CSS styling to the tabs based on the active theme."""
        if self.is_dark_mode:
            self.tabs_console.setStyleSheet("""
                QTabWidget::pane { border: none; border-top: 1px solid #333333; }
                QTabBar::tab { background: transparent; color: #858585; padding: 6px 15px; border: none; border-bottom: 2px solid transparent; font-family: 'Segoe UI'; font-size: 13px; }
                QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid #007acc; font-weight: bold; }
                QTabBar::tab:hover:!selected { color: #cccccc; }
            """)
        else:
            self.tabs_console.setStyleSheet("""
                QTabWidget::pane { border: none; border-top: 1px solid #cccccc; }
                QTabBar::tab { background: transparent; color: #666666; padding: 6px 15px; border: none; border-bottom: 2px solid transparent; font-family: 'Segoe UI'; font-size: 13px; }
                QTabBar::tab:selected { color: #000000; border-bottom: 2px solid #007acc; font-weight: bold; }
                QTabBar::tab:hover:!selected { color: #333333; }
            """)

    def set_theme(self, is_dark):
        """Updates the console's internal theme state."""
        self.is_dark_mode = is_dark
        self._apply_tab_style()

    def _process_enter(self):
        """Captures the input command, adds it to the history, and emits the execution signal."""
        command = self.input_line.text().strip()
        if command:
            self.input_line.add_history(command)
            self.signal_command.emit(command)
            self.input_line.clear()

    def write(self, text):
        """Writes plain text directly to the standard terminal display."""
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        color = QColor("#d4d4d4") if self.is_dark_mode else QColor("#333333")
        fmt.setForeground(color)
        fmt.setFontWeight(QFont.Weight.Normal)
        cursor.setCharFormat(fmt)
        
        self.text_area.setTextCursor(cursor)
        self.text_area.append(text)

    def write_base(self, text):
        """Writes text to the terminal preserving HTML spacing and line breaks."""
        html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_text = html_text.replace(" ", "&nbsp;").replace("\n", "<br>")
        
        color = "#d4d4d4" if self.is_dark_mode else "#333333"
        html_fragment = f'<span style="color: {color};">{html_text}</span>'
        
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html_fragment)
        
        cursor.setCharFormat(QTextCharFormat())
        self.text_area.setTextCursor(cursor)
        self.text_area.ensureCursorVisible()

    def write_error(self, text):
        """
        Writes an IDE-level error EXPLICITLY ONLY to the Problems tab,
        highlighting it in red and updating the error counter.
        """
        html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_text = html_text.replace(" ", "&nbsp;").replace("\n", "<br>")
        html_fragment = f'<span style="color: #ef4444; font-weight: bold;">{html_text}</span><br>'
        
        cursor_err = self.error_area.textCursor()
        cursor_err.movePosition(QTextCursor.MoveOperation.End)
        cursor_err.insertHtml(html_fragment)
        
        cursor_err.setCharFormat(QTextCharFormat())
        self.error_area.setTextCursor(cursor_err)
        self.error_area.ensureCursorVisible()
        
        self.error_count += 1
        self.tabs_console.setTabText(1, f"Problems ({self.error_count})")

    def write_routed(self, router_name, text):
        """
        Intercepts output from the internal CLIPS engine. Routes 'werror' EXCLUSIVELY
        to the Problems tab and applies specific HTML colors based on the router type.
        """
        html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_text = html_text.replace(" ", "&nbsp;").replace("\n", "<br>")

        if router_name == "wtrace":
            html_fragment = f'<span style="color: #eab308; font-style: italic;">{html_text}</span>'
        elif router_name == "werror":
            html_fragment = f'<span style="color: #ef4444; font-weight: bold;">{html_text}</span>'
            
            # Route to Problems tab ONLY
            cursor_err = self.error_area.textCursor()
            cursor_err.movePosition(QTextCursor.MoveOperation.End)
            cursor_err.insertHtml(html_fragment)
            cursor_err.setCharFormat(QTextCharFormat())
            self.error_area.setTextCursor(cursor_err)
            self.error_area.ensureCursorVisible()
            
            self.error_count += 1
            self.tabs_console.setTabText(1, f"Problems ({self.error_count})")
            
            return 
        else:
            color = "#d4d4d4" if self.is_dark_mode else "#333333"
            html_fragment = f'<span style="color: {color};">{html_text}</span>'

        # Always write traces and standard outputs to Terminal
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html_fragment)
        
        # Limpiar formato
        cursor.setCharFormat(QTextCharFormat())
        self.text_area.setTextCursor(cursor)
        self.text_area.ensureCursorVisible()

    def clear_console(self):
        """Wipes all text from both the Terminal and Problems displays."""
        self.text_area.clear()
        self.clear_errors()

    def clear_errors(self):
        """Wipes the Problems display and resets the counter."""
        self.error_area.clear()
        self.error_count = 0
        self.tabs_console.setTabText(1, "Problems")

    def _show_context_menu_terminal(self, position):
        """Context menu for the Terminal."""
        menu = self.text_area.createStandardContextMenu()
        menu.addSeparator() 
        action_clear = QAction("Clear Console", self)
        action_clear.triggered.connect(self.clear_console)
        menu.addAction(action_clear)
        menu.exec(self.text_area.mapToGlobal(position))

    def _show_context_menu_errors(self, position):
        """Context menu for the Problems tab."""
        menu = self.error_area.createStandardContextMenu()
        menu.addSeparator() 
        action_clear = QAction("Clear Errors", self)
        action_clear.triggered.connect(self.clear_errors)
        menu.addAction(action_clear)
        menu.exec(self.error_area.mapToGlobal(position))

class CommandLine(QLineEdit):
    """
    A custom command-line input widget that supports command history navigation 
    (Up/Down arrows), parenthesis auto-closing, and an intelligent autocomplete 
    system tailored for CLIPS syntax.

    Attributes:
        console (CLIPSConsole): The parent console widget where outputs are displayed.
        history (list of str): Stores previously executed commands.
        history_index (int): The current position in the command history array.
        temp_command (str): Temporarily stores the current unsent command while navigating history.
        completer_obj (QCompleter): The autocomplete popup logic.
        completion_model (QStringListModel): The dynamic vocabulary model used for autocompletion.
        clips_keywords (list of str): Static CLIPS reserved keywords for suggestions.
    """

    def __init__(self, console, parent=None):
        """
        Initializes the command line input with history tracking and autocompletion.

        Args:
            console (CLIPSConsole): The main console widget that owns this input line.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.console = console 
        self.history = []
        self.history_index = 0
        self.temp_command = "" 
        
        self.completer_obj = QCompleter(self)
        self.completer_obj.setWidget(self)
        self.completer_obj.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer_obj.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.completion_model = QStringListModel()
        self.completer_obj.setModel(self.completion_model)
        
        self.clips_keywords = [
            "defrule", "deffacts", "deftemplate", "defglobal",
            "assert", "retract", "modify", "printout", 
            "facts", "agenda", "bind", "if", "then", "else", "crlf"
        ]
        
        self.completer_obj.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        """
        Appends the selected autocomplete word to the current cursor position.

        Args:
            completion (str): The word chosen by the user from the autocomplete popup.
        """
        extra = len(completion) - len(self.completer_obj.completionPrefix())
        if extra > 0:
            self.insert(completion[-extra:])

    def text_under_cursor(self):
        """
        Extracts the word or variable currently being typed directly behind the cursor.

        Returns:
            str: The active word.
        """
        pos = self.cursorPosition()
        text_to_cursor = self.text()[:pos]
        match = re.search(r'[\?a-zA-Z0-9_\-]+$', text_to_cursor)
        if match:
            return match.group(0)
        return ""

    def update_dictionary(self):
        """
        Dynamically extracts words and variables from the main console output and 
        current input line to populate the autocomplete suggestions list.
        """
        console_text = self.console.text_area.toPlainText()
        line_text = self.text()
        total_text = console_text + " " + line_text
        
        doc_words = re.findall(r'\b[a-zA-Z_0-9\-]+\b', total_text)
        all_words = sorted(list(set(self.clips_keywords + doc_words)))
        self.completion_model.setStringList(all_words)

    def add_history(self, command):
        """
        Saves a command to the execution history if it is not empty and not identical 
        to the most recent entry.

        Args:
            command (str): The executed command string.
        """
        if command:
            if not self.history or self.history[-1] != command:
                self.history.append(command)
            self.history_index = len(self.history)

    def keyPressEvent(self, event):
        """
        Overrides default keyboard events to handle history navigation (Up/Down),
        parenthesis auto-closure, and autocomplete popup shortcuts.

        Args:
            event (QKeyEvent): The key press event object.
        """
        popup_visible = self.completer_obj.popup() and self.completer_obj.popup().isVisible()

        # Parenthesis auto-close logic
        if event.text() == "(":
            super().keyPressEvent(event) 
            pos = self.cursorPosition()
            self.insert(")")             
            self.setCursorPosition(pos)  
            return
            
        if event.text() == ")":
            pos = self.cursorPosition()
            if pos < len(self.text()) and self.text()[pos] == ")":
                self.setCursorPosition(pos + 1)
                return

        # History Navigation (Up Arrow)
        if event.key() == Qt.Key.Key_Up and not popup_visible:
            if self.history_index > 0:
                if self.history_index == len(self.history):
                    self.temp_command = self.text()
                self.history_index -= 1
                self.setText(self.history[self.history_index])
            return
            
        # History Navigation (Down Arrow)
        elif event.key() == Qt.Key.Key_Down and not popup_visible:
            if self.history_index < len(self.history):
                self.history_index += 1
                if self.history_index == len(self.history):
                    self.setText(self.temp_command)
                else:
                    self.setText(self.history[self.history_index])
            return

        is_popup_shortcut = event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
        if popup_visible and is_popup_shortcut:
            event.ignore()
            return

        super().keyPressEvent(event)

        ignore_keys = [Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta]
        if event.key() in ignore_keys or not event.text():
            return

        # Autocomplete evaluation
        current_word = self.text_under_cursor()
        
        if len(current_word) >= 2:
            self.update_dictionary()
            
            if current_word != self.completer_obj.completionPrefix():
                self.completer_obj.setCompletionPrefix(current_word)
                self.completer_obj.popup().setCurrentIndex(self.completer_obj.completionModel().index(0, 0))
            
            cr = self.cursorRect()
            cr.setWidth(self.completer_obj.popup().sizeHintForColumn(0) + self.completer_obj.popup().verticalScrollBar().sizeHint().width())
            self.completer_obj.complete(cr)
        else:
            self.completer_obj.popup().hide()

class CLIPSRouter(clips.Router):
    """
    A thread-safe CLIPS router that captures engine outputs and safely 
    transmits them to the PyQt GUI main thread using signals.
    It includes a buffering mechanism to prevent GUI freezing during heavy loops.
    """
    def __init__(self, console):
        super().__init__('ide_router', 30)
        self.console = console
        self.bridge = RouterSignals()
        self.bridge.signal_print.connect(self.console.write_routed)
        
        self.buffering = False
        self.buffer = []

    def query(self, router_name):
        return router_name in ("stdout", "wdisplay", "werror", "wtrace", "t")

    def write(self, router_name, text):
        if self.buffering:
            self.buffer.append((router_name, text))
        else:
            self.bridge.signal_print.emit(router_name, text)

    def enable_buffering(self, state):
        """Toggles silent memory buffering."""
        self.buffering = state

    def flush(self):
        """
        Dumps the entire memory buffer to the GUI in one go.
        Batches consecutive messages from the same router to reduce calls to the GUI.
        """
        if not self.buffer:
            return
            
        current_router = self.buffer[0][0]
        accumulated_text = ""
        
        for r_name, txt in self.buffer:
            if r_name == current_router:
                accumulated_text += txt
            else:
                self.bridge.signal_print.emit(current_router, accumulated_text)
                current_router = r_name
                accumulated_text = txt
                
        if accumulated_text:
            self.bridge.signal_print.emit(current_router, accumulated_text)
            
        self.buffer.clear()

class RouterSignals(QObject):
    signal_print = pyqtSignal(str, str)