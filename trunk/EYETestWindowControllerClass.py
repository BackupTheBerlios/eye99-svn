"""
Instances of EYETestWindowController are the controlling object
for the document windows for the 99eyeballs application.

Implements a standard toolbar.
"""

from AppKit import *
from Foundation import *
from PyObjCTools import NibClassBuilder
from hbalance import GlobDirectoryWalker
from MethodListController import MethodListController
from WorkerThread import WorkerThread

from objc import IBOutlet
from objc import selector
from objc import YES, NO
from objc import ivar

import sys
import types
import string
import traceback
import hbalance

from Foundation import NSObject
from objc import selector


kEYEReloadContentsToolbarItemIdentifier = "EYE: Reload Contents Toolbar Identifier"
"""Identifier for 'reload contents' toolbar item."""

kEYEPreferencesToolbarItemIdentifier = "EYE: Preferences Toolbar Identifier"
"""Identifier for 'preferences' toolbar item."""

kEYESearchFieldToolbarItemIdentifier = "EYE: Method Searchfield Toolbar Identifier"
#"""Idnetifier for URL text field toolbar item."""

def addToolbarItem(aController, anIdentifier, aLabel, aPaletteLabel,
                   aToolTip, aTarget, anAction, anItemContent, aMenu):
    """
    Adds an freshly created item to the toolbar defined by
    aController.  Makes a number of assumptions about the
    implementation of aController.  It should be refactored into a
    generically useful toolbar management untility.
    """
    toolbarItem = NSToolbarItem.alloc().initWithItemIdentifier_(anIdentifier)

    toolbarItem.setLabel_(aLabel)
    toolbarItem.setPaletteLabel_(aPaletteLabel)
    toolbarItem.setToolTip_(aToolTip)
    toolbarItem.setTarget_(aTarget)
    if anAction:
        toolbarItem.setAction_(anAction)

    if type(anItemContent) == NSImage:
        toolbarItem.setImage_(anItemContent)
    else:
        toolbarItem.setView_(anItemContent)
        bounds = anItemContent.bounds()
        minSize = (100, bounds[1][1])
        maxSize = (1000, bounds[1][1])
        toolbarItem.setMinSize_( minSize )
        toolbarItem.setMaxSize_( maxSize )

    if aMenu:
        menuItem = NSMenuItem.alloc().init()
        menuItem.setSubmenu_(aMenu)
        menuItem.setTitle_( aMenu.title() )
        toolbarItem.setMenuFormRepresentation_(menuItem)

    aController._toolbarItems[anIdentifier] = toolbarItem




NibClassBuilder.extractClasses( u"EYETest" )

