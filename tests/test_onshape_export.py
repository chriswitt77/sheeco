import pickle
import os
from hgen_sm.export.part_export import export_to_onshape

def debug_from_part_pkl():
    pkl_path = "tests/part.pkl"
    
    if not os.path.exists(pkl_path):
        print(f"Error: {pkl_path} not found. Run the main app once to generate it.")
        return

    # Load the actual object
    with open(pkl_path, "rb") as f:
        part = pickle.load(f)

    print(f"Loaded Part ID: {part.part_id}")
    
    # Run your export logic
    filepath = export_to_onshape(part)
    print(f"Success! Check: {filepath}")

if __name__ == "__main__":
    debug_from_part_pkl()




    #### DEBUGGING ####
    # # Inside plot_part:
    # with open("real_part.pkl", "wb") as f:
    #     pickle.dump(part, f)
    # print("DEBUG: Real part saved to real_part.pkl")
    # #### DEBUGGING ####
    