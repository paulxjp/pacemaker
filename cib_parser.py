import os
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
from io import StringIO

parsed_resources = set()  # To keep track of already parsed resources

def parse_nvpair_elements(element, element_name, output, context=""):
    if element is not None:
        for nvpair in element.findall("nvpair"):
            name = nvpair.get('name')
            value = nvpair.get('value')
            output.write(f"{context} {element_name}: {name}, Value: {value}\n")
            yield nvpair, context

def parse_operations(element, output):
    if element is not None:
        for op in element.findall("op"):
            op_name = op.get('name')
            interval = op.get('interval')
            timeout = op.get('timeout')
            output.write(f"Operation: {op_name}, Interval: {interval}, Timeout: {timeout}\n")

def parse_primitive_resource(resource, output):
    resource_id = resource.get('id')
    if resource_id in parsed_resources:
        return  # Skip already parsed resource
    parsed_resources.add(resource_id)

    resource_type = resource.get('type')
    output.write("-" * 40 + "\n")
    output.write(f"Resource ID: {resource_id}, Resource Type: {resource_type}\n")
    
    instance_attributes = resource.find("instance_attributes")
    for nvpair, context in parse_nvpair_elements(instance_attributes, "Parameter", output, context=resource_type):
        yield nvpair, context

    meta_attributes = resource.find("meta_attributes")
    for nvpair, context in parse_nvpair_elements(meta_attributes, "Meta-Attribute", output, context=resource_type):
        yield nvpair, context

    operations = resource.find("operations")
    parse_operations(operations, output)

def parse_group_element(group, output):
    group_id = group.get('id')
    output.write("-" * 40 + "\n")
    output.write(f"Group ID: {group_id}\n")

    primitives = group.findall("primitive")
    for primitive in primitives:
        for nvpair, context in parse_primitive_resource(primitive, output):
            yield nvpair, context

def parse_clone_element(clone, output):
    clone_id = clone.get('id')
    output.write("-" * 40 + "\n")
    output.write(f"Clone ID: {clone_id}\n")

    meta_attributes = clone.find("meta_attributes")
    for nvpair, context in parse_nvpair_elements(meta_attributes, "Meta-Attribute", output, context="Resource-Specific"):
        yield nvpair, context

    primitives = clone.findall("primitive")
    for primitive in primitives:
        for nvpair, context in parse_primitive_resource(primitive, output):
            yield nvpair, context

def parse_master_element(master, output):
    master_id = master.get('id')
    output.write("-" * 40 + "\n")
    output.write(f"Master/Slave ID: {master_id}\n")

    meta_attributes = master.find("meta_attributes")
    for nvpair, context in parse_nvpair_elements(meta_attributes, "Meta-Attribute", output, context="Resource-Specific"):
        yield nvpair, context

    primitive = master.find("primitive")
    if primitive is not None:
        for nvpair, context in parse_primitive_resource(primitive, output):
            yield nvpair, context

def parse_node_element(node, output):
    node_id = node.get('id')
    uname = node.get('uname')
    output.write("-" * 40 + "\n")
    output.write(f"Node ID: {node_id}, Node Name: {uname}\n")

    instance_attributes = node.find("instance_attributes")
    for nvpair, context in parse_nvpair_elements(instance_attributes, "Attribute", output, context="Node-Specific"):
        yield nvpair, context

def parse_constraints(constraints, output):
    parsed_elements = []
    for constraint in constraints:
        constraint_id = constraint.get('id')
        constraint_type = constraint.tag
        output.write("-" * 40 + "\n")
        output.write(f"Constraint ID: {constraint_id}, Type: {constraint_type}\n")
        
        for attr_name, attr_value in constraint.attrib.items():
            output.write(f"{attr_name}: {attr_value}\n")

        if constraint_type == "rsc_order":
            first = constraint.get('first')
            then = constraint.get('then')
            kind = constraint.get('kind', 'Mandatory')
            output.write(f"first: {first}, then: {then}, kind: {kind}\n")
        
        elif constraint_type == "rsc_colocation":
            rsc = constraint.get('rsc')
            with_rsc = constraint.get('with-rsc')
            score = constraint.get('score')
            rsc_role = constraint.get('rsc-role', 'Started')
            with_rsc_role = constraint.get('with-rsc-role', 'Started')
            output.write(f"rsc: {rsc}, with-rsc: {with_rsc}, score: {score}, rsc-role: {rsc_role}, with-rsc-role: {with_rsc_role}\n")
            parsed_elements.append((constraint, "rsc_colocation"))
    return parsed_elements

