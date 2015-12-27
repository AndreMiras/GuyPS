import os
import glob
import logging
from threading import Thread
from kivy.garden.mapview import MapView, MapMarker, Coordinate, MapSource
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty
from kivy.animation import Animation
from plyer import gps
from geopy.geocoders import Nominatim
from landez import MBTilesBuilder
from landez.sources import MBTilesReader
from popupmessage import PopupMessage
from confirmpopup import ConfirmPopup
from mbtcsource import MBTilesCompositeMapSource


__version__ = '0.1'
logging.basicConfig(level=logging.DEBUG)
app = None


class GpsMarker(MapMarker):

    def update_position(self):
        """
        Updates marker position on map layer.
        """
        layer = self._layer
        if layer is None:
            return
        mapview = layer.parent
        marker = self
        layer.set_marker_position(mapview, marker)

    def on_lat(self, instance, value):
        self.update_position()

    def on_lon(self, instance, value):
        self.update_position()


class OfflineMapsScreen(Screen):

    offline_maps_spinner = ObjectProperty()

    def available_offline_maps(self):
        """
        Lists *.mbtiles files and returns their basename.
        """
        filepaths = App.get_running_app().mbtiles_paths
        filenames = [os.path.basename(x) for x in filepaths]
        return filenames

    def offline_maps_spinner_values(self):
        """
        Adds "Online map" value to offline maps spinner.
        """
        maps = ["Online map"]
        maps += self.available_offline_maps()
        return maps


class CustomMapView(MapView):

    animated_latlon_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(CustomMapView, self).__init__(**kwargs)
        self.animated_latlon_property = Coordinate(self.lat, self.lon)

    def animated_center_on(self, latitude, longitude):
        widget = self
        anim = Animation(
            animated_latlon_property=Coordinate(latitude, longitude))
        anim.start(widget)

    def on_animated_latlon_property(self, instance, coordinate):
        # coordinate somehow lost its type
        coordinate = Coordinate(coordinate[0], coordinate[1])
        latitude = coordinate.lat
        longitude = coordinate.lon
        self.center_on(latitude, longitude)

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            self.animated_diff_scale_at(1, *touch.pos)
        return super(CustomMapView, self).on_touch_down(touch)

    def search(self, text):
        geolocator = Nominatim()
        location = geolocator.geocode(text)
        if location is None:
            popup = PopupMessage(
                        title="Error",
                        body="Can't find location.")
            popup.open()
            return
        latitude = location.latitude
        longitude = location.longitude
        # self.center_on(latitude, longitude)
        self.animated_center_on(latitude, longitude)

    def load_mbtiles(self, mbtiles):
        """
        Loads all the downloaded *.mbtiles, but centers on the requested one.
        """
        # downloaded *.mbtiles paths
        mbtiles_paths = App.get_running_app().mbtiles_paths
        # requested mbtiles path
        mbtiles_path = os.path.join(
            App.get_running_app().mbtiles_directory, mbtiles)
        map_source = MBTilesCompositeMapSource(mbtiles_paths)
        self.map_source = map_source
        mbreader = MBTilesReader(mbtiles_path)
        # centers on requested loaded mbtiles
        metadata = mbreader.metadata()
        if "center" in metadata:
            longitude, latitude, zoom = map(float, metadata["center"].split(","))
        self.animated_center_on(latitude, longitude)
        # TODO: highest zoom level of the loaded one
        # min_zoom = int(metadata.get("minzoom", 12))
        # mbreader.zoomlevels()

    def load_default_map_source(self):
        """
        Switch back to default MapSource online map.
        """
        self.map_source = MapSource()


class MapViewScreen(Screen):

    status_message = StringProperty()
    search_input_property = ObjectProperty()

    def update_status_message(self, text, lifetime=3):
        self.status_message = text
        # http://kivy.org/docs/api-kivy.clock.html
        # You cannot unschedule an anonymous function unless you keep
        # a reference to it.
        # It's better to add *args to your function definition
        # so that it can be called with an arbitrary number of parameters.
        Clock.unschedule(self.clean_status_message)
        Clock.schedule_once(self.clean_status_message, lifetime)

    def clean_status_message(self, dt):
        self.update_status_message("")


