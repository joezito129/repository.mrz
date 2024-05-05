from xbmcgui import WindowXMLDialog


class TextViewerXML(WindowXMLDialog):
    def __init__(self, xmlFilename: str, scriptPath: str, *args, **kwargs):
        super().__init__(xmlFilename, scriptPath)
        self.window_id = 2060
        self.heading = kwargs.get('heading')
        self.text = kwargs.get('text')

    def run(self):
        self.doModal()
        self.clearProperties()

    def onInit(self):
        self.set_properties()
        self.setFocusId(self.window_id)

    def onAction(self, action):
        if action in [92, 10]:
            self.close()

    def set_properties(self):
        self.setProperty('otaku.text', self.text)
        self.setProperty('otaku.heading', self.heading)
