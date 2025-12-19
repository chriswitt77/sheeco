import os
from dotenv import load_dotenv
import json
import datetime

load_dotenv() # Loads variables from .env into environment


def create_timestamp():
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d_%H%M")

    return timestamp

def create_part_json(part, timestamp = None):
    if timestamp is None:
        timestamp = create_timestamp()

    # 2. Prepare Data (Convert NumPy arrays to lists)
    export_data = {
        "timestamp": timestamp,
        "part_id": part.part_id,
        "tabs": {}
    }

    for tid, tab in part.tabs.items():
        export_data["tabs"][tid] = {
            "points": {label: pt.tolist() for label, pt in tab.points.items()}
        }

    return export_data

def export_to_json(part, solution_id = 0, output_dir="exports"):
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Assuming part.tabs is a dict of your tab objects
    num_tabs = len(part.tabs)
    # Assuming number of rectangles is stored or can be calculated
    num_rects = getattr(part, 'number_rectangles', num_tabs) 
    
    timestamp = create_timestamp()

    filename = f"{timestamp}_part{part.part_id}_solution{solution_id}_{num_rects}rects_{num_tabs}tabs.json"
    filepath = os.path.join(output_dir, filename)

    export_data = create_part_json(part, timestamp)    

    # 3. Write to file
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=4)

    print(f"Exported solution to: {filepath}")
    return filepath

# from onshape_client.client import Client

def export_to_onshape(part):
    part_json = create_part_json(part)
    convert_to_fs(part_json)


    # API_KEY = os.getenv("ONSHAPE_API_KEY")
    # SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")

    # # Authenticate
    # client = Client(configuration={
    #     "base_url": "https://cad.onshape.com",
    #     "access_key": API_KEY,
    #     "secret_key": SECRET_KEY
    # })

    # # Create a new document
    # doc = client.documents_api.create_document({"name": "Generated Tabs Sheet Metal"})
    # doc_id = doc.id

    # # Get workspace ID
    # workspaces = client.documents_api.get_document_workspaces(did=doc_id)
    # workspace_id = workspaces[0].id

    # print("Document ID:", doc_id)
    # print("Workspace ID:", workspace_id)

    # # Upload JSON file into the document
    # with open(export_data, "rb") as f:
    #     upload = client.blob_elements_api.upload_file_create_element(
    #         did=doc_id,
    #         wid=workspace_id,
    #         file=f
    #     )

    # print("Upload result:", upload)


def convert_to_fs(data):
    # Start building the FeatureScript string
    # We skip the imports so you don't get version errors
    fs = []
    fs.append('FeatureScript 2837;')
    fs.append('import(path : "onshape/std/common.fs", version : "2837.0");')    
    fs.append('annotation { "Feature Type Name" : "JSON Import" }')
    fs.append('export const jsonImport = defineFeature(function(context is Context, id is Id, definition is map)')
    fs.append('    precondition')
    fs.append('    {')
    fs.append('        // No inputs needed')
    fs.append('    }')
    fs.append('    {')

    # Loop through each tab in the JSON
    for tab_id, tab_data in data.get("tabs", {}).items():
        points_code = []
        point_list = list(tab_data["points"].values())
        
        # Add points to the list
        for p in point_list:
            points_code.append(f"            vector({p[0]}, {p[1]}, {p[2]}) * millimeter")
        
        # Close the loop (add start point to end)
        start_p = point_list[0]
        points_code.append(f"            vector({start_p[0]}, {start_p[1]}, {start_p[2]}) * millimeter")

        # Generate the vector array variable
        fs.append(f'        var points_{tab_id} = [')
        fs.append(",\n".join(points_code))
        fs.append('        ];')

        # Generate the Polyline operation
        fs.append(f'        opPolyline(context, id + "tab_{tab_id}", {{')
        fs.append(f'            "points" : points_{tab_id}')
        fs.append('        });')

    fs.append('    });')

    # Output to file
    with open('exports/output.fs', 'w') as f:
        f.write("\n".join(fs))

    print("Done. Content saved to output.fs")