def parse_cib_xml(file_path, resource_types, output):
    no_resource_messages = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        output.write(f"Error parsing XML file: {e}\n")
        return None, no_resource_messages, []
    except Exception as e:
        output.write(f"An error occurred while reading the XML file: {e}\n")
        return None, no_resource_messages, []

    resource_types_found = set()
    parsed_elements = []

    for resource_type in resource_types:
        resources = root.findall(f".//primitive[@type='{resource_type}']")
        if not resources:
            no_resource_messages.append(f"No '{resource_type}' type resources found.\n")
            continue

        resource_types_found.add(resource_type)
        output.write(f"\nResource Type: {resource_type}\n")  # Add a blank line before each resource type for clarity
        for resource in resources:
            for nvpair, context in parse_primitive_resource(resource, output):
                parsed_elements.append((nvpair, context))

    clones = root.findall(".//clone")
    for clone in clones:
        for nvpair, context in parse_clone_element(clone, output):
            parsed_elements.append((nvpair, context))

    groups = root.findall(".//group")
    for group in groups:
        for nvpair, context in parse_group_element(group, output):
            parsed_elements.append((nvpair, context))

    masters = root.findall(".//master")
    for master in masters:
        for nvpair, context in parse_master_element(master, output):
            parsed_elements.append((nvpair, context))

    constraints = root.findall(".//constraints/*")
    constraint_elements = parse_constraints(constraints, output)
    parsed_elements.extend(constraint_elements)

    rsc_defaults = root.findall(".//rsc_defaults/meta_attributes/nvpair")
    if rsc_defaults:
        output.write("-" * 40 + "\n")
        output.write("Resource Defaults:\n")
        for nvpair, context in parse_nvpair_elements(root.find(".//rsc_defaults/meta_attributes"), "rsc_defaults", output, context="global"):
            parsed_elements.append((nvpair, context))

    op_defaults = root.findall(".//op_defaults/meta_attributes/nvpair")
    if op_defaults:
        output.write("-" * 40 + "\n")
        output.write("Operation Defaults:\n")
        for nvpair, context in parse_nvpair_elements(root.find(".//op_defaults/meta_attributes"), "Default Parameter", output, context="global"):
            parsed_elements.append((nvpair, context))

    cib_bootstrap_options = root.find(".//cluster_property_set[@id='cib-bootstrap-options']")
    if cib_bootstrap_options is not None:
        output.write("-" * 40 + "\n")
        output.write("CIB Bootstrap Options:\n")
        for nvpair, context in parse_nvpair_elements(cib_bootstrap_options, "CIB Bootstrap Option", output, context="global"):
            parsed_elements.append((nvpair, context))

    rsc_location_constraints = root.findall(".//rsc_location")
    cli_constraints_found = False
    for rsc_location in rsc_location_constraints:
        if rsc_location.get('id', '').startswith('cli-'):
            cli_constraints_found = True
            output.write("-" * 40 + "\n")
            dark_blue = "\033[34m"
            reset_color = "\033[0m"
            output.write(f"{dark_blue}CLI Constraint ID: {rsc_location.get('id')}\n{reset_color}")
            output.write(f"Resource: {rsc_location.get('rsc')}\n")
            output.write(f"Role: {rsc_location.get('role')}\n")
            output.write(f"Node: {rsc_location.get('node')}\n")
            output.write(f"Score: {rsc_location.get('score')}\n")

    if not cli_constraints_found:
        dark_blue = "\033[34m"
        reset_color = "\033[0m"
        no_resource_messages.append(f"{dark_blue}No 'cli-' prefixed rsc_location constraints found.\n{reset_color}")

    nodes = root.findall(".//node")
    for node in nodes:
        for nvpair, context in parse_node_element(node, output):
            parsed_elements.append((nvpair, context))

    return root, no_resource_messages, resource_types_found, parsed_elements

def load_parameters(file_path):
    parameters = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if ':' in line:
                    scope, name, value = line.strip().split(':', 2)
                    if scope not in parameters:
                        parameters[scope] = {}
                    parameters[scope][name.strip()] = [v.strip() for v in value.split('|')]
    except Exception as e:
        print(f"An error occurred while reading the parameters file: {e}")
    return parameters

