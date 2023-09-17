from timetable_kit.amtrak import AmtrakAccessibilityInfo


# TODO BEFORE COMMIT HI ME: The feed needs to be passed in to avoid these cross dependencyes
class VIARailAccessibilityInfo(AmtrakAccessibilityInfo):
    # actual get methods are identical to amtrak's
    def _gather_accessibility_info(self):
        patched_feed = self._agency.gtfs_handler().patch_feed(self._agency.feed)
        assert (
            patched_feed is not self._agency.feed
        )  # it shouldn't be, as patch_feed should return a patched COPY

        # Now extract the dict from the feed
        stop_codes = patched_feed.stops["stop_code"].to_list()

        # First check for parent_station.
        # If this exists we need to do special stuff, which we have not implemented.
        # VIA Rail does not have stops with parents.
        # FIXME Warning! This depends on retaining the NaN blanks in the GTFS data.
        stops_with_parents = patched_feed.stops.dropna(subset=["parent_station"])
        if not stops_with_parents.empty:
            print(
                "Stops with parents found -- this invalidates wheelchair access detection. Aborting."
            )
            print(stops_with_parents)
            exit(1)
        # We interpret wheelchair_boarding with strict accuracy.
        # 0 or blank == unknown
        # 1 == accessible, for at least some services
        # 2 == inaccessible
        # gtfs_type_cleanup.py will correctly turn blanks into 0s for us, so don't need to worry about blanks.
        # We simply assume the wheelchair_access column exists, since it does for VIA Rail.
        stop_wheelchair_boarding_list = patched_feed.stops[
            "wheelchair_boarding"
        ].to_list()
        stop_can_board = map(lambda status: status == 1, stop_wheelchair_boarding_list)
        stop_cannot_board = map(
            lambda status: status == 2, stop_wheelchair_boarding_list
        )

        self._accessible_platform_dict = dict(zip(stop_codes, stop_can_board))
        self._inaccessible_platform_dict = dict(zip(stop_codes, stop_cannot_board))
        # these can now be drawn from using the methods carried over from the amtrak class
