from hgen_sm.create_segments.bend_strategies import one_bend, two_bends

def create_segments(segment, segment_cfg):
    segment_library = []

    if segment_cfg.get('single_bend', True): #and not collision_tab_bend(bend, rectangles)  
        # ADD IF RECTANGLES ARE PARALLEL, SKIP!!!
        new_segments = one_bend(segment)
        if new_segments is not None:
            segment_library.extend(new_segments)

    if segment_cfg.get('double_bend', True):
        segment_library.extend(two_bends(segment))

    return segment_library