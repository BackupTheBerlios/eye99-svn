"""
Instances of EYETestWindowController are the controlling object
for the document windows for the 99eyeballs application.

Implements a standard toolbar.
"""

from AppKit import *
from Foundation import *
from PyObjCTools import NibClassBuilder
from hbalance import GlobDirectoryWalker

from objc import IBOutlet
from objc import selector
from objc import YES, NO

from threading import Thread
from Queue import Queue

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

kEYEUrlTextFieldToolbarItemIdentifier = "EYE: URL Textfield Toolbar Identifier"
"""Idnetifier for URL text field toolbar item."""

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
class WorkerThread(Thread):
	
	def __init__(self):
		"""Create a worker thread. Start it by calling the start() method."""
		self.queue = Queue()
		Thread.__init__(self)
	
	def stop(self):
		"""Stop the thread a.s.a.p., meaning whenever the currently running
		job is finished."""
		self.working = 0
		self.queue.put(None)
	
	def scheduleWork(self, func, *args, **kwargs):
		"""Schedule some work to be done in the worker thread."""
		self.queue.put((func, args, kwargs))
	
	def run(self):
		"""Fetch work from a queue, block when there's nothing to do.
		This method is called by Thread, don't call it yourself."""
		self.working = 1
		while self.working:
			work = self.queue.get()
			if work is None or not self.working:
				break
			func, args, kwargs = work
			pool = NSAutoreleasePool.alloc().init()
			try:
				func(*args, **kwargs)
			finally:
			# delete all local references; if they are the last refs they
			# may invoke autoreleases, which should then end up in our pool
				del func, args, kwargs, work
				del pool



NibClassBuilder.extractClasses( "EYETest" )

