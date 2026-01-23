import numpy as np
import pyvista as pv

from src.hgen_sm.export.part_export import export_to_onshape, export_to_json

from functools import partial


def plot_part(part, plotter, plot_cfg, solution_idx, len_solutions):
    if plotter is None or plot_cfg is None:
        return
    
    standard_point_size = plot_cfg.get('point_size', 20)
    standard_font_size = plot_cfg.get('font_size', 30)

    color_rectangle = "#785ef0"
    color_tabs = "#648fff"
    color_flange = "#1dcc54"
    color_bend = "#ffb000"
    color_BP1 = "#dc267f"
    color_BP2 = "#26dc83"

    if plot_cfg.get('Legend', True):
        legend_text = """
    BP = Bending Point
    CP = Corner Point
    FP = Flange Point
    
    0,1,2,... = ID of Tab
    
    A,B,C,D = Corner Points of user input rectangle
    
    L = Left Side of Flange
    R = Right Side of Flange
            """
        plotter.add_text(legend_text, position="lower_right", font_size=15, color="black")

    # Plot rectangles
    if plot_cfg.get('Rectangles', False):

        # 1. Loop through all tabs in the part
        for tab_id, tab_obj in part.tabs.items():

            # Check if this specific tab has a 'rectangle' attribute/property
            if getattr(tab_obj, 'rectangle', None):
                corners = tab_obj.rectangle.points
                # Rectangle geometry: A -> B -> C -> D forms the perimeter
                pts = np.array([corners['A'], corners['B'], corners['C'], corners['D']])

                # Define the single quadrilateral face (4 points: 0, 1, 2, 3)
                # Order A -> B -> C -> D ensures correct winding
                faces = np.hstack([[4, 0, 1, 2, 3]])

                rectangle_mesh = pv.PolyData(pts, faces)

                label = f"Tab_{tab_id}"
                plotter.add_mesh(
                    rectangle_mesh,
                    color=color_rectangle,
                    opacity=0.9,
                    show_edges=True,
                )

                center_point = pts.mean(axis=0)
                if plot_cfg.get('Labels', False):
                    plotter.add_point_labels(
                            center_point,
                            [label],
                            font_size=standard_font_size,
                            always_visible=True,
                            show_points=False  # Do not plot a visible dot at the center
                        )

    if plot_cfg.get('Tabs', False) and getattr(part, 'tabs', None):
        for tab_id, tab_obj in part.tabs.items():
            if tab_obj.points:
                points_list = list(tab_obj.points.values())
                points_array = np.array(points_list)
                num_points = points_array.shape[0]

                # For tabs with more than 4 points (intermediate tabs), always triangulate
                # because they may be non-convex or non-planar
                should_triangulate = plot_cfg.get('Triangulate Tabs', False) or num_points > 4

                faces = np.hstack([[num_points], np.arange(num_points)])
                if should_triangulate:
                    mesh = pv.PolyData(points_array, faces=faces).triangulate()
                else:
                    mesh = pv.PolyData(points_array, faces=faces)
                plotter.add_mesh(
                    mesh,
                    color=color_tabs,
                    opacity=0.8,
                    show_edges=False,
                    style='surface',
                    label=f"Tab {tab_id}"
                )

                if plot_cfg.get('Labels', False): # Add labels for each point
                    point_ids = list(tab_obj.points.keys())
                    for i, point_id in enumerate(point_ids):
                        point_coord = points_array[i]
                        plotter.add_point_labels(
                            point_coord,
                            [point_id],
                            font_size=standard_font_size,
                            point_size=standard_point_size,
                            show_points=False
                        )
    
    if plot_cfg.get('Flanges', False) and getattr(part, 'tabs', None):
        first_flange_plotted = False
        for tab_id, tab_obj in part.tabs.items():
            # Group points by their full identifier (between BP/FP and L/R)
            flanges = {}
            for p_id, coords in tab_obj.points.items():
                if p_id.startswith("BP") or p_id.startswith("FP"):
                    # Extract full index (e.g., 'BP0_0_0_01L' -> '0_0_0_01', 'FP01R' -> '01')
                    # Remove prefix (BP/FP) and suffix (L/R)
                    idx = p_id[2:-1]  # Strip first 2 chars (BP/FP) and last char (L/R)
                    if idx not in flanges:
                        flanges[idx] = {}
                    flanges[idx][p_id] = coords

            # Plot each detected flange
            for idx, f_points in flanges.items():
                # A valid flange needs exactly 4 points: 2 BP and 2 FP
                if len(f_points) == 4:
                    # Sort points to ensure a clean quadrilateral (BPL -> BPR -> FPR -> FPL)
                    # This prevents 'bow-tie' artifacts in the mesh
                    ordered_keys = [f"BP{idx}L", f"BP{idx}R", f"FP{idx}R", f"FP{idx}L"]

                    try:
                        # Try ordered keys first for proper quadrilateral winding
                        pts = np.array([f_points[k] for k in ordered_keys])
                    except KeyError:
                        # Fallback: sort by key type to get proper winding
                        bp_keys = sorted([k for k in f_points if k.startswith("BP")])
                        fp_keys = sorted([k for k in f_points if k.startswith("FP")])
                        if len(bp_keys) == 2 and len(fp_keys) == 2:
                            # BPL -> BPR -> FPR -> FPL ordering
                            ordered_keys = [bp_keys[0], bp_keys[1], fp_keys[1], fp_keys[0]]
                            pts = np.array([f_points[k] for k in ordered_keys])
                        else:
                            pts = np.array([f_points[k] for k in f_points])

                    try:
                        faces = np.hstack([[4, 0, 1, 2, 3]])
                        flange_mesh = pv.PolyData(pts, faces)

                        # Only add label for first flange to avoid legend clutter
                        label = f"Flange {idx}" if not first_flange_plotted else None
                        first_flange_plotted = True

                        plotter.add_mesh(
                            flange_mesh,
                            color=color_flange,
                            opacity=0.9,
                            show_edges=True,
                            line_width=2,
                            label=label
                        )
                    except Exception:
                        continue  # Skip if there's any issue with the mesh

    # Plot mounts as red circles on the tab plane
    if plot_cfg.get('Mounts', True) and getattr(part, 'tabs', None):
        color_mount = "red"
        for tab_id, tab_obj in part.tabs.items():
            if hasattr(tab_obj, 'mounts') and tab_obj.mounts:
                # Calculate plane normal from tab points
                if 'A' in tab_obj.points and 'B' in tab_obj.points and 'C' in tab_obj.points:
                    A = np.array(tab_obj.points['A'])
                    B = np.array(tab_obj.points['B'])
                    C = np.array(tab_obj.points['C'])
                    AB = B - A
                    BC = C - B
                    normal = np.cross(AB, BC)
                    normal_len = np.linalg.norm(normal)
                    if normal_len > 1e-9:
                        normal = normal / normal_len
                    else:
                        normal = np.array([0, 0, 1])  # Fallback
                else:
                    normal = np.array([0, 0, 1])  # Fallback

                for mount in tab_obj.mounts:
                    if mount.global_coords is not None:
                        center = mount.global_coords
                        radius = mount.size
                        # Create a disc (filled circle) on the tab plane
                        disc = pv.Disc(center=center, inner=0, outer=radius, normal=normal, c_res=32)
                        plotter.add_mesh(
                            disc,
                            color=color_mount,
                            opacity=1.0,
                        )
                        if plot_cfg.get('Labels', False):
                            plotter.add_point_labels(
                                center,
                                [f"M_{tab_id}"],
                                font_size=standard_font_size,
                                show_points=False
                            )

    # Solution ID
    if solution_idx is not None and len_solutions is not None:
        counter_text = f"Solution: {solution_idx}/{len_solutions}"
        plotter.add_text(counter_text, position="upper_left", font_size=20, color="black", shadow=True)


    # --- Export Button ---
    def callback_text(part, state):
        if state:
            export_to_json(part)
            # plotter.add_checkbox_button_widget(partial(callback_text, part), value=False, position=(15, 80)) # Reset button state so it can be clicked again
    plotter.add_checkbox_button_widget(partial(callback_text, part), position=(15,80), color_on='green')
    plotter.add_text("Export JSON", position=(80, 85), font_size=18)

    def callback_onshape(part, state):
        if state:
            export_to_onshape(part)
            # plotter.add_checkbox_button_widget(partial(callback_onshape, part), value=False, position=(15, 15)) # Reset button state so it can be clicked again
    plotter.add_checkbox_button_widget(partial(callback_onshape, part), position=(15,15), color_on='green')
    plotter.add_text("Export Onshape Feature Script", position=(80, 20), font_size=18)

    # --- Finish plot ---
    plotter.show_grid()
    plotter.render()

