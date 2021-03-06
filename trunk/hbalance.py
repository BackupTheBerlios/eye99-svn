#TestSuit
import re
import hotshot, hotshot.stats
import os, fnmatch, sys

class GlobDirectoryWalker:
	def __init__(self, directory, pattern="*"):
		self.stack = [directory]
		self.pattern = pattern
		self.files = []
		self.index = 0
	
	def __getitem__(self, index):
		while 1:
			try:
				file = self.files[self.index]
				self.index = self.index + 1
			except IndexError:
				# pop next directory from stack
				self.directory = self.stack.pop()
				self.files = os.listdir(self.directory)
				self.index = 0
			else:
				# got a filename
				fullname = os.path.join(self.directory, file)
				if os.path.isdir(fullname) and not os.path.islink(fullname):
					self.stack.append(fullname)
				if fnmatch.fnmatch(file, self.pattern):
					return fullname


# quick regexp tutorial
# \b means word delimited.
# (testPhrase)? means testPhrase will appear 0 or 1 times, not more (not less either)
# [\s\]]$ means that the pattern must end with whitespace or ]
# * means something appears 0 or more times in a row
# [^=] everything except a = 
#
#copyPattern = re.compile(r'\b(mutableC|c)opy(WithZone)?[\s\]]')
##allocPattern = re.compile(r'\b(alloc)(WithZone)?[\s\]]')
#initPattern = re.compile(r'\sinit(With)?')
#retainPattern = re.compile(r'\bretain[\s\]]')
#kulPattern = re.compile(r'\s*:\s*\[')
#varPattern = re.compile(r'\b[A-Za-z_]\w*')
methodHeadPattern = re.compile(r'^[+-]\s*\(')
ifPattern = re.compile(r'\s*if\s*\(\W*([A-Za-z_]\w*)')
plusPattern = re.compile(r'\b(((alloc|(mutableC|c)opy)(WithZone)?)|retain)\s*\]')
allocPattern = re.compile(r'\b(alloc)(WithZone)?\s*\]')
anchorPattern = re.compile(r'(\b[A-Za-z_]\w*\b)?(\s*\[.*\])?\s*((==|=)|[:]|,|return|\()?\s*(\[)[\s\[]*$')
#										group1					group2		group3				group5
implPattern = re.compile(r'@implementation\s*([A-Za-z_]\w*)')
colAnchorPattern = re.compile(r'(\b[A-Za-z_]\w*)?(\s*):$')
autoreleasePattern = re.compile(r'\bautorelease(\s)*\]')
releasePattern = re.compile(r'\brelease(\s)*\]')
objectPattern = re.compile(r'^[\[\s]*([A-Za-z_]\w*)\b')
returnPattern = re.compile(r'\breturn\W')

def finder(inPattern,line,ln):
	"""returns a tuple with two lists containing the assigned variables list, and the unassigned position list """
	a = inPattern.search(line)
	linecheck=[]
	pluslista =[]
	offset=0
	while a:
		b=findMatchingBrace(line, a.start() + offset)
		if b==-1:
			return [],[]
		tmp= assigned(line,b)
		if tmp[1]==-2: # Passed to legal method e.g setDelegate
			pass
		elif tmp[1]==-1: # Assigned to varable
			pluslista +=[[tmp[0],ln]]
		elif tmp[1]==-3:
			#print "Could not parse: " + tmp[0]
			pass
		else:
			# Since we only check alloc against release we can get away with this
			# The day we also check the other way around we will need a unified list.
			pluslista +=[[tmp[0],ln]]
			linecheck+=[[ tmp[1],ln ]]
		end = a.start()+len(a.group())# a.end() does not work, why?
		a = inPattern.search(line[end + offset:])  
		offset += end
	return pluslista, linecheck

	
