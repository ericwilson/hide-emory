import re
#import xml.dom.ext
import xml.dom.minidom
import urllib
import subprocess
import os
import sys
from elementtree import ElementTree
from tempfile import NamedTemporaryFile




from xml.parsers import expat

#these variables should be set in order for the HIDE module to work correctly
#see loadConfig function.
#HIDELIB
#CONFIGTREE 

class MalletParser:
	def __init__(self):
		self._parser = expat.ParserCreate()
		self._parser.StartElementHandler = self.start
		self._parser.EndElementHandler = self.end
		self._parser.CharacterDataHandler = self.data
		self.currentTag = "O"
		self.output = ""
	
	def feed(self, data):
		self._parser.Parse(data, 0)

	def close(self):
		self._parser.Parse("", 1) # end of data
		del self._parser # get rid of circular references

	def start(self, tag, attrs):
		if (tag != 'object' and tag != 'br'):
			self.currentTag = str(tag)
		else:
			self.currentTag = "O"
	def end(self, tag):
		self.currentTag = "O"
        
	def getOutput(self):
		return self.output

	def data(self, data):
		currentTagCount = 0
		p = re.compile('(\\W)')
		vals = p.split(str(data))
		for v in vals:
			if ( v != '' ):
				val = urllib.quote(v)
				if ( self.currentTag != 'O'):
					if ( currentTagCount == 0 ):
						self.output += "TERM_" + val + "\tB-" + self.currentTag + "\n"
					else:
						self.output += "TERM_" + val + "\tI-" + self.currentTag + "\n"
				else:
					self.output += "TERM_" + val + "\tO" + "\n"
				currentTagCount+=1

	
				
							
#Configuration
def loadConfig( filename ):
   global CONFIGTREE
   global HIDELIB
   global EMORYCRFLIB
   global CRFMODELDIR
   global MAXMEM
   global DICTIONARY
   CONFIGTREE = ElementTree.parse(filename)
   croot = CONFIGTREE.getroot()
   HIDELIB = croot.find('hidelib').text
   EMORYCRFLIB = croot.find('crflib').text 
   CRFMODELDIR = croot.find('crfmodeldir').text
   MAXMEM = croot.find('maxmem').text
   DICTIONARYDIR = croot.find('dictionary').text
   DICTIONARY = dict()
   output = ""
   output += "reading dictionary from " + DICTIONARYDIR
   for fileName in os.listdir ( DICTIONARYDIR ):
      m = re.match('(.*).txt$', fileName)
      if m:
         dictname = m.group(1)
         #open file and populate appropriate dictionary
	 output += "loading " + dictname + " dictionary from " + fileName + "\n"
	 DICTIONARY[dictname] = dict()
	 f = open( DICTIONARYDIR + "/" + fileName, 'r' )
	 while 1:
	    line = f.readline()
	    if not line:
	       break
	    term = line.rstrip().lower()
	    #output += "adding " + term + " to " + dictname
	    DICTIONARY[dictname][term] = 1
   return output


def getReplacements():
   #CONFIGTREE contains the ElementTree of the XML file specified 
   legend = dict()
   root = CONFIGTREE.getroot()
   for l in root.findall('labels/label'):
      name = l.find('name').text
      repl = l.find('replacement').text
      legend[name] = repl 
   return legend


def getLegend():
   repl = dict()
   root = CONFIGTREE.getroot()
   for l in root.findall('gui/tag'):
      name = l.find('label').text
      color = l.find('color').text
      repl[name] = color
   return repl


def replaceTags( nodelist, parent, repl, replvals ):
   for subnode in nodelist:
      if (subnode.nodeType == subnode.ELEMENT_NODE):
         replaceTags( subnode.childNodes, subnode, repl, replvals )
      else:
          tagname = str(parent.tagName).lower()
          if ( tagname in repl ):
             #print "replacing " + subnode.nodeValue + " with " + repl[tagname]
             replvals[parent.tagName] = subnode.nodeValue
             subnode.nodeValue = repl[tagname]
				

def doReplacement( sgml, repl, replvals ):
   #TODO - consider using a non-validating SAX parser for this
   # so we don't have to add in tags to make sure we get xml.
   xhtml = sgml
   dom = xml.dom.minidom.parseString(xhtml)
   replaceTags(dom.childNodes, dom, repl, replvals)
   xmlstring = dom.toxml()
   val = xmlstring.replace("<?xml version=\"1.0\" ?>","")
   return val
	
        	
