import sys
from PyObjCTools import AppHelper

# import classes required to start application
import EYEApplicationDelegateClass
import EYETestWindowControllerClass

# pass control to the AppKit
AppHelper.runEventLoop()
