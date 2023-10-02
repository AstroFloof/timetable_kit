# generic_agency/agency.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
timetable_kit.generic_agency.agency module

This holds a class for "Agency" intended to be used as a singleton.
It has an interface; Amtrak and others need to provide the same interface.
This should be made easier by class inheritance.
"""
from __future__ import annotations

from timetable_kit.feed_enhanced import FeedEnhanced
from timetable_kit.debug import debug_print


# Intended to be used both directly and by subclasses
class Agency:
    """Agency-specific code for interpreting specs and GTFS feeds for a generic agency"""

    def __init__(
        self: Agency,
    ) -> None:
        # This is the GTFS feed.
        # It is filled in by init_from_feed, due to complex initialization ordering requirements.
        self._feed = None
        # These are built from the GTFS feed.
        # They start blank and are filled in by initialization code on first use (memoized)
        self._stop_code_to_stop_id_dict = None
        self._stop_id_to_stop_code_dict = None
        self._stop_code_to_stop_name_dict = None
        self._accessible_platform_dict = None
        self._inaccessible_platform_dict = None

    def init_from_feed(self, feed: FeedEnhanced):
        """Initalize this object with an enhanced GTFS feed.  Used for translating stop_code to and from stop_id."""
        """We don't want to do this at object creation for multiple reasons."""
        """1. We need to call agency routines on the feed before using it."""
        """2. We may not need to use this agency object at all, but it may need to be created in initialization."""
        """3. We may not need to initialize these tables in subclasses."""
        """4. This is expensive in both memory usage and time."""
        if self._feed is not None:
            debug_print(
                1,
                "Warning: resetting feed on agency when it has already been set once: this is discouraged",
            )
        self._feed = feed

    def _prepare_dicts(self):
        """
        Prepare the dicts for:
        _stop_code_to_stop_id
        _stop_id_to_stop_code
        _stop_code_to_stop_name
        _accessible_platform_dict
        _inaccessible_platform_dict

        These depend on a previously established feed (set by init_from_feed)
        """
        debug_print(1, "Preparing stop_code / stop_id dicts")
        if self._feed is None:
            raise RuntimeError(
                "in Agency class: init_from_feed must be run before preparing dicts"
            )

        # Create the conversion dicts from the feed
        stop_codes = self._feed.stops["stop_code"].to_list()
        stop_ids = self._feed.stops["stop_id"].to_list()
        stop_names = self._feed.stops["stop_name"].to_list()

        self._stop_code_to_stop_id_dict = dict(zip(stop_codes, stop_ids))
        self._stop_id_to_stop_code_dict = dict(zip(stop_ids, stop_codes))
        self._stop_code_to_stop_name_dict = dict(zip(stop_codes, stop_names))

        # OK.  Now wheelchair boarding.
        # First check for parent_station.
        # If this exists we need to do special stuff, which we have not implemented.
        # VIA Rail does not have stops with parents.
        # FIXME Warning! This depends on retaining the NaN blanks in the GTFS data.
        stops_with_parents = self._feed.stops.dropna(subset=["parent_station"])
        if not stops_with_parents.empty:
            print(
                "Warning: Stops with parents found -- this invalidates wheelchair access detection."
            )
            print(stops_with_parents)
            # Default to no information
            self._accessible_platform_dict = {}
            self._inaccessible_platform_dict = {}
        elif "wheelchair_boarding" not in self._feed.stops.columns:
            # If the wheelchair_boarding column does not exist... bail
            debug_print(1, "Warning: wheelchair_boarding column not found in GTFS data")
            # Default to no information
            self._accessible_platform_dict = {}
            self._inaccessible_platform_dict = {}
        else:
            # We interpret wheelchair_boarding with strict accuracy.
            # 0 or blank == unknown
            # 1 == accessible, for at least some services
            # 2 == inaccessible
            # gtfs_type_cleanup.py will correctly turn blanks into 0s for us, so don't need to worry about blanks.
            stop_wheelchair_boarding_list = self._feed.stops[
                "wheelchair_boarding"
            ].to_list()
            stop_can_board_list = [bool(x == 1) for x in stop_wheelchair_boarding_list]
            stop_cannot_board_list = [
                bool(x == 2) for x in stop_wheelchair_boarding_list
            ]
            self._accessible_platform_dict = dict(zip(stop_codes, stop_can_board_list))
            self._inaccessible_platform_dict = dict(
                zip(stop_codes, stop_cannot_board_list)
            )
        return

    def stop_code_to_stop_id(self, stop_code: str) -> str:
        """Given a stop_code, return a stop_id"""
        # Memoized
        if self._stop_code_to_stop_id_dict == None:
            self._prepare_dicts()
        return self._stop_code_to_stop_id_dict[stop_code]

    def stop_id_to_stop_code(self, stop_id: str) -> str:
        """Given a stop_id, return a stop_code"""
        # Memoized
        if self._stop_id_to_stop_code_dict == None:
            self._prepare_dicts()
        return self._stop_id_to_stop_code_dict[stop_id]

    def stop_code_to_stop_name(self, stop_code: str) -> str:
        """Given a stop_code, return a stop_name -- raw"""
        # Memoized
        if self._stop_code_to_stop_name_dict == None:
            self._prepare_dicts()
        return self._stop_code_to_stop_name_dict[stop_code]

    def station_has_inaccessible_platform(self, station_code: str) -> bool:
        """
        Does the station explicitly have an inaccessible platform?

        This excludes stations which don't say either way.

        Constructs and caches the data on first call.

        From GTFS data.
        """
        if self._inaccessible_platform_dict is None:
            self._prepare_dicts()
        return self._inaccessible_platform_dict[station_code]

    def station_has_accessible_platform(self, station_code: str) -> bool:
        """
        Does this station explicitly have an accessible platform?

        This excludes stations which don't say either way.

        Constructs and caches the data on first call.

        From GTFS data.
        """
        if self._accessible_platform_dict is None:
            self._prepare_dicts()
        return self._accessible_platform_dict[station_code]


# Establish the singleton
_singleton = Agency()


def get_singleton():
    """Get singleton for generic agency"""
    global _singleton
    return _singleton
