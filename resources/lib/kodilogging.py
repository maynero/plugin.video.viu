# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import xbmc
from resources.lib import settings
from resources.lib.common import ADDON_ID


class LoggerHandler(logging.StreamHandler):
    def __init__(self):
        logging.StreamHandler.__init__(self)
        formatter = logging.Formatter(f"[{ADDON_ID}] [%(name)s] %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
            logging.INFO: xbmc.LOGINFO,
            logging.DEBUG: xbmc.LOGDEBUG,
            logging.NOTSET: xbmc.LOGNONE,
        }
        if settings.is_debug():
            try:
                xbmc.log(self.format(record), levels[record.levelno])
            except UnicodeEncodeError:
                xbmc.log(
                    self.format(record).encode("utf-8", "ignore"),
                    levels[record.levelno],
                )

    def flush(self):
        pass


def config():
    """ Setup the logger with this handler """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Make sure we pass all messages, Kodi will do some filtering itself.
    logger.addHandler(LoggerHandler())
