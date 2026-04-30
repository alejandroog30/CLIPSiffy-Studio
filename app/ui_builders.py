import re
import ast

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLineEdit,
    QPushButton, QMessageBox, QPlainTextEdit, QCompleter,
    QLabel, QStackedWidget, QFormLayout, QDoubleSpinBox,
    QComboBox, QSpinBox, QDialog, QTableWidget,
    QDialogButtonBox, QHeaderView
)

from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, pyqtSignal

from PyQt6.QtGui import QTextCursor

class FuzzyBuilderPanel(QDockWidget):
    """
    A dockable panel that provides a graphical interface for defining and updating
    Fuzzy Logic constructs (Systems, Variables, Sets, Rules) without writing CLIPS 
    code manually. It includes a rule translator from pseudo-code to CLIPS.
    """
    signal_insert_fact = pyqtSignal(str)

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.systems_cache = {}
        self.vars_by_system = {}
        self.sets_by_variable = {}
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "FuzzySystemConfig", "FuzzyVar", "FuzzySet", 
            "CrispInput", "Connection", "LinguisticModifier",
            "FuzzyRule"
        ])
        self.type_combo.currentIndexChanged.connect(self._change_form)
        
        self.stack = QStackedWidget()
        
        self._create_form_system()
        self._create_form_var()
        self._create_form_set()
        self._create_form_input()
        self._create_form_connection()
        self._create_form_modifier()
        self._create_form_rule()
        
        self.btn_create = QPushButton("ADD / UPDATE")
        self.btn_create.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 5px;")
        self.btn_create.clicked.connect(self._generate_fact)
        
        main_layout.addWidget(self.type_combo)
        main_layout.addWidget(self.stack)
        main_layout.addWidget(self.btn_create)
        
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

    def _create_form_system(self):
        w = QWidget(); l = QFormLayout(w)
        self.sys_id = QLineEdit()
        self.sys_id.editingFinished.connect(self._try_autocomplete) 
        
        self.sys_method = QComboBox(); self.sys_method.addItems(["mamdani", "sugeno"])
        self.sys_mf = QComboBox(); self.sys_mf.addItems(["1", "2"])
        self.sys_and = QLineEdit(); self.sys_and.setText("min")
        self.sys_or = QLineEdit(); self.sys_or.setText("max")
        self.sys_imp = QLineEdit(); self.sys_imp.setText("min")
        self.sys_agg = QLineEdit(); self.sys_agg.setText("max")
        self.sys_defuzz = QLineEdit(); self.sys_defuzz.setText("centroid")
        self.sys_res = QSpinBox(); self.sys_res.setRange(10, 10000); self.sys_res.setValue(100)
        
        l.addRow("System ID:", self.sys_id)
        l.addRow("Method Type:", self.sys_method)
        l.addRow("MF Type:", self.sys_mf)
        l.addRow("AND Method:", self.sys_and)
        l.addRow("OR Method:", self.sys_or)
        l.addRow("Imp Method:", self.sys_imp)
        l.addRow("Agg Method:", self.sys_agg)
        l.addRow("Defuzz Method:", self.sys_defuzz)
        l.addRow("Resolution:", self.sys_res)
        self.stack.addWidget(w)

    def _create_form_var(self):
        w = QWidget(); l = QFormLayout(w)
        self.var_sys = QComboBox() 
        self.var_sys.currentIndexChanged.connect(self._try_autocomplete) 
        
        self.var_name = QLineEdit()
        self.var_name.editingFinished.connect(self._try_autocomplete) 
        
        self.var_type = QComboBox(); self.var_type.addItems(["input", "output"])
        self.var_min = QDoubleSpinBox(); self.var_min.setRange(-99999, 99999); self.var_min.setDecimals(4); self.var_min.setValue(0.0)
        self.var_max = QDoubleSpinBox(); self.var_max.setRange(-99999, 99999); self.var_max.setDecimals(4); self.var_max.setValue(100.0)
        
        l.addRow("System:", self.var_sys)
        l.addRow("Var Name:", self.var_name)
        l.addRow("Type:", self.var_type)
        l.addRow("Min:", self.var_min)
        l.addRow("Max:", self.var_max)
        self.stack.addWidget(w)

    def _create_form_set(self):
        w = QWidget(); l = QFormLayout(w)
        self.set_var = QComboBox() 
        self.set_var.currentIndexChanged.connect(self._try_autocomplete)
        
        self.set_label = QLineEdit()
        self.set_label.editingFinished.connect(self._try_autocomplete)
        
        mf_functions = ["mf-triangular", "mf-trapezoidal", "mf-gaussian", "mf-gamma", "mf-l", "mf-s", "mf-z", "mf-pi"]
        
        self.set_mf = QComboBox(); self.set_mf.addItems(mf_functions)
        self.set_mf.setEditable(True) 
        
        self.set_params = QLineEdit(); self.set_params.setPlaceholderText("Ex: 10.0 20.0 30.0")
        
        self.set_l_mf = QComboBox(); self.set_l_mf.addItems(mf_functions)
        self.set_l_mf.setEditable(True) 
        
        self.set_l_params = QLineEdit(); self.set_l_params.setPlaceholderText("Optional (T2)")
        
        self.set_u_mf = QComboBox(); self.set_u_mf.addItems(mf_functions)
        self.set_u_mf.setEditable(True) 
        
        self.set_u_params = QLineEdit(); self.set_u_params.setPlaceholderText("Optional (T2)")
        
        l.addRow("Variable:", self.set_var)
        l.addRow("Label:", self.set_label)
        l.addRow("MF (T1/T2):", self.set_mf)
        l.addRow("Params:", self.set_params)
        l.addRow("Low MF (T2):", self.set_l_mf)
        l.addRow("Low Params:", self.set_l_params)
        l.addRow("Up MF (T2):", self.set_u_mf)
        l.addRow("Up Params:", self.set_u_params)
        self.stack.addWidget(w)

    def _create_form_input(self):
        w = QWidget(); l = QFormLayout(w)
        self.in_var = QComboBox() 
        self.in_var.currentIndexChanged.connect(self._try_autocomplete) 
        
        self.in_val = QDoubleSpinBox(); self.in_val.setRange(-99999, 99999); self.in_val.setDecimals(4)
        self.in_source = QLineEdit(); self.in_source.setText("user")
        
        l.addRow("Variable:", self.in_var)
        l.addRow("Crisp Value:", self.in_val)
        l.addRow("Source:", self.in_source)
        self.stack.addWidget(w)

    def _create_form_connection(self):
        w = QWidget(); l = QFormLayout(w)
        self.conn_from_sys = QComboBox()
        self.conn_from_var = QComboBox()
        self.conn_to_var = QComboBox()
        
        self.conn_from_sys.currentIndexChanged.connect(self._try_autocomplete)
        self.conn_from_var.currentIndexChanged.connect(self._try_autocomplete)
        self.conn_to_var.currentIndexChanged.connect(self._try_autocomplete)
        
        l.addRow("From System:", self.conn_from_sys)
        l.addRow("From Var:", self.conn_from_var)
        l.addRow("To Var:", self.conn_to_var)
        self.stack.addWidget(w)

    def _create_form_modifier(self):
        w = QWidget(); l = QFormLayout(w)
        self.mod_var = QComboBox()
        self.mod_var.currentIndexChanged.connect(self._try_autocomplete) 
        
        self.mod_base = QComboBox()
        self.mod_new = QLineEdit()
        self.mod_new.editingFinished.connect(self._try_autocomplete) 
        
        self.mod_func = QComboBox(); self.mod_func.addItems(["mod-very", "mod-somewhat", "mod-extremely"])
        
        l.addRow("Variable:", self.mod_var)
        l.addRow("Base Label:", self.mod_base)
        l.addRow("New Label:", self.mod_new)
        l.addRow("Modifier:", self.mod_func)
        self.stack.addWidget(w)

    def _create_form_rule(self):
        w = QWidget()
        l = QVBoxLayout(w)
        
        form = QFormLayout()
        self.rule_sys = QComboBox()
        self.rule_sys.currentIndexChanged.connect(self._check_rule_system_type)
        self.rule_name = QLineEdit()
        
        form.addRow("System ID:", self.rule_sys)
        form.addRow("Rule Name:", self.rule_name)
        
        self.rule_text = FuzzyRulesEditor()
        self.rule_text.setPlaceholderText("Mamdani: IF Temp=Cold THEN Vel=Fast\nSugeno: IF Temp=Cold THEN Vel=10+Temp*15+Pressure*12")
        self.rule_text.setMinimumHeight(100)
        
        l.addLayout(form)
        
        self.btn_open_matrix = QPushButton("OPEN 2D FAM MATRIX EDITOR")
        self.btn_open_matrix.setStyleSheet("background-color: #a855f7; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.btn_open_matrix.clicked.connect(self._open_matrix_editor)
        l.addWidget(self.btn_open_matrix)
        
        l.addWidget(QLabel("<b>Logic structure (IF ... THEN ...):</b>"))
        l.addWidget(self.rule_text)
        
        self.stack.addWidget(w)

    def _try_autocomplete(self):
        if not hasattr(self.parent(), 'env'): return
        env = self.parent().env
        idx = self.stack.currentIndex()
        
        def safe_get(fact, slot, default=""):
            try: return str(fact[slot]) if fact[slot] is not None else default
            except: return default

        def safe_get_list(fact, slot):
            try: return " ".join([str(x) for x in fact[slot]]) if fact[slot] is not None else ""
            except: return ""

        for f in env.facts():
            template = f.template.name
            
            if idx == 0 and template == "FuzzySystemConfig":
                if safe_get(f, "id") == self.sys_id.text().strip():
                    self.sys_method.setCurrentText(safe_get(f, "method-type", "mamdani"))
                    self.sys_mf.setCurrentText(safe_get(f, "mf-type", "1"))
                    self.sys_and.setText(safe_get(f, "and-method", "min"))
                    self.sys_or.setText(safe_get(f, "or-method", "max"))
                    self.sys_imp.setText(safe_get(f, "imp-method", "min"))
                    self.sys_agg.setText(safe_get(f, "agg-method", "max"))
                    self.sys_defuzz.setText(safe_get(f, "defuzz-method", "centroid"))
                    try: self.sys_res.setValue(int(safe_get(f, "resolution", "100")))
                    except: pass
                    break
                    
            elif idx == 1 and template == "FuzzyVar":
                if safe_get(f, "system-id") == self.var_sys.currentText() and safe_get(f, "name") == self.var_name.text().strip():
                    self.var_type.setCurrentText(safe_get(f, "type", "input"))
                    try: 
                        self.var_min.setValue(float(safe_get(f, "min", "0.0")))
                        self.var_max.setValue(float(safe_get(f, "max", "100.0")))
                    except: pass
                    break
                    
            elif idx == 2 and template == "FuzzySet":
                if safe_get(f, "var-name") == self.set_var.currentText() and safe_get(f, "label") == self.set_label.text().strip():
                    self.set_mf.setCurrentText(safe_get(f, "mf", ""))
                    self.set_params.setText(safe_get_list(f, "params"))
                    self.set_l_mf.setCurrentText(safe_get(f, "l-mf", ""))
                    self.set_l_params.setText(safe_get_list(f, "l-params"))
                    self.set_u_mf.setCurrentText(safe_get(f, "u-mf", ""))
                    self.set_u_params.setText(safe_get_list(f, "u-params"))
                    break
                    
            elif idx == 3 and template == "CrispInput":
                if safe_get(f, "var-name") == self.in_var.currentText():
                    try: self.in_val.setValue(float(safe_get(f, "value", "0.0")))
                    except: pass
                    self.in_source.setText(safe_get(f, "source-system", "user"))
                    break
                    
            elif idx == 5 and template == "LinguisticModifier":
                if safe_get(f, "var-name") == self.mod_var.currentText() and safe_get(f, "new-label") == self.mod_new.text().strip():
                    self.mod_base.setCurrentText(safe_get(f, "base-label", ""))
                    self.mod_func.setCurrentText(safe_get(f, "modifier", "mod-very"))
                    break

    def _change_form(self, index):
        self.stack.setCurrentIndex(index)
        self.update_data(self.parent().env if hasattr(self.parent(), 'env') else None)

    def update_data(self, env):
        if not env: return
        systems = []; variables = []; variables_in = []; variables_out = []; sets = []
        
        self.systems_cache.clear()
        self.vars_by_system.clear()
        self.sets_by_variable.clear()

        for f in env.facts():
            if f.template.name == "FuzzySystemConfig": 
                sid = str(f["id"])
                systems.append(sid)
                self.systems_cache[sid] = {"method": str(f["method-type"]), "mf": int(f["mf-type"])}
            
            elif f.template.name == "FuzzyVar": 
                vname = str(f["name"])
                sys_id = str(f["system-id"])
                vtype = str(f["type"])
                variables.append(vname)
                
                if sys_id not in self.vars_by_system: 
                    self.vars_by_system[sys_id] = {"input": [], "output": []}
                self.vars_by_system[sys_id][vtype].append(vname)
                
                if vtype == "input": variables_in.append(vname)
                else: variables_out.append(vname)
            
            elif f.template.name == "FuzzySet": 
                vname = str(f["var-name"])
                lbl = str(f["label"])
                sets.append((vname, lbl))
                
                if vname not in self.sets_by_variable: self.sets_by_variable[vname] = []
                self.sets_by_variable[vname].append(lbl)

        def refresh_combo(combo, items):
            sel = combo.currentText()
            combo.clear()
            combo.addItems(list(set(items)))
            if sel in items: combo.setCurrentText(sel)

        self.var_sys.blockSignals(True)
        self.set_var.blockSignals(True)
        self.in_var.blockSignals(True)
        self.conn_from_sys.blockSignals(True)
        self.mod_var.blockSignals(True)

        refresh_combo(self.var_sys, systems)
        refresh_combo(self.set_var, variables)
        refresh_combo(self.in_var, variables_in)
        refresh_combo(self.conn_from_sys, systems)
        refresh_combo(self.conn_from_var, variables_out)
        refresh_combo(self.conn_to_var, variables_in)
        refresh_combo(self.mod_var, variables)
        refresh_combo(self.rule_sys, systems)
        
        base_labels = [c[1] for c in sets if c[0] == self.mod_var.currentText()]
        refresh_combo(self.mod_base, base_labels)

        self.var_sys.blockSignals(False)
        self.set_var.blockSignals(False)
        self.in_var.blockSignals(False)
        self.conn_from_sys.blockSignals(False)
        self.mod_var.blockSignals(False)

        idx = self.stack.currentIndex()
        enabled = True
        if idx in [1, 6] and not systems: enabled = False
        elif idx == 2 and not variables: enabled = False
        elif idx == 3 and not variables_in: enabled = False
        elif idx == 4 and (not systems or not variables_out or not variables_in): enabled = False
        elif idx == 5 and not base_labels: enabled = False
        
        self.btn_create.setEnabled(enabled)
        self.btn_create.setText("ADD / UPDATE" if enabled else "NOT ENOUGH FACTS")
        self._check_rule_system_type()

    def _check_rule_system_type(self):
        sid = self.rule_sys.currentText()
        suggestions = []
        if sid in self.vars_by_system:
            all_vars = self.vars_by_system[sid]["input"] + self.vars_by_system[sid]["output"]
            for vname in all_vars:
                suggestions.append(vname) 
                if vname in self.sets_by_variable:
                    for lbl in self.sets_by_variable[vname]:
                        suggestions.append(f"{vname}={lbl}")
        self.rule_text.update_dictionary(suggestions)

    def _open_matrix_editor(self):
        """Validates the system, opens the FAM Matrix Editor, and injects rules individually."""
        sys_id = self.rule_sys.currentText()
        if not sys_id: 
            return
            
        var_dict = self.vars_by_system.get(sys_id, {"input": [], "output": []})
        inputs = var_dict["input"]
        outputs = var_dict["output"]
        
        if len(inputs) != 2 or len(outputs) != 1:
            QMessageBox.warning(self, "Invalid Dimensions", 
                                "The FAM Matrix Editor requires the system to have EXACTLY 2 input variables and 1 output variable.")
            return
            
        config = self.systems_cache.get(sys_id, {"method": "mamdani", "mf": 1})
        is_sugeno = (config["method"] == "sugeno")
        
        dialog = FAMMatrixDialog(sys_id, inputs[0], inputs[1], outputs[0], self.sets_by_variable, is_sugeno, self)
        
        if dialog.exec():
            rules_data = dialog.get_rules_pseudo_code()
            if not rules_data: return
            
            if not hasattr(self.parent(), 'env'):
                return
            env = self.parent().env
            
            success_count = 0
            errors = 0
            error_msgs = []
            
            for r_name, pseudo in rules_data:
                try:
                    rule_str = self._translate_logic_rule(custom_sys_id=sys_id, custom_rule_name=r_name, custom_text=pseudo)
                    env.build(rule_str)
                    success_count += 1
                except Exception as e:
                    errors += 1
                    error_msgs.append(f"{r_name}: {str(e)}")
            
            if hasattr(self.parent(), 'update_memory_views'):
                self.parent().update_memory_views()
                
            if hasattr(self.parent(), 'console'):
                self.parent().console.write(f"\n> [FAM MATRIX] Automatically generated and injected {success_count} rules for system '{sys_id}'.")
            
            if errors == 0:
                QMessageBox.information(self, "Success", f"Successfully generated and injected {success_count} rules from the FAM Matrix.")
            else:
                err_text = "\n".join(error_msgs[:5])
                QMessageBox.warning(self, "Partial Success", f"Injected {success_count} rules, but {errors} failed.\nErrors:\n{err_text}")

    def _generate_fact(self):
        if hasattr(self.parent(), 'env'):
            env = self.parent().env
            
            try:
                engine_templates = [str(p) for p in env.eval("(get-deftemplate-list *)")]
                library_loaded = any("FuzzySystemConfig" in p for p in engine_templates)
                
                if not library_loaded:
                    QMessageBox.warning(
                        self, 
                        "Fuzzy Library Missing", 
                        "Warning! Code cannot be injected because the Fuzzy library is not loaded in the current memory.\n\n"
                        "Please press F4 or go to 'Run -> Load Environment' to load the base library."
                    )
                    return 
            except Exception:
                pass 

        idx = self.stack.currentIndex()
        
        if idx == 6: 
            try:
                clips_rule = self._translate_logic_rule()
                self.signal_insert_fact.emit(clips_rule)
                self.rule_text.clear()
            except Exception as e:
                QMessageBox.critical(self, "Fuzzy Syntax Error", str(e))
            return

        h = ""
        retract_cmd = ""
        
        if idx == 0:
            sys_id = self.sys_id.text().strip()
            if not sys_id: return
            retract_cmd = f'(do-for-all-facts ((?f FuzzySystemConfig)) (eq ?f:id {sys_id}) (retract ?f))'
            h = f"(FuzzySystemConfig (id {sys_id}) (method-type {self.sys_method.currentText()}) " \
                f"(mf-type {self.sys_mf.currentText()}) (and-method {self.sys_and.text()}) " \
                f"(or-method {self.sys_or.text()}) (imp-method {self.sys_imp.text()}) " \
                f"(agg-method {self.sys_agg.text()}) (defuzz-method {self.sys_defuzz.text()}) " \
                f"(resolution {self.sys_res.value()}))"
                
        elif idx == 1:
            sys_id = self.var_sys.currentText()
            name = self.var_name.text().strip()
            if not name: return
            retract_cmd = f'(do-for-all-facts ((?f FuzzyVar)) (and (eq ?f:system-id {sys_id}) (eq ?f:name {name})) (retract ?f))'
            h = f"(FuzzyVar (system-id {sys_id}) (name {name}) " \
                f"(type {self.var_type.currentText()}) (min {self.var_min.value()}) (max {self.var_max.value()}))"
                
        elif idx == 2:
            var_name = self.set_var.currentText()
            label = self.set_label.text().strip()
            if not label: return
            retract_cmd = f'(do-for-all-facts ((?f FuzzySet)) (and (eq ?f:var-name {var_name}) (eq ?f:label {label})) (retract ?f))'
            base = f"(FuzzySet (var-name {var_name}) (label {label}) " \
                   f"(mf {self.set_mf.currentText()}) (params {self.set_params.text()})"
            if self.set_l_mf.currentText() and self.set_l_params.text():
                base += f" (l-mf {self.set_l_mf.currentText()}) (l-params {self.set_l_params.text()})"
            if self.set_u_mf.currentText() and self.set_u_params.text():
                base += f" (u-mf {self.set_u_mf.currentText()}) (u-params {self.set_u_params.text()})"
            h = base + ")"
            
        elif idx == 3:
            var_name = self.in_var.currentText()
            retract_cmd = f'(do-for-all-facts ((?f CrispInput)) (eq ?f:var-name {var_name}) (retract ?f))'
            h = f"(CrispInput (var-name {var_name}) (value {self.in_val.value()}) " \
                f"(source-system {self.in_source.text()}))"
                
        elif idx == 4:
            from_sys = self.conn_from_sys.currentText()
            from_var = self.conn_from_var.currentText()
            to_var = self.conn_to_var.currentText()
            retract_cmd = f'(do-for-all-facts ((?f Connection)) (and (eq ?f:from-system {from_sys}) ' \
                          f'(eq ?f:from-var {from_var}) (eq ?f:to-var {to_var})) (retract ?f))'
            h = f"(Connection (from-system {from_sys}) (from-var {from_var}) (to-var {to_var}))"
            
        elif idx == 5:
            var_name = self.mod_var.currentText()
            new_label = self.mod_new.text().strip()
            if not new_label: return
            retract_cmd = f'(do-for-all-facts ((?f LinguisticModifier)) (and (eq ?f:var-name {var_name}) ' \
                          f'(eq ?f:new-label {new_label})) (retract ?f))'
            h = f"(LinguisticModifier (var-name {var_name}) (base-label {self.mod_base.currentText()}) " \
                f"(new-label {new_label}) (modifier {self.mod_func.currentText()}))"
        
        if h:
            if hasattr(self.parent(), 'env') and retract_cmd:
                self.parent().env.eval(retract_cmd)
                
            self.signal_insert_fact.emit(f"(assert {h})")

    def _translate_logic_rule(self, custom_sys_id=None, custom_rule_name=None, custom_text=None):
        sys_id = custom_sys_id or self.rule_sys.currentText()
        rule_name = custom_rule_name or self.rule_name.text().strip()
        text = custom_text or self.rule_text.toPlainText().replace('\n', ' ').strip()
        
        if not sys_id or not rule_name:
            raise ValueError("You must specify the System and a Name for the rule.")
        if not text.upper().startswith("IF ") or " THEN " not in text.upper():
            raise ValueError("The rule must have the strict format 'IF ... THEN ...'")

        config = self.systems_cache.get(sys_id, {"method": "mamdani", "mf": 1})
        is_sugeno = (config["method"] == "sugeno")
        is_type2 = (config["mf"] == 2)
        
        idx_then = text.upper().find(" THEN ")
        lhs = text[3:idx_then].strip()
        rhs = text[idx_then + 6:].strip()
        
        rhs = re.sub(r'\s*=\s*', '=', rhs) 
        if "=" not in rhs:
            raise ValueError("The consequent must be Var=Label (or Var=Expression for Sugeno)")
            
        out_var, out_expr = rhs.split("=", 1)
        
        lhs = re.sub(r'\s*=\s*', '=', lhs) 
        raw_pairs = re.findall(r'([a-zA-Z0-9_\-]+=[a-zA-Z0-9_\-]+)', lhs)
        unique_pairs = list(dict.fromkeys(raw_pairs)) 
        
        mapping = {par: f"v{i+1}" for i, par in enumerate(unique_pairs)}
        
        py_expr = lhs
        py_expr = re.sub(r'\bAND\b', 'and', py_expr, flags=re.IGNORECASE)
        py_expr = re.sub(r'\bOR\b', 'or', py_expr, flags=re.IGNORECASE)
        for par, var_id in mapping.items():
            py_expr = py_expr.replace(par, var_id)
            
        try:
            tree = ast.parse(py_expr, mode='eval').body
        except SyntaxError:
            raise ValueError("There is an error in the parentheses or the use of AND / OR in the antecedents.")

        def ast_to_clips(node, prefix):
            if isinstance(node, ast.Name):
                return f"?{prefix}{node.id[1:]}" 
            elif isinstance(node, ast.BoolOp):
                op = "?and" if isinstance(node.op, ast.And) else "?or"
                args = [ast_to_clips(val, prefix) for val in node.values]
                return f"(funcall {op} " + " ".join(args) + ")"
            return ""

        inputs_str = ""
        antecedent_list = []
        
        for i, par in enumerate(unique_pairs):
            v, l = par.split("=")
            antecedent_list.extend([v, l])
            if is_type2:
                inputs_str += f"    (FuzzyInput (var-name {v}) (label {l}) (l-mu ?l{i+1}) (u-mu ?u{i+1}))\n"
            else:
                inputs_str += f"    (FuzzyInput (var-name {v}) (label {l}) (mu ?mu{i+1}))\n"
                
        antecedents_str = " ".join(antecedent_list)
        
        out_lbl = out_expr
        y_val_str = ""
        
        if is_sugeno:
            out_lbl = "sugeno_calc" 
            try:
                math_tree = ast.parse(out_expr, mode='eval').body
            except SyntaxError:
                raise ValueError(f"Syntax error in Sugeno's mathematical equation: '{out_expr}'")

            def math_ast_to_clips(node):
                if isinstance(node, ast.Constant): return str(node.value)
                elif isinstance(node, ast.Num): return str(node.n) 
                elif isinstance(node, ast.Name): return f"?crisp_{node.id}"
                elif isinstance(node, ast.BinOp):
                    op_map = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}
                    if type(node.op) not in op_map:
                        raise ValueError(f"Unsupported operator: {type(node.op)}")
                    return f"({op_map[type(node.op)]} {math_ast_to_clips(node.left)} {math_ast_to_clips(node.right)})"
                elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                    return f"(- 0 {math_ast_to_clips(node.operand)})"
                else:
                    raise ValueError("Unsupported mathematical structure.")

            rhs_vars = sorted(list(set(node.id for node in ast.walk(math_tree) if isinstance(node, ast.Name))))
            
            for v in rhs_vars:
                inputs_str += f"    (CrispInput (var-name {v}) (value ?crisp_{v}))\n"

            clips_math = math_ast_to_clips(math_tree)
            y_val_str = f"\n        (y-value {clips_math})"
        
        if is_type2:
            binds_str = f"    (bind ?alpha-lower {ast_to_clips(tree, 'l')})\n"
            binds_str += f"    (bind ?alpha-upper {ast_to_clips(tree, 'u')})"
            strength_str = "        (l-strength ?alpha-lower)\n        (u-strength ?alpha-upper)"
        else:
            binds_str = f"    (bind ?alpha {ast_to_clips(tree, 'mu')})"
            strength_str = "        (strength ?alpha)"
            
        final_rule = f"""(defrule INFER::{rule_name}
    (FuzzySystemConfig (id {sys_id}) (and-method ?and) (or-method ?or))
{inputs_str}    =>
{binds_str}
    (assert (FuzzyRuleOutput 
        (system-id {sys_id})
        (rule-name {rule_name})
        (antecedents {antecedents_str})
        (var-name {out_var}) 
        (label {out_lbl}) 
{strength_str}{y_val_str})))"""

        return final_rule