class Controller(RelativeLayout):
    mapview_screen_property = ObjectProperty()
    mapview_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(Controller, self).__init__(**kwargs)
        self.gps_marker = None
        self.mapview_property = self.mapview_screen_property.ids['mapview']
        self.bind_events()

    def bind_events(self):
        search_input = self.mapview_screen_property.search_input_property
        search_input.bind(
            on_text_validate=lambda obj: self.on_search(search_input.text))

    def start_gps_localize(self):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Waiting for GPS location...", 10)
        try:
            gps.configure(
                on_location=self.on_location, on_status=self.on_status)
            gps.start()
        except NotImplementedError:
            message = "GPS not found."
            mapview_screen.update_status_message(message)
            popup = PopupMessage(
                        title="Error",
                        body=message)
            popup.open()

    def stop_gps_localize(self):
        mapview = self.mapview_property
        gps.stop()
        # if self.gps_marker is None:
        mapview.remove_marker(self.gps_marker)
        self.gps_marker = None

    def toggle_gps_localize(self, start):
        if start:
            self.start_gps_localize()
        else:
            self.stop_gps_localize()

    def on_location(self, **kwargs):
        # gps.stop()
        mapview = self.mapview_property
        mapview_screen = self.mapview_screen_property
        latitude = kwargs['lat']
        longitude = kwargs['lon']
        if self.gps_marker is None:
            self.gps_marker = GpsMarker(lat=latitude, lon=longitude)
            mapview.add_marker(self.gps_marker)
        else:
            self.gps_marker.lat = latitude
            self.gps_marker.lon = longitude
        mapview.animated_center_on(latitude, longitude)
        mapview_screen.update_status_message(
            "Latitude: %s / Longitude: %s" %
            (round(latitude, 2), round(longitude, 2)), 10)

    def on_status(self, stype, status):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message(
            'type={}\n{}'.format(stype, status), 10)

    def on_search(self, text):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Looking for \"%s\"" % (text))

    def geopy_bbox_to_bbox(self, geopy_bbox):
        """
        Changes geopy bbox to mbtiles bbox.
        """
        # bottom, top, left, right
        (min_lat, max_lat, min_lon, max_lon) = [float(x) for x in geopy_bbox]
        bbox = (min_lon, min_lat, max_lon, max_lat)
        return bbox

    def prepare_download_for_offline1(self, text):
        """
        Verifes location requested for download is valid,
        i.e. exists and is allowed (city only).
        """
        geolocator = Nominatim()
        location = geolocator.geocode(text)
        if location is None:
            popup = PopupMessage(
                        title="Error",
                        body="Can't find location.")
            popup.open()
            return
        if location.raw['type'] != 'city':
            popup = PopupMessage(
                        title="Error",
                        body="Only cities are allowed.")
            popup.open()
            return
        # move to the downloading location
        mapview = self.mapview_property
        mapview.animated_center_on(location.latitude, location.longitude)
        # exctracts the city from the address string
        city = location.address.split(',')[0]
        # changes geopy bounding box format to landez one
        geopy_bbox = location.raw['boundingbox']
        filename = city + '.mbtiles'
        bbox = self.geopy_bbox_to_bbox(geopy_bbox)
        zoomlevels = range(12, 15+1)
        self.prepare_download_for_offline2(filename, bbox, zoomlevels)

    def prepare_download_for_offline2(self, filename, bbox, zoomlevels):
        """
        Verifies the file system is ready for this download.
        Checks the directory are created, verifies if the file already exists.
        """
        if not os.path.exists(App.get_running_app().mbtiles_directory):
            os.makedirs(App.get_running_app().mbtiles_directory)
        filepath = os.path.join(
            App.get_running_app().mbtiles_directory, filename)
        if os.path.exists(filepath):
            popup = ConfirmPopup(
                title="File already exists",
                text="File already exists.\nDo you want to override?")
            popup.bind(on_yes=lambda obj: self.download_for_offline(
                filepath, bbox, zoomlevels, delete=True))
            popup.open()
            mapview_screen = self.mapview_screen_property
            mapview_screen.update_status_message(
                "File already exists: %s" % (filename), 10)
            return
        self.download_for_offline(filepath, bbox, zoomlevels)

    def download_for_offline(self, filepath, bbox, zoomlevels, delete=False):
        """
        Starts the actual download and probes the progress.
        """
        if delete:
            os.remove(filepath)
        mb = MBTilesBuilder(filepath=filepath, cache=True)
        mb.add_coverage(bbox=bbox,
                        zoomlevels=zoomlevels)
        mb_run_thread = Thread(target=mb.run, kwargs={'force': False})
        mb_run_thread.start()
        Clock.schedule_interval(
            lambda dt: self.probe_mb_tiles_builder_thread(
                mb, mb_run_thread), 0.5)

    def download_world_map(self):
        """
        Downloads the first few zoom levels of world map.
        """
        filename = 'World.mbtiles'
        bbox = (-179.0, -89.0, 179.0, 89.0)
        zoomlevels = range(0, 5+1)
        self.prepare_download_for_offline2(filename, bbox, zoomlevels)

    def probe_mb_tiles_builder_thread(self, mb, mb_run_thread):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message(
            "Downloading tiles %s/%s" % (mb.rendered, mb.nbtiles), 10)
        if not mb_run_thread.is_alive():
            mapview_screen.update_status_message(
                "Downloading tiles %s/%s" % (mb.nbtiles, mb.nbtiles), 10)
            return False

    def load_mbtiles(self, mbtiles):
        mapview = self.mapview_property
        mapview.load_mbtiles(mbtiles)

    def load_map(self, name):
        """
        Either loads default online map or mbtiles local map.
        """
        mapview = self.mapview_property
        if name == "Online map":
            mapview.load_default_map_source()
        else:
            self.load_mbtiles(name)


class MapViewApp(App):
    def build(self):
        global app
        app = self
        self.controller = Controller()
        return self.controller

    def on_pause(self):
        # do not be close the application completely
        return True

    @property
    def mbtiles_directory(self):
        """
        Returns the mbtiles directory.
        """
        return os.path.join(self.user_data_dir, 'mbtiles')

    @property
    def mbtiles_paths(self):
        """
        Returns the list of mbtiles files paths.
        """
        filepath = os.path.join(
            self.mbtiles_directory, '*.mbtiles')
        filepaths = glob.glob(filepath)
        return filepaths

MapViewApp().run()
