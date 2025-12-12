from src.hgen_sm.data import Part

def part_assembly(part, segments, cfg):
    segments
    
    for segment in segments:
        return






















    part.bends.update(segments[0].bends)
    part.tabs[segments[0].tab_x_id] = segments[0].tabs[0]

    for segment in segments:
        tab_x = part.get_tab_id(segment.tab_x_id)
        tab_x = part.tabs[tab_x]
        tab_z = part.get_tab_id(segment.tab_z_id)
        tab_z = part.tabs[tab_z]
        for bend in segment.bends:
            
            # 1. Assign Tabs to the Bend object
            bend.tab_x = tab_x
            bend.tab_z = tab_z
            
            # 2. Assign Bend to the Tabs (Create the bidirectional link)
            tab_x.bends.append(bend)
            tab_z.bends.append(bend)

    return segments[0]

    # part.extend(segments=segments_combination)
    # for segment in segments_combination:
    # return assembly