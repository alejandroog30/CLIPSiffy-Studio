from PyQt6.QtWidgets import (
    QDockWidget,
    QTreeWidget,
    QTreeWidgetItem, QListWidget
)

from PyQt6.QtCore import Qt

class FuzzyFactsPanel(QDockWidget):
    """
    A dockable panel that provides a structured, hierarchical view of all 
    fuzzy-related facts currently loaded in the CLIPS memory. It categorizes 
    systems, variables, connections, and runtime execution data.

    Attributes:
        tree_widget (QTreeWidget): The hierarchical tree widget used to display the data.
    """

    def __init__(self, title, parent=None):
        """
        Initializes the fuzzy facts panel.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("FUZZY MEMORY")
        self.setWidget(self.tree_widget)

    def update_facts(self, env):
        """
        Scrapes the active CLIPS environment for specific fuzzy templates 
        (e.g., FuzzySystemConfig, FuzzyVar, FuzzySet, CrispInput) and organizes 
        them into a readable tree structure.

        Args:
            env (clips.Environment): The active CLIPS environment containing the facts.
        """
        self.tree_widget.clear()

        systems = {}           
        vars_by_system = {}   
        sets_by_var = {}       
        connections = []         
        crisp_inputs = []       
        
        fuzzy_inputs = {}       
        rule_outputs = {}       
        system_outputs = {}     

        def safe_get(fact, slot):
            try: return str(fact[slot]) if fact[slot] is not None else ""
            except: return ""

        for f in env.facts():
            t = f.template.name
            f_str = str(f)

            if t == "FuzzySystemConfig":
                sys_id = safe_get(f, "id")
                systems[sys_id] = f_str
                if sys_id not in vars_by_system:
                    vars_by_system[sys_id] = {'input': {}, 'output': {}}
                    
            elif t == "FuzzyVar":
                sys_id = safe_get(f, "system-id")
                var_name = safe_get(f, "name")
                var_type = safe_get(f, "type")
                
                if sys_id not in vars_by_system:
                    vars_by_system[sys_id] = {'input': {}, 'output': {}}
                if var_type in ['input', 'output']:
                    vars_by_system[sys_id][var_type][var_name] = f_str
                    
            elif t == "FuzzySet":
                var_name = safe_get(f, "var-name")
                if var_name not in sets_by_var: sets_by_var[var_name] = []
                sets_by_var[var_name].append(f_str)
                
            elif t == "Connection":
                connections.append(f_str)
                
            elif t == "CrispInput":
                crisp_inputs.append(f_str)
                
            elif t == "FuzzyInput":
                var_name = safe_get(f, "var-name")
                if var_name not in fuzzy_inputs: fuzzy_inputs[var_name] = []
                fuzzy_inputs[var_name].append(f_str)
                
            elif t == "FuzzyRuleOutput":
                rule_name = safe_get(f, "rule-name")
                if rule_name not in rule_outputs: rule_outputs[rule_name] = []
                rule_outputs[rule_name].append(f_str)
                
            elif t == "SystemOutput":
                sys_id = safe_get(f, "system-id")
                if sys_id not in system_outputs: system_outputs[sys_id] = []
                system_outputs[sys_id].append(f_str)

        # Build UI Tree for Systems
        if systems:
            root_systems = QTreeWidgetItem(self.tree_widget, ["Fuzzy Systems"])
            root_systems.setExpanded(True)
            
            for sys_id, sys_str in systems.items():
                item_sys = QTreeWidgetItem(root_systems, [f"System: {sys_id}"])
                QTreeWidgetItem(item_sys, [sys_str]) 
                
                vars_sys = vars_by_system.get(sys_id, {'input': {}, 'output': {}})
                
                if vars_sys['input']:
                    item_inputs = QTreeWidgetItem(item_sys, ["Inputs"])
                    for var_name, var_str in vars_sys['input'].items():
                        item_var = QTreeWidgetItem(item_inputs, [f"Variable: {var_name}"])
                        QTreeWidgetItem(item_var, [var_str]) 
                        for set_str in sets_by_var.get(var_name, []):
                            QTreeWidgetItem(item_var, [set_str])
                            
                if vars_sys['output']:
                    item_outputs = QTreeWidgetItem(item_sys, ["Outputs"])
                    for var_name, var_str in vars_sys['output'].items():
                        item_var = QTreeWidgetItem(item_outputs, [f"Variable: {var_name}"])
                        QTreeWidgetItem(item_var, [var_str]) 
                        for set_str in sets_by_var.get(var_name, []):
                            QTreeWidgetItem(item_var, [set_str])

        # Build UI Tree for Connections
        if connections:
            root_conn = QTreeWidgetItem(self.tree_widget, ["Connections"])
            for c in connections:
                QTreeWidgetItem(root_conn, [c])

        # Build UI Tree for Runtime Inputs
        if crisp_inputs:
            root_crisp = QTreeWidgetItem(self.tree_widget, ["Crisp Inputs"])
            for c in crisp_inputs:
                QTreeWidgetItem(root_crisp, [c])

        if fuzzy_inputs:
            root_fi = QTreeWidgetItem(self.tree_widget, ["Fuzzy Inputs (Execution)"])
            for var_name, facts in fuzzy_inputs.items():
                item_var = QTreeWidgetItem(root_fi, [f"Var: {var_name}"])
                for h in facts:
                    QTreeWidgetItem(item_var, [h])

        # Build UI Tree for Runtime Outputs
        if rule_outputs:
            root_ro = QTreeWidgetItem(self.tree_widget, ["Fuzzy Rule Outputs (Execution)"])
            for rule_name, facts in rule_outputs.items():
                item_rule = QTreeWidgetItem(root_ro, [f"Rule: {rule_name}"])
                for h in facts:
                    QTreeWidgetItem(item_rule, [h])

        if system_outputs:
            root_so = QTreeWidgetItem(self.tree_widget, ["System Outputs (Execution)"])
            for sys_id, facts in system_outputs.items():
                item_sys = QTreeWidgetItem(root_so, [f"System: {sys_id}"])
                for h in facts:
                    QTreeWidgetItem(item_sys, [h])

class CLIPSFactsPanel(QDockWidget):
    """
    A dockable panel that lists all raw facts currently asserted in the CLIPS memory.

    Attributes:
        list_widget (QListWidget): The UI component displaying the list of facts.
    """

    def __init__(self, title, parent=None):
        """
        Initializes the raw facts panel.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.list_widget = QListWidget()
        self.setWidget(self.list_widget)

    def update(self, env):
        """
        Clears the current list and repopulates it with the latest facts from the engine.

        Args:
            env (clips.Environment): The active CLIPS environment.
        """
        self.list_widget.clear()
        for fact in env.facts():
            self.list_widget.addItem(str(fact))

