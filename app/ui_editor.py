import re

from PyQt6.QtWidgets import QTextEdit, QWidget, QPlainTextEdit, QCompleter

from PyQt6.QtCore import (
    Qt,
    QRegularExpression, QRect, QSize,
    QStringListModel, QTimer
)

from PyQt6.QtGui import (
    QFont, QSyntaxHighlighter, QTextCharFormat,
    QColor, QPainter, QTextFormat,
    QTextCursor
)

class CLIPSEditor(QPlainTextEdit): 
    """
    A custom plain text editor specifically tailored for writing CLIPS code.
    It features real-time syntax highlighting, parenthesis matching/linting,
    code folding (collapsing blocks), and intelligent autocomplete functionality.

    Attributes:
        is_dark_mode (bool): Tracks the current theme to adjust highlighting colors.
        highlighter (CLIPSHighlighter): The syntax highlighting logic processor.
        error_selections (list): Stores active text selections indicating syntax errors.
        folding_regions (dict): Maps the start line of a block to its end line.
        folded_blocks (set): Tracks which block starts (line numbers) are currently collapsed.
        linting_timer (QTimer): Delays linting execution while the user is typing actively.
        line_number_area (LineNumberArea): The left margin widget showing line numbers and folding icons.
        completer (QCompleter): The popup widget providing autocomplete suggestions.
    """

    def __init__(self, parent=None):
        """
        Initializes the CLIPS editor, configuring fonts, margins, autocompletion models, 
        and event connections.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.is_dark_mode = True
        
        font = QFont("Courier", 12) 
        self.setFont(font)
        self.setPlaceholderText("; Write your CLIPS code here...\n")
        
        self.highlighter = CLIPSHighlighter(self.document())
        
        self.error_selections = []
        self.folding_regions = {} 
        self.folded_blocks = set() 
        
        # Debounce the linting process so it doesn't lag the editor while typing
        self.linting_timer = QTimer(self)
        self.linting_timer.setSingleShot(True)
        self.linting_timer.timeout.connect(self.run_linting)
        self.document().contentsChange.connect(lambda: self.linting_timer.start(800)) 
        
        self.line_number_area = LineNumberArea(self)
        
        self.blockCountChanged.connect(self.update_margin_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_margin_width(0)
        self.highlight_current_line()

        # Autocomplete configuration
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.completion_model = QStringListModel()
        self.completer.setModel(self.completion_model)
        
        self.clips_keywords = [
            "defrule", "deffacts", "deftemplate", "defglobal",
            "assert", "retract", "modify", "printout", 
            "facts", "agenda", "bind", "if", "then", "else", "crlf"
        ]
        
        self.completer.activated.connect(self.insert_completion)

    def set_theme(self, is_dark):
        """
        Updates the editor's visual theme variables based on the application's global theme.

        Args:
            is_dark (bool): True to apply dark mode colors, False for light mode.
        """
        self.is_dark_mode = is_dark
        self.highlight_current_line()
        self.line_number_area.update()

    def run_linting(self):
        """
        Performs basic syntax checking. Specifically, it tracks parenthesis balance to underline 
        unclosed/unopened parentheses in red. It also recalculates the foldable block regions 
        (e.g., (defrule ... ) blocks) for the margin area.
        """
        text = self.toPlainText()
        stack = []
        errors = []
        
        for i, char in enumerate(text):
            if char == '(': stack.append(i)
            elif char == ')':
                if stack: stack.pop()
                else: errors.append(i) 
        errors.extend(stack) 
        
        self.error_selections = []
        error_format = QTextCharFormat()
        error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        error_format.setUnderlineColor(QColor("#ef4444"))
        
        for pos in errors:
            sel = QTextEdit.ExtraSelection()
            c = self.textCursor()
            c.setPosition(pos)
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            sel.format = error_format
            sel.cursor = c
            self.error_selections.append(sel)
            
        new_regions = {}
        doc = self.document()
        for i in range(doc.blockCount()):
            block = doc.findBlockByNumber(i)
            txt = block.text().lstrip()
            if txt.startswith("(def"):
                start_pos = block.position() + block.text().find("(def")
                end_pos = self._find_matching(text, start_pos, 1, '(', ')')
                
                if end_pos != -1:
                    end_block = doc.findBlock(end_pos).blockNumber()
                    if end_block > i:
                        new_regions[i] = end_block
                        
        self.folding_regions = new_regions
        self.folded_blocks = {b for b in self.folded_blocks if b in self.folding_regions}
        
        self.highlight_current_line()
        self.line_number_area.update()

    def toggle_folding(self, start_block):
        """
        Expands or collapses a block of code spanning from start_block to its pre-calculated end_block.

        Args:
            start_block (int): The line index where the foldable construct begins.
        """
        if start_block not in self.folding_regions: return
        end_block = self.folding_regions[start_block]
        is_folded = start_block in self.folded_blocks
        
        if is_folded: self.folded_blocks.remove(start_block)
        else: self.folded_blocks.add(start_block)
            
        doc = self.document()
        for i in range(start_block + 1, end_block + 1):
            doc.findBlockByNumber(i).setVisible(is_folded)
            
        self.document().markContentsDirty(doc.findBlockByNumber(start_block).position(), 
                                          doc.findBlockByNumber(end_block).position() - doc.findBlockByNumber(start_block).position())
        self.viewport().update()
        self.line_number_area.update()

    def _find_matching(self, text, pos, direction, char_open, char_close):
        """
        Utility function to locate the index of a matching parenthesis.

        Args:
            text (str): The full text being analyzed.
            pos (int): The starting index of the opening/closing character.
            direction (int): 1 to search forwards, -1 to search backwards.
            char_open (str): The character representing opening (e.g., '(').
            char_close (str): The character representing closing (e.g., ')').

        Returns:
            int: The index of the matching character, or -1 if none is found.
        """
        stack = 0
        i = pos
        while 0 <= i < len(text):
            if text[i] == char_open: stack += 1
            elif text[i] == char_close: stack -= 1
            if stack == 0: return i
            i += direction
        return -1

    def insert_completion(self, completion):
        """
        Inserts the selected autocomplete word into the text document at the cursor position.

        Args:
            completion (str): The word chosen from the autocomplete popup.
        """
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self):
        """
        Extracts the word or CLIPS variable (starting with '?') directly immediately behind the cursor.

        Returns:
            str: The active word being typed.
        """
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.LineUnderCursor)
        full_line = tc.selectedText()
        col_pos = self.textCursor().positionInBlock()
        text_to_cursor = full_line[:col_pos]
        
        match = re.search(r'[\?a-zA-Z0-9_\-]+$', text_to_cursor)
        if match: return match.group(0)
        return ""

    def update_dictionary(self):
        """
        Scans the current document text to dynamically extract custom variables and 
        combines them with standard CLIPS keywords to update the autocomplete suggestions list.
        """
        text = self.toPlainText()
        doc_words = re.findall(r'\b[a-zA-Z_0-9\-]+\b', text)
        all_words = sorted(list(set(self.clips_keywords + doc_words)))
        self.completion_model.setStringList(all_words)

    def keyPressEvent(self, event):
        """
        Overrides default keystroke behavior to provide automatic parenthesis closure
        and manage the autocomplete popup interactions.

        Args:
            event (QKeyEvent): The key press event object.
        """
        # Auto-close parenthesis
        if event.text() == "(":
            super().keyPressEvent(event)
            tc = self.textCursor()
            tc.insertText(")")
            tc.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(tc)
            return
            
        # Avoid duplicating closing parentheses if user types it manually over an auto-closed one
        if event.text() == ")":
            tc = self.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            if tc.selectedText() == ")":
                tc.clearSelection()
                self.setTextCursor(tc)
                return

        # Let the completer handle specific navigation keys if the popup is visible
        is_popup_shortcut = event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
        if self.completer.popup() and self.completer.popup().isVisible():
            if is_popup_shortcut:
                event.ignore()
                return

        super().keyPressEvent(event)

        ignore_keys = [Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta]
        if event.key() in ignore_keys or not event.text(): return

        # Evaluate word typed to trigger autocompletion popup
        current_word = self.text_under_cursor()
        if len(current_word) >= 2:
            self.update_dictionary()
            if current_word != self.completer.completionPrefix():
                self.completer.setCompletionPrefix(current_word)
                self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))
            
            cr = self.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def line_number_area_width(self):
        """
        Calculates the required width of the margin area based on the number of lines in the document.

        Returns:
            int: The calculated pixel width.
        """
        digits = 1
        maximum = max(1, self.blockCount())
        while maximum >= 10:
            maximum /= 10
            digits += 1
        return 25 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_margin_width(self, _):
        """
        Updates the editor's left viewport margin to accommodate the line number area.
        """
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """
        Keeps the line number area in sync when the document is scrolled or edited.

        Args:
            rect (QRect): The rectangle that needs updating.
            dy (int): The scroll vertical delta.
        """
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.update_margin_width(0)

    def resizeEvent(self, event):
        """
        Ensures the margin area is resized properly alongside the main editor window.

        Args:
            event (QResizeEvent): The resize event.
        """
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        """
        Applies a subtle background color to the line currently containing the cursor.
        It also dynamically boldens and colors matching parentheses if the cursor is near them.
        """
        selections = []
        if not self.isReadOnly():
            line_selection = QTextEdit.ExtraSelection()
            bg_color = QColor("#282828") if self.is_dark_mode else QColor("#e8e8e8")
            line_selection.format.setBackground(bg_color)
            line_selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            line_selection.cursor = self.textCursor()
            line_selection.cursor.clearSelection()
            selections.append(line_selection)

        pos = self.textCursor().position()
        text = self.toPlainText()
        char_pos = -1
        
        # Check if cursor is adjacent to a parenthesis
        if pos < len(text) and text[pos] in "()": char_pos = pos
        elif pos > 0 and text[pos-1] in "()": char_pos = pos - 1
            
        if char_pos != -1:
            char = text[char_pos]
            match_pos = -1
            if char == '(': match_pos = self._find_matching(text, char_pos, 1, '(', ')')
            elif char == ')': match_pos = self._find_matching(text, char_pos, -1, ')', '(')
            
            if match_pos != -1:
                paren_format = QTextCharFormat()
                bg_paren = QColor("#4d4d4d") if self.is_dark_mode else QColor("#d1d5db")
                fg_paren = QColor("#a855f7") if self.is_dark_mode else QColor("#7e22ce")
                paren_format.setBackground(bg_paren)
                paren_format.setForeground(fg_paren)
                paren_format.setFontWeight(QFont.Weight.Bold)
                
                for p in [char_pos, match_pos]:
                    sel = QTextEdit.ExtraSelection()
                    c = self.textCursor()
                    c.setPosition(p)
                    c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
                    sel.format = paren_format
                    sel.cursor = c
                    selections.append(sel)
                    
        # Append error linting rules to the selection array
        if hasattr(self, 'error_selections'):
            selections.extend(self.error_selections)
        self.setExtraSelections(selections)

    def paint_line_number_area(self, event):
        """
        Draws the line numbers and the [+] or [-] code folding icons in the margin area.

        Args:
            event (QPaintEvent): The paint event specifying the area to redraw.
        """
        painter = QPainter(self.line_number_area)
        bg_margin = QColor("#1e1e1e") if self.is_dark_mode else QColor("#f3f3f3")
        
        painter.fillRect(event.rect(), bg_margin)
        
        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_num + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(0, top, self.line_number_area.width() - 20, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
                
                # Draw folding indicators if block is collapsible
                if block_num in self.folding_regions:
                    is_folded = block_num in self.folded_blocks
                    
                    icon_size = 10
                    icon_x = self.line_number_area.width() - 15
                    icon_y = top + (self.fontMetrics().height() - icon_size) // 2
                    
                    painter.setPen(QColor("#858585"))
                    painter.drawRect(icon_x, icon_y, icon_size, icon_size)
                    
                    painter.drawLine(icon_x + 2, icon_y + icon_size // 2, 
                                     icon_x + icon_size - 2, icon_y + icon_size // 2)
                    if is_folded:
                        painter.drawLine(icon_x + icon_size // 2, icon_y + 2, 
                                         icon_x + icon_size // 2, icon_y + icon_size - 2)
                        
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_num += 1

class CLIPSHighlighter(QSyntaxHighlighter):
    """
    Provides syntax highlighting for the CLIPS programming language within a QTextDocument.
    It highlights keywords, variables, strings, and comments.

    Attributes:
        highlight_rules (list of tuple): A list containing pairs of QRegularExpression 
                                         and QTextCharFormat to apply to the document.
    """

    def __init__(self, document):
        """
        Initializes the syntax highlighter and sets up the matching rules and color formats.

        Args:
            document (QTextDocument): The text document to apply the highlighting to.
        """
        super().__init__(document)
        self.highlight_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            r"\bdefrule\b", r"\bdeffacts\b", r"\bdeftemplate\b", r"\bdefglobal\b",
            r"\bassert\b", r"\bretract\b", r"\bmodify\b", r"\bprintout\b", 
            r"\bfacts\b", r"\bagenda\b", r"\bbind\b", r"\bif\b", r"\bthen\b", r"\belse\b",
            r"=>", r"\bcrlf\b", r"\bt\b"
        ]
        for word in keywords:
            pattern = QRegularExpression(word)
            self.highlight_rules.append((pattern, keyword_format))

        # Format for Variables (start with '?' in CLIPS)
        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor("#9CDCFE"))
        var_pattern = QRegularExpression(r"\?[a-zA-Z0-9_\-]+")
        self.highlight_rules.append((var_pattern, variable_format))

        # Format for Strings ("text")
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        string_pattern = QRegularExpression(r"\".*?\"")
        self.highlight_rules.append((string_pattern, string_format))

        # Format for Comments (start with ';' to the end of the line)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        comment_format.setFontItalic(True)
        comment_pattern = QRegularExpression(r";[^\n]*")
        self.highlight_rules.append((comment_pattern, comment_format))

    def highlightBlock(self, text):
        """
        Internal PyQt method executed automatically line by line to apply the formats.

        Args:
            text (str): The block of text (usually a single line) to format.
        """
        for pattern, format in self.highlight_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class LineNumberArea(QWidget):
    """
    A custom widget used as the left margin area of the code editor.
    It displays line numbers and handles code folding interactions (the [+] and [-] icons).

    Attributes:
        editor (CLIPSEditor): The parent editor widget associated with this margin.
    """

    def __init__(self, editor):
        """
        Initializes the LineNumberArea widget.

        Args:
            editor (CLIPSEditor): The main code editor instance.
        """
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        """
        Returns the recommended size for the widget.

        Returns:
            QSize: The recommended dimensions based on the editor's required margin width.
        """
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        """
        Handles the painting of the widget, delegating the actual drawing to the editor.

        Args:
            event (QPaintEvent): The paint event containing the region to update.
        """
        self.editor.paint_line_number_area(event)

    def mousePressEvent(self, event):
        """
        Detects mouse clicks inside the margin to trigger code folding or unfolding.

        Args:
            event (QMouseEvent): The mouse event object containing click coordinates.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            block = self.editor.firstVisibleBlock()
            top = round(self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top())
            bottom = top + round(self.editor.blockBoundingRect(block).height())
            
            while block.isValid() and top <= self.rect().bottom():
                if block.isVisible() and bottom >= self.rect().top():
                    if top <= event.pos().y() <= bottom:
                        block_num = block.blockNumber()
                        if block_num in self.editor.folding_regions:
                            icon_x = self.width() - 20
                            if event.pos().x() >= icon_x:
                                self.editor.toggle_folding(block_num)
                                return
                block = block.next()
                top = bottom
                bottom = top + round(self.editor.blockBoundingRect(block).height())
        super().mousePressEvent(event)
