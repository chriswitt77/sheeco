# src/hgen-sm/determine_sequences/__init__.py
# Version information
__version__ = "0.1.0"
__author__ = "Maxim Moellhoff"

from .choose_pairs import determine_sequences, can_connect
from .surface_separation import separate_surfaces, are_siblings

# Define what is available when the package is imported
__all__ = [
    "__version__",
    "determine_sequences",
    "separate_surfaces",
    "are_siblings",
    "can_connect"
]