class EYETestWindowController(NibClassBuilder.AutoBaseClass):
   """
   As per the definition in the NIB file,
   EYETestWindowController is a subclass of
   NSWindowController.
   """
   bookmarksArray = ivar('bookmarksArray')

   def testWindowController(self):
       """
       Create and return a default test window instance.
       """
       return EYETestWindowController.alloc().init()
   
   testWindowController = classmethod(testWindowController)
   
   def init(self):
      """
      Designated initializer.
      
      Returns self (as per ObjC designated initializer definition,
      unlike Python's __init__() method).
      """
      self.bookmarksArray = [] #NSMutableArray.array()
      self = self.initWithWindowNibName_("EYETest")
      
      self._toolbarItems = {}
      self._toolbarDefaultItemIdentifiers = []
      self._toolbarAllowedItemIdentifiers = []
      
      self._editorname = "/Applications/TextEdit.app"
      self.searchTextField=""
      self._methodList = []
      self._working = 0
      self._windowIsClosing = 0
      self._workerThread = WorkerThread()
      self._workerThread.start()
      NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self,
         "handleEditorChange:",u"JMEditorChanged",None)
      return self
   
   def awakeFromNib(self):
      """
      Invoked when the NIB file is loaded.  Initializes the various
      UI widgets.
      """
      self.retain() # balanced by autorelease() in windowWillClose_
      self.methods.setDoubleAction_("openEditor:")
      self.statusTextField.setStringValue_(u"")
      self.progressIndicator.setStyle_(NSProgressIndicatorSpinningStyle)
      self.progressIndicator.setDisplayedWhenStopped_(NO)
      
      self.createToolbar()
      # read in the editor from the prefs.
      self.setEditor()

   def setEditor(self):
      editor = NSUserDefaults.standardUserDefaults().objectForKey_(u"ODBTextEditor")
      if not editor:    self._editorname = u"/Applications/TextEdit.app"
      bundle = NSBundle.mainBundle()
      editorDict = NSDictionary.dictionaryWithContentsOfFile_(bundle.pathForResource_ofType_("ODBEditors","plist" ))    
      editorList=editorDict.objectForKey_(u"ODBEditors")
      for editorItem in editorList:
         name = editorItem.objectForKey_(u"ODBEditorName")
         if name == editor:
            bundleID = editorItem.objectForKey_(u"ODBEditorBundleID")
            self._editorname = NSWorkspace.sharedWorkspace().absolutePathForAppBundleWithIdentifier_(bundleID)
            break
      # check to see if the editor is run on the CLI
      if editorItem.objectForKey_(u"ODBEditorLaunchStyle") == 1:
         self._editorname =editorItem.objectForKey_(u"ODBEditorPath")
           
   
   def windowWillClose_(self, aNotification):
      """
      Clean up when the document window is closed.
      """
      # We must stop the worker thread and wait until it actually finishes before
      # we can allow the window to close. Weird stuff happens if we simply let the
      # thread run. When this thread is idle (blocking in queue.get()) there is
      # no problem and we can almost instantly close the window. If it's actually
      # in the middle of working it may take a couple of seconds, as we can't
      # _force_ the thread to stop: we have to ask it to to stop itself.
      self._windowIsClosing = 1  # try to stop the thread a.s.a.p.
      self._workerThread.stop()  # signal the thread that there is no more work to do
      self._workerThread.join()  # wait until it finishes
      self.autorelease()
   
   def createToolbar(self):
      """
      Creates and configures the toolbar to be used by the window.
      """
      toolbar = NSToolbar.alloc().initWithIdentifier_(u"EYE Test Window")
      toolbar.setDelegate_(self)
      toolbar.setAllowsUserCustomization_(YES)
      toolbar.setAutosavesConfiguration_(YES)
      
      self.createToolbarItems()
      
      self.window().setToolbar_(toolbar)
      
      #lastURL = NSUserDefaults.standardUserDefaults().stringForKey_("LastURL")
      #if lastURL and len(lastURL):
      #    self.urlTextField.setStringValue_(lastURL)
   
   def createToolbarItems(self):
      """
      Creates all of the toolbar items that can be made available in
      the toolbar.  The actual set of available toolbar items is
      determined by other mechanisms (user defaults, for example).
      """
      addToolbarItem(self, kEYEReloadContentsToolbarItemIdentifier,
                     "Check", "Check", "Run Check", None,
                     "reloadVisibleData:", NSImage.imageNamed_(u"beholder"), None)
      addToolbarItem(self, kEYEPreferencesToolbarItemIdentifier,
                     "Preferences", "Preferences", "Show Preferences", None,
                     "orderFrontPreferences:", NSImage.imageNamed_(u"Preferences"), None)
      addToolbarItem(self, kEYESearchFieldToolbarItemIdentifier,
                    "Search", "Search", "Placeholder", None, None, self.searchField, None)
    #  
      self._toolbarDefaultItemIdentifiers = [
          kEYEReloadContentsToolbarItemIdentifier,
          kEYESearchFieldToolbarItemIdentifier,
          NSToolbarSeparatorItemIdentifier,
          NSToolbarCustomizeToolbarItemIdentifier,
      ]
      
      self._toolbarAllowedItemIdentifiers = [
          kEYEReloadContentsToolbarItemIdentifier,
          kEYESearchFieldToolbarItemIdentifier,
          NSToolbarSeparatorItemIdentifier,
          NSToolbarSpaceItemIdentifier,
          NSToolbarFlexibleSpaceItemIdentifier,
          NSToolbarPrintItemIdentifier,
          kEYEPreferencesToolbarItemIdentifier,
          NSToolbarCustomizeToolbarItemIdentifier,
      ]   
   
   def toolbarDefaultItemIdentifiers_(self, anIdentifier):
      """
      Return an array of toolbar item identifiers that identify the
      set, in order, of items that should be displayed on the
      default toolbar.
      """
      return self._toolbarDefaultItemIdentifiers
   
   def toolbarAllowedItemIdentifiers_(self, anIdentifier):
      """
      Return an array of toolbar items that may be used in the toolbar.
      """
      return self._toolbarAllowedItemIdentifiers
   
   def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(self,
                                                               toolbar,
                                                               itemIdentifier, flag):
      """
      Delegate method fired when the toolbar is about to insert an
      item into the toolbar.  Item is identified by itemIdentifier.
      
      Effectively makes a copy of the cached reference instance of
      the toolbar item identified by itemIdentifier.
      """
      newItem = NSToolbarItem.alloc().initWithItemIdentifier_(itemIdentifier)
      item = self._toolbarItems[itemIdentifier]
      
      newItem.setLabel_( item.label() )
      newItem.setPaletteLabel_( item.paletteLabel() )
      if item.view():
          newItem.setView_( item.view() )
      else:
          newItem.setImage_( item.image() )
      
      newItem.setToolTip_( item.toolTip() )
      newItem.setTarget_( item.target() )
      newItem.setAction_( item.action() )
      newItem.setMenuFormRepresentation_( item.menuFormRepresentation() )
      
      if newItem.view():
          newItem.setMinSize_( item.minSize() )
          newItem.setMaxSize_( item.maxSize() )
      
      return newItem
   
   def setStatusTextFieldMessage_(self, aMessage):
      """
      Sets the contents of the statusTextField to aMessage and
      forces the field's contents to be redisplayed.
      """
      if not aMessage:
          aMessage = u"Displaying information about " +`len(self._methodList)` +" methods." +`self._working`
      self.statusTextField.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setStringValue:", unicode(aMessage), 0)

   def startWorking(self):
      """Signal the UI there's work goin on."""
      if not self._working:
         self.progressIndicator.startAnimation_(self)
      self._working += 1
      
   def stopWorking(self):
      """Signal the UI that the work is done."""
      self._working -= 1
      if not self._working:
         self.progressIndicator.performSelectorOnMainThread_withObject_waitUntilDone_(
         "stopAnimation:", self, 0)
   
