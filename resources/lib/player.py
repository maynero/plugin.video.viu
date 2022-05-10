import sys
import xbmc
import xbmcplugin
from resources.lib.kodilogging import ADDON_ID, LOG
from resources.lib import kodiutils


class ViuPlayer(xbmc.Player):
    def __init__(self, handle, current_info, series_info):
        self.handle = handle
        self.video_id = None
        self.video_lastpos = 0
        self.video_totaltime = 0
        self.playing = False
        self.paused = False
        self.series_info = series_info
        self.current_info = current_info
        self.number = int(self.current_info["number"])
        self.title = f"{self.series_info['name']} - {self.number}. {self.current_info['synopsis']}"

    def resolve(self, li):
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=li)
        LOG.info("[ViuPlayer] Event resolve")
        self.playing = True

    def onPlayBackStarted(self):  # pylint: disable=invalid-name
        """Called when user starts playing a file"""
        LOG.info("[ViuPlayer] Event onPlayBackStarted")
        self.onAVStarted()

    def onAVStarted(self):  # pylint: disable=invalid-name
        """Called when Kodi has a video or audiostream"""
        LOG.info("[ViuPlayer] Event onAVStarted")
        self.push_upnext()

    def onPlayBackSeek(self, time, seekOffset):  # pylint: disable=invalid-name
        """Called when user seeks to a time"""
        LOG.info(
            "[ViuPlayer] Event onPlayBackSeek time="
            + str(time)
            + " offset="
            + str(seekOffset)
        )
        self.video_lastpos = time // 1000

        # If we seek beyond the end, exit Player
        if self.video_lastpos >= self.video_totaltime:
            self.stop()

    def onPlayBackPaused(self):  # pylint: disable=invalid-name
        """Called when user pauses a playing file"""
        LOG.info("[ViuPlayer] Event onPlayBackPaused")
        self.paused = True

    def onPlayBackEnded(self):  # pylint: disable=invalid-name
        """Called when Kodi has ended playing a file"""
        LOG.info("[ViuPlayer] Event onPlayBackEnded")
        self.playing = False
        # Up Next calls onPlayBackEnded before onPlayBackStarted if user doesn't select Watch Now
        # Reset current video id
        self.video_id = None

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        """Called when user stops Kodi playing a file"""
        LOG.info("[ViuPlayer] Event onPlayBackStopped")
        self.playing = False
        # Reset current video id
        self.video_id = None

    def onPlayerExit(self):  # pylint: disable=invalid-name
        """Called when player exits"""
        LOG.info("[ViuPlayer] Event onPlayerExit")
        self.playing = False

    def onPlayBackResumed(self):  # pylint: disable=invalid-name
        """Called when user resumes a paused file or a next playlist item is started"""
        if self.paused:
            suffix = "after pausing"
            self.paused = False
        # playlist change
        # Up Next uses this when user clicks Watch Now, only happens if user is watching first episode in row after
        # that onPlayBackEnded is used even if user clicks Watch Now
        else:
            suffix = "after playlist change"
            self.paused = False
            # Reset current video id
            self.video_id = None
        log = "[ViuPlayer] Event onPlayBackResumed " + suffix
        LOG.info(log)

    def push_upnext(self):
        next_product = self.get_next_episode(self.number)
        LOG.info(next_product)

        if next_product is not None:
            next_info = dict(
                current_episode=dict(
                    episodeid=self.current_info["product_id"],
                    tvshowid=self.current_info["series_id"],
                    title=self.title,
                    art={"thumb": self.current_info["cover_image_url"]},
                    season=None,
                    episode=str(self.current_info),
                    showtitle=self.title,
                    plot=self.current_info["description"],
                    playcount=1,
                    rating=None,
                    firstaired=None,
                    runtime=int(self.current_info["time_duration"]),
                ),
                next_episode=dict(
                    episodeid=next_product["product_id"],
                    tvshowid=self.current_info["series_id"],
                    title=next_product["synopsis"],
                    art={"thumb": next_product["cover_image_url"]},
                    season=None,
                    episode=self.number,
                    showtitle=next_product["synopsis"],
                    plot=next_product["synopsis"],
                    playcount=0,
                    rating=None,
                    firstaired=None,
                    runtime=int(self.current_info["time_duration"]),
                ),
                play_url=f"{ADDON_ID}/action=play&content_id={next_product['product_id']}",
                notification_time=10,
            )

            kodiutils.upnext_signal(
                sender=ADDON_ID,
                next_info=next_info,
            )

    def get_next_episode(self, cur_ep_num):
        # Viu episode numbering is just sequential numbers, adding one to the current number should provide accurate next episode
        next_ep_num = cur_ep_num + 1

        return next(
            filter(
                lambda product: (int(product.get("number")) == next_ep_num),
                self.series_info["product"],
            ),
            None,
        )
