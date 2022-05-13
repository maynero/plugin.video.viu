class Product:
    def __init__(
        self,
        product_id,
        number,
        synopsis,
        schedule_start_time,
        schedule_end_time,
        cover_image_url,
        series_category_name,
        is_parental_lock_limited,
        description,
        allow_download,
        offline_time,
        free_time,
        premium_time,
        is_free_premium_time,
        user_level,
        poster_logo_url,
        source_flag,
        allow_tv,
        released_product_total,
    ):
        self.product_id = product_id
        self.number = number
        self.synopsis = synopsis
        self.schedule_start_time = schedule_start_time
        self.schedule_end_time = schedule_end_time
        self.cover_image_url = cover_image_url
        self.series_category_name = series_category_name
        self.is_parental_lock_limited = is_parental_lock_limited
        self.description = description
        self.allow_download = allow_download
        self.offline_time = offline_time
        self.free_time = free_time
        self.premium_time = premium_time
        self.is_free_premium_time = is_free_premium_time
        self.user_level = user_level
        self.poster_logo_url = poster_logo_url
        self.source_flag = source_flag
        self.allow_tv = allow_tv
        self.released_product_total = released_product_total


class UserStatus:
    def __init__(self, user_id, username, user_level):
        self.user_id = user_id
        self.username = username
        self.user_level = user_level


class SiteSetting:
    def __init__(self, area_id, language_flag_id):
        self.area_id = area_id
        self.language_flag_id = language_flag_id
