import objc
from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder, AppHelper
NibClassBuilder.extractClasses( u"EYETest" )

class MethodListController(NibClassBuilder.AutoBaseClass):
   searchString = None

   def arrangeObjects_(self, objects):
      supermethod = super(MethodListController, self).arrangeObjects_
      if not self.searchString:
          return supermethod(objects)
      if len(self.searchString)==0:
         return supermethod(objects)
      sublist = []
      for obj in objects:
         for a in obj.keys():
            if obj[a].find(self.searchString) !=-1:
               sublist+=[obj]
               break
      return supermethod(sublist)

   def performSearch_(self, sender):
      self.searchString = unicode(sender.stringValue())
      self.rearrangeObjects()