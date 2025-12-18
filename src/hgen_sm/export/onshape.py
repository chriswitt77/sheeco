import os
from dotenv import load_dotenv

load_dotenv() # Loads variables from .env into environment

API_KEY = os.getenv("ONSHAPE_API_KEY")
SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY")

def export_to_onshape(part):
    print("Not working yet")
    print(part.part_id)
    # print(part)

    
# from onshape_client.client import Client
# import onshape_keys

# # Authenticate
# client = Client(configuration={
#     "base_url": "https://cad.onshape.com",
#     "access_key": onshape_keys.API_KEY,
#     "secret_key": onshape_keys.API_SECRET
# })

# # Create a new document
# doc = client.documents_api.create_document({"name": "Generated Tabs Sheet Metal"})
# doc_id = doc.id

# # Get workspace ID
# workspaces = client.documents_api.get_document_workspaces(did=doc_id)
# workspace_id = workspaces[0].id

# print("Document ID:", doc_id)
# print("Workspace ID:", workspace_id)

# # Upload STL file into the document
# with open("02_Mesh/tabs_mesh.stl", "rb") as f:
#     upload = client.blob_elements_api.upload_file_create_element(
#         did=doc_id,
#         wid=workspace_id,
#         file=f
#     )

# print("Upload result:", upload)
