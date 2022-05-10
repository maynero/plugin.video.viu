# -*- coding: utf-8 -*-
from resources.lib.kodiutils import get_setting, get_setting_as_bool, get_setting_as_int


# General settings
def is_debug():
    return get_setting_as_bool("debug")


def is_upnext_on():
    return get_setting_as_bool("upnext")


def get_item_limit():
    return get_setting_as_int("itemlimit")


# Stream settings
def get_resolution():
    return get_setting("resolution")


def get_subtitle_lang():
    return get_setting("subtitle_lang")


# Account settings
def get_username():
    return get_setting("username")


def get_password():
    return get_setting("password")
