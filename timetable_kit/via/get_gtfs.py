#! /usr/bin/env python3
# via/get_gtfs.py
# Part of timetable_kit
# Copyright 2022, 2023 Nathanael Nerode.  Licensed under GNU Affero GPL v.3 or later.
"""
Retrieve VIA Rail's static GTFS data from the canonical location.

Severely duplicative of amtrak/get_gtfs.py.  Duplication should be removed,
but I needed a working prototype
"""

import sys  # for sys.exit
from pathlib import Path
from zipfile import ZipFile

import requests


if __name__ == "__main__":
    from timetable_kit.amtrak import Amtrak

    gtfs_handler = Amtrak.get_gtfs_handler()
    gtfs_handler.save_gtfs(gtfs_handler.download_gtfs())
    print("Amtrak GTFS saved at " + str(Amtrak.gtfs_zip_local_path))
    gtfs_handler.unzip_gtfs()
