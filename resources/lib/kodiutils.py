# -*- coding: utf-8 -*-
import logging
import xbmc
import xbmcgui
from resources.lib.common import ADDON

LOG = logging.getLogger(__name__)


def notification(
    header, message, time=5000, icon=ADDON.getAddonInfo("icon"), sound=True
):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def show_settings():
    ADDON.openSettings()


def get_setting(setting):
    return ADDON.getSetting(setting).strip()


def set_setting(setting, value):
    ADDON.setSetting(setting, str(value))


def get_setting_as_bool(setting):
    return get_setting(setting).lower() == "true"


def get_setting_as_float(setting):
    try:
        return float(get_setting(setting))
    except ValueError:
        return 0


def get_setting_as_int(setting):
    try:
        return int(get_setting(setting))
    except ValueError:
        return 0


def get_string(string_id):
    return ADDON.getLocalizedString(string_id).encode("utf-8", "ignore")


# Up Next
def upnext_signal(sender, next_info):
    """Send a signal to Kodi using JSON RPC"""
    from base64 import b64encode
    from json import dumps

    data = [to_unicode(b64encode(dumps(next_info).encode()))]
    notify(sender=f"{sender}.SIGNAL", message="upnext_data", data=data)


def notify(sender, message, data):
    """Send a notification to Kodi using JSON RPC"""
    result = jsonrpc(
        method="JSONRPC.NotifyAll",
        params= {
            "sender": sender,
            "message": message,
            "data": data,
        },
    )
    if result.get("result") != "OK":
        LOG.info("Failed to send notification: %s", result.get("error").get("message"))
        return False
    LOG.info("Succesfully sent notification")
    return True


def jsonrpc(**kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    if kwargs.get("id") is None:
        kwargs.update(id=0)
    if kwargs.get("jsonrpc") is None:
        kwargs.update(jsonrpc="2.0")
    return loads(xbmc.executeJSONRPC(dumps(kwargs)))


def to_unicode(text, encoding="utf-8", errors="strict"):
    """Force text to unicode"""
    if isinstance(text, bytes):
        return text.decode(encoding, errors=errors)
    return text
