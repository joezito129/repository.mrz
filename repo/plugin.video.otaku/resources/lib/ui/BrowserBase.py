class BrowserBase:
    _BASE_URL = None

    @staticmethod
    def _clean_title(text):
        return text.replace(u'×', ' x ')

    @staticmethod
    def _sphinx_clean(text):
        text = text.replace('+', '\+')  # noQA
        text = text.replace('-', '\-')  # noQA
        text = text.replace('!', '\!')  # noQA
        text = text.replace('^', '\^')  # noQA
        text = text.replace('"', r'\"') # noQA
        text = text.replace('~', '\~')  # noQA
        text = text.replace('*', '\*')  # noQA
        text = text.replace('?', '\?')  # noQA
        text = text.replace(':', '\:')  # noQA
        return text

    @staticmethod
    def get_size(size=0):
        power = 1024.0
        n = 0
        power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
        while size > power:
            size /= power
            n += 1
        return '{0:.2f} {1}'.format(size, power_labels[n])
