import os
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QTextEdit, QGroupBox 
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network


class EquationSystemWidget(QWidget):
    def __init__(self, eqsys, parent=None):
        super().__init__(parent)
        self.eqsys = eqsys

        # refresh on change in eqsys
        self.eqsys.data_changed.connect(self.update_widget)
        
        # Layout for the widget
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Add a QPushButton for hiding/showing the equation system info
        self.toggle_button = QPushButton("Hide/Show Equation system info")
        self.toggle_button.clicked.connect(self.toggle_eqinfo_box)
        self.layout.addWidget(self.toggle_button)

        # GroupBox for the equation system info
        self.eqinfo_groupbox = QGroupBox("Equation system info")
        self.eqinfo_layout = QVBoxLayout()
        self.eqinfo_groupbox.setLayout(self.eqinfo_layout)
        self.layout.addWidget(self.eqinfo_groupbox)

        # Add variable count and button to view variables
        self.variable_layout = QHBoxLayout()
        self.variable_count_label = QLabel(f"Variables: {len(self.eqsys.variables)}")
        self.variable_layout.addWidget(self.variable_count_label)
        self.view_variables_button = QPushButton("View Variables")
        self.view_variables_button.clicked.connect(self.view_variables)
        self.variable_layout.addWidget(self.view_variables_button)
        self.eqinfo_layout.addLayout(self.variable_layout)

        # Add equations count and button to view equations
        self.equation_layout = QHBoxLayout()
        self.equations_count_label = QLabel(f"Equations: {len(self.eqsys.equations)}")
        self.equation_layout.addWidget(self.equations_count_label)
        self.view_equations_button = QPushButton("View Equations")
        self.view_equations_button.clicked.connect(self.view_equations)
        self.equation_layout.addWidget(self.view_equations_button)
        self.eqinfo_layout.addLayout(self.equation_layout)
        
        # Add parameter variable count and button to view parameter variables
        self.param_variable_layout = QHBoxLayout()
        self.param_variable_count_label = QLabel(f"Param Variables: {len(self.eqsys.parameter_variables)}")
        self.param_variable_layout.addWidget(self.param_variable_count_label)
        self.view_param_variable_button = QPushButton("View Parameter Variables")
        self.view_param_variable_button.clicked.connect(self.view_param_variable)
        self.param_variable_layout.addWidget(self.view_param_variable_button)
        self.eqinfo_layout.addLayout(self.param_variable_layout)
        
        # Add grid count and button to view grid
        self.grid_layout = QHBoxLayout()
        self.grid_count_label = QLabel(f"Grid: {len(self.eqsys.grid.variables)}")
        self.grid_layout.addWidget(self.grid_count_label)
        self.view_grid_button = QPushButton("View Grid")
        self.view_grid_button.clicked.connect(self.view_grid)
        self.grid_layout.addWidget(self.view_grid_button)
        self.eqinfo_layout.addLayout(self.grid_layout)

        # Add function units count and button to view function units
        self.function_units_layout = QHBoxLayout()
        self.function_units_count_label = QLabel(f"Function Units: {len(self.eqsys.function_units)}")
        self.function_units_layout.addWidget(self.function_units_count_label)
        self.view_function_units_button = QPushButton("View Function Units")
        self.view_function_units_button.clicked.connect(self.view_function_units)
        self.function_units_layout.addWidget(self.view_function_units_button)
        self.eqinfo_layout.addLayout(self.function_units_layout)

        # GroupBox for the blocking operation
        self.blocking_groupbox = QGroupBox()
        self.blocking_layout = QVBoxLayout()
        self.blocking_groupbox.setLayout(self.blocking_layout)
        self.layout.addWidget(self.blocking_groupbox)

        # Add button for blocking operation
        self.blocking_button = QPushButton("Refresh eqsys blocks")
        self.blocking_button.clicked.connect(self.refresh_web_widget)
        self.blocking_layout.addWidget(self.blocking_button)

        # Create a web widget to display the network graph
        self.web_widget = QWebEngineView()
        self.blocking_layout.addWidget(self.web_widget)
        
        # Hide the equation system info by default
        self.eqinfo_groupbox.hide()
        
        # refresh graph on start
        self.refresh_web_widget()
    
    def update_widget(self):
        self.variable_count_label.setText(f"Variables: {len(self.eqsys.variables)}")
        self.equations_count_label.setText(f"Equations: {len(self.eqsys.equations)}")
        self.param_variable_count_label.setText(f"Parameters: {len(self.eqsys.parameter_variables)}")
        self.grid_count_label.setText(f"Grid: {len(self.eqsys.grid.variables)}")
        self.function_units_count_label.setText(f"Function Units: {len(self.eqsys.function_units)}")

    def toggle_eqinfo_box(self):
        if self.eqinfo_groupbox.isVisible():
            self.eqinfo_groupbox.hide()
        else:
            self.eqinfo_groupbox.show()

    def view_variables(self):
        self.view_dict(self.eqsys.variables)

    def view_equations(self):
        self.view_dict(self.eqsys.equations)
        
    def view_param_variable(self):
        self.view_dict(self.eqsys.parameter_variables)
        
    def view_grid(self):
        self.view_dict(self.eqsys.grid.variables)

    def view_function_units(self):
        self.view_dict(self.eqsys.function_units)
    
    @staticmethod
    def view_dict(d):
        dialog = QDialog()
        dialog.setWindowTitle("Viewer")
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        text_edit = QTextEdit()

        # Create a string that represents the dictionary with one key-value pair per line
        dict_str = '\n'.join([f'{k}: {v}' for k, v in d.items()])

        text_edit.setText(dict_str)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        dialog.exec()

    def refresh_web_widget(self):
        def get_variables(block):
            return set(var for eq_id in block for var in self.eqsys.equations[eq_id].variables)
        
        blocking_results = self.eqsys.blocking()
        validation_results = self.eqsys.validate_equation_system()
        
        nodes = {}
        self.web_widget.setHtml("")

        network = Network(height="500", width="100%", directed=True, notebook=True)

        for block_index, (block, validation_result) in enumerate(zip(blocking_results, validation_results)):
            status = validation_results[block_index][0]
            unsolved = ", ".join(validation_results[block_index][2])  # [2] is a list of the vars being solved in that block 
            
            node_id = block_index + 1
            node_value = len(block)
            # The title is a list of equations in the block
            node_title = "\n".join([str(self.eqsys.equations[eq_id]) for eq_id in block])
            
            node_color = 'red' if status != 'valid' else 'green'

            # Store the node details and the variables for this block
            nodes[node_id] = {"value": node_value,
                              "title": node_title,
                              "label": f"BLOCK {node_id}\n{status}\n{unsolved}",
                              "variables": get_variables(block),
                              "color": node_color}  # add the color attribute
        # Create directed edges based on shared variables between consecutive blocks
        edges = []
        for node_id, node_data in nodes.items():
            if node_id + 1 in nodes:  # Only create an edge if there is a next block
                # Calculate shared variables with the next block
                shared_variables = node_data["variables"].intersection(nodes[node_id + 1]["variables"])
                if len(shared_variables) > 0:
                    edges.append((node_id, node_id + 1, len(shared_variables)))

        # Add nodes and edges to the network
        network.add_nodes(list(nodes.keys()), value=[node["value"] for node in nodes.values()],
                          title=[node["title"] for node in nodes.values()],
                          label=[node["label"] for node in nodes.values()],
                          color=[node["color"] for node in nodes.values()])

        network.add_edges(edges)
        network.toggle_physics(True)
        
        # Create html file
        # path to 
        path = "ui/pyvis/"

        # Generate the file path in the specified directory
        file_path = os.path.join(path, "template.html")

        # Show the network, which will also save it to the temporary file
        network.show(file_path)

        # To fix bug with undefined vis.js
        script_tag = '<script src="vis-network.min.js"></script>'
        css_tag = '<link href="vis-network.css" rel="stylesheet">'

        # Read the HTML file
        with open(file_path, 'r') as file:
            file_content = file.read()

        # Insert the script and css tags before the closing </head> tag
        file_content = file_content.replace('</head>', f'{css_tag}{script_tag}</head>')

        # Write the modified HTML back to the file
        with open(file_path, 'w') as file:
            file.write(file_content)

        # Load the network in the web widget

        self.web_widget.setUrl(QUrl.fromLocalFile(os.path.abspath(file_path)))
 