class FuzzyRulesEditor(QPlainTextEdit):
    """
    A specialized plain text editor designed to facilitate the writing of linguistic 
    fuzzy rules (IF...THEN statements). It includes a customized autocompletion engine 
    that suggests logical operators, variable names, and variable=label pairs.

    Attributes:
        completer (QCompleter): The popup widget displaying autocomplete suggestions.
        completion_model (QStringListModel): The data model feeding the completer.
        keywords (list of str): Core logical operators for fuzzy rules.
    """

    def __init__(self, parent=None):
        """
        Initializes the fuzzy rules editor and configures the completer.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.completion_model = QStringListModel()
        self.completer.setModel(self.completion_model)
        self.completer.activated.connect(self.insert_completion)
        
        self.keywords = ["IF", "THEN", "AND", "OR"]

    def update_dictionary(self, system_suggestions):
        """
        Refreshes the autocomplete dictionary by combining base keywords with 
        dynamic system variables and labels provided by the parent panel.

        Args:
            system_suggestions (list of str): Dynamically generated suggestions (e.g., 'Temp=Cold').
        """
        all_words = sorted(list(set(self.keywords + system_suggestions)))
        self.completion_model.setStringList(all_words)

    def insert_completion(self, completion):
        """
        Inserts the selected suggestion into the editor.

        Args:
            completion (str): The fully expanded word/phrase selected by the user.
        """
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self):
        """
        Determines the current token being typed by the user directly behind the cursor,
        supporting complex variable-label formats (e.g., VarName=Value).

        Returns:
            str: The active token.
        """
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.LineUnderCursor)
        line = tc.selectedText()
        pos = self.textCursor().positionInBlock()
        text_to_cursor = line[:pos]
        
        match = re.search(r'[a-zA-Z0-9_\-]+(?:=[a-zA-Z0-9_\-]*)?$', text_to_cursor)
        if match:
            return match.group(0)
        return ""

    def keyPressEvent(self, event):
        """
        Overrides the default keyboard event handler to manage the display and 
        selection of autocomplete suggestions.

        Args:
            event (QKeyEvent): The key press event object.
        """
        is_popup_shortcut = event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
        if self.completer.popup() and self.completer.popup().isVisible():
            if is_popup_shortcut:
                event.ignore()
                return

        super().keyPressEvent(event)

        ignore_keys = [Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta]
        if event.key() in ignore_keys or not event.text() or event.text() == " ":
            self.completer.popup().hide()
            return

        current_word = self.text_under_cursor()
        
        if len(current_word) >= 1:
            if current_word != self.completer.completionPrefix():
                self.completer.setCompletionPrefix(current_word)
                self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))
            
            cr = self.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

class FAMMatrixDialog(QDialog):
    """
    A pop-up dialog that provides a 2D grid interface (Fuzzy Associative Memory)
    to quickly design and generate rule bases for 2-input fuzzy systems.
    """
    def __init__(self, sys_id, in_var1, in_var2, out_var, sets_by_var, is_sugeno, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"FAM Matrix Editor - System: {sys_id}")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("background-color: #1a1a1a; color: #d4d4d4;")
        
        self.sys_id = sys_id
        self.in_var1 = in_var1
        self.in_var2 = in_var2
        self.out_var = out_var
        self.is_sugeno = is_sugeno
        
        self.sets1 = sets_by_var.get(in_var1, [])
        self.sets2 = sets_by_var.get(in_var2, [])
        self.out_sets = sets_by_var.get(out_var, []) if not is_sugeno else []
        
        layout = QVBoxLayout(self)
        
        mode_text = "SUGENO (Type math equations or crisp values)" if is_sugeno else "MAMDANI (Select output labels)"
        info_html = f"""
        <div style='background-color: #2d2d2d; padding: 10px; border-radius: 5px;'>
            <b style='color: #a855f7;'>MODE:</b> {mode_text}<br>
            <b style='color: #3b82f6;'>ROWS (Input 1):</b> {in_var1}<br>
            <b style='color: #10b981;'>COLUMNS (Input 2):</b> {in_var2}<br>
            <b style='color: #f97316;'>OUTPUT:</b> {out_var}
        </div>
        """
        lbl_info = QLabel(info_html)
        layout.addWidget(lbl_info)
        
        self.table = QTableWidget(len(self.sets1), len(self.sets2))
        self.table.setVerticalHeaderLabels(self.sets1)
        self.table.setHorizontalHeaderLabels(self.sets2)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; gridline-color: #3d3d3d; }
            QHeaderView::section { background-color: #2d2d2d; color: white; font-weight: bold; padding: 4px; border: 1px solid #3d3d3d; }
            QTableCornerButton::section { background-color: #2d2d2d; }
        """)
        
        for i, s1 in enumerate(self.sets1):
            for j, s2 in enumerate(self.sets2):
                if self.is_sugeno:
                    edit = QLineEdit()
                    edit.setPlaceholderText("Leave empty to skip")
                    edit.setStyleSheet("background-color: #2d2d2d; border: 1px solid #555; padding: 5px;")
                    self.table.setCellWidget(i, j, edit)
                else:
                    combo = QComboBox()
                    combo.addItem("")
                    combo.addItems(self.out_sets)
                    combo.setStyleSheet("background-color: #2d2d2d; border: 1px solid #555;")
                    self.table.setCellWidget(i, j, combo)
                    
        layout.addWidget(self.table)
        
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.setStyleSheet("QPushButton { background-color: #007acc; color: white; padding: 6px 15px; font-weight: bold; }")
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        layout.addWidget(self.btn_box)
        
    def get_rules_pseudo_code(self):
        """Extracts the table data and formats it into pseudo-code logic strings."""
        rules = []
        for i, s1 in enumerate(self.sets1):
            for j, s2 in enumerate(self.sets2):
                widget = self.table.cellWidget(i, j)
                out_val = widget.text().strip() if self.is_sugeno else widget.currentText()
                    
                if out_val:
                    rule_name = f"fam_{self.sys_id}_{s1}_{s2}".lower().replace("-", "_")
                    pseudo = f"IF {self.in_var1}={s1} AND {self.in_var2}={s2} THEN {self.out_var}={out_val}"
                    rules.append((rule_name, pseudo))
        return rules

