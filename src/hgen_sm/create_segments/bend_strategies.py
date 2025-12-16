import numpy as np
import itertools

from config.design_rules import min_flange_width
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection, create_bending_point, calculate_flange_points
from .utils import check_lines_cross, cord_lines_cross, normalize

from ..data.bend import Bend

from hgen_sm.data import Part, Tab, Rectangle

from typing import Set, Tuple

def lines_cross(
    P1: np.ndarray, P2: np.ndarray, 
    P3: np.ndarray, P4: np.ndarray, 
    epsilon: float = 1e-6
) -> bool:
    """
    Checks if the 2D segments P1-P2 and P3-P4 intersect.
    
    This function uses a 2D cross product check for segment intersection.
    Assumes points are already projected onto a 2D plane (e.g., ignores the Z-coordinate
    if the segment is planar to the XY plane).
    """
    
    # Simple projection to 2D (ignoring Z)
    p1 = P1[:2]
    p2 = P2[:2]
    p3 = P3[:2]
    p4 = P4[:2]

    def cross_product_2d(a, b, c) -> float:
        """Calculates the 2D cross product (orientation) of vectors (b-a) and (c-a)"""
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    o1 = cross_product_2d(p1, p2, p3)
    o2 = cross_product_2d(p1, p2, p4)
    o3 = cross_product_2d(p3, p4, p1)
    o4 = cross_product_2d(p3, p4, p2)

    # General Case: Segments intersect if and only if the orientation 
    # of the three points (o1, o2) flips, and (o3, o4) flips.
    if (o1 * o2 < -epsilon) and (o3 * o4 < -epsilon):
        return True

    # Collinear/Boundary cases (often needed for full robustness, 
    # but excluded here for minimal complexity)
    return False

def are_corners_neighbours(cp_id1: str, cp_id2: str) -> bool:
    """Checks if two corner IDs are adjacent on the perimeter of the rectangle."""
    
    # Define all valid, adjacent (non-directional) pairs
    # Using a Set of Tuples ensures fast, order-independent lookup.
    ADJACENT_PAIRS: Set[Tuple[str, str]] = {
        ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')
    }
    
    # Normalize the input by sorting the IDs to handle both ('A', 'B') and ('B', 'A')
    normalized_pair = tuple(sorted((cp_id1, cp_id2)))
    
    return normalized_pair in ADJACENT_PAIRS

from typing import Dict, Any, Optional

def next_cp(points_dict: Dict[str, Any], current_key: str) -> Optional[str]:
    ordered_keys = list(points_dict.keys())
    
    try:
        current_index = ordered_keys.index(current_key)
        
        # If the input is the last element (D), return the first element (A)
        if current_index == len(ordered_keys) - 1:
            return ordered_keys[0]
        
        # Otherwise, return the next element
        elif current_index + 1 < len(ordered_keys):
            return ordered_keys[current_index + 1]
            
        else:
            # Should only happen if the dictionary is empty or contains only one point
            return None
            
    except ValueError:
        return None

