from kivy.garden.mapview.mapview.mbtsource import MBTilesMapSource


class MBTilesCompositeMapSource(MBTilesMapSource):
    """
    Handles multiple MBTilesMapSource as one.
    """

    def __init__(self, filenames):
        super(MBTilesCompositeMapSource, self).__init__(filenames[0])
        self.filenames = filenames
        self.mbtiles_map_sources = []
        for filename in filenames:
            mbtiles_map_source = MBTilesMapSource(filename)
            self.mbtiles_map_sources.append(mbtiles_map_source)
        # merges meta data of all map sources
        self.min_zoom = min(
            [map_source.min_zoom for map_source in self.mbtiles_map_sources])
        self.max_zoom = max(
            [map_source.max_zoom for map_source in self.mbtiles_map_sources])
        # creates the largest bounding box that contains them all
        left = min(
            [map_source.bounds[0] for map_source in self.mbtiles_map_sources])
        bottom = min(
            [map_source.bounds[1] for map_source in self.mbtiles_map_sources])
        right = max(
            [map_source.bounds[2] for map_source in self.mbtiles_map_sources])
        top = max(
            [map_source.bounds[3] for map_source in self.mbtiles_map_sources])
        self.bounds = (left, bottom, right, top)

    def _load_tile(self, tile):
        for mbtiles_map_source in self.mbtiles_map_sources:
            ret = mbtiles_map_source._load_tile(tile)
            if ret is not None:
                return ret