class EYETestWindowController(NibClassBuilder.AutoBaseClass):
	"""
	As per the definition in the NIB file,
	EYETestWindowController is a subclass of
	NSWindowController.
	"""
	__slots__ = ('_toolbarItems',
					'_toolbarDefaultItemIdentifiers',
					'_toolbarAllowedItemIdentifiers',
					'_methods',
					'_methodList',
					'_subset',
					'_OrigList',
					'_editorname',		
					'_server',
					'_methodPrefix',
					'_workQueue',
					'_working',
					'_workerThread',
					'_windowIsClosing')
	
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
		self = self.initWithWindowNibName_("EYETest")
		
		self._toolbarItems = {}
		self._toolbarDefaultItemIdentifiers = []
		self._toolbarAllowedItemIdentifiers = []
		
		self._editorname = "/Applications/TextEdit.app"
		self._server =""
		self._methods = {}
		self._subset=[]
		self._OrigList=[]
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
		self.methodsTable.setDoubleAction_("textEditOpen:")
		self.statusTextField.setStringValue_("")
		self.progressIndicator.setStyle_(NSProgressIndicatorSpinningStyle)
		self.progressIndicator.setDisplayedWhenStopped_(NO)
		
		self.createToolbar()
		# read in the editor from the prefs.
		self.setEditor()

	def setEditor(self):
		editor = NSUserDefaults.standardUserDefaults().objectForKey_(u"ODBTextEditor")
		if not editor: 	self._editorname = "/Applications/TextEdit.app"
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
			self._editorname =editorItem.objectForKey_("ODBEditorPath")
	  		
	
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
		toolbar = NSToolbar.alloc().initWithIdentifier_("EYE Test Window")
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
		               "reloadVisibleData:", NSImage.imageNamed_("beholder"), None)
		addToolbarItem(self, kEYEPreferencesToolbarItemIdentifier,
		               "Preferences", "Preferences", "Show Preferences", None,
		               "orderFrontPreferences:", NSImage.imageNamed_("Preferences"), None)
		addToolbarItem(self, kEYEUrlTextFieldToolbarItemIdentifier,
		               "Search", "Search", "Placeholder", None, None, self.urlTextField, None)
		
		self._toolbarDefaultItemIdentifiers = [
		    kEYEReloadContentsToolbarItemIdentifier,
		    kEYEUrlTextFieldToolbarItemIdentifier,
		    NSToolbarSeparatorItemIdentifier,
		    NSToolbarCustomizeToolbarItemIdentifier,
		]
		
		self._toolbarAllowedItemIdentifiers = [
		    kEYEReloadContentsToolbarItemIdentifier,
		    kEYEUrlTextFieldToolbarItemIdentifier,
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

	def reloadData(self):
		"""Tell the main thread to update the table view."""
		self.methodsTable.performSelectorOnMainThread_withObject_waitUntilDone_( "reloadData", None, 0)
	
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

# TableView methods, all of this just because I can not get cocoabindings to work.
	def numberOfRowsInTableView_(self,tableView):
		return len(self._methodList)
	def tableView_objectValueForTableColumn_row_(self, tableView, tableColumn,row):
		if tableColumn.headerCell().stringValue()=="Message":
			return self._methodList[row][0]
		elif tableColumn.headerCell().stringValue()=="Location":
			return self._methodList[row][1][self._methodList[row][1].rfind("/")+1:] 
		elif tableColumn.headerCell().stringValue()=="Method":
			return self._methodList[row][2]
		else:
			return ""
 
	def tableView_didClickTableColumn_(self, tableView, tableColumn):
		if tableColumn.headerCell().stringValue()=="Message":
			self.rowSort(0)
		elif tableColumn.headerCell().stringValue()=="Location":
			self.rowSort(1)
		elif tableColumn.headerCell().stringValue()=="Method":
			self.rowSort(2)
		else:
			return
		self.reloadData()
	
	def rowSort(self, n):
		nlist = [(x[n], x) for x in self._methodList]
		nlist.sort()
		self._methodList = [val for (key, val) in nlist]
	
	def controlTextDidChange_(self, aNotification):
		searchString = aNotification.object().stringValue()
		if searchString.length()==0:
			self._methodList = self._OrigList
		self._subset=[]
		for obj in self._OrigList:
			a = obj[0].find(searchString)
			if a !=-1:
				self._subset+=[obj]
		self._methodList =self._subset
		self.reloadData()
	
# external editor protocol as described here http://www.codingmonkeys.de/techpubs/externaleditor/pbxexternaleditor.html
	def openInExternalEditor(self, _filePath, _lnnum):
		from aem.send import Application
		import struct
		from Carbon.File import FSSpec
		SelectionRange=struct.pack('hhllll', 0, int(_lnnum)-1, 1,1,0,0)
		Application(self._editorname).event('aevt', 'odoc',{'----':FSSpec(_filePath),'kpos':SelectionRange}).send()

	def testAction_(self, sender):
		self.reloadVisibleData_(sender)
	
	def textEditOpen_(self):
		row=self.methodsTable.selectedRow()
		self.openInExternalEditor(self._methodList[row][1][:self._methodList[row][1].rfind(":")],\
											self._methodList[row][1][self._methodList[row][1].rfind(":")+1:])
		self.reloadData()

	def handleEditorChange_(self, note):
		self.setEditor()
				
	def reloadVisibleData_(self, sender):
		if self._working:
			# don't start a new job while there's an unfinished one
			return
		self.setStatusTextFieldMessage_("Checking ...")
		self.startWorking()
		url = self._server
		self._workerThread.scheduleWork(self.getMethods, url)
	
	def getMethods(self, url):
		pool = NSAutoreleasePool.alloc().init()
		self._methodList =[]
		self._OrigList=[]
		self.startWorking() # Start Process indicator
		filelist =GlobDirectoryWalker(url, "*.m")
		for filename in filelist:
			self.receiveMethods(filename)
			self.setStatusTextFieldMessage_("Found %d methods." % len(self._methodList))
		self.stopWorking()
		del pool
		if self._windowIsClosing:
			return
		self.reloadData()
		self.stopWorking()
		

	def receiveMethods(self, filename):
		a = hbalance.maine(filename)
		if a : # a can be None
			self._OrigList += a
			self._methodList+= a
		self.reloadData() 