def SGMLToMallet ( sgml ):
	#convert the sgml to mallet
	#p = MalletParser()
	#p.feed(sgml)
	#p.close()
	#return p.getOutput()
	#print "SGMLToMallet " + sgml
	path= HIDELIB + "sgml2mallet-stdin.pl"
	print >> sys.stderr, "[" + path + "]"
	#add features to the mallet file
	proc = subprocess.Popen("perl " + path,
			shell=True,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			)
	stdout_value, stderr_value = proc.communicate(str(sgml))
	#print str(stderr_value)
	#print "SGMLToMallet RETURNING " + stdout_value
	return stdout_value
	
	
	
def MalletToSGML ( mallet ):
	#for now we use the old perl code to this conversion and return the result
	#print "MalletToSGML: " + mallet
	path = HIDELIB + "mallet2sgml-stdin.pl"
	print >> sys.stderr, "[" + path + "]"
	#add features to the mallet file
	proc = subprocess.Popen("perl " + path,
			shell=True,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			)
	stdout_value, stderr_value = proc.communicate(mallet)
	#print >> sys.stderr, str(stderr_value)
	#print >> sys.stderr, "RETURNING " + str(stdout_value)
	return str(stdout_value)
	

	
	
def extractTags( sgml, tagstoa ):
	#extract tags extracts the values between the tags in a document
	# in the case of numeric attributes it returns the value
	# string attributes are converted to a numeric value
	# depending on the tag.
#	print "Extracting ",
#	print tagstoa
#	print " from " + sgml
	dom = xml.dom.minidom.parseString(sgml)
	extract = []
	for tag in tagstoa:
		#print "extracting " + tag
		foundtags = dom.getElementsByTagName(tag)
		if ( foundtags.length > 0 ):
			t = foundtags[0]
			value = str(t.childNodes[0].nodeValue)
			if t.nodeName == 'gender':
				if ( value == 'F' or value == 'f' ):
					value = "0"
				elif ( value == 'M' or value == 'm'):
					value = "1"
			#print "found " + tag + " = " + value
			extract.append(value)
	output = "\t".join(map( str, extract))
	#print output
	return output 

def buildTemplate( sgml, tagstoa ):
	#this function builds a unique ID for every sgml match of any of the tags
	#specified in the argument
	# the mapping is an integer value combined with the tagname 
	#corresponding to each occurrence of
	occurrences = dict()
	dom = xml.dom.minidom.parseString(sgml)
	extract = []
	foundtags = dom.getElementsByTagName(tag)
	for tag in tagstoa:
		if ( foundtags.length > 0 ):
			for t in foundtags:
				value = str(t.childNodes[0].nodeValue)
				if t.nodeName == 'gender':
					if ( value == 'F' or value == 'f' ):
						value = "0"
					elif ( value == 'M' or value == 'm'):
						value = "1"
				
				#print "found " + tag + " = " + value
				extract.append(value)


def addFeatures( mallet ):
   """Currently calls perl to generate most regular expression features.
      The dictionary features are added in the python code.
      The dictionary features are currently case-insensitive."""

   #the dictionary features are currently case-insensitive
   #TODO - add support for passing in extra feature processing
   #this function adds the standard features to a mallet formatted file
   
   tempfile = NamedTemporaryFile(delete=False)
   tempfilename = tempfile.name
   tempfile.write(mallet)
   tempfile.close()

   #print >> sys.stderr, os.system("which perl")
   addfeatures = "perl " + HIDELIB + "/HIDE-addfeatures.pl " + tempfilename
