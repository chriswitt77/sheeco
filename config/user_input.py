A = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0],
        'mounts': []  # Optional: list of 3D mount coordinates
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80],
        'mounts': []
    },
    {
        'pointA': [30, 0, 100],
        'pointB': [30, 30, 100],
        'pointC': [80, 30, 100],
        'mounts': []
    }
]

B = [
    {
        'pointA': [10, 30, 0],
        'pointB': [10, 0, 0],
        'pointC': [60, 0, 0]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80]
    }
]

C = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0]
    },
    {
        'pointA': [-20, 80, 40],
        'pointB': [-20, 40, 40],
        'pointC': [-40, 40, 80]
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
        'pointC': [50, 50, 0]
    },
    {
        'pointA': [0, 0, 10],
        'pointB': [50, 0, 10],
        'pointC': [50, 50, 10]
    }
]

same_plane = [
    {
        'pointA': [0, 0, 0],
        'pointB': [50, 0, 0],
        'pointC': [50, 50, 0]
    },
    {
        'pointA': [150, 100, 0],
        'pointB': [120, 100, 0],
        'pointC': [120, 150, 0]
    }
]

# Example with mounts
with_mounts = [
    {
        'pointA': [50, 0, 0],
        'pointB': [50, 100, 0],
        'pointC': [100, 100, 0],
        'mounts': [
            [70, 25, 0],   # Mount near left side
            [75, 80, 0]    # Mount near right side
        ]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80],
        'mounts': [
            [0, 50, 60]   # Single mount
        ]
    }
]

# -------------------------------------------------
# ------ Verification and Validation Examples -----
# -------------------------------------------------

ver_example_one = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0]
    },
    {
        'pointA': [-20, 80, 40],
        'pointB': [-20, 40, 40],
        'pointC': [-40, 40, 80]
    }
]

ver_example_two = [
    {
        'pointA': [30, 30, 0],
        'pointB': [30, 0, 0],
        'pointC': [80, 0, 0]
    },
    {
        'pointA': [0, 80, 40],
        'pointB': [0, 40, 40],
        'pointC': [0, 40, 80]
    },
    {
        'pointA': [30, 0, 100],
        'pointB': [30, 30, 100],
        'pointC': [80, 30, 100]
    }
]

shock_absorber_sequence = [['1', '2'], ['1', '0']]
shock_absorber = [
    {
        'pointA': [20, 0, 0],
        'pointB': [80, 0, 0],
        'pointC': [80, 35, 0],
    },
    {
        'pointA': [0, 0, 20],
        'pointB': [0, 0, 60],
        'pointC': [0, 80, 60],
    },
    {
        'pointA': [20, 45, 0],
        'pointB': [80, 45, 0],
        'pointC': [80, 80, 0],
    },
]

shock_absorber_double_tab_sequence = [['1', '2'], ['0', '1'], ['3', '2']]
shock_absorber_double_tab = [
    {
        'pointA': [20, 0, 0],
        'pointB': [80, 0, 0],
        'pointC': [80, 35, 0],
    },
    {
        'pointA': [0, 0, 20],
        'pointB': [0, 0, 60],
        'pointC': [0, 35, 60],
    },
    {
        'pointA': [0, 45, 20],
        'pointB': [0, 45, 60],
        'pointC': [0, 80, 60],
    },
    {
        'pointA': [20, 45, 0],
        'pointB': [80, 45, 0],
        'pointC': [80, 80, 0],
    },
]

ver_acrylic_model = [
    {
        'pointA': [20, 0, 0],
        'pointB': [50, 0, 0],
        'pointC': [50, 40, 0]
    },
    {
        'pointA': [0, 0, 10],
        'pointB': [0, 0, 70],
        'pointC': [0, 40, 70]
    }
]

campbell_vertical = [
    {
        'pointA': [0, 0, 0],
        'pointB': [40, 0, 0],
        'pointC': [40, 40, 0]
    },
    {
        'pointA': [20, 35, 60],
        'pointB': [20, 5, 60],
        'pointC': [20, 5, 100]
    }
]


barda_example_one_sequence = [['0', '1'], ['0', '2'], ['3', '0'], ['3', '4'], ['3', '5'], ]
barda_example_one = [
    {
        'pointA': [0, 0, 55],
        'pointB': [0, 50, 55],
        'pointC': [35, 50, 55]
    },
    {
        'pointA': [-2, -25, 0],
        'pointB': [-2, -30, 0],
        'pointC': [32, -30, 0]
    },
    {
        'pointA': [3, 75, 0],
        'pointB': [3, 80, 0],
        'pointC': [35, 80, 0]
    },
    {
        'pointA': [60, 0, 55],
        'pointB': [60, 50, 55],
        'pointC': [100, 50, 55]
    },
    {
        'pointA': [58, -25, 0],
        'pointB': [58, -30, 0],
        'pointC': [90, -30, 0]
    },
    {
        'pointA': [58, 75, 0],
        'pointB': [58, 80, 0],
        'pointC': [95, 80, 0]
    },
]

barda_example_two_sequence = [['0', '1'], ['0', '2'], ['0', '3']]
barda_example_two = [
    {
        'pointA': [0, 0, 90],
        'pointB': [120, 0, 90],
        'pointC': [120, 220, 90]
    },
    {
        'pointA': [0, 80, 0],
        'pointB': [14, 80, 0],
        'pointC': [14, 120, 0]
    },
    {
        'pointA': [104, 56, 0],
        'pointB': [120, 56, 0],
        'pointC': [120, 126, 0],
    },
    {
        'pointA': [-40, 252, 100],
        'pointB': [120, 262, 100],
        'pointC': [120, 262, 110],
    },
]

zylinderhalter = [
    {
        'pointA': [0, 0, 0],
        'pointB': [40, 0, 0],
        'pointC': [0, 30, 0],
        'mounts': [
            [20, 10, 0]
        ]
    },
    {
        'pointA': [0, 90, 0],
        'pointB': [40, 90, 0],
        'pointC': [0, 120, 0],
        'mounts': [
            [20, 110, 0]
        ]
    },
    {
        'pointA': [0, 50, 30],
        'pointB': [40, 50, 30],
        'pointC': [0, 70, 30],
        'mounts': [
            [10, 50, 30],
            [30, 50, 30],
            [10, 70, 30],
            [30, 70, 30]
        ]
    }
]

transportschuh = [
    {
        'pointA': [0, 0, 0],
        'pointB': [160, 0, 0],
        'pointC': [0, 160, 0],
        'mounts': [
            [30, 15, 0],
            [130, 15, 0]
            #[30, 150, 0],
            #[130, 150, 0]
        ]
    },
    {
        'pointA': [0, 180, 40],
        'pointB': [160, 180, 40],
        'pointC': [0, 180, 200],
        # 'mounts': [
        #     [30, 180, 110],
        #     [130, 180, 110],
        #     [30, 180, 185],
        #     [130, 180, 185]
        # ]
    }
]

# ver_example_one, ver_example_two, shock_absorber, shock_absorber_double_tab, ver_acrylic_model, campbell_vertical, barda_example_one, barda_example_two, zylinderhalter, transportschuh
RECTANGLE_INPUTS = zylinderhalter