def plot_input_rectangles(part, plot_cfg):
    """
    Plot only the input rectangles and mounts before processing.
    Creates a blocking window - processing continues only after user closes it.
    """
    plotter = pv.Plotter()

    standard_point_size = plot_cfg.get('point_size', 20)
    standard_font_size = plot_cfg.get('font_size', 30)

    color_rectangle = "#785ef0"
    color_mount = "red"

    # Add title
    plotter.add_text("Input Rectangles - Close to continue", position="upper_left", font_size=25, color="black", shadow=True)

    # Plot rectangles
    for tab_id, tab_obj in part.tabs.items():
        if getattr(tab_obj, 'rectangle', None):
            corners = tab_obj.rectangle.points
            pts = np.array([corners['A'], corners['B'], corners['C'], corners['D']])
            faces = np.hstack([[4, 0, 1, 2, 3]])
            rectangle_mesh = pv.PolyData(pts, faces)

            plotter.add_mesh(
                rectangle_mesh,
                color=color_rectangle,
                opacity=0.9,
                show_edges=True,
            )

            # Add tab label at center
            center_point = pts.mean(axis=0)
            label = f"Tab_{tab_id}"
            if plot_cfg.get('Labels', False):
                plotter.add_point_labels(
                    center_point,
                    [label],
                    font_size=standard_font_size,
                    always_visible=True,
                    show_points=False
                )

            # Add corner point labels
            if plot_cfg.get('Corner Points', False):
                for corner_name, corner_coord in corners.items():
                    plotter.add_point_labels(
                        corner_coord,
                        [f"{corner_name}_{tab_id}"],
                        font_size=standard_font_size - 5,
                        point_size=standard_point_size,
                        show_points=True,
                        point_color="blue"
                    )

    # Plot mounts
    if plot_cfg.get('Mounts', True):
        for tab_id, tab_obj in part.tabs.items():
            if hasattr(tab_obj, 'mounts') and tab_obj.mounts:
                # Calculate plane normal from rectangle
                if getattr(tab_obj, 'rectangle', None):
                    corners = tab_obj.rectangle.points
                    A = np.array(corners['A'])
                    B = np.array(corners['B'])
                    C = np.array(corners['C'])
                    AB = B - A
                    AC = C - A
                    normal = np.cross(AB, AC)
                    normal_len = np.linalg.norm(normal)
                    if normal_len > 1e-9:
                        normal = normal / normal_len
                    else:
                        normal = np.array([0, 0, 1])
                else:
                    normal = np.array([0, 0, 1])

                for mount in tab_obj.mounts:
                    if mount.global_coords is not None:
                        center = mount.global_coords
                        radius = mount.size
                        disc = pv.Disc(center=center, inner=0, outer=radius, normal=normal, c_res=32)
                        plotter.add_mesh(
                            disc,
                            color=color_mount,
                            opacity=1.0,
                        )
                        if plot_cfg.get('Labels', False):
                            plotter.add_point_labels(
                                center,
                                [f"M_{tab_id}"],
                                font_size=standard_font_size,
                                show_points=False
                            )

    plotter.show_grid()
    plotter.enable_trackball_style()
    plotter.show()  # Blocking - waits for user to close window


def plot_solutions(solutions, plot_cfg, plotter=None):
    """
    Create interactive plotting window, which can be cycled through to explore all the solutions.
    Creates a new plotter instance separate from the input visualization.
    """
    if plotter is None:
        plotter = pv.Plotter()

    solution_idx = [0]
    def show_solution(idx):
        plotter.clear()
        plotter.clear_button_widgets()
        part = solutions[idx]
        plot_part(part, plotter=plotter, plot_cfg=plot_cfg, solution_idx=solution_idx[0]+1, len_solutions=len(solutions))

    def key_press_callback(key):
        if key == 'Right':
            solution_idx[0] = (solution_idx[0] + 1) % len(solutions)
            show_solution(solution_idx[0])
        elif key == 'Left':
            solution_idx[0] = (solution_idx[0] - 1) % len(solutions)
            show_solution(solution_idx[0])

    plotter.add_key_event("Right", lambda: key_press_callback("Right"))
    plotter.add_key_event("Left", lambda: key_press_callback("Left"))
    show_solution(solution_idx[0])
    plotter.enable_trackball_style()

    plotter.show()

    return