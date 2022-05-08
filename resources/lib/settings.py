# -*- coding: utf-8 -*-
from resources.lib.kodiutils import get_setting, get_setting_as_bool


def isDebug():
    return get_setting_as_bool("debug")


def isUpnextOn():
    return get_setting_as_bool("upnext")


def getResolution():
    return get_setting("resolution")


def getSubtitleLang():
    return get_setting("subtitle_lang")
