import objc
from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder, AppHelper


NibClassBuilder.extractClasses("Preferences")


# class defined in Preferences.nib
class PreferenceController(NibClassBuilder.AutoBaseClass):
    # the actual base class is NSWindowController
    def init(self):
		self = self.initWithWindowNibName_("Preferences")
		return self
    def changeTextEditor_(self, sender):
      NSUserDefaults.standardUserDefaults().setObject_forKey_(self.editorPopup.titleOfSelectedItem(), u"ODBTextEditor")

    def awakeFromNib(self):
        #bundle = NSBundle.bundleForClass_( self.class__() )
        bundle = NSBundle.mainBundle()
        editorDict = NSDictionary.dictionaryWithContentsOfFile_(bundle.pathForResource_ofType_("ODBEditors","plist" ))
        #if not editorPlist: return
        editorList = editorDict.objectForKey_(u"ODBEditors")
        
        editor = NSUserDefaults.standardUserDefaults().objectForKey_(u"ODBTextEditor") 
        if not editor: 	editor = "BBEdit"            
        self.editorPopup.removeAllItems()
        
        for editorItem in editorList:
           bundleID = editorItem.objectForKey_(u"ODBEditorBundleID")
           name = editorItem.objectForKey_(u"ODBEditorName")
           signature =editorItem.objectForKey_(u"ODBEditorCreatorCode")
           menuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(name,None,"")               
           popupMenu = self.editorPopup.menu()
           popupMenu.addItem_( menuItem )
        self.editorPopup.selectItemWithTitle_(editor)

          

if __name__ == "__main__":
    AppHelper.runEventLoop()