def check_pacemaker_resource_values(parsed_elements, parameters, original_lines, resource_types_found):
    analysis_output = StringIO()
    found_parameters = {scope: {name: False for name in params} for scope, params in parameters.items()}

    def check_nvpair(nvpair, context):
        name = nvpair.get('name').strip()
        value = nvpair.get('value').strip()
        for scope in parameters:
            if (scope == "property" and context == "global") or (scope in resource_types_found and scope == context) or (scope == "global" and context == "global"):
                if name in parameters[scope]:
                    found_parameters[scope][name] = True
                    expected_values = parameters[scope][name]
                    if value.lower() not in (ev.lower() for ev in expected_values):
                        expected_values_str = ', '.join(expected_values)
                        analysis_output.write(f"Warning: {context} {name} is set to {value} instead of one of the best practice values: {expected_values_str}.\n")
                        for line in original_lines:
                            if f'name="{name}"' in line and f'value="{value}"' in line:
                                analysis_output.write(f"Original line: {line}\n")
                                break

    def check_constraint(constraint, context):
        for param_name in parameters.get(context, {}):
            param_value = constraint.get(param_name)
            if param_value is not None:
                param_value = param_value.strip()
            else:
                analysis_output.write(f"Warning: {context} {param_name} is missing in constraint {constraint.get('id')}.\n")
                for line in original_lines:
                    if f'id="{constraint.get("id")}"' in line:
                        analysis_output.write(f"Original line: {line}\n")
                        break
                continue

            found_parameters[context][param_name] = True
            expected_values = parameters[context][param_name]
            if param_value.lower() not in (ev.lower() for ev in expected_values):
                expected_values_str = ', '.join(expected_values)
                analysis_output.write(f"Warning: {context} {param_name} is set to {param_value} instead of one of the best practice values: {expected_values_str}.\n")
                for line in original_lines:
                    if f'{param_name}="{param_value}"' in line:
                        analysis_output.write(f"Original line: {line}\n")
                        break

    for element, context in parsed_elements:
        if context == "rsc_colocation":
            check_constraint(element, context)
        else:
            check_nvpair(element, context)

    for scope, params in found_parameters.items():
        if scope in resource_types_found or scope in ["global", "property", "rsc_colocation"]:
            for name, found in params.items():
                if not found:
                    expected_values_str = ', '.join(parameters[scope][name])
                    analysis_output.write(f"Warning: {scope} {name} setting is missing. It should be set to one of the best practice values: {expected_values_str}.\n")

    analysis_result = analysis_output.getvalue()
    analysis_output.close()
    return analysis_result

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    file_path = input("Enter the absolute path of the CIB XML file (or press Enter to search in the current directory): ").strip()

    if not file_path:
        current_dir = os.getcwd()
        file_path = os.path.join(current_dir, "CIB.xml")
        if not os.path.isfile(file_path):
            print("CIB.xml not found in the current directory.")
            return

    if not os.path.isfile(file_path):
        print(f"The file {file_path} does not exist.")
        return

    resources_file_path = os.path.join(script_dir, "cib_resources.txt")
    if not os.path.isfile(resources_file_path):
        print("cib_resources.txt file not found in the script directory.")
        return

    parameters_file_path = os.path.join(script_dir, "cib_parameters_value.txt")
    if not os.path.isfile(parameters_file_path):
        print("cib_parameters_value.txt file not found in the script directory.")
        return

    parameters = load_parameters(parameters_file_path)

    try:
        with open(resources_file_path, 'r') as file:
            resource_types = [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"An error occurred while reading the resource types file: {e}")
        return

    if not resource_types:
        print("No resource types found in cib_resources.txt file.")
        return

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    with open(file_path, 'r') as f:
        original_lines = f.readlines()

    root, no_resource_messages, resource_types_found, parsed_elements = parse_cib_xml(file_path, resource_types, mystdout)

    sys.stdout = old_stdout

    output = mystdout.getvalue()

    title = """
##########################################
#                                        #
#       Pacemaker CIB Analysis Report    #
#       From Azure Linux Team            #
#                                        #
##########################################
"""

    combined_output = title + "\n" + "\n".join(no_resource_messages) + "\n" + output

    print(combined_output)
    

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file_path = os.path.join(script_dir, f"cib-parser-{timestamp}.txt")
    with open(output_file_path, 'w') as file:
        file.write(combined_output)

    if root is not None:
        analysis_output = check_pacemaker_resource_values(parsed_elements, parameters, original_lines, resource_types_found)
        
        print("\n" + "-" * 40 + "\nPacemaker Resource Analysis:\n" + analysis_output)
        print("\n" + "Pacemaker Resource Analysis Done\n")

        with open(output_file_path, 'a') as file:
            file.write("\n" + "-" * 40 + "\n")
            file.write("Pacemaker Resource Analysis:\n")
            file.write(analysis_output)
            file.write("Pacemaker Resource Analysis Done\n")

if __name__ == "__main__":
    main()
