import os
import glob
import logging
from threading import Thread
from kivy.app import App
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.garden.mapview import MapView, MapMarker, Coordinate, MapSource
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.animation import Animation
from plyer import gps
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
from landez import MBTilesBuilder
from landez.sources import MBTilesReader
from popupmessage import PopupMessage
from confirmpopup import ConfirmPopup
from mbtcsource import MBTilesCompositeMapSource
from mbtmerge import MbtMerge


__version__ = '0.1'
logging.basicConfig(level=logging.DEBUG)
app = None

OFFLINE_CITY_MIN_ZOOM = 12
OFFLINE_CITY_MAX_ZOOM = 15
OFFLINE_WORLD_MIN_ZOOM = 0
OFFLINE_WORLD_MAX_ZOOM = 5
MBTILES_DIRECTORY_PATH = "mbtiles"
MAIN_MBTILES_PATH = "main.mbtiles"
JSON_STORE_PATH = "config.json"


class MbtMergeManager(object):
    """
    Keeps track mbtiles merging state (merged vs not merged)
    and handles merging.
    """
    def __init__(self):
        json_store_path = App.get_running_app().json_store_path
        self.store = JsonStore(json_store_path)

    def merge_not_merged(self):
        """
        Merges not merged files.
        """
        mbtmerge = MbtMerge()
        sources = self.not_merged()
        destination = App.get_running_app().main_mbtiles_path
        mbtmerge.merge(sources, destination)
        for source in sources:
            self.add_to_merged(source)

    def not_merged(self):
        """
        Returns the list of not merged files.
        """
        merged_list = self.merged()
        not_merged_list = App.get_running_app().mbtiles_paths
        for merged in merged_list:
          not_merged_list.remove(merged)
        return not_merged_list

    def merged(self):
        """
        Returns the list of merged files.
        """
        try:
            merged = self.store.get('merged_mbtiles')['list']
        except KeyError:
            merged = []
        return merged

    def add_to_merged(self, mbtiles_path):
        """
        Adds the mbtiles to the merged list.
        """
        merged = self.merged()
        merged.append(mbtiles_path)
        self.store.put('merged_mbtiles', list=merged)

    def remove_from_merged(self, mbtiles_path):
        """
        Removes the mbtiles from the merged list.
        """
        merged = self.merged()
        merged.remove(mbtiles_path)
        self.store.put('merged_mbtiles', list=merged)

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

    def on_parent(self, instance, value):
        """
        Gets called when the widget gets loaded or unloaded.
        Merges unmerged mbtiles files.
        """
        # self.parent is not None when the widget gets loaded
        is_loaded = self.parent is not None
        if is_loaded:
            mbt_merge_manager = MbtMergeManager()
            mbt_merge_manager.merge_not_merged()

    def available_offline_maps(self):
        """
        Lists *.mbtiles files and returns their basename.
        """
        filepaths = App.get_running_app().mbtiles_paths
        filenames = [os.path.basename(x) for x in filepaths]
        return filenames