# external editor protocol as described here http://www.codingmonkeys.de/techpubs/externaleditor/pbxexternaleditor.html
   def openInExternalEditor(self, _filePath, _lnnum):
      from aem.send import Application
      import struct
      from Carbon.File import FSSpec
      SelectionRange=struct.pack('hhllll', 0, int(_lnnum)-1, 1,1,0,0)   
      try:
         Application(self._editorname).event('aevtodoc',{'----':FSSpec(_filePath),'kpos':SelectionRange}).send()
      except:
         print "error;"
         pass

   def testAction_(self, sender):
      self.reloadVisibleData_(sender)
      
   def openEditor_(self):
      
      #row=self.methods.selectedRow()
      aDict=self.tableContentController.selectedObjects()[0]
      #loc =self.bookmarksArray[row]["Location"]
      self.openInExternalEditor(aDict["Path"],
                                 aDict["Location"][aDict["Location"].rfind(":")+1:])

   def handleEditorChange_(self, note):
      self.setEditor()
            
   def reloadVisibleData_(self, sender):
      if self._working:
         # don't start a new job while there's an unfinished one
         return
      self.setStatusTextFieldMessage_(u"Checking ...")
      self.startWorking()
      self.bookmarksArray=[]
      url = self._server
      self._workerThread.scheduleWork(self.getMethods, url)
   
   def getMethods(self, url):
      pool = NSAutoreleasePool.alloc().init()
      self.startWorking() # Start Process indicator
      filelist =GlobDirectoryWalker(url, "*.m")
      if not filelist:
         self.setStatusTextFieldMessage_(u"No Objective-C files found")
      for filename in filelist:
         if self._windowIsClosing:
            return
         self.receiveMethods(filename)
         self.setStatusTextFieldMessage_(unicode("Found " + str(len(self.bookmarksArray))+" methods."))
      self.stopWorking()
      del pool
      if self._windowIsClosing:
         return
      self.stopWorking()
      

   def receiveMethods(self, filename):
      a = hbalance.maine(filename)
      if a : # a can be None
         #self.bookmarksArray+=a
         for b in a:
            path = b[1]
            self.tableContentController.performSelectorOnMainThread_withObject_waitUntilDone_("addObject:",{"Message":b[0],"Location":path[path.rfind("/")+1:],"Method":b[2],"Path":path[:path.rfind(":")]},0)
      