from .kodiutils import get_setting_as_bool


def is_debug():
    return get_setting_as_bool('debug')