class EnvironmentBuilderPanel(QDockWidget):
    """
    A dockable panel that provides a graphical interface for defining and updating
    environment configurations without writing CLIPS code manually. It generates
    and asserts facts like EnvConfig, EnvVar, EnvEquation, and EnvLink.

    Attributes:
        signal_insert_fact (pyqtSignal): Emitted with the CLIPS string command to assert the new fact.
        type_combo (QComboBox): Dropdown to select the type of environment component to build.
        stack (QStackedWidget): Container holding the different input forms.
    """

    signal_insert_fact = pyqtSignal(str)

    def __init__(self, title, parent=None):
        """
        Initializes the environment builder panel and its sub-forms.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "EnvConfig", "EnvVar", "EnvEquation", "EnvLink"
        ])
        self.type_combo.currentIndexChanged.connect(self._change_form)
        
        self.stack = QStackedWidget()
        
        self._create_form_config()
        self._create_form_var()
        self._create_form_equation()
        self._create_form_link()
        
        self.btn_create = QPushButton("ADD / UPDATE ENVIRONMENT")
        self.btn_create.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 5px;")
        self.btn_create.clicked.connect(self._generate_fact)
        
        main_layout.addWidget(self.type_combo)
        main_layout.addWidget(self.stack)
        main_layout.addWidget(self.btn_create)
        
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

    def _create_form_config(self):
        """Creates the form layout for defining the main Environment Configuration."""
        w = QWidget(); l = QFormLayout(w)
        self.env_id = QLineEdit(); self.env_id.setText("env1")
        self.env_max_steps = QSpinBox(); self.env_max_steps.setRange(1, 10000); self.env_max_steps.setValue(100)
        self.env_dt = QDoubleSpinBox(); self.env_dt.setRange(0.001, 100.0); self.env_dt.setDecimals(3); self.env_dt.setValue(1.0)
        
        l.addRow("Env ID:", self.env_id)
        l.addRow("Max Steps:", self.env_max_steps)
        l.addRow("Delta T (dt):", self.env_dt)
        self.stack.addWidget(w)

    def _create_form_var(self):
        """Creates the form layout for defining Environment Variables."""
        w = QWidget(); l = QFormLayout(w)
        self.var_env_id = QLineEdit(); self.var_env_id.setText("env1")
        self.var_name = QLineEdit()
        self.var_val = QDoubleSpinBox(); self.var_val.setRange(-99999, 99999); self.var_val.setDecimals(4); self.var_val.setValue(0.0)
        
        l.addRow("Env ID:", self.var_env_id)
        l.addRow("Var Name:", self.var_name)
        l.addRow("Initial Value:", self.var_val)
        self.stack.addWidget(w)

    def _create_form_equation(self):
        """Creates the form layout for defining mathematical update Equations."""
        w = QWidget(); l = QFormLayout(w)
        self.eq_env_id = QLineEdit(); self.eq_env_id.setText("env1")
        self.eq_target = QLineEdit()
        self.eq_func = QLineEdit(); self.eq_func.setPlaceholderText("Ex: +")
        self.eq_args = QLineEdit(); self.eq_args.setPlaceholderText("Ex: velocity dt")
        
        l.addRow("Env ID:", self.eq_env_id)
        l.addRow("Target Var:", self.eq_target)
        l.addRow("Update Func:", self.eq_func)
        l.addRow("Args (spaced):", self.eq_args)
        self.stack.addWidget(w)

    def _create_form_link(self):
        """Creates the form layout for linking environment outputs to fuzzy system inputs."""
        w = QWidget(); l = QFormLayout(w)
        self.link_env_id = QLineEdit(); self.link_env_id.setText("env1")
        self.link_env_var = QLineEdit()
        self.link_fuzzy_in = QLineEdit()
        
        l.addRow("Env ID:", self.link_env_id)
        l.addRow("Env Var:", self.link_env_var)
        l.addRow("To Fuzzy Input:", self.link_fuzzy_in)
        self.stack.addWidget(w)

    def _change_form(self, index):
        """
        Switches the visible form in the stacked widget based on the dropdown selection.

        Args:
            index (int): The selected index in the combo box.
        """
        self.stack.setCurrentIndex(index)

    def _generate_fact(self):
        """
        Parses the active form data, retracts any existing matching fact in the engine,
        and emits the signal to assert the new updated environment fact.
        """
        if hasattr(self.parent(), 'env'):
            env = self.parent().env
            try:
                engine_templates = [str(p) for p in env.eval("(get-deftemplate-list *)")]
                
                library_loaded = any("EnvConfig" in t_name for t_name in engine_templates)
                
                if not library_loaded:
                    QMessageBox.warning(
                        self, 
                        "Environment Library Missing", 
                        "Warning! Code cannot be injected because the Environment library is not loaded in the current memory.\n\n"
                        "Please press F4 or go to 'Run -> Load Environment' to load the base library."
                    )
                    return
            except Exception:
                return

        idx = self.stack.currentIndex()
        h = ""
        retract_cmd = ""
        
        if idx == 0:
            eid = self.env_id.text().strip()
            if not eid: return
            retract_cmd = f'(do-for-all-facts ((?f EnvConfig)) (eq ?f:id {eid}) (retract ?f))'
            h = f"(EnvConfig (id {eid}) (max-steps {self.env_max_steps.value()}) (dt {self.env_dt.value()}))"
            
        elif idx == 1:
            eid = self.var_env_id.text().strip()
            name = self.var_name.text().strip()
            if not name: return
            retract_cmd = f'(do-for-all-facts ((?f EnvVar)) (and (eq ?f:env-id {eid}) (eq ?f:name {name})) (retract ?f))'
            h = f"(EnvVar (env-id {eid}) (name {name}) (value {self.var_val.value()}))"
            
        elif idx == 2:
            eid = self.eq_env_id.text().strip()
            target = self.eq_target.text().strip()
            if not target: return
            retract_cmd = f'(do-for-all-facts ((?f EnvEquation)) (and (eq ?f:env-id {eid}) (eq ?f:target-var {target})) (retract ?f))'
            h = f"(EnvEquation (env-id {eid}) (target-var {target}) (update-func {self.eq_func.text().strip()}) (args {self.eq_args.text().strip()}))"
            
        elif idx == 3:
            eid = self.link_env_id.text().strip()
            evar = self.link_env_var.text().strip()
            fin = self.link_fuzzy_in.text().strip()
            if not evar or not fin: return
            retract_cmd = f'(do-for-all-facts ((?f EnvLink)) (and (eq ?f:env-id {eid}) (eq ?f:env-var {evar}) (eq ?f:fuzzy-input {fin})) (retract ?f))'
            h = f"(EnvLink (env-id {eid}) (env-var {evar}) (fuzzy-input {fin}))"
            
        if h:
            if hasattr(self.parent(), 'env') and retract_cmd:
                try:
                    # We wrap the retraction in a try-except so it can never crash the GUI
                    self.parent().env.eval(retract_cmd)
                except Exception:
                    pass 
                    
            self.signal_insert_fact.emit(f"(assert {h})")