class CustomMapView(MapView):

    # default values
    DEFAULT_LATLON = (43.61, 3.88)
    DEFAULT_ZOOM = 8
    # properties used for lat/lon animations
    animated_latlon_property = ObjectProperty()
    animated_zoom_property = NumericProperty()

    def __init__(self, **kwargs):
        """
        Loads default lat/long and zoom values
        """
        super(CustomMapView, self).__init__(**kwargs)
        # loads default values
        self.lat, self.lon = CustomMapView.DEFAULT_LATLON
        self.zoom = CustomMapView.DEFAULT_ZOOM
        # updates animated properties with default values
        self.animated_latlon_property = Coordinate(self.lat, self.lon)
        self.animated_zoom_property = self.zoom

    def animated_diff_scale(self, d):
        """
        Makes a smooth differential in or out scaling.
        Overloads MapView.animated_diff_scale_at() with default x, y values.
        x, y are choosen to be the middle of the screen.
        """
        size_x, size_y = self.size
        x = size_x / 2
        y = size_y / 2
        super(CustomMapView, self).animated_diff_scale_at(d, x, y)

    def _animated_zoom_to_target(self, dt):
        """
        Animated zoom until zoom target is reached.
        """
        diff = (self._zoom_target - self.zoom)
        if diff == 0:
            # zoom target is reached
            return False
        diff = diff < 0 and -1 or 1
        self.animated_diff_scale(diff)

    def animated_zoom(self, zoom):
        """
        Makes a smooth in or out zoom.
        """
        diff = (zoom - self.zoom) + 1
        self.animated_diff_scale(diff)

    def animated_zoom2(self, zoom):
        """
        Makes a smooth in or out zoom.
        """
        self._zoom_target = zoom
        Clock.unschedule(self._animated_zoom_to_target)
        Clock.schedule_interval(self._animated_zoom_to_target, 0.25)

    def zoom_out_in(
            self, zoom_out,
            zoom_in=None, duration=2, transition='in_out_expo'):
        """
        Zooms out then back in using animations.
        if zoom_in value is None, zooms back to initial zoom.
        """
        widget = self
        if zoom_in is None:
            # defaults to initial zoom
            zoom_in = self.zoom
        anim = Animation(
            animated_zoom_property=zoom_out,
            duration=duration/2.0,
            t=transition)
        anim += Animation(
            animated_zoom_property=zoom_in,
            duration=duration/2.0,
            t=transition)
        anim.start(widget)

    def on_animated_zoom_property(self, instance, zoom):
        self.zoom = int(zoom)

    def animated_center_on(self, latitude, longitude, zoom=None):
        """
        Animated move from current location to the new specified lat/lon.
            1) zooms out
            2) moves to location
            3) zooms back to initial
        """
        widget = self
        initial_zoom = zoom if zoom is not None else self.zoom
        zoom_out = 5
        duration = 2
        transition = 'in_out_expo'
        # zooms out and back in
        self.zoom_out_in(
            zoom_out, zoom_in=initial_zoom,
            duration=duration, transition=transition)
        # moves to location
        anim = Animation(
            animated_latlon_property=Coordinate(latitude, longitude),
            duration=duration,
            t=transition)
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
        try:
            location = geolocator.geocode(text)
        except GeocoderServiceError as e:
            popup = PopupMessage(
                        title="Error",
                        body=e.message)
            popup.open()
            return
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
        mbt_merge_manager = MbtMergeManager()
        not_merged_mbtiles = mbt_merge_manager.not_merged()
        main_mbtiles_path = App.get_running_app().main_mbtiles_path
        # not yet merged *.mbtiles plus main one
        mbtiles_paths = not_merged_mbtiles + [main_mbtiles_path]
        # requested mbtiles path
        mbtiles_path = os.path.join(
            App.get_running_app().mbtiles_directory, mbtiles)
        map_source = MBTilesCompositeMapSource(mbtiles_paths)
        self.map_source = map_source
        mbreader = MBTilesReader(mbtiles_path)
        # centers on requested loaded mbtiles
        metadata = mbreader.metadata()
        if "center" in metadata:
            center = metadata["center"]
            longitude, latitude, default_zoom = map(float, center.split(","))
        # defaults to the minimum available zoom
        zoom = int(default_zoom)
        self.animated_center_on(latitude, longitude, zoom)

    def load_default_map_source(self):
        """
        Switch back to default MapSource online map.
        """
        self.map_source = MapSource()


class Toolbar(BoxLayout):

    MAX_ALPHA = 0.6
    alpha_color = NumericProperty()

    def __init__(self, **kwargs):
        super(Toolbar, self).__init__(**kwargs)
        self.show(animated=False)

    def show(self, animated=True):
        if animated:
            widget = self
            anim = Animation(alpha_color=Toolbar.MAX_ALPHA, duration=1)
            anim.start(widget)
        else:
            self.alpha_color = Toolbar.MAX_ALPHA

    def hide(self, animated=True):
        if animated:
            widget = self
            anim = Animation(alpha_color=0, duration=1)
            anim.start(widget)
        else:
            self.alpha_color = 0


