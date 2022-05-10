# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcvfs
import json as json
import os
from resources.lib.common import ADDON

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


def kodi_json_request(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode("utf-8", "ignore"))

    try:
        if "result" in response:
            return response["result"]
        return None
    except KeyError:
        LOG.warn("[%s] %s" % (params["method"], response["error"]["message"]))
        return None


def rmtree(path):
    if isinstance(path, unicode):
        path = path.encode("utf-8")

    dirs, files = xbmcvfs.listdir(path)
    for _dir in dirs:
        rmtree(os.path.join(path, _dir))
    for _file in files:
        xbmcvfs.delete(os.path.join(path, _file))
    xbmcvfs.rmdir(path)


# Up Next
def upnext_signal(sender, next_info):
    """Send a signal to Kodi using JSON RPC"""
    from base64 import b64encode
    from json import dumps

    data = [to_unicode(b64encode(dumps(next_info).encode()))]
    notify(sender=sender + ".SIGNAL", message="upnext_data", data=data)


def notify(sender, message, data):
    """Send a notification to Kodi using JSON RPC"""
    result = jsonrpc(
        method="JSONRPC.NotifyAll",
        params=dict(
            sender=sender,
            message=message,
            data=data,
        ),
    )
    if result.get("result") != "OK":
        xbmc.log(
            "Failed to send notification: " + result.get("error").get("message"), 4
        )
        return False
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
