"""
EYEApplicationDelegateClass

An instance of this class is instantiated in the MainMenu.nib default NIB file.
All outlets and the base class are automatically derived at runtime by the
AutoBaseClass mechanism provided by the NibClassBuilder.
"""
from AppKit import NSOpenPanel
from PyObjCTools import NibClassBuilder
from EYETestWindowControllerClass import EYETestWindowController
from PreferenceController import *
# Make NibClassBuilder aware of the classes in the main NIB file.
NibClassBuilder.extractClasses( "MainMenu" )

# EYEApplicationDelegate will automatically inherit from the
# appropriate ObjC class [NSObject, in this case] and will have the
# appropriate IBOutlets already defined based on the data found in the
# NIB file(s) that define the class.
class EYEApplicationDelegate(NibClassBuilder.AutoBaseClass):
	def init(self):
		self = super(EYEApplicationDelegate, self).init()
		self.prefController = None
		return self
	def showPreferencePanel_(self, sender):
		if not self.prefController:
			self.prefController= PreferenceController.alloc().init()
		self.prefController.showWindow_(self)
	#showPreferencePanel_ = classmethod(showPreferencePanel_)
	def openDocument_(self, sender):
		openPanel = NSOpenPanel.openPanel()
		openPanel.setAllowsMultipleSelection_(False)
		openPanel.setCanChooseDirectories_(True)
		openPanel.setCanChooseFiles_(False)
		openPanel.runModalForTypes_(None)
		a =EYETestWindowController.testWindowController()
		a.showWindow_(sender)
		a.window().setTitle_(`openPanel.filenames()`[2:-2])
		a._server=`openPanel.filenames()`[2:-2]
  	
	def applicationDidFinishLaunching_(self, aNotification):
		"""Create and display a new connection window"""
		#self.openDocument_(None)
		#self.newConnectionAction_(None)
		#self.newTestAction_(None)
	