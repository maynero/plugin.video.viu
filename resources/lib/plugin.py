# -*- coding: utf-8 -*-
import logging
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import sys
import requests

from resources.lib import logger
from resources.lib import kodiutils
from resources.lib import settings
from urllib.parse import urlencode
from urllib.parse import parse_qsl
from bs4 import BeautifulSoup

ADDON = xbmcaddon.Addon()
LOG = logging.getLogger(ADDON.getAddonInfo("id"))
logger.config(LOG)


class ViuPlugin(object):
    ITEMS_LIMIT = 15

    VIU_COLLECTION_URL = "https://www.viu.com/ott/{}/index.php?r=category/series-category&platform_flag_label=web&area_id={}&language_flag_id={}&cpreference_id=&category_id={}&length={}&offset={}"
    VIU_ITEM_URL = "https://www.viu.com/ott/{}/index.php?area_id={}&language_flag_id={}&r=vod/ajax-detail&platform_flag_label=web&product_id={}&ut=0"
    VIU_SEARCH_URL = "https://www.viu.com/ott/{}/index.php?r=vod/jsonp&area_id={}&language_flag_id={}&cpreference_id="
    VIU_STREAM_URL = "https://api-gateway-global.viu.com/api/playback/distribute?cpreference_id=&language_flag_id={}&ccs_product_id={}"
    VIU_SETTING_URL = "https://api-gateway-global.viu.com/api/mobile?r=/setting/query2&platform_flag_label=web"
    VIU_SEARCH_API_URL = "https://api-gateway-global.viu.com/api/mobile?r=/search/video&language_flag_id={}&cpreference_id=&platform_flag_label=web"

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

        return item["series_image_url"]

    @staticmethod
    def get_user_input():
        kb = xbmc.Keyboard("", "Search")
        kb.doModal()  # Onscreen keyboard appears
        if not kb.isConfirmed():
            return

        # User input
        return kb.getText()

    @staticmethod
    def get_stream_url(stream):
        for url_key in ["url4", "url3", "url2", "url"]:
            if url_key in stream:
                resolution_key = settings.getResolution()
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
        self.token = (
            self.params["token"] if "token" in self.params else self._getToken()
        )
        self._setSetting()
        self._setRegion()

    def _setSetting(self):
        data = self.makeGetRequest(self.VIU_SETTING_URL)
        self.area_id = data["server"]["area"]["area_id"]
        self.language_flag_id = data["server"]["area"]["language"][0][
            "language_flag_id"
        ]

    def _getHeaders(self):
        headers = {
            "Origin": "https://www.viu.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.viu.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
        }
        if hasattr(self, "token"):
            headers["Authorization"] = self.token

        return headers

    def _getToken(self):
        self.session.get("https://www.viu.com/ott/ph")
        return "Bearer {}".format(self.session.cookies["token"])

    def _setRegion(self):
        response = self.session.get("http://ip-api.com/json")
        assert response.status_code == 200
        LOG.debug(response.json())
        self.region = response.json()["countryCode"].lower()

    def listCollections(self, container_id, start_offset, container_name):
        xbmcplugin.setPluginCategory(self.handle, container_name)

        data = self.makeGetRequest(
            self.VIU_COLLECTION_URL.format(
                self.region,
                self.area_id,
                self.language_flag_id,
                container_id,
                self.ITEMS_LIMIT,
                start_offset,
            )
        )

        for product in data["data"]["series"]:
            if not product.get("product_id"):
                continue

            if product["is_movie"] == 1:
                self.addVideoItem(product["name"], product)
            else:
                self.addDirectoryItem(
                    content_id=product["product_id"],
                    title=product["name"],
                    description=product.get("description"),
                    action="product",
                    parent_title=container_name,
                    item=product,
                )

        self.addNextPageItem(
            item=data["data"],
            start_offset=int(start_offset),
            original_title=container_name,
            action="collections",
        )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def listProducts(self, category_id, title):
        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(self.handle, title)

        data = self.makeGetRequest(
            self.VIU_ITEM_URL.format(
                self.region, self.area_id, self.language_flag_id, category_id
            )
        )

        for product in data["data"]["series"]["product"]:
            self.addVideoItem(
                data["data"]["series"]["name"], product, data["data"]["series"]["tag"]
            )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def listCategories(self):
        xbmcplugin.setPluginCategory(self.handle, "Categories")

        response = self.session.get("https://www.viu.com/ott/ph/en-us")
        assert response.status_code == 200
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find("ul", class_="v-nav").find_all("li"):
            for cat in tag.find_all("a", href=True):
                self.addDirectoryItem(
                    title=cat.get_text(),
                    content_id=cat["data-id"],
                    description=cat.get_text(),
                    action="collections",
                )

        self.addSearchItem()
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def listSearch(self):
        query = ViuPlugin.get_user_input()
        if not query:
            return []

        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(self.handle, "Search / {}".format(query))

        body = {
            "keyword": [query],
            "url": self.VIU_SEARCH_API_URL.format(self.language_flag_id),
        }

        data = self.makePostRequest(
            self.VIU_SEARCH_URL.format(
                self.region, self.area_id, self.language_flag_id
            ),
            body=body,
        )
        if not data["data"].get("series") or not data["data"].get("product"):
            kodiutils.notification(
                "No Search Results", "No item found for {}".format(query)
            )
            return

        for series in data["data"]["series"]:
            if series["category_name"] != "Preview":
                self.addDirectoryItem(
                    content_id=series["series_id"],
                    title=series["name"],
                    description=series["name"],
                    action="product",
                    parent_title="Search/{}".format(query),
                    item=series,
                )
            else:
                self.addVideoItem(series["name"], series)

        for product in data["data"]["product"]:
            self.addVideoItem(product["series_name"], product)

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def makePostRequest(self, url, body):
        LOG.info("Making request: {}".format(url))
        response = self.session.post(
            url, headers=self._getHeaders(), cookies=self.session.cookies, json=body
        )
        LOG.debug(response.content)
        assert response.status_code == 200
        return response.json()

    def makeGetRequest(self, url):
        LOG.info("Making request: {}".format(url))
        response = self.session.get(
            url, headers=self._getHeaders(), cookies=self.session.cookies
        )
        LOG.debug(response.content)
        assert response.status_code == 200
        return response.json()

    def addVideoItem(self, name, video, video_genre=None):
        # Create a list item with a text label and a thumbnail image.

        if video.get("is_movie", 0) == 1:
            title = name
        else:
            title = "{}. {} - {}".format(
                video.get("number", video.get("product_number", "")),
                name,
                video["synopsis"],
            )

        if video.get("user_level", 0) == 2:
            title = title + " [COLOR red][B]PREMIUM[/B][/COLOR]"

        list_item = xbmcgui.ListItem(label=title)

        all_genre = []
        if video_genre is not None:
            for genre in video_genre:
                all_genre.append(genre["name"])
        else:
            all_genre.append("All")

        list_item.setInfo(
            "video",
            {
                "title": title,
                "genre": ", ".join(all_genre),
                "plot": video["synopsis"],
                "mediatype": "video",
            },
        )

        image = video["cover_image_url"]
        list_item.setArt({"thumb": image, "icon": image, "fanart": image})
        list_item.setProperty("IsPlayable", "true")
        url = self.getUrl(action="play", content_id=video["product_id"])
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

    def addDirectoryItem(
        self,
        title,
        description,
        content_id,
        action,
        parent_title="",
        item=None,
        url_params={},
    ):
        list_item = xbmcgui.ListItem(label=title)

        if item:
            image = ViuPlugin.get_images(item)
            list_item.setArt({"thumb": image, "icon": image, "fanart": image})

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

        url = self.getUrl(
            action=action,
            content_id=content_id,
            title="{}/{}".format(parent_title, title) if parent_title else title,
            **url_params
        )

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

    def addNextPageItem(self, item, start_offset, original_title, action):
        if start_offset + ViuPlugin.ITEMS_LIMIT < int(
            item["category_series_total"][0].get("series_total")
        ):
            title = "[B]Next Page >>[/B]"
            list_item = xbmcgui.ListItem(label=title)
            list_item.setInfo("video", {"mediatype": "video"})

            url = self.getUrl(
                action=action,
                content_id=item["category_series_total"][0]["category_id"],
                start_offset=start_offset + ViuPlugin.ITEMS_LIMIT,
                title=original_title,
            )
            LOG.info(url)

            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

    def addSearchItem(self):
        self.addDirectoryItem(
            title="[Search]", content_id=1, description="Search", action="search"
        )

    def getUrl(self, **kwargs):
        """
        Create a URL for calling the plugin recursively from the given set of keyword arguments.

        :param kwargs: "argument=value" pairs
        :type kwargs: dict
        :return: plugin call URL
        :rtype: str
        """
        valid_kwargs = {
            key: ViuPlugin.safe_string(value)
            for key, value in kwargs.items()
            if value is not None
        }
        return "{0}?{1}".format(self.plugin_url, urlencode(valid_kwargs))

    def playVideo(self, item_id):
        """
        Play a video by the provided path.
        """
        data = self.makeGetRequest(
            self.VIU_ITEM_URL.format(
                self.region, self.area_id, self.language_flag_id, item_id
            )
        )
        title = "{} - {}".format(
            data["data"]["series"]["name"], data["data"]["current_product"]["synopsis"]
        )
        ccs_product_id = data["data"]["current_product"]["ccs_product_id"]
        description = data["data"]["current_product"]["description"]

        subtitles = []
        for item in data["data"]["current_product"]["subtitle"]:
            if settings.getSubtitleLang() == item["code"]:
                subtitles.append(item["subtitle_url"])

        data = self.makeGetRequest(
            self.VIU_STREAM_URL.format(self.language_flag_id, ccs_product_id)
        )

        stream_url = ViuPlugin.get_stream_url(data["data"]["stream"])

        if not stream_url:
            raise ValueError("Missing video URL for {}".format(item_id))

        LOG.info(
            "playing: {}, url: {}, subtitles: {}".format(title, stream_url, subtitles)
        )
        # Create a playable item with a path to play.
        play_item = xbmcgui.ListItem(label=title, path=stream_url)
        play_item.setInfo(
            "video", {"title": title, "plot": description, "playcount": 1}
        )

        if subtitles:
            play_item.setSubtitles(subtitles)

        # Pass the item to the Kodi player.
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)

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
            start_offset = self.params.get("start_offset", 0)

            if action == "product":
                self.listProducts(content_id, title)
            elif action == "collections":
                self.listCollections(content_id, start_offset, title)
            elif action == "play":
                self.playVideo(content_id)
            elif action == "search":
                self.listSearch()
            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError("Invalid paramstring: {0}!".format(self.params))
        else:
            # List all the channels at the base level.
            self.listCategories()


def run():
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    ViuPlugin(sys.argv).router()
