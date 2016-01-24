#!/usr/bin/env python2
import os
import sqlite3
import argparse
from shutil import copyfile


class MbtMerge(object):
    """
    Handles mbtiles merging.
    """

    def _merge_tiles_table(self, source, destination):
        """
        Merges tiles table from source to destination.
        """
        conn = sqlite3.connect(destination)
        cursor = conn.cursor()
        cursor.execute("ATTACH '%s' as db2" % (source))
        cursor.execute("INSERT OR IGNORE INTO tiles SELECT * FROM db2.tiles")
        conn.commit()
        conn.close()

    def _merge_metadata_zooms(self, source, destination):
        """
        Merges source and destination metadata minzoom and maxzoom values.
        """
        conn = sqlite3.connect(destination)
        cursor = conn.cursor()
        cursor.execute("ATTACH '%s' as db2" % (source))
        metadata = dict(cursor.execute("SELECT * FROM metadata"))
        metadata2 = dict(cursor.execute("SELECT * FROM db2.metadata"))
        min_zoom = int(metadata.get("minzoom", 12))
        min_zoom2 = int(metadata2.get("minzoom", 12))
        new_min_zoom = min(min_zoom, min_zoom2)
        max_zoom = int(metadata.get("maxzoom", 14))
        max_zoom2 = int(metadata2.get("maxzoom", 14))
        new_max_zoom = max(max_zoom, max_zoom2)
        cursor.execute("UPDATE metadata SET value=:value WHERE name='minzoom'", { "value": new_min_zoom })
        cursor.execute("UPDATE metadata SET value=:value WHERE name='maxzoom'", { "value": new_max_zoom })
        cursor.execute("DETACH db2")
        conn.commit()
        conn.close()

    def _merge_metadata_bounds(self, source, destination):
        """
        Merges source and destination metadata bounds.
        Creates the largest bounding box that contains both
        source and destination.
        """
        # TODO
        pass

    def _merge_metadata_table(self, source, destination):
        """
        Merges source and destination metadata tables.
        """
        self._merge_metadata_zooms(source, destination)
        self._merge_metadata_bounds(source, destination)

    def _merge_one(self, source, destination):
        """
        If destination is empty, creates it.
        """
        # if destination doesn't exist, nothing to do except copying
        if not os.path.isfile(destination):
            copyfile(source, destination)
            return
        self._merge_tiles_table(source, destination)
        self._merge_metadata_table(source, destination)

    def merge(self, sources, destination):
        for source in sources:
            self._merge_one(source, destination)


def main():
    parser = argparse.ArgumentParser(description="Merges mbtiles together.")
    parser.add_argument(
        '--sources', '-s',
        type=str, nargs='+', required=True,
        help="source mbtiles files")
    parser.add_argument(
        '--destination', '-d',
        type=str, nargs=1, required=True,
        help="destination mbtiles file")
    args = parser.parse_args()
    sources = args.sources
    destination = args.destination[0]
    mbtmerge = MbtMerge()
    mbtmerge.merge(sources, destination)

if __name__ == "__main__":
    main()
