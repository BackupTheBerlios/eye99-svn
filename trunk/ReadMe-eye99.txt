All the Gui code, is derived from the Web Services Tool that is included with pyobjc. To this I have added a preference pane, a searchfield, my own icons, sorting(limited) and external editor support. 99eyeballs requires Panther, if this annoys you search for this line: NSWorkspace.sharedWorkspace().absolutePathForAppBundleWithIdentifier_ and come up with a better solution. Chances are that I will start using cocoa binding once I get it to work with pyobjc. 

WARNING!
99eyeballs will recurse down the folder you select in the open panel, looking for m-files. If you select a folder with many subfolders this might take a while.

Bugs
Many, among things cli based editor support is just a placeholder for now. Both tabs and whitespaces are mixed in the source files, this is very annoying I know.


Build Requirements
from <http://pyobjc.sourceforge.net>
py2objc , its recommended to build this from source so that you get all the extras.
from <http://freespace.virgin.net/hamish.sanderson/>
aem
LaunchServices


