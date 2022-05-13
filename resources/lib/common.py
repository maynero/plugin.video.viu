import logging
import time
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
VIU_COLLECTION_URL = "https://www.viu.com/ott/{}/index.php?r=category/series-category&platform_flag_label=web&area_id={}&language_flag_id={}&cpreference_id=&category_id={}&length={}&offset={}"
VIU_PRODUCT_URL = "https://www.viu.com/ott/{}/index.php?area_id={}&language_flag_id={}&r=vod/ajax-detail&platform_flag_label=web&product_id={}&ut=0"
VIU_SEARCH_URL = "https://www.viu.com/ott/{}/index.php?r=vod/jsonp&area_id={}&language_flag_id={}&cpreference_id="
VIU_STREAM_URL = "https://api-gateway-global.viu.com/api/playback/distribute?cpreference_id=&language_flag_id={}&ccs_product_id={}"
VIU_SETTING_URL = "https://api-gateway-global.viu.com/api/mobile?r=/setting/query2&platform_flag_label=web"
VIU_SEARCH_API_URL = "https://api-gateway-global.viu.com/api/mobile?r=/search/video&language_flag_id={}&cpreference_id=&platform_flag_label=web"
VIU_RECOMMENDATION_URL = "https://www.viu.com/ott/ph/index.php?r=home/ajax-index&area_id={}&language_flag_id={}"
VIU_USER_STATUS_URL = f"https://api-gateway-global.viu.com/api/subscription/status?v={int(time.time())}"
VIU_LOGIN_URL = "https://api-gateway-global.viu.com/api/auth/login"