def assigned(line,i):
		""" finds out if a message is attached to a variable, returns a tuple
		 with variable and position, position will be -1 if attached to varible,
		 -2 if attached to allowed message, if its attached to a colon
		the position of the colon will be returned, -3 means error"""
		anc = anchorPattern.search(line[:i+1]) # i+1 should be "[", or we are SOL
		if anc:
			kol = findMatchingCol(line,anc.start())
			c = anc.group(3)
			ob = objectPattern.search(line[i:])
			if c =="=":
				if not anc.group(1):
					return (line, -3)
				return (anc.group(1), -1)
			elif c==":":
				if partOfAllowed(anc.group(1)):
					return (0,-2)
				elif ob:
					if anc.group(2): # all this uglieness just because I can`t get end() to work
						return (ob.group(1), anc.start() + len(map( anc.group, (1,2,3) ) ))
					return (ob.group(1), anc.start() + len(map( anc.group, (1,2,3) ) ) ) # yes group(2) should be omitted
			elif c==",":
				kol = findMatchingCol(line,line[:anc.end()].rfind(","))
				anchor = colAnchorPattern.search(line[:kol+1])
				if anchor:
					if partOfAllowed(anchor.group(1)):
						return (0,-2)
				if ob:
					return (ob.group(1), line[:anc.end()].rfind(",") ) # Yes ugly
			elif c=="return" or c =="(":
	#Some people put parens around their return statements,
				if ob:			 								#this line is just for them
					return ob.group(1), line[:anc.end()].rfind("return")
				return "return", i
			elif ob:					
				return ob.group(1), -1
			return (line,-3)	# errorcode


			
def partOfAllowed(message, _extra=[]):
	"""Checks if the object is sent to a message that acts as a "sink" i.e. it does not retain"""
	allow=["init","setDelegate"] + _extra
	for elem in allow:
		if message.startswith(elem):
			return True
	return False

		
def findMatchingBrace(line,idx):
	le = len(line)
	lineje = line[:idx]
	lineje = lineje[::-1]
	braceup = 0
	instring = False                                                 				
	i = 1
	for c in lineje:
		if c =='"':
			instring = not instring
		elif c =="]" and not instring:
			braceup+=1
		elif c == "[" and not instring:
			if braceup==0:
				return (le-len(line))-i + idx # Maybe some arithmetics expert can simplify?
			else: braceup-=1
		i+=1 
	return -1

def findMatchingCol(line,idx):
	le = len(line)
	lineje = line[:idx]
	lineje = lineje[::-1]
	braceup = 0
	instring = False                                                 				
	i = 1
	for c in lineje:
		if c =='"':
			instring = not instring
		elif c =="]" and not instring:
			braceup+=1
		elif c == "[" and not instring:
			braceup-=1
		elif c ==":" and not instring:
			if braceup<1:
				return (le-len(line))-i + idx
		i+=1 
	return -1	

def lineLeakFinder(plus, minus,  filename, methodname,linenum, line):
	Warninglist=[]
	for posPlus, lnPlus in plus:
		ok = False
		for posMinus,lnMinus in minus:
			if posPlus ==posMinus and lnPlus ==lnMinus: # if hooked up to same message
				ok =True
		if not ok:
			Warninglist +=[[ "Warning: Non-autoreleased object assigned to message",\
									filename + ":"+`linenum`, methodname]]
	return Warninglist


	
def leakFinder(plus, minus, filename, methodname, returnline, ivarList, iflist):
	Warninglist=[]
	warned = False
	for elemPlus in plus:
		ok = False
		for elemMinus in minus: # Same as "elemPlus in minus"
			if elemMinus!=[] and elemMinus and elemPlus:
				if elemPlus[0]==elemMinus[0]: # if hooked up to same variable
					ok = True
		if elemPlus[0] in ivarList:
			ok = True
		if elemPlus[0][0].isupper(): # if first letter in elemPlus is uppercase, We got the wrong value
			ok = True					  # We are hiding that fact from the end-user though ;)
		if methodname.find("copyWithZone")!=-1 and returnline.find(`elemPlus[0]`[1:-1])!=-1:
			ok = True
		# Clumsy way to findout if it is a accessor
		if methodname.find(`elemPlus[0]`[1:-1])!=-1 and returnline.find(`elemPlus[0]`[1:-1])!=-1:
			ok = True
		for elemIf, lnIf in iflist: # check for if guard e.g if(!elem)
			if `elemPlus[0]`[1:-1] == elemIf and not elemPlus[1]<lnIf:
				ok = True
		if not ok:
			Warninglist +=[[ "Warning: " + `elemPlus[0]` + " had a retain increase but no decrease",\
								filename+":"+`elemPlus[1]`, methodname]]
	return Warninglist

