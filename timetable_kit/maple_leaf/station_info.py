# maple_leaf/station_info.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.

"""
Utility routines to style Amtrak and VIA station names as HTML or text for the Maple Leaf.

This mostly uses the Amtrak approach (lots of duplicated code) but with some special tweaks.

It probably deserves a refactor to eliminate the code duplication, but there are some tricky
problems with potential circular dependencies.
"""
from timetable_kit.amtrak import AmtrakStationInfo

# VIA rail station codes
from timetable_kit.maple_leaf.station_code_translations import amtrak_code_to_via_code


class MapleLeafStationInfo(AmtrakStationInfo):
    def station_name_to_multiline_text(self, station_name: str, major=False) -> str:
        """
        Produce pretty Amtrak station name for plaintext -- multi-line.

        Given an Amtrak station name in one of these two forms:
        Champaign-Urbana, IL (CHM)
        New Orleans, LA - Union Passenger Terminal (NOL)
        Produce a pretty-printable text version (possibly multiple lines)
        If "major", then make the station name bigger and bolder
        We want to avoid very long lines as they mess up timetable formats
        """
        if " - " in station_name:
            (city_state_name, second_part) = station_name.split(" - ", 1)
            (facility_name, suffix) = second_part.split(" (", 1)
            (station_code, _) = suffix.split(")", 1)
        else:
            facility_name = None
            (city_state_name, suffix) = station_name.split(" (", 1)
            (station_code, _) = suffix.split(")", 1)

        if major:
            enhanced_city_state_name = city_state_name.upper()
        else:
            enhanced_city_state_name = city_state_name

        # Special tweak for Maple Leaf -- we add the VIA rail station code too
        via_code = amtrak_code_to_via_code[station_code]

        enhanced_station_code = "".join(["(", station_code, " / ", via_code, ")"])

        if facility_name:
            enhanced_facility_name = "".join(["\n", " - ", facility_name])
        else:
            enhanced_facility_name = ""

        fancy_name = "".join(
            [
                enhanced_city_state_name,
                " ",
                enhanced_station_code,
                enhanced_facility_name,
            ]
        )
        return fancy_name
