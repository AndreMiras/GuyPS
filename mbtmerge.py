#!/usr/bin/env python2
import os
import sqlite3
import argparse
from shutil import copyfile


class MbtMerge(object):
    """
    Handles mbtiles merging.
    """

    def _merge_one(self, source, destination):
        """
        If destination is empty, creates it.
        """
        # if destination doesn't exist, nothing to do except copying
        if not os.path.isfile(destination):
            copyfile(source, destination)
            return
        conn = sqlite3.connect(destination)
        cursor = conn.cursor()
        # metadata = dict(cursor.execute("SELECT * FROM metadata"))
        cursor.execute("ATTACH '%s' as db2" % (source))
        cursor.execute("INSERT OR IGNORE INTO tiles SELECT * FROM db2.tiles")
        # TODO: do a proper merging of metadata and merge zoom levels
        cursor.execute("INSERT OR IGNORE INTO metadata SELECT * FROM db2.metadata")
        cursor.execute("DETACH db2")
        conn.commit()
        conn.close()

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