def parseHeader(fname, implementationName):
	ln =0
	ivarList =[]
	ininter = False
	inblock = False
	ivarPattern = re.compile(r'(id|\*)\s*([A-Za-z_]\w*)')
	a=fname.rfind("/")
	filename =fname[:a+1]+implementationName+".h"
	try:
		fh=open(filename)
	except IOError:
		try: 
			fh=open(fname[:-1]+"h")
		except IOError:
			return []
	for line in fh.readlines():
		ln += 1
		if line.startswith("@interface"):
			ininter = True
			lnnum=ln
		elif line.startswith("}") or line.startswith("@end"):
			ininter = False
			inblock = False
		if ininter and line.find("{") !=-1:
			tempnum = ln - lnnum
			if 0 <= tempnum and tempnum < 3 : # the openbrace has threelines to appear 
				inblock = True						 # 3 because its nice and small
		if ininter and inblock: 
			a = ivarPattern.search(line)
			if a: # TODO extend so that we can have several declarations on one line
				ivarList += [a.group(2)]
	return ivarList

   
def maine(filename):
		Warninglist =[]
		totalPlusList=[]
		totalMinusList=[]
		lu=[]
		ininter = False
		inmethod = False
		inblock = False
		templine =""
		methodname=""
		returnline=""
		iflist=[]
		specialcase = True
		totalPlusList =[]
		totalMinusList=[]
		ivarList=[]
		
		ln =0
		
		# strip comments
		phrase = open(filename).read()
		def insEmp(a):
		   t = a[0]
		   b = 0
		   if t !="" and t[-1] !="\n" and a[1] !="":
		      b = len(a[0].splitlines())-1
		   else:
		      b = len(a[0].splitlines())
		   return "\n"*b+a[3]
		comPat = re.compile(r"""((/\*[^*]*\*+([^/*][^*]*\*+)*/[\n]*)|//[^\n]*\n[\n]*)|([\n]+|"(\\.|[^"\\])*"[\n]?|'(\ \.|[^'\\])*'|.[^/"'\\]*)""") # I have zero clues why this work
		phrase = "".join([insEmp(a) for a in comPat.findall(phrase)])# since we want to keep linenumbering we check insEmp
		phrase = phrase.splitlines()
		for codeline in phrase:
			ln +=1
			if codeline.startswith("@implementation"):
				ivarList =[]
				a=implPattern.search(codeline)
				if a:
					objectname=a.group(1)
					ivarList =parseHeader(filename, objectname)
				else:
					print "Error: " + `codeline`
					ivarList=[]
				ininter = True
				inmethod = False	
			elif ininter and codeline.startswith("@end"):
				ininter = False
				inmethod = False
				if not specialcase:
					Warninglist+=leakFinder(totalPlusList, totalMinusList, filename, methodname, returnline, ivarList, iflist)
				inmethod = False
			if ininter:
				a = methodHeadPattern.search(codeline)
				if a:
					if not specialcase:
					#When we are ready to start with new method, check old one for faults
						Warninglist+=leakFinder(totalPlusList, totalMinusList, filename, methodname, returnline, ivarList, iflist)
					# Clear the lists before starting in new method
					#os.close(sys.stderr.fileno()) 
					totalPlusList =[]
					totalMinusList=[]
					hasdealloc =[]
					returnline =""
					iflist=[]
					# Here we deduce if the method is of a type that is allowed to have positive retainee count
					methodname = codeline	
					if codeline.find(")init")!=-1 or codeline.find(") init")!=-1:
						specialcase = True
					elif codeline.find(")set")!=-1 or codeline.find(") set")!=-1:
						specialcase = True
					elif codeline.find(") dealloc")!=-1 or codeline.find(")dealloc")!=-1:
						specialcase = True
					elif codeline.find("windowDidLoad")!=-1 or codeline.find("viewDidLoad")!=-1 or codeline.find("awakeFromNib")!=-1:
						specialcase = True
					else:
						specialcase = False
						inmethod = True
			a = codeline.find("static")
			if a!=-1:
				ivarPattern=re.compile(r'(id|\*)\s*([A-Za-z_]\w*)')
				b = ivarPattern.search(codeline[a+6:])
				if b:
					ivarList += [b.group(2)]
			
			if not specialcase and ininter and inmethod:
				# attempt at comment removal
				#a = codeline.find("//")
				#if a !=-1 and codeline[a-1]!=":":# ugly way of removing comment, not "http://"
				#	codeline =codeline[:a]
				#a = codeline.find("/*")
				#b = codeline.find("*/")
				#if a!=-1 and b!=-1: # even uglier and more wrong, but speeds up a lot
				#	codeline = codeline[:a]+codeline[b+2:]
				# Conclusion: in need of a real comment remover
				templine +=codeline
				# Make sure we get complete multi-line msg, ugly and easily fooled
				# pray that you dont have strings with "]"
				if templine.count("[") == templine.count("]") and templine.count("/*") == templine.count("*/"):
					codeline=templine
					#a = codeline.find("/*")
					#b = codeline.find("*/")
					#if a!=-1 and b!=-1: # even uglier and more wrong, but speeds up a lot
					#	codeline = codeline[:a]+codeline[b+2:] 
					templine =""
					hasalloc, unHookedPlus = finder(plusPattern, codeline,ln)
					hasdealloc, unHookedMinus=finder(autoreleasePattern, codeline, ln)
					Warninglist+=lineLeakFinder(unHookedPlus, unHookedMinus, filename, methodname,ln, codeline )
					# Yes this is wasteful, but until proper headerfile support, well...
					hasalloc, unHookedPlus = finder(allocPattern, codeline,ln)
					if hasalloc !=[]: # We dont want to add empty strings
						totalPlusList+=hasalloc
					if hasdealloc !=[]:# Once for the autoreleased
						totalMinusList+=hasdealloc
					hasdealloc, unHookedMinus=finder(releasePattern, codeline, ln)
					#lineReleaseFinder(unHookedMinus)
					if hasdealloc !=[]: # Once for normal release
						totalMinusList+=hasdealloc
					a = ifPattern.search(codeline)
					if a: # very crude way to check if if-guarded
						iflist +=[ (`a.group(1)`[1:-1],ln)] # group(1) can be None
					a = returnPattern.search(codeline)
					if a:
						returnline = codeline
		return Warninglist						
		

# taken from Krzysztof Kowalczyk's blog
# for profiling performance
# Won`t work because of restructured code, hint prof.run calls with what argument?
profData = 'log2.dat'
def mainProf():
	global profData
	print "doing profiling"
	prof = hotshot.Profile(profData)
	prof.run("maine()")
	prof.close()

def dumpProfileStats():
	import hotshot.stats
	global profData
	print "dump profiling data"
	stats = hotshot.stats.load(profData)
	stats.sort_stats("cumulative")
	stats.print_stats()


if __name__ == "__main__":
	#mainProf()
	filelist =GlobDirectoryWalker(".", "*.m") #Yes line before makes a huge difference
	for filename in filelist:
	#filename = "/Users/joachimm/Projects/Adium/Source/ESUserIconHandlingPlugin.m"
		if filename.find("Controller.m")==-1:
			print filename
			maine(filename)
	#dumpProfileStats()
	

	
	