def one_bend(segment):
    tab_x = segment.tabs['tab_x']
    tab_x_id = tab_x.tab_id
    tab_z = segment.tabs['tab_z']
    tab_z_id = tab_z.tab_id

    rect_x = tab_x.rectangle
    rect_z = tab_z.rectangle

    plane_x = calculate_plane(rect_x)
    plane_z = calculate_plane(rect_z)
    intersection = calculate_plane_intersection(plane_x, plane_z)
    bend = Bend(position=intersection["position"], orientation=intersection["orientation"])
    
    rect_x_combinations = list(itertools.permutations(rect_x.corners, 2))
    rect_z_combinations = list(itertools.permutations(rect_z.corners, 2))

    segment_library = []
    for pair_x in rect_x_combinations:
        CP_xL_id = pair_x[0]
        CP_xL = tab_x.points[CP_xL_id]
        CP_xR_id = pair_x[1]
        CP_xR = tab_x.points[CP_xR_id]
        
        for pair_z in rect_z_combinations:
            CP_zL_id = pair_z[0]
            CP_zL = tab_z.points[CP_zL_id]
            CP_zR_id = pair_z[1]
            CP_zR = tab_z.points[CP_zR_id]
            
            # ---- Bending Points ----
            BPL = create_bending_point(CP_xL, CP_zL, bend)
            BPR = create_bending_point(CP_xR, CP_zR, bend)
            FPxL, FPxR, FPzL, FPzR = calculate_flange_points(BPL, BPR, planeA=plane_x, planeB=plane_z)

            # ---- Check Crossover
            if lines_cross(CP_zL, FPzL, CP_zR, FPzR) or lines_cross(CP_xL, FPxL, CP_xR, FPxR):
                continue

            # ---- Update Segment.tabs ----
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            # ---- Insert Points in Tab x----
            CPL = {CP_xL_id: CP_xL}
            bend_points_x = { 
                                f"FP{tab_x_id}{tab_z_id}L": FPxL, 
                                f"BP{tab_x_id}{tab_z_id}L": BPL, 
                                f"BP{tab_x_id}{tab_z_id}R": BPR, 
                                f"FP{tab_x_id}{tab_z_id}R": FPxR
                                }
            
            new_tab_x.insert_points(L=CPL, add_points=bend_points_x)
            
            if not are_corners_neighbours(CP_xL_id, CP_xR_id):
                rm_point_id = next_cp(new_tab_x.rectangle.corners, CP_xL_id)
                rm_point = new_tab_x.rectangle.corners[rm_point_id]
                new_tab_x.remove_point(point={rm_point_id: rm_point})

            # ---- Insert Points in Tab z----
            CPL = {CP_zL_id: CP_zL}
            bend_points_z = { 
                                f"FP{tab_z_id}{tab_x_id}L": FPzL, 
                                f"BP{tab_z_id}{tab_x_id}L": BPL, 
                                f"BP{tab_z_id}{tab_x_id}R": BPR, 
                                f"FP{tab_z_id}{tab_x_id}R": FPzR
                                }
            
            new_tab_z.insert_points(L=CPL, add_points=bend_points_z)
            
            if not are_corners_neighbours(CP_zL_id, CP_zR_id):
                rm_point_id = next_cp(new_tab_z.rectangle.corners, CP_zL_id)
                rm_point = new_tab_z.rectangle.corners[rm_point_id]
                new_tab_z.remove_point(point={rm_point_id: rm_point})
            
            # ---- Update New Segment with New Tabs and add to Stack
            new_segment.tabs['tab_x'] = new_tab_x
            new_segment.tabs['tab_z'] = new_tab_z
            segment_library.append(new_segment)

    return segment_library