#   if DICTIONARYFILE != '':
#      addfeatures = "perl " + HIDELIB + "/HIDE-addfeatures.pl " + tempfilename + " " + DICTIONARYFILE

   print >> sys.stderr, "execing [" + addfeatures + "]"
   proc = subprocess.Popen(addfeatures,
      shell=True,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      )
   stdout_value, stderr_value = proc.communicate()
   #print >> sys.stderr, "stdout_value = "  + str(stdout_value)
   #print >> sys.stderr, "stderr_value = "  + str(stderr_value)
   os.unlink(tempfile.name)
   features = str(stdout_value)
   #we now have all of the features
   #now loop through (*again*) and add the dictionary features
   fvs = features.split("\n")
   for i in range(len(fvs)):
      fv = fvs[i]
      fs = re.split('\s+', fv)
      for f in fs:
         #this is down to the actual feature level
	 # find the TERM_ -> check dictionary -> append to fv and break
	 m = re.match('TERM_(.*)', f)
	 if m:
	    term = m.group(1)
	    in_dict = checkDictionaries( term )
	    if in_dict != '':
	       #print "FOUND that [" + term + "] is in " + in_dict
	       fvs[i] = in_dict + " " + fv
	       break
   features = "\n".join(fvs) #remake the string from the fvs
   return features

def checkDictionaries( term ):
   t = term.lower()
   in_dict = []
   #look through all of the dictionaries and add to in_dict array if match
   for k in DICTIONARY.keys():
      if t in DICTIONARY[k]:
         in_dict.append("IN_" + str(k))

   return " ".join(in_dict)
   

def trainModel( modelfile, mallet ):
   #write a temporary file containing the mallet features file
   #train a CRF with the file, then delete it
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   javaclasspath = EMORYCRFLIB + "emorycrf" + ":" + EMORYCRFLIB + "mallet/class/:" + EMORYCRFLIB + "mallet/lib/mallet-deps.jar"
   javaargs = "-Xmx" + MAXMEM + " -cp \"" + javaclasspath + "\""
   execme = 'java ' + javaargs + " EmoryCRF --fully-connected false --train true --model-file " + modelfile + " " + tempfile.name + " 2>" + modelfile + ".log"

   print >> sys.stderr, "executing " + execme

   #open up EmoryCRF
   proc = subprocess.Popen( execme,
               shell=True,
               stdout=subprocess.PIPE,
            #   stderr=subprocess.PIPE,
               )
   #read output from EmoryCRF
   stdout_value, stderr_value = proc.communicate()
   os.unlink(tempfile.name)


def testModel (outfile, modelfile, mallet ):
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   results = labelMallet( modelfile, mallet)

   print >> sys.stderr, "writing results to " + outfile;
   f = open( outfile , 'w' )
   f.write(results)
   f.close()
   print >> sys.stderr, "done writing results";

   return 1
   


def labelMallet( modelfile, mallet ):
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   #setup the external call to EmoryCRF
   #TODO update this to allow the user to specify the CRF to use.
   javaclasspath = EMORYCRFLIB + "emorycrf" + ":" + EMORYCRFLIB + "mallet/class/:" + EMORYCRFLIB + "mallet/lib/mallet-deps.jar"
   javaargs = "-Xmx" + MAXMEM + " -cp \"" + javaclasspath + "\""
   execme = 'java ' + javaargs + " EmoryCRF --model-file " + modelfile + " " + tempfile.name

   print >> sys.stderr, "executing " + execme

   #open up EmoryCRF
   proc = subprocess.Popen( execme,
               shell=True,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               )

   #read output from EmoryCRF
   stdout_value, stderr_value = proc.communicate()
   #print >> sys.stderr, stderr_value

   print >> sys.stderr, "waiting on response"
   resultlabels = stdout_value
   print >> sys.stderr, "got response"
   #delete the created tempfile
   print >> sys.stderr, "unlinking file"

#   os.unlink(tempfile.name)

   print >> sys.stderr, "unlinked file"

   #build the mallet file from the resulting labels and the original mallet
   #mallet is the original
   #resultlabels are the labels
   rows = mallet.split("\n")
   labels = resultlabels.split("\n")

   print >> sys.stderr, "got rows " + str(len(rows)) +" and labels " + str(len(labels))

   resultsmallet = ""
   for i in range(0, len(rows)):
      r = rows[i]
      l = labels[i]
      resultsmallet += r + " " + l + "\n"

   print "returning results"
   return resultsmallet

def getTags ( xml ):
#extracts all the tag names in the xml document
   dtags = dict()
   tags = re.findall( "<([^<>/]+)(\s+[^<>]+)?>", xml )
   for t in tags:
      a = t[0].split(' ')
      dtags[a[0]] = 1
   return dtags.keys()