class CLIPSRulesPanel(QDockWidget):
    """
    A dockable panel that lists all the rules currently defined in the CLIPS memory.

    Attributes:
        list_widget (QListWidget): The UI component displaying the list of rules.
    """

    def __init__(self, title, parent=None):
        """
        Initializes the rules panel.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.list_widget = QListWidget()
        self.setWidget(self.list_widget)

    def update(self, env):
        """
        Clears the current list and repopulates it with the names of all defined rules.

        Args:
            env (clips.Environment): The active CLIPS environment.
        """
        self.list_widget.clear()
        try:
            # Query the engine for the list of all defrules
            all_rules = env.eval("(get-defrule-list *)")
            
            for rule in all_rules:
                self.list_widget.addItem(str(rule))
        except Exception as e:
            self.list_widget.addItem(f"; Error reading rules: {str(e)}")

class CLIPSAgendaPanel(QDockWidget):
    """
    A dockable panel that displays the current execution agenda of the CLIPS engine,
    showing which rules are activated and their corresponding salience (priority).

    Attributes:
        list_widget (QListWidget): The UI component displaying the agenda.
    """

    def __init__(self, title, parent=None):
        """
        Initializes the agenda panel.

        Args:
            title (str): The text title of the dock panel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.list_widget = QListWidget()
        self.setWidget(self.list_widget)

    def update(self, env):
        """
        Clears the current list and retrieves the pending rule activations from the engine.

        Args:
            env (clips.Environment): The active CLIPS environment.
        """
        self.list_widget.clear()
        try:
            for activation in env.activations():
                rule_name = activation.name
                salience = activation.salience
                
                text = f"[{salience}] {rule_name}"
                self.list_widget.addItem(text)
        except Exception as e:
            self.list_widget.addItem(f"; Error reading agenda: {str(e)}")