def two_bends(segment):
    tab_x = segment.tabs['tab_x']
    tab_z = segment.tabs['tab_z']
    tab_x_id = tab_x.tab_id
    tab_z_id = tab_z.tab_id

    rect_x = tab_x.rectangle
    rect_z = tab_z.rectangle

    plane_x = calculate_plane(rect_x)
    plane_z = calculate_plane(rect_z)

    rect_x_combinations = list(itertools.permutations(rect_x.corners, 2))
    rect_z_combinations = list(itertools.permutations(rect_z.corners, 2))

    segment_library = []
    for pair_x in rect_x_combinations:  
        CPxL_id = pair_x[0]
        CPxR_id = pair_x[1]
        CPxL = tab_x.points[CPxL_id]
        CPxR = tab_x.points[CPxR_id]
        CPxM = (CPxL + CPxR) / 2

        for i, CPzM_id in enumerate(rect_z.corners):
            new_segment = segment.copy()

            CPzM = rect_z.corners[CPzM_id]
            CPz_plus1_id = list(rect_z.corners.keys())[(i + 1) % 4]
            CPz_minus1_id = list(rect_z.corners.keys())[(i - 1) % 4]
            CPz_plus1 = rect_z.corners[CPz_plus1_id]
            CPz_minus1 = rect_z.corners[CPz_minus1_id]

            # # If dist(FP-CP) > min_flange_length for both CP, use corner strat
            # # If it is smaller, use edge strat for whatever edge it is smaller
            # # corner strat: FP are defined by going the movement CM-rect_center from the adjacent CP -> FP,
            # # BP becomes the points going from FP min_flange_lange away from centroid
            # # edge strat: CPM becomes FPL or FPR, and the other FP is defined by going along the edge till its enough  
            # # 
            # FPxyL =  
            # FPxyR = 
            # CP_triangle = {"A": FPxyL, "B": FPxyR, "C": CPzM}
            # plane_y = calculate_plane(triangle=CP_triangle)
            
            
            # rect_z_centroid = (CPzL + CPzR) / 2
            CP = rect_z.corners
            pts = np.array([CP['A'], CP['B'], CP['C'], CP['D']])
            rect_z_centroid = pts.mean(axis=0)

            CP_triangle = {"A": CPxL, "B": CPxR, "C": CPzM}
            plane_y = calculate_plane(triangle=CP_triangle)
            new_tab_y = Tab(tab_id=tab_x_id + tab_z_id, points =  CP_triangle)
            tab_y_id = new_tab_y.tab_id
            
            CP_bend_yz = calculate_plane_intersection(plane_y, plane_z)
            dir_vector_yz = np.cross(plane_z.orientation, CP_bend_yz["orientation"]) 
            dir_vector_yz /= np.linalg.norm(dir_vector_yz)

            if np.dot(dir_vector_yz, rect_z_centroid - CPzM) > 0:
                dir_vector_yz *= -1

            CP_bend_yz["position"] = CP_bend_yz["position"] - min_flange_width * dir_vector_yz

            # ---- Bending Points ----
            BPzM = CPzM - 5*min_flange_width * dir_vector_yz
            BPxL = CPxL
            BPxR = CPxR

            BP_triangle = {"A": BPxL, "B": BPxR, "C": BPzM}
            plane_y = calculate_plane(triangle=BP_triangle)

            intersection_xy = calculate_plane_intersection(plane_x, plane_y)
            bend_xy = Bend(position=intersection_xy["position"], orientation=intersection_xy["orientation"])
            
            intersection_yz = calculate_plane_intersection(plane_y, plane_z)
            bend_yz = Bend(position=intersection_yz["position"], orientation=intersection_yz["orientation"])
            
            dir_vector = np.cross(plane_y.orientation, bend_xy.orientation)
            dir_vector /= np.linalg.norm(dir_vector)
            
            # creat Flange points for side x on plane y
            FPxyL, FPxyR, FPyxL, FPyxR = calculate_flange_points(BPxL, BPxR, plane_x, plane_y)
            
            # create BPL and BPR for Side z
            BPzL = create_bending_point(CPz_plus1, FPxyL, bend_yz)
            BPzR = create_bending_point(CPz_minus1, FPxyR, bend_yz)

            # Create Flange points for side z on plane y
            BPyzL = BPzM + np.linalg.norm(BPzL - BPzR)/2 * normalize(bend_yz.orientation)
            BPyzR = BPzM - np.linalg.norm(BPzL - BPzR)/2 * normalize(bend_yz.orientation)

            FPyzL, FPyzR, FPzyL, FPzyR = calculate_flange_points(BPzL, BPzR, plane_y, plane_z)

            # ---- Create new Segment ----
            new_segment = segment.copy()
            new_tab_x = new_segment.tabs['tab_x']
            new_tab_z = new_segment.tabs['tab_z']

            # ---- Insert Points in Tab x----
            bend_points_x = { 
                                f"FP{tab_x_id}_{tab_y_id}L": FPxyL, 
                                f"BP{tab_x_id}_{tab_y_id}L": BPxL, 
                                f"BP{tab_x_id}_{tab_y_id}R": BPxR, 
                                f"FP{tab_x_id}_{tab_y_id}R": FPxyR
                                }
            
            new_tab_x.insert_points(L={CPxL_id: CPxL}, add_points=bend_points_x)
            
            # ---- Replace Points in Tab y----
            bend_points_y = { 
                                f"FP{tab_y_id}_{tab_x_id}L": FPyxL, 
                                f"BP{tab_y_id}_{tab_x_id}L": BPxL, 
                                f"BP{tab_y_id}_{tab_x_id}R": BPxR, 
                                f"FP{tab_y_id}_{tab_x_id}R": FPyxR,
                                f"FP{tab_y_id}_{tab_z_id}L": FPyzL, 
                                f"BP{tab_y_id}_{tab_z_id}L": BPzL, 
                                f"BP{tab_y_id}_{tab_z_id}R": BPzR, 
                                f"FP{tab_y_id}_{tab_z_id}R": FPyzR
                                
                                }
            new_tab_y.points = bend_points_y
            
            # ---- Insert Points in Tab z ----
            bend_points_z = { 
                                f"FP{tab_z_id}_{tab_y_id}L": FPzyL, 
                                f"BP{tab_z_id}_{tab_y_id}L": BPzL, 
                                f"BP{tab_z_id}_{tab_y_id}R": BPzR, 
                                f"FP{tab_z_id}_{tab_y_id}R": FPzyR
                                }
            
            new_tab_z.insert_points(L={CPz_plus1_id: CPz_plus1}, add_points=bend_points_z)

            new_segment.tabs = {'tab_x':new_tab_x, 'tab_y': new_tab_y, 'tab_z': new_tab_z}

            segment_library.append(new_segment)

    return segment_library