from __future__ import annotations

from enum import Enum

class MonitorType(str, Enum):
    """
    An enumeration to save the states of monitor threads.
    """
    periodic = 'periodic'
    change = 'change'
    inactive = 'inactive'

    def from_string(string_mode: str) -> MonitorType:
        """
        Raises ValueError.
        """
        if string_mode == 'periodic':
            return MonitorType.periodic
        elif string_mode == 'change':
            return MonitorType.change
        elif string_mode == 'inactive':
            return MonitorType.inactive
        else:
            raise ValueError("Only 'periodic', 'change' or 'inactive' are allowed for monitor type.")

