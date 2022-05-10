# -*- coding: utf-8 -*-
from math import prod
import xbmc
import xbmcgui
import xbmcplugin
import sys
import requests

from resources.lib.common import *
from resources.lib.kodilogging import LOG
from resources.lib import model, kodiutils, settings
from urllib.parse import urlencode
from urllib.parse import parse_qsl
from bs4 import BeautifulSoup
from resources.lib.player import ViuPlayer


class ViuPlugin(object):
    @staticmethod
    def safe_string(content):
        import unicodedata

        if not content:
            return content

        if isinstance(content, str):
            content = unicodedata.normalize("NFKD", content).encode("ascii", "ignore")

        return content

    @staticmethod
    def get_images(item):
        """
        Returns the image url.
        """
        if not item:
            return None

        return item["series_image_url"] or item["cover_image_url"]

    @staticmethod
    def get_user_input():
        kb = xbmc.Keyboard("", "Search")
        kb.doModal()
        if not kb.isConfirmed():
            return

        # User input
        return kb.getText()

    @staticmethod
    def get_stream_url(stream):
        for url_key in ["url4", "url3", "url2", "url"]:
            if url_key in stream:
                resolution_key = settings.get_resolution()
                if resolution_key in stream[url_key]:
                    return stream[url_key][resolution_key]
                else:
                    return stream[url_key][list(stream[url_key].keys())[-1]]

    def __init__(self, plugin_args):
        # Get the plugin url in plugin:// notation.
        self.plugin_url = plugin_args[0]
        # Get the plugin handle as an integer number.
        self.handle = int(plugin_args[1])
        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        self.params = dict(parse_qsl(plugin_args[2][1:]))

        # Static data
        self.platform = ""
        self.session = requests.Session()

        # Initialise the token.
        self.region = (
            self.params["region"] if "region" in self.params else self._get_region()
        )
        self.token = (
            self.params["token"] if "token" in self.params else self._get_token()
        )
        self.user_status = (
            self.params["user_status"]
            if "user_status" in self.params
            else self._get_user_status()
        )
        self._set_setting()

    def _set_setting(self):
        data = self.make_get_request(VIU_SETTING_URL)
        area = data["server"]["area"]
        self.area_id = area.get("area_id", 5)
        self.language_flag_id = area["language"][0]["language_flag_id"]

    def _get_headers(self):
        headers = {
            "Origin": "https://www.viu.com/",
            "Accept": "*/*",
            "Referer": "https://www.viu.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
        }
        if hasattr(self, "token"):
            headers["Authorization"] = self.token

        return headers

    def _get_region(self):
        data = self.make_get_request("http://ip-api.com/json")
        LOG.info(data)
        return data.get("countryCode", "ph").lower()

    def _get_token(self):
        self.session.get(f"https://www.viu.com/ott/{self.region}")
        LOG.info(self.session.cookies)
        return "Bearer {}".format(self.session.cookies.get("token"))

    def _get_user_status(self):
        data = self.make_get_request(VIU_USER_STATUS_URL)
        LOG.info(data)
        user = data["user"]
        user_status = model.UserStatus(
            user["userId"],
            user["username"],
            user["userLevel"],
            data["plan"]["privileges"],
        )
        return user_status

    def list_collections(self, container_id, start_offset, container_name):
        xbmcplugin.setPluginCategory(self.handle, container_name)

        data = self.make_get_request(
            VIU_COLLECTION_URL.format(
                self.region,
                self.area_id,
                self.language_flag_id,
                container_id,
                settings.get_item_limit(),
                start_offset,
            )
        )
        series = data["data"]["series"]
        series_total = data["data"]["category_series_total"][0]

        for product in series:
            product_id = product.get("product_id")
            product_name = product["name"]
            product_desc = product.get("description")
            is_movie = product["is_movie"]

            if not product_id:
                continue

            if is_movie == 1:
                self.add_video_item(product_name, product)
            else:
                self.add_directory_item(
                    content_id=product_id,
                    title=product_name,
                    description=product_desc,
                    action="product",
                    parent_title=container_name,
                    item=product,
                )

        self.add_next_page_item(
            total=int(series_total.get("series_total", "1")),
            content_id=series_total["category_id"],
            start_offset=int(start_offset),
            original_title=container_name,
            action="collections",
        )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_products(self, category_id, title):
        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(self.handle, title)

        data = self.make_get_request(
            VIU_PRODUCT_URL.format(
                self.region, self.area_id, self.language_flag_id, category_id
            )
        )

        for product in data["data"]["series"]["product"]:
            self.add_video_item(
                data["data"]["series"]["name"], product, data["data"]["series"]["tag"]
            )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    # This uses HTML scraper since there's no available API to retrieved the categories
    def list_categories(self):
        xbmcplugin.setPluginCategory(self.handle, ADDON.getLocalizedString(33100))

        response = self.session.get(f"https://www.viu.com/ott/{self.region}/en-us")
        assert response.status_code == 200
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find("ul", class_="v-nav").find_all("li"):
            for cat in tag.find_all("a", href=True):
                self.add_directory_item(
                    title=cat.get_text(),
                    content_id=cat["data-id"],
                    description=cat.get_text(),
                    action="collections",
                )

        self.add_directory_item(
            title=f"[{ADDON.getLocalizedString(33101)}]",
            content_id="0",
            description=ADDON.getLocalizedString(33101),
            action="recommendations",
        )

        # Add Search item at the very top of the list
        self.add_directory_item(
            title=f"[{ADDON.getLocalizedString(33102)}]",
            content_id=1,
            description=ADDON.getLocalizedString(33102),
            action="search",
            position="top",
        )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_search(self):
        query = self.get_user_input()
        if not query:
            return []

        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(
            self.handle, f"{ADDON.getLocalizedString(33102)} / {query}"
        )

        body = {
            "keyword": [query],
            "url": VIU_SEARCH_API_URL.format(self.language_flag_id),
        }

        data = self.make_post_request(
            VIU_SEARCH_URL.format(self.region, self.area_id, self.language_flag_id),
            body=body,
        )

        series_list = data["data"].get("series")
        product_list = data["data"].get("product")

        if (
            not series_list
            and series_list is None
            and not product_list
            and product_list is None
        ):
            kodiutils.notification(
                ADDON.getLocalizedString(33000),
                ADDON.getLocalizedString(33001).format(query),
            )
            return

        if series_list and series_list is not None:
            for series in series_list:
                if series["category_name"] != "Preview":
                    self.add_directory_item(
                        content_id=series["product_id"],
                        title=series["name"],
                        description=series["name"],
                        action="product",
                        parent_title="Search/{}".format(query),
                        item=series,
                    )
                else:
                    self.add_video_item(series["name"], series)

        if product_list and product_list is not None:
            for product in product_list:
                self.add_video_item(product["series_name"], product)

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_recommendations(self):
        xbmcplugin.setPluginCategory(self.handle, ADDON.getLocalizedString(33101))

        data = self.make_get_request(
            VIU_RECOMMENDATION_URL.format(self.area_id, self.language_flag_id)
        )
        for grid in data["data"]["grid"]:
            LOG.info(grid)
            if grid is not None and grid["product"] is not None:
                self.add_directory_item(
                    title=grid["name"] or grid["description"],
                    content_id=grid["grid_id"],
                    description=grid["description"] or grid["name"],
                    action="recommended_collection",
                )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def list_recommended_collections(self, content_id, title):
        xbmcplugin.setPluginCategory(self.handle, title)

        data = self.make_get_request(
            VIU_RECOMMENDATION_URL.format(self.area_id, self.language_flag_id)
        )
        for grid in data["data"]["grid"]:
            if grid is not None and grid.get("grid_id", 0) == content_id:
                for product in grid.get("product"):
                    menu = None
                    if product["is_movie"] == 0:
                        url = self.get_url(
                            action="collections", content_id=product["series_id"]
                        )
                        LOG.info(url)
                        menu = [("Open", f"RunPlugin({url})")]

                    self.add_video_item(
                        name=product["series_name"],
                        video_info=product,
                        context_menu=menu,
                    )
                break

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def make_post_request(self, url, body):
        LOG.info("Making request: {}".format(url))
        response = self.session.post(
            url, headers=self._get_headers(), cookies=self.session.cookies, json=body
        )
        LOG.info(response.content)
        assert response.status_code == 200
        return response.json()

    def make_get_request(self, url):
        LOG.info("Making request: {}".format(url))
        response = self.session.get(
            url, headers=self._get_headers(), cookies=self.session.cookies
        )
        LOG.info(response.content)
        assert response.status_code == 200
        return response.json()

    def add_video_item(self, name, video_info, genres=None, context_menu=None):
        is_movie = video_info.get("is_movie", 0)
        sequence = video_info.get("number", video_info.get("product_number", ""))
        synopsis = video_info["synopsis"]
        user_level = video_info.get("user_level", 0)
        image = video_info.get("cover_image_url")
        content_id = video_info.get("product_id", video_info.get("id"))

        if is_movie == 1:
            title = name
        else:
            title = f"{sequence}. {name} - {synopsis}"

        if user_level == 2:
            title = f"[COLOR red][B]*[/B][/COLOR] {title}"

        list_item = xbmcgui.ListItem(label=title)

        all_genre = []
        if genres is not None:
            for genre in genres:
                all_genre.append(genre["name"])
        else:
            all_genre.append("All")

        list_item.setInfo(
            "video",
            {
                "title": title,
                "genre": ", ".join(all_genre),
                "plot": synopsis,
                "mediatype": "video",
            },
        )

        if image is not None:
            list_item.setArt({"thumb": image, "icon": image, "fanart": image})

        if context_menu is not None:
            list_item.addContextMenuItems(context_menu)

        if content_id is not None:
            list_item.setProperty("IsPlayable", "true")
            url = self.get_url(action="play", content_id=content_id)

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

    def add_directory_item(
        self,
        title,
        description,
        content_id,
        action,
        parent_title="",
        item=None,
        position=None,
        url_params={},
    ):
        list_item = xbmcgui.ListItem(label=title)

        if item:
            image = self.get_images(item)
            list_item.setArt({"thumb": image, "icon": image, "fanart": image})

        if position:
            list_item.setProperty("SpecialSort", position)

        list_item.setInfo(
            "video",
            {
                "count": content_id,
                "title": title,
                "genre": "All",
                "plot": description or title,
                "mediatype": "video",
            },
        )

        url = self.get_url(
            action=action,
            content_id=content_id,
            title="{}/{}".format(parent_title, title) if parent_title else title,
            **url_params,
        )

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

    def add_next_page_item(
        self, content_id, total, start_offset, original_title, action
    ):
        if start_offset + settings.get_item_limit() < total:
            title = "[B]Next Page >>[/B]"
            list_item = xbmcgui.ListItem(label=title)
            list_item.setInfo("video", {"mediatype": "video"})
            list_item.setProperty("SpecialSort", "bottom")

            url = self.get_url(
                action=action,
                content_id=content_id,
                start_offset=start_offset + settings.get_item_limit(),
                title=original_title,
            )

            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

    def get_url(self, **kwargs):
        """
        Create a URL for calling the plugin recursively from the given set of keyword arguments.

        :param kwargs: "argument=value" pairs
        :type kwargs: dict
        :return: plugin call URL
        :rtype: str
        """
        valid_kwargs = {
            key: self.safe_string(value)
            for key, value in kwargs.items()
            if value is not None
        }
        return "{0}?{1}".format(self.plugin_url, urlencode(valid_kwargs))

    def play_video(self, product_id):
        """
        Play a video by the provided path.
        """
        data = self.make_get_request(
            VIU_PRODUCT_URL.format(
                self.region, self.area_id, self.language_flag_id, product_id
            )
        )
        product = data["data"]["current_product"]
        series = data["data"]["series"]
        name = series["name"]
        number = int(product["number"])
        synopsis = product["synopsis"]

        if int(self.user_status.user_level) < product.get("user_level", "0"):
            kodiutils.notification(
                ADDON.getLocalizedString(33103),
                ADDON.getLocalizedString(33104),
            )
            return

        if product["is_movie"] == 1:
            title = name
        else:
            title = f"{name} - {number}. {synopsis}"

        subtitles = []
        for subtitle in product["subtitle"]:
            if settings.get_subtitle_lang() == subtitle["code"]:
                subtitles.append(subtitle["subtitle_url"])

        data = self.make_get_request(
            VIU_STREAM_URL.format(self.language_flag_id, product["ccs_product_id"])
        )

        stream_url = self.get_stream_url(data["data"]["stream"])

        if not stream_url:
            raise ValueError("Missing video URL for {}".format(product_id))

        LOG.info(
            "playing: {}, url: {}, subtitles: {}".format(title, stream_url, subtitles)
        )
        # Create a playable item with a path to play.
        play_item = xbmcgui.ListItem(label=title, path=stream_url)
        play_item.setInfo(
            "video",
            {
                "title": title,
                "plot": product["description"],
                "playcount": 1,
                "episode": int(product["number"]),
                "season": 1,
                "duration": int(product["time_duration"]),
            },
        )

        if subtitles:
            play_item.setSubtitles(subtitles)

        # Pass the item to the Kodi player.
        player = ViuPlayer(handle=self.handle, current_info=product, series_info=series)
        player.resolve(play_item)

        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and player.playing:
            if player.isPlayingVideo():
                player.video_totaltime = player.getTotalTime()
                player.video_lastpos = player.getTime()

            xbmc.sleep(1000)

    def router(self):
        """
        Main routing function which parses the plugin param string and handles it appropirately.
        """
        # Check the parameters passed to the plugin
        LOG.info("Handling route params -- {}".format(self.params))
        if self.params:
            action = self.params.get("action")
            content_id = self.params.get("content_id")
            title = self.params.get("title")

            if action == "product":
                self.list_products(content_id, title)
            elif action == "collections":
                start_offset = self.params.get("start_offset", 0)
                self.list_collections(content_id, start_offset, title)
            elif action == "play":
                self.play_video(content_id)
            elif action == "search":
                self.list_search()
            elif action == "recommendations":
                self.list_recommendations()
            elif action == "recommended_collection":
                self.list_recommended_collections(content_id, title)
            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError("Invalid action: {0}!".format(self.params))
        else:
            # List all the channels at the base level.
            self.list_categories()


def run():
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    ViuPlugin(sys.argv).router()
