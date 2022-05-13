# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
import xbmc
import xbmcplugin
import logging

LOG = logging.getLogger(__name__)

class ViuPlayer(xbmc.Player):
    """A custom Player object to check if Playback has started"""

    def __init__(self, handle):
        """Initialises a custom Player object"""
        xbmc.Player.__init__(self)

        self.__monitor = xbmc.Monitor()
        self.__playBackEventsTriggered = False  # pylint: disable=invalid-name
        self.__playPlayBackStoppedEventsTriggered = (
            False  # pylint: disable=invalid-name
        )
        self.__pollInterval = 1  # pylint: disable=invalid-name
        self.handle = handle

    def resolve(self, list_item):
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)

    def waitForPlayBack(self, url=None, time_out=30):  # pylint: disable=invalid-name
        """Blocks the call until playback is started. If an url was specified, it will wait
        for that url to be the active one playing before returning.
        :type url: str
        :type time_out: int
        """
        LOG.info("ViuPlayer: Waiting for playback")
        if self.__is_url_playing(url):
            self.__playBackEventsTriggered = True
            LOG.info("ViuPlayer: Already Playing")
            return True

        for i in range(0, int(time_out / self.__pollInterval)):
            if self.__monitor.abortRequested():
                LOG.info("ViuPlayer: Abort requested (%s)" % i * self.__pollInterval)
                return False

            if self.__is_url_playing(url):
                LOG.info("ViuPlayer: PlayBack started (%s)" % i * self.__pollInterval)
                return True

            if self.__playPlayBackStoppedEventsTriggered:
                LOG.warning(
                    "ViuPlayer: PlayBackStopped triggered while waiting for start."
                )
                return False

            self.__monitor.waitForAbort(self.__pollInterval)
            LOG.info("ViuPlayer: Waiting for an abort (%s)", i * self.__pollInterval)

        LOG.warning("ViuPlayer: time-out occurred waiting for playback (%s)", time_out)
        return False

    def onAVStarted(self):  # pylint: disable=invalid-name
        """Will be called when Kodi has a video or audiostream"""
        LOG.info("ViuPlayer: [onAVStarted] called")
        self.__playback_started()

    def onPlayBackStopped(self):  # pylint: disable=invalid-name
        """Will be called when [user] stops Kodi playing a file"""
        LOG.info("ViuPlayer: [onPlayBackStopped] called")
        self.__playback_stopped()

    def onPlayBackError(self):  # pylint: disable=invalid-name
        """Will be called when playback stops due to an error."""
        LOG.info("ViuPlayer: [onPlayBackError] called")
        self.__playback_stopped()

    def __playback_stopped(self):
        """Sets the correct flags after playback stopped"""
        self.__playBackEventsTriggered = False
        self.__playPlayBackStoppedEventsTriggered = True

    def __playback_started(self):
        """Sets the correct flags after playback started"""
        self.__playBackEventsTriggered = True
        self.__playPlayBackStoppedEventsTriggered = False

    def __is_url_playing(self, url):
        """Checks whether the given url is playing
        :param str url: The url to check for playback.
        :return: Indication if the url is actively playing or not.
        :rtype: bool
        """
        if not self.isPlaying():
            LOG.info("ViuPlayer: Not playing")
            return False

        if not self.__playBackEventsTriggered:
            LOG.info("ViuPlayer: Playing but the Kodi events did not yet trigger")
            return False

        # We are playing
        if url is None or url.startswith("plugin://"):
            LOG.info("ViuPlayer: No valid URL to check playback against: %s", url)
            return True

        playing_file = self.getPlayingFile()
        LOG.info("ViuPlayer: Checking \n'%s' vs \n'%s'", url, playing_file)
        return url == playing_file
