import numpy as np
import itertools

from config.design_rules import min_flange_width
from src.hgen_sm.create_segments.geometry_helpers import calculate_plane, calculate_plane_intersection, create_bending_point, calculate_flange_points
from .utils import check_lines_cross, cord_lines_cross

from ..data.bend import Bend

from hgen_sm.data import *

def get_point_map(rect):
        return {
            id(rect.pointA): 'A', id(rect.pointB): 'B', id(rect.pointC): 'C', id(rect.pointD): 'D'
        }

def one_bend(segment):
    tab_x_id = segment.tab_x_id
    tab_z_id = segment.tab_z_id

    tab_x = segment.tabs[tab_x_id]
    tab_z = segment.tabs[tab_z_id]

    rect_x = segment.rects[tab_x_id]
    rect_z = segment.rects[tab_z_id]

    plane_x = calculate_plane(rect_x)
    plane_z = calculate_plane(rect_z)
    intersection = calculate_plane_intersection(plane_x, plane_z)
    bend = Bend(position=intersection["position"], orientation=intersection["orientation"])

    segment.bends.append(bend)

    rect_x_points = [rect_x.pointA, rect_x.pointB, rect_x.pointC, rect_x.pointD]
    rect_z_points = [rect_z.pointA, rect_z.pointB, rect_z.pointC, rect_z.pointD]

    rect_x_combinations = list(itertools.permutations(rect_x_points, 2))
    rect_z_combinations = list(itertools.permutations(rect_z_points, 2))

    segment_library = []
    for pair_x in rect_x_combinations:
        for pair_z in rect_z_combinations:
            # ---- Copy ----
            # For each segment the tab can change, and therefore needs to be copied. The rects stay the same in each case
            new_segment = segment.copy()
            new_tab_x = tab_x.copy()
            new_tab_z = tab_z.copy()
            new_segment.tabs[tab_x_id] = new_tab_x
            new_segment.tabs[tab_z_id] = new_tab_z

            # ---- Assign used Corner Points CP to Segment ----
            CPxL = pair_x[0]
            CPxR = pair_x[1]
            CPzL = pair_z[0]
            CPzR = pair_z[1]

            CPxL_id = get_point_map(rect_x)[id(CPxL)]
            CPxR_id = get_point_map(rect_x)[id(CPxR)]
            CPzL_id = get_point_map(rect_z)[id(CPzL)]
            CPzR_id = get_point_map(rect_z)[id(CPzR)]
            
            new_tab_x.corner_usage[CPxL_id] = True
            new_tab_x.corner_usage[CPxR_id] = True
            new_tab_z.corner_usage[CPzL_id] = True
            new_tab_z.corner_usage[CPzR_id] = True
            
            # ---- Bends ----
            new_bend = bend.copy()

            BPL = create_bending_point(CPxL, CPzL, bend)
            BPR = create_bending_point(CPxR, CPzR, bend)

            new_bend.BPL, new_bend.BPR = BPL, BPR

            new_bend.FPL_A, new_bend.FPL_B, new_bend.FPR_A, new_bend.FPR_B = (
                 calculate_flange_points(BPL, BPR, planeA=plane_x, planeB=plane_z)
            )

            inter = None
            # if check_lines_cross(CP, FP, BP): 
            #     #continue
            #     inter = cord_lines_cross(CP, FP, BP) # FOR DEBUGGING
            #     new_state.comment.append("Bad")  # FOR DEBUGGING
            # else: new_state.comment.append("Good") # FOR DEBUGGING

            segment_library.append(new_segment)

    return segment_library

