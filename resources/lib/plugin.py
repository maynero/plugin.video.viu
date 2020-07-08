# -*- coding: utf-8 -*-
import logging
import xbmcaddon
from . import kodilogging
from . import kodiutils
from . import settings

import sys
import uuid

from urllib import urlencode
from urllib import quote
from urlparse import parse_qsl

from datetime import datetime

import xbmcgui
import xbmcplugin
import xbmc

import requests
import collections
import time

ADD_ON = xbmcaddon.Addon()
logger = logging.getLogger(ADD_ON.getAddonInfo('id'))
kodilogging.config(logger)

_category_t = collections.namedtuple('Category', ['id', 'title', 'item'])


class ViuPlugin(object):

    ITEMS_LIMIT = 25
    HOME_CATEGORIES = {
        'Tamil': map(lambda x: _category_t(x[0], x[1], None), (
            ('7_0_2_6_2', 'Premium Korean Shows'),
            ('playlist-25258826', 'Award-winning Films Bollywood Movies'),
            ('playlist-25722267', 'Kadhal Sadugudu'),
            ('playlist-25722268', 'Tentukottai'),
            ('16_0_2_6_2', 'Just Added'),
            ('15_0_2_6_2', 'You Might Also Like To Watch'),
            ('playlist-25705800', 'Veralevel Short Films'),
            ('9_0_2_6_2', 'Cricket Corner'),
            ('17_0_2_6_2', 'Best Romantic K Dramas'),
            ('20_0_2_6_2', 'Trending On Viu'),
            ('22_0_2_6_2', 'Tamil Originals'),
            ('97_0_2_1_2', 'Telugu Originals'),
            ('0_0_2_6_2', 'Spotlight')
        )),
        'Telugu': map(lambda x: _category_t(x[0], x[1], None), (
            ('120_0_2_1_2', u'Just Added Shows'),
            ('7_0_2_1_2', u'Spotlight'),
            ('97_0_2_1_2', u'Telugu Originals'),
            ('98_0_2_1_2', u'Popular TV Shows'),
            ('69_0_2_1_2', u'Top Picks For You'),
            ('playlist-23320605', u'Latest On Viu'),
            ('127_0_2_1_2', u'Best Romantic K Dramas'),
            ('123_0_2_1_2', u'Premium Korean Shows (Subtitles)'),
            ('playlist-25719023', u'Critically Acclaimed Movies'),
            ('playlist-24623179', u'Popular Movies For You'),
            ('96_0_2_1_2', u'Hindi Originals'),
            ('125_0_2_1_2', u'Tamil Originals'),
            ('playlist-24919061', u"Family Drama's"),
            ('playlist-24919065', u'Action & Adventures'),
            ('playlist-25723660', u'Horror-Comedies'),
            ('130_0_2_1_2', u'#Trending Music Videos')
        )),
        'Hindi': map(lambda x: _category_t(x[0], x[1], None), (
            ('2_0_2_2', u'Spotlight'),
            ('361_0_2_2', u'Just Added Shows'),
            ('351_0_2_2', u'VIU Originals'),
            ('362_0_2_2', u'Top Picks For You'),
            ('374_0_2_2', u'Best Romantic K Dramas'),
            ('372_0_2_2', u'Premium Korean Shows (Subtitles)'),
            ('playlist-23789616', u'South Action Movies'),
            ('playlist-22671542', u'Fresh On Viu'),
            ('playlist-23670893', u'Popular Movies For You'),
            ('364_0_2_2', u'Telugu VIU Originals'),
            ('playlist-22147346', u'Bollywood Sequels'),
            ('playlist-22253288', u'Dil Vil Pyaar Vyaar'),
            ('playlist-22147314', u'Movies That Will Make You Scream'),
            ('playlist-25258826', u'Award-winning Films'),
            ('playlist-21989604', u'The Versatile Akshay'),
            ('playlist-21992833', u'Salman Ka Swag'),
            ('playlist-22272906', u'Laughter Riot')
        ))
    }

    def __init__(self, plugin_args):
        # Get the plugin url in plugin:// notation.
        self.plugin_url = plugin_args[0]
        # Get the plugin handle as an integer number.
        self.handle = int(plugin_args[1])
        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        self.params = dict(parse_qsl(plugin_args[2][1:]))

        # Static data
        self.platform = ''
        self.session = requests.Session()

        # Initialise the token.
        self.token = self.params['token'] if 'token' in self.params else self._get_token()

    def _get_headers(self):
        headers = {
            "Origin": "https://www.viu.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.viu.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "x-client-auth": "b6fea2dd3d110b12fbd23d7ab8cd0ba3",
            "x-session-id": str(uuid.uuid4()),
            "x-request-id": str(uuid.uuid4()),
        }
        if hasattr(self, 'token'):
            headers["Authorization"] = self.token

        return headers

    def _get_token(self):
        post_body = {
            "configVersion": "1.0",
            "deviceId": str(uuid.uuid4()),
            "languageid": "en",
            "contentFlavour": "tamil",
            "contentCountry": "in"
        }
        data = self.make_post_request(
            'https://www.viu.com/ott/web/api/v3/workflow/web/auth?&fmt=json', post_body
        )
        logger.info("Got token from the server -- {}".format(data))
        return 'Bearer {}'.format(data['user']['jwtToken'])

    def list_container(self, container_id, start_offset, container_name):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, container_name)

        data = self.make_request(
            'https://www.viu.com/ott/web/api/container/load?id={container_id}&start={start}&limit={limit}&geofiltered=false&contentCountry=IN&languageid=en&ccode=IN&geo=2&fmt=json&ver=1.0&aver=5.0'.format(
                container_id=container_id,
                start=start_offset,
                limit=ViuPlugin.ITEMS_LIMIT,
            )
        )
        # {
        #     "response": {
        #         "container": {
        #             "containertype": "list",
        #             "createtime": 1546871031751,
        #             "total": 8,
        #             "item": [
        #                 {
        #                     "tcid_16x9": 1164839631,
        #                     "preferred_thumb": "withtitle",
        #                     "playlistItemsCount": 14,
        #                     "language": "Tamil",
        #                     "type": "playlist",
        #                     "title": "Nila Nila Odi Vaa",
        #                     "tcid_4x3": 1164839637,
        #                     "total": 14,
        #                     "tcid_2x3": 1164839641,
        #                     "tcid_4x3_t": 1164839633,
        #                     "tver": 3,
        #                     "id": "playlist-25705853",
        #                     "originals": true,
        #                     "tcid_2x1": 1164903442,
        #                     "slug": "nila_nila_odi_vaa",
        #                     "tcid_1x1": 1164839662,
        #                     "createtime": 1546886299500,
        #                     "contenttype": "tvshows",
        #                     "tcid_2x3_t": 1164839636,
        #                     "tcid_1x1.5": 1164839641,
        #                     "bgcolor": "#894040",
        #                     "spotlight_tcid_16x9": 1165116640,
        #                     "paid": false,
        #                     "updatetime": 1546886299500,
        #                     "tcid_16x9_t": 1164839635,
        #                     "tcid_38x13_d": 1165116639,
        #                     "tcid": 1164848288
        #                 },
        #             ],
        #             "start": 0,
        #             "id": "22_0_2_6_2",
        #             "title": "Tamil Originals",
        #             "updatetime": 1546871031751,
        #             "slug": "tamil_originals",
        #             "n": 8,
        #             "contenttype": "tvshows"
        #         },
        #         "ids": "",
        #         "status": "success"
        #     }
        # }
        for item in data['response']['container']['item']:
            if not item.get('id'):
                continue

            type = item['type']
            if type == 'clip':
                self.add_video_item(item)
            else:
                self.add_directory_item(
                    content_id=item['id'],
                    title=item['title'],
                    description=item.get('description'),
                    action='container',
                    parent_title=container_name,
                    item=item,
                )

        self.add_next_page_and_search_item(
            item=data['response']['container'],
            start_offset=int(start_offset),
            original_title=container_name,
            action='container'
        )

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    def list_collections(self, category_id, category_url):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'Collections')

        data = self.make_request('{}en/{}.json'.format(category_url, category_id))
        categories = map(
            lambda item: _category_t(item['id'], item['title'], item['item'][0] if item.get('item') else None),
            data['container'] if isinstance(data['container'], list) else [data['container']]
        )

        for category in categories:
            self.add_directory_item(
                title=category.title,
                content_id=category.id,
                description=category.title,
                action='container',
                parent_title=category_id,
                item=category.item,
            )

        self.add_search_item()

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    def list_categories(self, region):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'Categories')

        url = 'https://watch.viu.com/ott/web/api/v3/workflow/programming?ver=1.0&fmt=json&aver=5.0&appver=2.0&appid=viu_desktop&platform=web&configVersion=1.0&languageId=en&contentFlavour={}&countryCode=sa'.format(
            region.lower()
        )
        data = self.make_request(url)
        logger.info("Config json -- {}".format(data))
        category_url = data['categoryJson']

        data = self.make_request('{}en/categories.json'.format(category_url))
        categories = map(
            lambda item: _category_t(item['id'], item['title'], item['item'][0] if item.get('item') else None),
            data['categories']
        )

        for category in categories:
            self.add_directory_item(
                title=category.title,
                content_id=category.id,
                description=category.title,
                action='collections',
                parent_title=region,
                item=category.item,
                url_params=dict(category_url=category_url)
            )

        self.add_search_item()

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    def list_regions(self):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'Regions')

        # languages = ViuPlugin.HOME_CATEGORIES.iterkeys()
        languages = ['Indian', 'Arab', 'Pinoy']
        for category_id in languages:
            self.add_directory_item(
                title=category_id,
                content_id=category_id,
                description=category_id,
                action='categories',
            )

        self.add_search_item()

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    @staticmethod
    def get_user_input():
        kb = xbmc.Keyboard('', 'Search for Movies/TV Shows/Trailers/Videos')
        kb.doModal()  # Onscreen keyboard appears
        if not kb.isConfirmed():
            return

        # User input
        return kb.getText()

    def list_search(self):

        def _get_items_as_list(data, field):
            items = data.get(field)
            if not items:
                return []
            return [items] if isinstance(items, dict) else items

        query = ViuPlugin.get_user_input()
        if not query:
            return []

        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'Search/{}'.format(query))

        url = 'https://www.viu.com/ott/web/api/search/extsearch?keyword={query}&contentCountry=IN&languageid=en&ccode=IN&geo=2&ver=1.0&fmt=json&aver=5.0&appver=2.0&appid=viu_desktop&platform=desktop'.format(
            query=quote(query),
        )
        data = self.make_request(url)
        if not data['response'].get('container'):
            kodiutils.notification('No Search Results', 'No item found for {}'.format(query))
            return

        for container in _get_items_as_list(data['response'], 'container'):
            items = container.get('item')
            if not items:
                continue

            for item in _get_items_as_list(container, 'item'):
                if not item['id']:
                    continue

                if item['type'] == 'clip':
                    self.add_video_item(item)
                else:
                    self.add_directory_item(
                        content_id=item['id'],
                        title=item['title'],
                        description=item.get('description'),
                        action='container',
                        parent_title='Search/{}'.format(query),
                        item=item,
                    )

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def make_post_request(self, url, body):
        logger.info("Making request: {}".format(url))
        response = self.session.post(url, headers=self._get_headers(), cookies=self.session.cookies, json=body)
        assert response.status_code == 200
        return response.json()

    def make_request(self, url):
        logger.info("Making request: {}".format(url))
        response = self.session.get(url, headers=self._get_headers(), cookies=self.session.cookies)
        assert response.status_code == 200
        return response.json()

    @staticmethod
    def get_genre(item):
        """
        Returns a string of genre -- comma separated if multiple genres.
        Returns ALL as default.
        """
        if not item:
            return 'ALL'

        return item.get('genrename', item.get('contenttype', 'ALL'))

    @staticmethod
    def get_images(item):
        """
        Returns the image url.
        """
        if not item:
            return None

        random_tcid = next((value for key, value in item.iteritems() if 'tcid' in key), None)
        return 'https://vuclipi-a.akamaihd.net/p/tthumb640x480/d-1/{tcid}.jpg'.format(
            tcid=item.get('tcid', random_tcid)
        )

    def add_video_item(self, video):
        # {
        #     "videoviews": 0,
        #     "subtitle_en_srt": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/en.srt",
        #     "numshares": 0,
        #     "display_title": "Episode 1",
        #     "type": "clip",
        #     "cue_points": "480000,960000",
        #     "tur": "16:54",
        #     "genrename": "TV Shows",
        #     "allowedregions": "WW",
        #     "tdirforwhole": "vp63207_V20180723153318",
        #     "id": 1164843914,
        #     "href": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/vp63207_V20180723153318/hlsc_e2931.m3u8",
        #     "thumbnailBgColor": "#002060",
        #     "s3url": "http://premiumvideo.nc.vuclip.com/0802ee82fbd23fb659d4f1238f572398",
        #     "execution_date": "30-12-2017",
        #     "iconmaxidx": 101,
        #     "download_rights": "Yes",
        #     "slugLanguage": "Tamil",
        #     "videoviewsimpressions": 0,
        #     "tags": "Madras Mansion, Tamil Original, Viu Original, Tamil Comedy, Madras Mansion Ep 1, Mansion Introduction",
        #     "subgenre": 41,
        #     "device": "Desktop, Mobiles, Tabs, TV",
        #     "available_subtitle_languages": "en",
        #     "content_form": "short",
        #     "subgenrename": "Comedy",
        #     "musicdirector": "Athiappan Siva",
        #     "simultaneous": -1,
        #     "concurrentstreams": -1,
        #     "geo": "WW",
        #     "genre": 13,
        #     "jwmhlsfile": "hlsc_me2931.m3u8",
        #     "start_date": "30-12-2017",
        #     "number_of_devices": -1,
        #     "product": "All,VIU,VIULIFE",
        #     "year_of_release": 2018,
        #     "genderrelevance": "Both",
        #     "impressions": 0,
        #     "holdback": false,
        #     "actor": "Subramanian Subbu, Adithya Shivpink, Atul Raghunathan, Sharath Ravi, Gopal Krishnamoorthy",
        #     "allowedregionssearch": "IN,BH,KW,OM,QA,SA,AE,MY,SA",
        #     "moviealbumshowname": "Madras Mansion",
        #     "complete": true,
        #     "tcid_16x9": 1164854619,
        #     "subtitle_en_vtt": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/en.vtt",
        #     "episodeno": 1,
        #     "localisedgenrename": "TV Shows",
        #     "index_geo": "IN,BH,KW,OM,QA,SA,AE,MY,SA;",
        #     "language": "Tamil",
        #     "themetype": "default",
        #     "tver": 2,
        #     "vod_type": "AVOD,FVOD,SVOD,TVOD",
        #     "slug": "madras_mansion_ep_1",
        #     "drm": "inhouse",
        #     "actress": "Varshini Pakal",
        #     "numberofsearch": 0,
        #     "blockedregionssearch": "none",
        #     "isgeoblocked": false,
        #     "isAdsAllowed": true,
        #     "deal_type": "FF",
        #     "jwhlsfile": "hlsc_e2931.m3u8",
        #     "groupid": 1164843914,
        #     "download_expiry_duration": 0,
        #     "producer": "SuperTalkies",
        #     "prefixforwhole": "0802_",
        #     "hlsfile": "hlsc_whe2931.m3u8",
        #     "localisedlanguage": "Tamil",
        #     "urlpathd": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398",
        #     "profileforwhole": 7,
        #     "mood": "Funny",
        #     "description": "Excitement is created when an Actress enters the mansion and the residents all want a picture with her. This turns out to be ploy by the caretaker to ensure that the people who haven&#8217;t paid the rent to give their actual details.",
        #     "watcheddur": 0,
        #     "media": {
        #         "subtitles": {
        #             "subtitle": [
        #                 {
        #                     "format": "srt",
        #                     "language": "en",
        #                     "url": "https://gcpvuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/en_1543997558105.srt"
        #                 },
        #                 {
        #                     "format": "vtt",
        #                     "language": "en",
        #                     "url": "https://gcpvuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/en_1543997558105.vtt"
        #                 }
        #             ]
        #         },
        #         "videos": {
        #             "video": {
        #                 "codingFormat": {
        #                     "files": {
        #                         "file": [
        #                             {
        #                                 "type": "CK",
        #                                 "url": "https://gcpvuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/vp93207_V20180724024724/mpegdash_ck/vod_ck_V20190107151541.mpd"
        #                             },
        #                             {
        #                                 "type": "WV",
        #                                 "url": "https://gcpvuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/vp93207_V20180724024724/mpegdash_ck/vod_wv_V20190107151541.mpd"
        #                             }
        #                         ]
        #                     }
        #                 }
        #             }
        #         },
        #         "thumbnails": {
        #             "formulaCloudUrl": "https://vuclip-a.akamaihd.net/cloudinary/image/fetch/{parameters}/{source_image_url}",
        #             "formulaCdnUrl": "https://vuclip-a.akamaihd.net/p/tthumb{w}x{h}/v{v}/d-1/{tcid}.{ext}"
        #         }
        #     },
        #     "title": "Madras Mansion - Ep 1",
        #     "platform": "MobileWeb,OTT,DesktopWeb,ChromeCast",
        #     "availablesubs": "en",
        #     "duration": 1013,
        #     "deal_region": "India",
        #     "contentprovider": "AP International",
        #     "icondir": "80x60",
        #     "originals": true,
        #     "mpdckfile": "mpegdash_ck/vod_ck_V20190107151541.mpd",
        #     "categoryid": "tvshows",
        #     "numlikes": 0,
        #     "adultexplicitvisua": false,
        #     "contenttype": "tvshows",
        #     "aduleexplicitlyric": false,
        #     "args": "?c=1164843914&u=5571203139&s=BaCWb5&abrs",
        #     "cpchannel": "MADRAS MANSION",
        #     "urlpath": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398",
        #     "paid": false,
        #     "size_vp1": "21.1MB",
        #     "size_vp2": "28.0MB",
        #     "size_vp3": "34.2MB",
        #     "writer": "G Radhakrishnan",
        #     "tcid": 1164843914,
        #     "size_vp4": "55.1MB",
        #     "size_vp5": "83.2MB",
        #     "size_vp6": "188.1MB"
        # },

        # Create a list item with a text label and a thumbnail image.
        title = video['title']
        list_item = xbmcgui.ListItem(label=title)

        # Set additional info for the list item.
        # "execution_date": "30-12-2017",
        episode_date = video.get('execution_date')
        if episode_date:
            try:
                episode_date = datetime(*time.strptime(episode_date, "%d-%m-%Y")[0:6])
            except Exception as e:
                logger.warn('Failed to parse the episode date - {} -- {}'.format(episode_date, str(e)))
                episode_date = None
                pass

        list_item.setInfo('video', {
            'title': title,
            'genre': ViuPlugin.get_genre(video),
            'plot': video.get('description'),
            'duration': video.get('duration'),
            'year': episode_date.year if episode_date else None,
            'date': episode_date.strftime('%d.%m.%Y') if episode_date else None,
            'mediatype': 'video',
        })

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        image = ViuPlugin.get_images(video)
        list_item.setArt({
            'thumb': image,
            'icon': image,
            'fanart': image
        })

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=play&video=http:
        # //www.vidsplay.com/wp-content/uploads/2017/04/crab.mp4
        url = self.get_url(
            action='play',
            content_id=video['id'],
            # "href": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/vp63207_V20180723153318/hlsc_e2931.m3u8",
            video_url=video.get('href'),
            # "subtitle_en_srt": "https://vuclip-a.akamaihd.net/0802ee82fbd23fb659d4f1238f572398/en.srt",
            subtitle=video.get('subtitle_en_srt'),
        )

        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

    def add_directory_item(
            self,
            title,
            description,
            content_id,
            action,
            parent_title='',
            item=None,
            url_params={},
    ):
        # {
        #     "tcid_16x9": 1164839631,
        #     "preferred_thumb": "withtitle",
        #     "playlistItemsCount": 14,
        #     "language": "Tamil",
        #     "type": "playlist",
        #     "title": "Nila Nila Odi Vaa",
        #     "tcid_4x3": 1164839637,
        #     "total": 14,
        #     "tcid_2x3": 1164839641,
        #     "tcid_4x3_t": 1164839633,
        #     "tver": 3,
        #     "id": "playlist-25705853",
        #     "originals": true,
        #     "tcid_2x1": 1164903442,
        #     "slug": "nila_nila_odi_vaa",
        #     "tcid_1x1": 1164839662,
        #     "createtime": 1546886299500,
        #     "contenttype": "tvshows",
        #     "tcid_2x3_t": 1164839636,
        #     "tcid_1x1.5": 1164839641,
        #     "bgcolor": "#894040",
        #     "spotlight_tcid_16x9": 1165116640,
        #     "paid": false,
        #     "updatetime": 1546886299500,
        #     "tcid_16x9_t": 1164839635,
        #     "tcid_38x13_d": 1165116639,
        #     "tcid": 1164848288
        # },
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=title)

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        if item:
            image = ViuPlugin.get_images(item)
            list_item.setArt({
                'thumb': image,
                'icon': image,
                'fanart': image
            })

        # Set additional info for the list item.
        # Here we use a category name for both properties for for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {
            'count': content_id,
            'title': title,
            'genre': self.get_genre(item),
            'plot': description or title,
            'mediatype': 'video'
        })

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(
            action=action,
            content_id=content_id,
            title=u'{}/{}'.format(parent_title, title) if parent_title else title,
            **url_params
        )

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

    def add_next_page_and_search_item(self, item, start_offset, original_title, action):
        if start_offset + ViuPlugin.ITEMS_LIMIT < item.get('total', 0):
            title = '| Next Page >>>'
            list_item = xbmcgui.ListItem(label=title)
            list_item.setInfo('video', {
                'mediatype': 'video'
            })

            # Create a URL for a plugin recursive call.
            # Example: plugin://plugin.video.example/?action=listing&category=Animals
            url = self.get_url(
                action=action,
                content_id=item['id'],
                start_offset=start_offset + ViuPlugin.ITEMS_LIMIT,
                title=original_title
            )

            # is_folder = True means that this item opens a sub-list of lower level items.
            is_folder = True

            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

        # Add Search item.
        self.add_search_item()

    def add_search_item(self):
        self.add_directory_item(
            title='| Search', content_id=1, description='Search', action='search'
        )

    @staticmethod
    def safe_string(content):
        import unicodedata

        if not content:
            return content

        if isinstance(content, unicode):
            content = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore')

        return content

    def get_url(self, **kwargs):
        """
        Create a URL for calling the plugin recursively from the given set of keyword arguments.

        :param kwargs: "argument=value" pairs
        :type kwargs: dict
        :return: plugin call URL
        :rtype: str
        """
        valid_kwargs = {
            key: ViuPlugin.safe_string(value)
            for key, value in kwargs.iteritems()
            if value is not None
        }
        valid_kwargs['token'] = self.token
        return '{0}?{1}'.format(self.plugin_url, urlencode(valid_kwargs))

    def play_video(self, item_id, title, video_url, subtitle):
        """
        Play a video by the provided path.
        """
        if not video_url:
            raise ValueError('Missing video URL for {}'.format(item_id))

        logger.debug('Playing video: {}, subtitles: {}'.format(video_url, subtitle))
        # Create a playable item with a path to play.
        play_item = xbmcgui.ListItem(label=title, path=video_url)
        if subtitle:
            play_item.setSubtitles([subtitle])

        # Pass the item to the Kodi player.
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)

    def router(self):
        """
        Main routing function which parses the plugin param string and handles it appropirately.
        """
        # Check the parameters passed to the plugin
        logger.info('Handling route params -- {}'.format(self.params))
        if self.params:
            action = self.params.get('action')
            content_id = self.params.get('content_id')
            title = self.params.get('title')
            start_offset = self.params.get('start_offset', 0)

            if action == 'categories':
                self.list_categories(content_id)

            elif action == 'collections':
                self.list_collections(content_id, self.params['category_url'])

            elif action == 'container':
                self.list_container(content_id, start_offset, title)

            elif action == 'play':
                self.play_video(
                    content_id,
                    title,
                    self.params.get('video_url'),
                    self.params.get('subtitle')
                )

            elif action == 'search':
                self.list_search()

            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError('Invalid paramstring: {0}!'.format(self.params))

        else:
            # List all the channels at the base level.
            self.list_regions()


def run():
    # Initial stuffs.
    # kodiutils.cleanup_temp_dir()

    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    ViuPlugin(sys.argv).router()