class MapViewScreen(Screen):

    status_bar_property = ObjectProperty()
    status_message = StringProperty()
    search_input_property = ObjectProperty()

    def __init__(self, **kwargs):
        super(MapViewScreen, self).__init__(**kwargs)
        # starts by default without the status message bar
        Clock.schedule_once(
            lambda dt: self.status_bar_property.hide(animated=False), 0)

    def update_status_message(self, text, lifetime=3):
        self.status_bar_property.show()
        self.status_message = text
        # http://kivy.org/docs/api-kivy.clock.html
        # You cannot unschedule an anonymous function unless you keep
        # a reference to it.
        # It's better to add *args to your function definition
        # so that it can be called with an arbitrary number of parameters.
        Clock.unschedule(self._clean_status_message)
        Clock.schedule_once(self._clean_status_message, lifetime)

    def _clean_status_message(self, dt=None):
        self.status_message = ""
        self.status_bar_property.hide()


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
        # mapview = self.mapview_property
        # mapview_screen = self.mapview_screen_property
        # mapview.bind(
        #     zoom=lambda obj, zoom: mapview_screen.update_status_message(
        #         "Zoom level %s" % (zoom)))

    def gps_not_found_message(self):
        """
        Shows a "GPS not found" status bar and popup error message.
        """
        mapview_screen = self.mapview_screen_property
        message = "GPS not found."
        # status bar error message
        mapview_screen.update_status_message(message)
        # popup error message
        popup = PopupMessage(
                    title="Error",
                    body=message)
        popup.open()

    def start_gps_localize(self):
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message("Waiting for GPS location...", 10)
        try:
            gps.configure(
                on_location=self.on_location, on_status=self.on_status)
            gps.start()
        except NotImplementedError:
            self.gps_not_found_message()

    def stop_gps_localize(self):
        mapview = self.mapview_property
        try:
            gps.stop()
        except NotImplementedError:
            self.gps_not_found_message()
            return
        if self.gps_marker is not None:
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
        location_type = location.raw['type']
        if location_type not in ['city', 'administrative']:
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
        zoomlevels = range(OFFLINE_CITY_MIN_ZOOM, OFFLINE_CITY_MAX_ZOOM+1)
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
            mbt_merge_manager = MbtMergeManager()
            mbt_merge_manager.remove_from_merged(filepath)
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
        zoomlevels = range(OFFLINE_WORLD_MIN_ZOOM, OFFLINE_WORLD_MAX_ZOOM+1)
        self.prepare_download_for_offline2(filename, bbox, zoomlevels)

    def probe_mb_tiles_builder_thread(self, mb, mb_run_thread):
        """
        Probes tiles downloading.
        """
        mapview_screen = self.mapview_screen_property
        mapview_screen.update_status_message(
            "Downloading tiles %s/%s" % (mb.rendered, mb.nbtiles), 10)
        if not mb_run_thread.is_alive():
            mapview_screen.update_status_message(
                "Downloading tiles %s/%s" % (mb.nbtiles, mb.nbtiles), 10)
            return False

    def load_mbtiles(self, mbtiles):
        """
        Loads mbtiles local maps.
        """
        mapview = self.mapview_property
        mapview.load_mbtiles(mbtiles)

    def load_default_map_source(self):
        """
        Loads default online map.
        """
        mapview = self.mapview_property
        mapview.load_default_map_source()


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
    def json_store_path(self):
        """
        Returns the JSON store file path.
        """
        return os.path.join(self.user_data_dir, JSON_STORE_PATH)

    @property
    def main_mbtiles_path(self):
        """
        Returns the merged mbtiles file path.
        """
        return os.path.join(self.user_data_dir, MAIN_MBTILES_PATH)

    @property
    def mbtiles_directory(self):
        """
        Returns the mbtiles directory.
        """
        return os.path.join(self.user_data_dir, MBTILES_DIRECTORY_PATH)

    @property
    def mbtiles_paths(self):
        """
        Returns the list of mbtiles files paths.
        """
        filepath = os.path.join(
            self.mbtiles_directory, u'*.mbtiles')
        filepaths = glob.glob(filepath)
        return filepaths

MapViewApp().run()
