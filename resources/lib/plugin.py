# -*- coding: utf-8 -*-
from datetime import datetime
from urllib.parse import urlencode
from urllib.parse import parse_qsl
import sys
import logging
import uuid
import requests
import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
import resources.lib.common as common
from resources.lib.player import ViuPlayer
from resources.lib import model, kodiutils, settings

LOG = logging.getLogger(__name__)


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

        return {
            "poster": item.get("series_image_url") or item.get("cover_image_url"),
            "fanart": item.get("product_image_url"),
        }

    @staticmethod
    def get_user_input():
        kb = xbmc.Keyboard("", "Search")
        kb.doModal()
        if not kb.isConfirmed():
            return False

        # User input
        return kb.getText()

    @staticmethod
    def get_stream_url(stream):
        LOG.info("available streams: %s", stream)
        parse_stream = stream.get("url4", stream.get("url3", stream.get("url2", stream.get("url"))))
        resolution_key = settings.get_resolution()

        if parse_stream is not None:
            return parse_stream.get(resolution_key, parse_stream.get(list(parse_stream.keys())[-1]))

        return ""

    @staticmethod
    def get_next_episode(cur_ep_num, series):
        # Viu episode numbering is just sequential numbers, adding one to the current number should provide accurate next episode
        next_ep_num = cur_ep_num + 1

        return next(
            filter(
                lambda product: (int(product.get("number")) == next_ep_num),
                series.get("product"),
            ),
            None,
        )

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
        self.site_setting = (
            self.params["site_setting"]
            if "site_setting" in self.params
            else self._get_site_setting()
        )
        self.token = (
            self.params["token"] if "token" in self.params else self._get_token()
        )
        self.user_status = (
            self.params["user_status"]
            if "user_status" in self.params
            else self._get_user_status()
        )

    def _get_site_setting(self):
        data = self.make_get_request(common.VIU_SETTING_URL)
        area = data.get("server").get("area")

        site_setting = model.SiteSetting(
            area_id=area.get("area_id", 5),
            language_flag_id=area.get("language")[0].get("language_flag_id"),
            language=area.get("language")[0].get("mark"),
        )
        return site_setting

    def _get_headers(self):
        headers = {
            "Origin": "https://www.viu.com/",
            "Referer": "https://www.viu.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Content-Type": "application/json",
            "Upgrade-Insecure-Requests": "1",
        }
        if hasattr(self, "token"):
            headers["Authorization"] = self.token

        return headers

    def _get_region(self):
        data = self.make_get_request("http://ip-api.com/json")
        LOG.info("_get_region: %s", data)
        return data.get("countryCode", "ph").lower()

    def _get_token(self):
        body = {
            "countryCode": self._get_region().upper(),
            "deviceId": str(uuid.uuid4()),
            "platform": "browser",
            "platformFlagLabel": "web",
            "language": self.site_setting.language,
            "carrierId": "0",
        }

        data = self.make_post_request(
            common.VIU_TOKEN_URL,
            body=body,
        )

        LOG.info("_get_token: %s", data)
        return f"Bearer {data.get('token')}"

    def _get_user_status(self):
        if (
            settings.is_account_login_enabled()
            and settings.get_username() is not None
            and settings.get_password() is not None
        ):
            body = {
                "email": settings.get_username(),
                "password": settings.get_password(),
                "provider": "email",
            }
            data = self.make_post_request(url=common.VIU_LOGIN_URL, body=body)
            LOG.info("_get_user_status, auth: %s", data)

            if data["status"] == 0:
                error_message = data.get("error").get("message")
                LOG.info("_get_user_status: %s", error_message)
                kodiutils.notification("Unable to login", message=error_message)
            else:
                self.token = f"Bearer {data.get('token')}"

        data = self.make_get_request(common.VIU_USER_STATUS_URL)
        LOG.info("_get_user_status: %s", data)
        user = data.get("user")
        user_status = model.UserStatus(
            user.get("userId"), user.get("username"), user.get("userLevel")
        )
        return user_status

    def list_collections(self, container_id, start_offset, container_name):
        xbmcplugin.setPluginCategory(self.handle, container_name)

        data = self.make_get_request(
            common.VIU_COLLECTION_URL.format(
                self.region,
                self.site_setting.area_id,
                self.site_setting.language_flag_id,
                container_id,
                settings.get_item_limit(),
                start_offset,
            )
        )
        series = data.get("data").get("series")
        series_total = data.get("data").get("category_series_total")[0]

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
            content_id=series_total.get("category_id"),
            start_offset=int(start_offset),
            original_title=container_name,
            action="collections",
        )

        # Add Search item at the very top of the list
        self.add_search_item()
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_products(self, category_id, title):
        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(self.handle, title)

        data = self.make_get_request(
            common.VIU_PRODUCT_URL.format(
                self.region,
                self.site_setting.area_id,
                self.site_setting.language_flag_id,
                category_id,
            )
        )

        for product in data.get("data").get("series").get("product"):
            self.add_video_item(
                data.get("data").get("series").get("name"),
                product,
                data.get("data").get("series").get("tag"),
            )

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    # This uses HTML scraper since there's no available API to retrieved the categories
    def list_categories(self):
        xbmcplugin.setPluginCategory(
            self.handle, common.ADDON.getLocalizedString(33100)
        )

        response = self.session.get(f"https://www.viu.com/ott/{self.region}/en-us")
        assert response.status_code == 200
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find("ul", class_="MuiBox-root").find_all("li"):
            for cat in tag.find_all("a", href=True):
                category_id = "".join(list(filter(str.isdigit, cat["href"])))

                self.add_directory_item(
                    title=cat["title"],
                    content_id=category_id,
                    description=cat.get_text(),
                    action="collections",
                )

        self.add_directory_item(
            title=f"[{common.ADDON.getLocalizedString(33101)}]",
            content_id="0",
            description=common.ADDON.getLocalizedString(33101),
            action="recommendations",
        )

        # Add Search item at the very top of the list
        self.add_search_item()
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_search(self):
        query = self.get_user_input()
        if not query:
            return []

        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(
            self.handle, f"{common.ADDON.getLocalizedString(33102)} / {query}"
        )

        body = {
            "keyword": [query],
            "url": common.VIU_SEARCH_API_URL.format(self.site_setting.language_flag_id),
        }

        data = self.make_post_request(
            common.VIU_SEARCH_URL.format(
                self.region,
                self.site_setting.area_id,
                self.site_setting.language_flag_id,
            ),
            body=body,
        )

        series_list = data.get("data").get("series")
        product_list = data.get("data").get("product")

        if (
            not series_list
            and series_list is None
            and not product_list
            and product_list is None
        ):
            kodiutils.notification(
                common.ADDON.getLocalizedString(33000),
                common.ADDON.getLocalizedString(33001).format(query),
            )
            return []

        if series_list and series_list is not None:
            for series in series_list:
                if series.get("category_name") != "Preview":
                    self.add_directory_item(
                        content_id=series.get("product_id"),
                        title=series.get("name"),
                        description=series.get("name"),
                        action="product",
                        parent_title=f"Search/{query}",
                        item=series,
                    )
                else:
                    self.add_video_item(series.get("name"), series)

        if product_list and product_list is not None:
            for product in product_list:
                self.add_video_item(product.get("series_name"), product)

        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)
        return []

    def list_recommendations(self):
        xbmcplugin.setPluginCategory(
            self.handle, common.ADDON.getLocalizedString(33101)
        )

        data = self.make_get_request(
            common.VIU_RECOMMENDATION_URL.format(
                self.site_setting.area_id, self.site_setting.language_flag_id
            )
        )
        for grid in data.get("data").get("grid"):
            LOG.info("viu homepage grid: %s", grid)
            if grid is not None and grid.get("product") is not None:
                self.add_directory_item(
                    title=grid.get("name") or grid.get("description"),
                    content_id=grid.get("grid_id"),
                    description=grid.get("description") or grid.get("name"),
                    action="recommended_collection",
                )

        # Add Search item at the very top of the list
        self.add_search_item()
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)

    def list_recommended_collections(self, content_id, title):
        xbmcplugin.setPluginCategory(self.handle, title)

        data = self.make_get_request(
            common.VIU_RECOMMENDATION_URL.format(
                self.site_setting.area_id, self.site_setting.language_flag_id
            )
        )
        for grid in data.get("data").get("grid"):
            if grid is not None and grid.get("grid_id", 0) == content_id:
                for product in grid.get("product"):
                    self.add_video_item(name=product.get("series_name"), video_info=product)
                break

        # Add Search item at the very top of the list
        self.add_search_item()
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def make_post_request(self, url, body):
        LOG.info("make_post_request: %s", url)
        response = self.session.post(
            url=url,
            headers=self._get_headers(),
            cookies=self.session.cookies,
            json=body,
        )
        assert response.status_code == 200
        return response.json()

    def make_get_request(self, url):
        LOG.info("make_get_request: %s", url)
        response = self.session.get(
            url=url, headers=self._get_headers(), cookies=self.session.cookies
        )
        assert response.status_code == 200
        return response.json()

    def add_video_item(self, name, video_info, genres=None, context_menu=None):
        is_movie = video_info.get("is_movie", 0)
        sequence = video_info.get("number", video_info.get("product_number", ""))
        synopsis = video_info["synopsis"]
        user_level = video_info.get("user_level", 0)
        image = video_info.get("cover_image_url")
        content_id = video_info.get("product_id", video_info.get("id"))
        product_start_time = video_info.get(
            "schedule_start_time", video_info.get("product_schedule_start_time")
        )
        start_time = datetime.now()

        if product_start_time is not None:
            start_time = datetime.fromtimestamp(int(product_start_time))

        if is_movie == 1:
            title = name
        else:
            title = f"{sequence}. {name} - {synopsis}"

        # Tag items that are not release yet
        if start_time > datetime.now():
            title = f"{title} [COLOR red][B](Available at {start_time.strftime('%b %d %Y %H:%M %p')})[/B][/COLOR]"

        if user_level == 2:
            title = f"{title} [COLOR red][B]*[/B][/COLOR]"

        list_item = xbmcgui.ListItem(label=title)

        all_genre = []
        if genres is not None:
            for genre in genres:
                all_genre.append(genre.get("name"))
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
            if start_time <= datetime.now():
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
    ):
        list_item = xbmcgui.ListItem(label=title)

        if item:
            image = self.get_images(item)
            list_item.setArt(
                {
                    "thumb": image["poster"],
                    "icon": image["poster"],
                    "fanart": image["fanart"],
                }
            )

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
            title=f"{parent_title}/{title}" if parent_title else title,
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

    def add_search_item(self):
        # Add Search item at the very top of the list
        self.add_directory_item(
            title=f"[{common.ADDON.getLocalizedString(33102)}]",
            content_id=1,
            description=common.ADDON.getLocalizedString(33102),
            action="search",
            position="top",
        )

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
        return f"{self.plugin_url}?{urlencode(valid_kwargs)}"

    def play_video(self, product_id):
        """
        Play a video by the provided path.
        """
        data = self.make_get_request(
            common.VIU_PRODUCT_URL.format(
                self.region,
                self.site_setting.area_id,
                self.site_setting.language_flag_id,
                product_id,
            )
        )
        LOG.info("play_video: %s", data)

        product = data.get("data").get("current_product")
        series = data.get("data").get("series")
        series_name = series.get("name")
        episode_number = int(product.get("number"))
        synopsis = product.get("synopsis")
        description = product.get("description")
        duration = int(product.get("time_duration"), 0)
        is_movie = product.get("is_movie", False)
        ccs_product_id = product.get("ccs_product_id")
        title = (
            series_name
            if is_movie == 1
            else f"{episode_number}. {series_name} - {synopsis}"
        )

        if int(self.user_status.user_level) < int(product.get("user_level", "0")):
            LOG.info("video is for user with level of %s", product["user_level"])
            kodiutils.notification(
                common.ADDON.getLocalizedString(33103),
                common.ADDON.getLocalizedString(33104),
            )
            return

        subtitles = []
        preferred_subtitle = None
        for subtitle in product.get("subtitle"):
            if subtitle.get("code") == settings.get_subtitle_lang():
                preferred_subtitle = subtitle.get("subtitle_url").split("/")[-1]
            subtitles.append(subtitle.get("subtitle_url"))

        data = self.make_get_request(
            common.VIU_STREAM_URL.format(
                self.site_setting.language_flag_id, ccs_product_id
            )
        )
        stream_url = self.get_stream_url(data["data"]["stream"])

        if not stream_url:
            raise ValueError(f"Missing video URL for {product_id}")

        LOG.info("playing: %s, url: %s", title, stream_url)

        # Create a playable item with a path to play.
        play_item = xbmcgui.ListItem(label=title, path=stream_url)
        play_item.setInfo(
            "video",
            {
                "title": title,
                "plot": description,
                "playcount": 1,
                "episode": episode_number,
                "season": 1,
                "duration": duration,
                "mediatype": "movie" if is_movie == 1 else "episode",
            },
        )

        if subtitles:
            play_item.setSubtitles(subtitles)

        # Pass the item to the Kodi player.
        player = ViuPlayer(self.handle)
        player.resolve(play_item)

        if not player.waitForPlayBack(url=stream_url):
            xbmcplugin.endOfDirectory(self.handle)
            return

        if preferred_subtitle is not None:
            for i, subtitle_stream in enumerate(player.getAvailableSubtitleStreams()):
                if preferred_subtitle in subtitle_stream:
                    player.setSubtitleStream(i)
                    break

        # Send up next signal
        if xbmc.getCondVisibility('System.HasAddon(service.upnext)') == 0:
            kodiutils.notification(common.ADDON.getLocalizedString(33105), common.ADDON.getLocalizedString(33106))
            return

        next_product = self.get_next_episode(episode_number, series)
        LOG.info("next episode: %s", next_product)

        if (
            not settings.is_upnext_enabled()
            or next_product is None
            or datetime.fromtimestamp(int(next_product["schedule_start_time"]))
            > datetime.now()
        ):
            return

        next_info = {
            "current_episode": {
                "episodeid": product.get("product_id"),
                "tvshowid": product.get("product_id"),
                "title": title,
                "art": {"thumb": product.get("cover_image_url")},
                "season": 1,
                "episode": episode_number,
                "showtitle": title,
                "plot": description,
                "playcount": 1,
                "rating": None,
                "firstaired": None,
                "runtime": duration,
            },
            "next_episode": {
                "episodeid": next_product.get("product_id"),
                "tvshowid": next_product.get("product_id"),
                "title": next_product.get("synopsis"),
                "art": {"thumb": next_product.get("cover_image_url")},
                "season": 1,
                "episode": next_product.get("number"),
                "showtitle": next_product.get("synopsis"),
                "plot": next_product.get("synopsis"),
                "playcount": 0,
                "rating": None,
                "firstaired": None,
                "runtime": None,
            },
            "play_url": self.get_url(
                action="play", content_id=next_product.get("product_id")
            )
        }

        kodiutils.upnext_signal(
            sender=common.ADDON_ID,
            next_info=next_info,
        )

    def router(self):
        """
        Main routing function which parses the plugin param string and handles it appropirately.
        """
        # Check the parameters passed to the plugin
        LOG.info("handling route params -- %s", self.params)
        if self.params:
            action = self.params.get("action")
            content_id = self.params.get("content_id")
            title = self.params.get("title")

            if action == "product":
                self.list_products(content_id, title)
            elif action == "collections":
                start_offset = self.params.get("start_offset", 0)
                self.list_collections(content_id, start_offset, title)
            elif action == "recommendations":
                self.list_recommendations()
            elif action == "recommended_collection":
                self.list_recommended_collections(content_id, title)
            elif action == "search":
                self.list_search()
            elif action == "play":
                self.play_video(content_id)
            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError(f"Invalid action: {self.params}!")
        else:
            # List all the channels at the base level.
            self.list_categories()


def run():
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    ViuPlugin(sys.argv).router()
