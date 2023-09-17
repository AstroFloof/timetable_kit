# runtime_config.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
This file exists to hold data which is set at runtime, but is the same across a single run of
timetable.py.  This data needs to be shared by multiple modules, so it needs to be "low-level".

This data includes the critical choice of which agency's subpackage to use.
"""
from typing import Type

# The agencies we might need to import
from timetable_kit.debug import debug_print
from timetable_kit.generic_agency import Agency

# These are the choices which can be set at the command line.
agency_choices = ["generic", "amtrak", "via", "hartford", "maple_leaf"]


def get_agency_class(agency_name: str) -> Type[Agency]:
    """
    Set the agency subpackage to use to get agency-specific data (e.g. generic, amtrak, via).

    Called by initialization code
    """

    match agency_name:
        case "generic":
            raise NotImplementedError("There is no generic agency, what did you do?")
        case "amtrak":
            debug_print(1, "Using Amtrak data")
            from timetable_kit.amtrak import Amtrak

            return Amtrak
        case "hartford":
            debug_print(1, "Using Hartford Line data with Amtrak data")
            from timetable_kit.hartford_line import HartfordLine

            return HartfordLine
        case "via":
            debug_print(1, "Using VIA Rail data")
            from timetable_kit.via import VIARail

            return VIARail
        case "maple_leaf":
            debug_print(1, "Using Amtrak and VIA Rail data for Maple Leaf")
            from timetable_kit.maple_leaf import MapleLeaf

            return MapleLeaf
        case _:
            raise ImportError("Invalid agency subpackage choice")
