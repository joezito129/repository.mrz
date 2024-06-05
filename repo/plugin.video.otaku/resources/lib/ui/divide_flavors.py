import json

from resources.lib.ui import control


def div_flavor(f):
    def wrapper(*args, **kwargs):
        if control.getSetting("divflavors.bool") == "true":
            dubsub_filter = control.getSetting("divflavors.menu")
            with open(control.maldubFile) as file:
                mal_dub = json.load(file)
            return f(mal_dub=mal_dub, dubsub_filter=dubsub_filter, *args, **kwargs)
        return f(*args, **kwargs)
    return wrapper
