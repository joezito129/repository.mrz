from xbmcgui import WindowXMLDialog


class TextViewerXML(WindowXMLDialog):
    def __init__(self, xml_file, location, *args, **kwargs):
        super().__init__(xml_file, location)
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
        actionID = action.getId()
        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.close()

    def set_properties(self):
        self.setProperty('otaku.text', self.text)
        self.setProperty('otaku.heading', self.heading)
