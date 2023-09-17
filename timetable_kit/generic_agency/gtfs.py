from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import requests
from gtfs_kit import Feed

from timetable_kit.debug import debug_print
from timetable_kit.feed_enhanced import FeedEnhanced


@dataclass
class AgencyGTFSHandler:
    """
    Generic GTFS handler. Simple as can be.
    Patching should be reviewed every time Amtrak releases another GTFS.
    """

    gtfs_url: str
    zip_path: Path | str
    unzip_path: Path | str

    def download_gtfs(self):
        """Download GTFS from its canonical location and return it"""
        response = requests.get(self.gtfs_url)
        if response.status_code != requests.codes.ok:
            print(
                "Download of ",
                self.gtfs_url,
                " failed with error ",
                response.status_code,
            )
            response.raise_for_status()  # Raise an error
        return response.content  # This is binary data

    def save_gtfs(self, gtfs_zip: bytes):
        """Save GTFS file in a canonical local location."""
        with open(self.zip_path, "wb") as binary_file:
            binary_file.write(gtfs_zip)

    def unzip_gtfs(self):
        """
        Extract GTFS file from a canonical local location to a canonical local location.

        This is used directly by the program.
        """
        with ZipFile(self.zip_path) as my_zip:
            if not self.unzip_path.exists():
                self.unzip_path.mkdir(parents=True)
            my_zip.extractall(path=self.unzip_path)
            print("Extracted to " + str(self.unzip_path))

    def patch_feed(self, feed: Feed | FeedEnhanced) -> Feed | FeedEnhanced:
        """
        Apply patches to the GTFS feed to fix issues with specific agencies' mishandling of hem, which is too common...
        Default implementation: do not patch the feed.
        """
        debug_print(2, "Falling back to default feed patching: not at all")
        return feed
