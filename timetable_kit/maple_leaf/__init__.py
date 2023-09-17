# hartford_line/__init.py__
# Init file for maple_leaf subpackage of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.maple_leaf module

Maple Leaf specific functions for timetable_kit.

This defines an interface; each agency needs to provide the same interface
"""
from pathlib import Path
from typing import Iterable

from timetable_kit.amtrak import Amtrak

# Hartford Line leans on Amtrak functions, but this does not work
# import timetable_kit.amtrak as amtrak


# Routine to pretty-print a station name
# (including subtitles, connecting agency logos, etc.)
# Based on Amtrak's but with subtle differences.
# (Amtrak station DB DOES include Canadian stations)
from timetable_kit.maple_leaf.station_info import MapleLeafStationInfo


# For making the key for connecting services (including only those in this timetable)
# This takes a list of stations as an argument
from timetable_kit.maple_leaf.connecting_services_data import (
    get_all_connecting_services,
)

# The rest of this should be copied from Amtrak
module_location = Path(__file__).parent


class MapleLeaf(Amtrak):
    name = "Maple Leaf"
    input_dir = Path("specs_maple_leaf")
    # Published agency name
    published_name = "Amtrak and VIA Rail"
    published_names_or = "Amtrak or VIA Rail"
    published_names_and = "Amtrak and VIA Rail"

    # Published URL for the GTFS.... um.  Use Amtrak for now
    # Need to redo the templates to allow multiples

    _station_info_class = MapleLeafStationInfo

    # This is where the Maple Leaf specific GTFS should go.
    gtfs_zip_local_path = module_location / "gtfs.zip"
    gtfs_unzipped_local_path = module_location / "gtfs"

    @staticmethod
    def get_all_connecting_services(stations: Iterable[str]) -> list[str]:
        from timetable_kit.maple_leaf.connecting_services_data import (
            get_all_connecting_services,
        )

        return get_all_connecting_services(stations)