# If there are two bends, there are three planes, which are called A, B and C
# The first rectangle the user provides is A, and the second one is C, and the one in between B
def two_bends(segment):
    rectangles = segment.rectangles
    tab_x_id = segment.tab_x_id
    tab_z_id = segment.tab_z_id

    planeA = segment.planes[0]
    planeC = segment.planes[1]

    rectA_corners = list(rectangles[0].values())
    rectC_corners = list(rectangles[1].values())

    for i, j in [(0,1), (1,2), (2,3), (3,0), (1,0), (2,1), (3,2), (0,3)]:     
        CPA1 = rectA_corners[i]
        CPA2 = rectA_corners[j]
        for i, CPC0 in enumerate(rectC_corners):
            CPC1 = rectC_corners[(i + 1) % 4]
            CPC2 = rectC_corners[(i - 1) % 4]
            rectCmid = (CPC1 + CPC2) / 2
            new_state = segment.copy()
            new_state.corner_points.extend([CPA1, CPA2, CPC0, CPC1, CPC2])
            
            CP_triangle = {"pointA": CPA1, "pointB": CPA2, "pointC": CPC0}
            CP_planeB = calculate_plane(rectangles=[CP_triangle])[0]
            CP_bendBC = calculate_plane_intersection(planes=[CP_planeB, planeC])
            dir_vector_BC = np.cross(planeC.orientation, CP_bendBC["direction"]) 
            dir_vector_BC /= np.linalg.norm(dir_vector_BC)

            if np.dot(dir_vector_BC, CPC0 - rectCmid) > 0:
                dir_vector_BC *= -1

            CP_bendBC["point"] = CP_bendBC["point"] - min_flange_width * dir_vector_BC

            BPC0 = CPC0 - min_flange_width * dir_vector_BC
            BPA1 = CPA1
            BPA2 = CPA2

            BP_triangle = {"pointA": BPA1, "pointB": BPA2, "pointC": BPC0}
            planeB = calculate_plane(rectangles=[BP_triangle])[0]
            bendBC = calculate_plane_intersection(planes=[planeB, planeC])
            
            bendAB = calculate_plane_intersection(planes=[planeA, planeB])
            
            dir_vector = np.cross(planeB.orientation, bendAB["direction"])
            dir_vector /= np.linalg.norm(dir_vector)
            
            # creat Flange points for side A on plane B
            FPAB1 = BPA1 - min_flange_width * dir_vector
            FPAB2 = BPA2 - min_flange_width * dir_vector
            
            # create BP1 and BP2 for Side C
            create_bending_point(CPC1, FPAB1, bendBC)
            create_bending_point(CPC2, FPAB2, bendBC)

            # Create Flange points for side C on plane B
            BPC1 = BPC0 + np.linalg.norm(BPA1 - BPA2)/2 * normalize(bendBC["direction"])
            BPC2 = BPC0 - np.linalg.norm(BPA1 - BPA2)/2 * normalize(bendBC["direction"])
            
            FPBC1, FPBC2, FPC1, FPC2 = calculate_flange_points(BPC1, BPC2, planeB, planeC)

            # # create Elements rectA, FlangeA, rectB, Flange C, rectC
            new_state.flanges.append({"bend_id": 0, "bend": bendAB, "BP1": BPA1, "BP2": BPA2, 
                                    "FPA1": FPAB1, "FPA2": FPAB2, "FPB1": FPAB1, "FPB2": FPAB2})
            new_state.flanges.append({"bend_id": 1, "bend": bendBC, "BP1": BPC1, "BP2": BPC2,
                                      "FPBC1": FPBC1, "FPBC2": FPBC2, "FPC1": FPC1, "FPC2": FPC2})

            new_state.elements.append(turn_points_into_element(rectA_corners))
            new_state.elements.append(turn_points_into_element([BPA1, FPAB1, FPAB2, BPA2]))
            new_state.elements.append(turn_points_into_element([FPAB2, FPBC1, FPBC2, FPAB1]))
            new_state.elements.append(turn_points_into_element([FPBC1, BPC1, BPC2, FPBC2]))
            new_state.elements.append(turn_points_into_element([BPC1, FPC1, FPC2, BPC2]))
            new_state.elements.append(turn_points_into_element([FPC1, CPC1, CPC2, FPC2]))
            segment.elements.append(turn_points_into_element(rectC_corners))

            new_state.points = {"CPA1": CPA1, "CPA2": CPA2,
                                "BPA1": BPA1, "BPA2":BPA2, 
                                "FPAB1":FPAB1, "FPAB2":FPAB2, "FPBC1":FPBC1, "FPBC2":FPBC2, 
                                "BPC1":BPC1, "BPC2":BPC2, 
                                "FPC1":FPC1, "FPC2":FPC2,
                                "CPC1":CPC1, "CPC2":CPC2}

            solutions.append(new_state)

    # for pairB in rectC_combinations:
    #     for BPA1 in rectA_corners:
    #         continue

    return solutions