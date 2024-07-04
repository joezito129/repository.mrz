from resources.lib.ui import control


def div_flavor(f):
    def wrapper(*args, **kwargs):
        if control.bools.div_flavor:
            import json
            with open(control.maldubFile) as file:
                mal_dub = json.load(file)
            return f(mal_dub=mal_dub, dubsub_filter=control.getSetting("divflavors.menu"), *args, **kwargs)
        return f(*args, **kwargs)
    return wrapper
