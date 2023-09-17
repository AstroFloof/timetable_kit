# hartford_line/__init.py__
# Init file for hartford_line subpackage of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.hartford_line module

Hartford-line-specific functions for timetable_kit.
"""
from pathlib import Path
from typing import Iterable

# Published URL for the Hartford Line GTFS
from .get_gtfs import (
    published_gtfs_url,
)

# Where to find the GTFS (merged GTFS)
from .merge_gtfs import (
    gtfs_unzipped_local_path,
)
from timetable_kit.amtrak import Amtrak

# How to title the routes at the top of the column

# Routine to pretty-print a station name
# (including subtitles, connecting agency logos, etc.)
# This needs to be different from Amtrak's.
from .station_info import HartfordLineStationInfo

# For making the key for connecting services (including only those in this timetable)
# This takes a list of stations as an argument
from .connecting_services_data import get_all_connecting_services


class HartfordLine(Amtrak):
    # Hartford Line has only a few differences from the main Amtrak class, so this is all we need.

    name = "Hartford Line"
    input_dir = Path("specs_hartford")
    # Published agency name
    published_name = "CTRail Hartford Line"
    published_names_or = "CTRail Hartford Line or Amtrak"
    published_names_and = "CTRail Hartford Line and Amtrak"
    # Published agency website, for printing.
    # Does not include the https:// and should be capitalized for print.
    published_website = "HartfordLine.com"
    _station_info_class = HartfordLineStationInfo

    @staticmethod
    def get_all_connecting_services(stations: Iterable[str]) -> list[str]:
        from timetable_kit.hartford_line.connecting_services_data import (
            get_all_connecting_services,
        )

        return get_all_connecting_services(stations)
