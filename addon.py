# -*- coding: utf-8 -*-
from resources.lib import plugin
from resources.lib import kodilogging

import xbmcaddon

# Keep this file to a minimum, as Kodi
# doesn't keep a compiled copy of this

kodilogging.config()
plugin.run()
