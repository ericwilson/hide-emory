import re
#import xml.dom.ext
import xml.dom.minidom
import urllib
import subprocess
from tidylib import tidy_document
from django.conf import settings
from elementtree import ElementTree




from xml.parsers import expat

#these variables should be set in order for the HIDE and SEQL module to work correctly
HIDELIB = getattr(settings,'HIDELIB', '/default/path/')
#CONFIGTREE = ElementTree.parse(getattr(settings,'HIDECONFIG', '/nothing/'))

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
   CONFIGTREE = ElementTree.parse(filename)

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
				

def doReplacement( sgml, repl ):
	#p = ReplaceParser()
	#print p.feed(sgml)
	#p.close()
	#print sgml
	
	xhtml, errors = tidy_document( sgml,
		options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
	#print "xhtml:" + xhtml
	
	dom = xml.dom.minidom.parseString(xhtml)
	
		
	replvals = dict()
	
	replaceTags(dom.childNodes, dom, repl, replvals)
	
	print replvals
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
	print "[" + path + "]"
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
	print "[" + path + "]"
	#add features to the mallet file
	proc = subprocess.Popen("perl " + path,
			shell=True,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			)
	stdout_value, stderr_value = proc.communicate(mallet)
	#print str(stderr_value)
	#print "RETURNING " + str(stdout_value)
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

