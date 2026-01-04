# ============================================================================
# USER INPUT - Rectangle Definitions with Optional Mounts
# ============================================================================

A = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0],
        'mounts': [
            [55, 15, 0]
        ]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80],
        'mounts': [
            [0, 60, 60]
        ]
    },
    {
        'pointA': [30, 0, 100],
        'pointB': [30, 30, 100],
        'pointC': [80, 30, 100],
        'mounts': [
            [55, 15, 100]
        ]
    }
]

B = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0],
        'mounts': [
            [55, 10, 0]
        ]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80],
        'mounts': [
            [0, 60, 60]
        ]
    }
]

C = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0]
        # No mounts for this rectangle
    },
    {
        'pointA': [-20, 80, 40],
        'pointB': [-20, 40, 40],
        'pointC': [-40, 40, 80],
        'mounts': [
            [-30, 60, 60]
        ]
    }
]

D = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0]
    },
    {
        'pointA': [-20, 80, 40],
        'pointB': [-20, 40, 40],
        'pointC': [-40, 40, 80]
    },
    {
        'pointA': [30, 0, 100],
        'pointB': [30, 30, 100],
        'pointC': [80, 30, 100]
    },
    {
        'pointA': [60, 0, 50],
        'pointB': [60, 30, 50],
        'pointC': [140, 30, 50]
    }
]

two_parallel = [
    {
        'pointA': [0, 0, 0],
        'pointB': [50, 0, 0],
        'pointC': [50, 50, 0],
        'mounts': [
            [25, 25, 0]
        ]
    },
    {
        'pointA': [0, 0, 10],
        'pointB': [50, 0, 10],
        'pointC': [50, 50, 10],
        'mounts': [
            [25, 25, 10]
        ]
    }
]

same_plane = [
    {
        'pointA': [0, 0, 0],
        'pointB': [50, 0, 0],
        'pointC': [50, 50, 0]
    },
    {
        'pointA': [150, 0, 0],
        'pointB': [20, 0, 0],
        'pointC': [20, 50, 0]
    }
]

multi_mount_example = [
    {
        'pointA': [20, 0, 0],
        'pointB': [20, 60, 0],
        'pointC': [80, 0, 0],
        'mounts': [
            [50, 10, 0],
            [50, 50, 0]
        ]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80],
        'mounts': [
            [0, 60, 60]
        ]
    }
]

# ============================================================================
# Select which input to use
# ============================================================================

RECTANGLE_INPUTS = multi_mount_example