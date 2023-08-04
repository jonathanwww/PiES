import os
from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QTextEdit, QGroupBox 
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network
import json
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox, QCheckBox
from PyQt6.QtCore import Qt


class GraphWidget(QWidget):
    def __init__(self, eqsys, parent=None):
        super().__init__(parent)
        self.eqsys = eqsys
        
        # Layout for the widget
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self._setup_blocking_layout()
        
        # refresh graph on start
        # self.refresh_web_widget()
        
    def _setup_blocking_layout(self):
        # GroupBox for the blocking operation
        self.blocking_groupbox = QGroupBox()
        self.blocking_layout = QVBoxLayout()
        self.blocking_groupbox.setLayout(self.blocking_layout)
        self.layout.addWidget(self.blocking_groupbox)

        # Create a horizontal layout
        self.horizontal_layout = QHBoxLayout()

        # Add two dropdowns to the horizontal layout
        self.attribute_filter = QComboBox()
        self.attribute_filter.currentIndexChanged.connect(self.on_property_changed)
        self.value_filter = QComboBox()
        self.value_filter.currentIndexChanged.connect(self.on_value_changed)
        self.horizontal_layout.addWidget(self.attribute_filter)
        self.horizontal_layout.addWidget(self.value_filter)

        # buttons        
        self.horizontal_layout.addStretch()
        self.refresh_button = QPushButton("Refresh graph")
        # self.refresh_button.clicked.connect(self.refresh_web_widget)
        self.horizontal_layout.addWidget(self.refresh_button)

        # Add block graph toggle to the horizontal layout
        self.toggle = QCheckBox("Block graph")
        self.toggle.setCheckState(Qt.CheckState.Checked)
        # self.toggle.stateChanged.connect(self.refresh_web_widget)
        self.horizontal_layout.addWidget(self.toggle)

        # Add the horizontal layout to the blocking layout
        self.blocking_layout.addLayout(self.horizontal_layout)

        # Create a web widget to display the network graph
        self.web_widget = QWebEngineView()
        self.blocking_layout.addWidget(self.web_widget)
    
    def get_and_fill_properties(self):
        # Define a callback function that will be called with the result of the JavaScript
        def callback(result):
            # Clear the dropdowns
            self.attribute_filter.clear()
            self.value_filter.clear()

            # Loop over the properties and add them to the dropdowns
            allowed_props = ['block', 'status']
            for prop in result:
                if prop in allowed_props:
                    self.attribute_filter.addItem(prop)

        # Run the JavaScript and call the callback with the result
        self.web_widget.page().runJavaScript('getProperties();', callback)
    
    def on_property_changed(self, index):
        # Get the selected property
        property_name = self.attribute_filter.currentText()
        js_code = f"getValuesForProperty('{property_name}')"
        # Call the JavaScript function and provide a callback to handle the result
        self.web_widget.page().runJavaScript(js_code, self.on_values_received)
    
    def on_values_received(self, values):
        # Clear the second dropdown
        self.value_filter.clear()
        
        self.value_filter.addItem('Select value')
        for value in sorted(values):
            self.value_filter.addItem(str(value))
        
        # clear the filter selection after loading
        self.clear_filter_js()
            
    def on_value_changed(self):
        selected_property = self.attribute_filter.currentText()
        selected_value = self.value_filter.currentText()
        script = f"applyValueFilter('{selected_property}', '{selected_value}');"
        self.web_widget.page().runJavaScript(script)
    
    def clear_filter_js(self):
        script = f"clearFilter(true)"
        self.web_widget.page().runJavaScript(script)
            
    def create_equation_graph(self):
        blocking_results, graph = self.eqsys.blocking(return_graph=True)
        val_results = self.eqsys.validation_handler.validate_blocks()

        # remove bidirectional edge pairs, and re-add in pyvis (else they get two arrows)
        bidirectional_edges = []
        for edge in list(graph.edges()):
            # If the reverse of the edge exists in the graph
            if (edge[1], edge[0]) in graph.edges():
                bidirectional_edges.append(edge)
                graph.remove_edge(edge[0], edge[1])
                graph.remove_edge(edge[1], edge[0])

        # add nodes to group based on block. Color is assigned to each block
        for i, block in enumerate(blocking_results):
            unsolved_vars = val_results[i][2]
            for node in block:
                equation = self.eqsys.equations[node]
                eq_variables = ', '.join(equation.variables)
                eq_unsolved_vars = ', '.join(unsolved_vars)
                graph.nodes[node]['title'] = f"Equation: {equation.input_form}\nVariables: {eq_variables}\n\nIn block {i} ({val_results[i][0]})\nTotal eqs in block: {len(block)}\nUnsolved vars in block: {len(unsolved_vars)}\n {eq_unsolved_vars}"
                graph.nodes[node]['label'] = f" "  # f"Eq: {equation.id}\nBlock {i}"
                graph.nodes[node]['size'] = 5 + len(equation.variables)
                graph.nodes[node]['group'] = i  # for adding colors to each block
                graph.nodes[node]['block'] = i  # for filtering
                graph.nodes[node]['status'] = val_results[i][0]  # get status for block i

        # validation results is a dictionary. THe keys are ints, which corresponds to the block. 
        # The value is a tuple: (status, list of equations, list of unsolved variables)
        network = Network(directed=True)
        network.from_nx(graph)

        for edge in bidirectional_edges:
            network.add_edge(edge[0], edge[1], arrows="to, from")

        # for normalizing 
        max_shared_elements = 0

        # update the weight of all edges based on shared variables
        for edge in network.edges:
            # node names is string ints
            # get the list of variables from an equation:
            variables_node1 = set(self.eqsys.equations[edge['from']].variables)
            variables_node2 = set(self.eqsys.equations[edge['to']].variables)

            # calculate shared elements
            shared_elements = len(variables_node1.intersection(variables_node2))

            # update the edge weight
            edge['width'] = shared_elements

            # update max_shared_elements if this edge has more shared elements
            max_shared_elements = max(max_shared_elements, shared_elements)

        # normalize the edge widths
        for edge in network.edges:
            edge['width'] /= (max_shared_elements / 1.5)
            
        return network.nodes, network.edges

    def create_block_graph(self):
        blocking_results = self.eqsys.blocking()
        val_results = self.eqsys.validation_handler.validate_blocks()

        # pyvis network
        network = Network(directed=True)

        # Create nodes for each block
        for i, block in enumerate(blocking_results):
            unsolved_vars = val_results[i][2]
            block_equations = [self.eqsys.equations[eq_id].input_form for eq_id in block]
            unsolved_vars_strings = ', '.join(unsolved_vars) 
            block_eq_strings = '\n'.join(block_equations[:5])
            if len(block_equations) > 5:
                block_eq_strings = block_eq_strings + "\n ..."
                
            node_attributes = {
                "title":  f"Block {i} ({val_results[i][0]})\n\nEqs in block: {len(block)}\n{block_eq_strings}\n\nUnsolved vars in block: {len(unsolved_vars)}\n {unsolved_vars_strings}",
                "label": f"Block {i}",
                "size": 15 + len(block)*7,  # Set the size attribute based on the number of equations in the block
                "status": val_results[i][0]  # get status for block i
            }
            network.add_node(i, **node_attributes)

        # Iterate over the blocks and their corresponding validation info
        for i, (block, val_info) in enumerate(zip(blocking_results, val_results.items())):
            if i < len(blocking_results) - 1:
                next_block = blocking_results[i + 1]
                
                # Get the variables in the current block
                block_variables = set()
                for equation_id in block:
                    equation = self.eqsys.equations[equation_id]
                    block_variables.update(equation.variables)

                # Add edges to the next block in the blocking results if there are shared variables
                next_block_variables = set()
                for equation_id in next_block:
                    equation = self.eqsys.equations[equation_id]
                    next_block_variables.update(equation.variables)

                shared_variables = block_variables.intersection(next_block_variables)                

                if not shared_variables:
                    network.add_edge(i, i + 1, color="#cccccc") 
                else:
                    network.add_edge(i, i + 1)

            if val_info[1][0] != "valid":
                network.nodes[i]["color"] = "red"

        return network.nodes, network.edges
    
    def refresh_web_widget(self):
        # check toggle on what graph to generate
        if self.toggle.checkState() == Qt.CheckState.Checked:
            nodes, edges = self.create_block_graph()
        else:
            nodes, edges = self.create_equation_graph()
            
        # Convert the nodes and edges to JSON
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)

        # Open the HTML file and read its contents
        path = "view/pyvis/"
        template_path = os.path.join(path, "template.html")
        output_path = os.path.join(path, "output.html")
        
        # create output file
        with open(template_path, "r") as f:
            html = f.read()
            
        html = html.replace("nodes = new vis.DataSet([{}]);", "nodes = new vis.DataSet(" + nodes_json + ");")
        html = html.replace("edges = new vis.DataSet([{}]);", "edges = new vis.DataSet(" + edges_json + ");")
        
        with open(output_path, "w") as f:
            f.write(html)
        
        # refresh webwidget
        self.web_widget.setHtml("")
        self.web_widget.setUrl(QUrl.fromLocalFile(os.path.abspath(output_path)))
        
        # Once the page is loaded, fill the dropdowns
        self.web_widget.loadFinished.connect(self.get_and_fill_properties)
        