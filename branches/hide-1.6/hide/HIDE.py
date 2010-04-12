import re
#import xml.dom.ext
import xml.dom.minidom
import urllib
import subprocess
import os
import sys
import time
import xmlprinter
import StringIO
from elementtree import ElementTree
from tempfile import NamedTemporaryFile

from tidylib import tidy_document



from JSAXParser import SGMLToMalletHandler
from JSAXParser import SGMLToSuiteHandler


from xml.sax import make_parser
from xml.sax import parseString
from xml.sax.handler import ContentHandler


#these variables should be set in order for the HIDE module to work correctly
#see loadConfig function.
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
   DICTIONARY = buildDictionary( croot.find('dictionary').text )
   f = open('/tmp/dict.text', 'w')
   f.write( str(DICTIONARY ) )
   f.close()
   output = ""
   return output

def buildDictionary( dir ):
   """Builds the dictionary concept map based on the specified directory"""
   print "reading dictionary from " + dir
   DICTIONARY = dict()
   for fileName in os.listdir ( dir ):
      m = re.match('(.*).txt$', fileName)
      if m:
         dictname = m.group(1)
      else:
         continue
         #open file and populate appropriate dictionary
         #output += "loading " + dictname + " dictionary from " + fileName + "\n"
      DICTIONARY[dictname] = dict()
      f = open( dir + "/" + fileName, 'r' )
      while 1:
         line = f.readline()
         if not line:
            break
         term = line.rstrip().lower()
         terms = re.split('\\s+', term)
         phrase = ' '.join(terms)

         if (term not in DICTIONARY[dictname]) or (DICTIONARY[dictname][term][1] != 1):
            for i in range(0,len(terms)):
               entry = ' '.join( terms[0:(i+1)] )
               if entry not in DICTIONARY[dictname]:
                  DICTIONARY[dictname][entry] = [0,0]
               DICTIONARY[dictname][entry][0]+=1

         DICTIONARY[dictname][phrase][1] = 1
   return DICTIONARY


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

def getLegendSpec( matches ):
   repl = dict()
   root = CONFIGTREE.getroot()
   for l in root.findall('gui/tag'):
      name = l.find('label').text.lower()
      color = l.find('color').text
      print "comparing "  + name + " to " + str(matches)
#      if name not in matches:
#         continue
      print "adding " + name + " to legend"
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
   xhtml, errors = tidy_document( "<pre>" + sgml + "</pre>",
      options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
#   print "tidy = " + xhtml 
   #pull everything between pre tags
   spre = re.compile('^<pre>', re.I)
   epre = re.compile('</pre>$', re.I)
   xhtml = re.sub(spre, '', xhtml)
   xhtml = re.sub(epre, '', xhtml)
   xhtml = '<report>' + xhtml + '</report>'
   parser = make_parser()
   curHandler = SGMLToMalletHandler()
   #parser.setContentHandler(curHandler)
   xml.sax.parseString(xhtml, curHandler)
   mallet = curHandler.mallet
#   print "mallet " + mallet
   return mallet

def SGMLToSuite ( sgml ):
   xhtml, errors = tidy_document( "<pre>" + sgml + "</pre>",
      options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
#   print "tidy = " + xhtml 
   #pull everything between pre tags
   spre = re.compile('^<pre>', re.I)
   epre = re.compile('</pre>$', re.I)
   xhtml = re.sub(spre, '', xhtml)
   xhtml = re.sub(epre, '', xhtml)
   xhtml = '<report>' + xhtml + '</report>'
   parser = make_parser()
   curHandler = SGMLToSuiteHandler()
   #parser.setContentHandler(curHandler)
   xml.sax.parseString(xhtml, curHandler)
   mallet = curHandler.mallet
#   print "mallet " + mallet
   return mallet
#path= HIDELIB + "sgml2mallet-stdin.pl"
#print >> sys.stderr, "[" + path + "]"
#add features to the mallet file
#proc = subprocess.Popen("perl " + path,
#		shell=True,
#		stdin=subprocess.PIPE,
#		stdout=subprocess.PIPE,
#		stderr=subprocess.PIPE,
#		)
#stdout_value, stderr_value = proc.communicate(str(sgml))
#print str(stderr_value)
#print "SGMLToMallet RETURNING " + stdout_value
#return stdout_value

def MalletToSuite ( mallet ):
   fvs = re.split('\n', mallet)
   text = ''
   for fv in fvs:
      fv = fv.strip()
      features = re.split('\\s', fv)
      label = features[len(features)-1]
      mfeatures = features[0:len(features)-1]
      text += label + "\t" + "\t".join(mfeatures) + "\n"
   return text

def MalletToSGML ( mallet ):
   sgml = ''
   print "mallet = " + mallet
   fvs = re.split('\n' , mallet)
   currentTag = "O"
   print "converting text with " + str(len(fvs)) + "tokens"
   for fv in fvs:
      #get the term from the fvs
      fv = fv.strip()
      if fv == '':
         continue
      features = re.split('\\s', fv)
      go = False
      term = ''
      i = 2
      while ( not go ):
         token = features[len(features)-i]
         m = re.match('^TERM_(.*)$', token)
         if m:
            term = m.group(1)
            go = True
         else:
            if ( i > 2 ):
               print "ERROR: we don't have a term yet [" + token + "]"
               print str(features)
            i += 1
      #print features
      label = features[len(features)-1]
      #print "writing out " + term + " with label " + label
      term = urllib.unquote(term)
      m = re.match('^B-(.*)$', label)
      if m:
         l = m.group(1)
         currentTag = l
         sgml += '<' + currentTag + '>'
      elif currentTag != 'O' and label != 'I-'+ currentTag:
         sgml += '</' + currentTag + '>'
         m = re.match('^B-(.*)$', label)
         if m:
            l = m.group(1)
            currentTag = l
         else:
            currentTag = 'O'

      sgml += term

   return sgml
	
def FeaturesToSGML ( mallet ):
   sgml = ''
   print "mallet = " + mallet
   fvs = re.split('\n' , mallet)
   currentTag = "O"
   print "converting text with " + str(len(fvs)) + "tokens"
   for fv in fvs:
      #get the term from the fvs
      fv = fv.strip()
      if fv == '':
         continue
      features = re.split('\\s', fv)
      go = False
      term = ''
      i = 1
      while ( not go ):
         token = features[i]
         m = re.match('^TERM_(.*)$', token)
         if m:
            term = m.group(1)
            go = True
         else:
            if ( i > 2 ):
               print "ERROR: we don't have a term yet [" + token + "]"
               print str(features)
            i += 1
      #print features
      label = features[len(features)-1]
      #print "writing out " + term + " with label " + label
      term = urllib.unquote(term)
      m = re.match('^B-(.*)$', label)
      if m:
         l = m.group(1)
         currentTag = l
         sgml += '<' + currentTag + '>'
      elif currentTag != 'O' and label != 'I-'+ currentTag:
         sgml += '</' + currentTag + '>'
         m = re.match('^B-(.*)$', label)
         if m:
            l = m.group(1)
            currentTag = l
         else:
            currentTag = 'O'

      sgml += term

   return sgml
	
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


#addFeatures calls addSomeFeatures with all features as argument
def addFeatures( features ):
   """Generates dictionary, history , and regular expression based features for input."""
   ftypes = { 'regex' : 1, 'affix' : 1, 'context':1, 'dictionary':1 }
   return addSomeFeatures( features,  ftypes )

def addSomeFeatures( suite, ftypes ):
   """Generates dictionary, history , and regular expression based features for input."""

 #  print str(ftypes)
   history = []
   historySize = 4

   suite = suite.strip()
   fvs = suite.split("\n")
   for i in range(len(fvs)):
      print "adding features to token " + str(i)
      fvs[i] = fvs[i].strip()
      if fvs[i] == '':
         print "warning we have an empty FV"
         continue
      features = re.split('\\s', fvs[i])
      token = features[1]
      m = re.match('TERM_(.*)', token)
      term = m.group(1)
      cterm = urllib.unquote(term)
      foundfeatures = []
      if 'regex' in ftypes:
#         print "adding regex features"
         foundfeatures.extend(regexMatchFeatures( cterm ))
      if 'affix' in ftypes:
#         print "adding affix features"
         affixfeatures = affixFeatures( cterm )
         foundfeatures.extend(affixfeatures)
      if 'context' in ftypes:
#         print "adding context features"
         for j in range(0, historySize):
            if j >= len(history):
               break
            foundfeatures.append( "PREV" + str(len(history) - j - 1) + "_" + history[j] )
            fvs[i-j-1] += "\tNEXT" + str(j) + "_" + term
         history.append( term )
         if ( len(history) > historySize ):
            history = history[1:(len(history)-1)]
            
      fvs[i] = fvs[i] + "\t" + "\t".join(foundfeatures)
      if 'dictionary' in ftypes:
#         print "adding dictionary features"
         in_dict = checkDictionaries( term )
         if in_dict != '':
            fvs[i] += "\t" + in_dict

   features = "\n".join(fvs) #remake the string from the fvs
   features = features.strip()
   return features

def addSomeFeaturesMallet( mallet, ftypes ):
   """Generates dictionary, history , and regular expression based features for input."""

   print str(ftypes)
   history = []
   historySize = 4

   mallet = mallet.strip()
   fvs = mallet.split("\n")
   for i in range(len(fvs)):
      fvs[i] = fvs[i].strip()
      if fvs[i] == '':
         print "warning we have an empty FV"
         continue
      features = re.split('\\s', fvs[i])
      token = features[len(features)-2]
      m = re.match('TERM_(.*)', token)
      term = m.group(1)
      cterm = urllib.unquote(term)
      foundfeatures = []
      if 'regex' in ftypes:
#         print "adding regex features"
         foundfeatures.extend(regexMatchFeatures( cterm ))
      if 'affix' in ftypes:
#         print "adding affix features"
         affixfeatures = affixFeatures( cterm )
         foundfeatures.extend(affixfeatures)
      if 'context' in ftypes:
#         print "adding context features"
         for j in range(0, historySize):
            if j >= len(history):
               break
            foundfeatures.append( "PREV" + str(len(history) - j - 1) + "_" + history[j] )
            fvs[i-j-1] = "NEXT" + str(j) + "_" + term + " " + fvs[i-j-1]
         history.append( term )
         if ( len(history) > historySize ):
            history = history[1:(len(history)-1)]
            
      fvs[i] = " ".join(foundfeatures) + " " + fvs[i]
      if 'dictionary' in ftypes:
#         print "adding dictionary features"
         in_dict = checkDictionaries( term )
         if in_dict != '':
            fvs[i] = in_dict + " " + fvs[i]

   features = "\n".join(fvs) #remake the string from the fvs
   features = features.strip()
   return features
def affixFeatures( term ):
   alength = 3
   if (len(term) < alength):
      alength = len(term)-1
   features = []
   if len(term) > 1:
      for i in range(1, alength+1):
         prefix = term[0:i]
         suffix = term[(len(term)-i):(len(term))]
         features.append("PRE" + str(i) + "_" + prefix)
         features.append("SUF" + str(i) + "_" + suffix)
   return features

def regexMatchFeatures( term ):
   features = []
#   print "checking features for [" + term + "]"
   if re.match( '^[A-Za-z]$', term ):
      features.append( 'ALPHA' )
   if re.match( '^[A-Z].*$', term):
      features.append( 'INITCAPS' )
   if re.match( '^[A-Z][a-z].*$', term ):
      features.append( 'UPPER-LOWER')
   if re.match( '^[A-Z]+$', term ):
      features.append( 'ALLCAPS' )
   if re.match( '^[A-Z][a-z]+[A-Z][A-Za-z]*$', term ):
      features.append( 'MIXEDCAPS' )
   if re.match( '^[A-Za-z]$', term ):
      features.append('SINGLECHAR')
   if re.match( '^[0-9]$', term):
      features.append('SINGLEDIGIT')
   if re.match( '^[0-9][0-9]$', term):
      features.append('DOUBLEDIGIT')
   if re.match( '^[0-9][0-9][0-9]$', term):
      features.append('TRIPLEDIGIT')
   if re.match( '^[0-9][0-9][0-9][0-9]$', term):
      features.append('QUADDIGIT')
   if re.match( '^[0-9,]+$', term):
      if not re.match( '^,$', term ):
         features.append('NUMBER')
   if re.search( '[0-9]', term):
      features.append('HASDIGIT')
   if re.match( '^.*[0-9].*[A-Za-z].*$', term):
      features.append("ALPHANUMERIC")
   if re.match( '^.*[A-Za-z].*[0-9].*$', term):
      features.append("ALPHANUMERIC")
   if re.match( '^[0-9]+[A-Za-z]$', term ):
      features.append("NUMBERS_LETTERS")
   if re.match( '^[A-Za-z]+[0-9]+$', term ):
      features.append( "LETTERS_NUMBERS" )
   if re.search ( '-', term ):
      features.append( "HASDASH" )
   if re.search ( "'", term ):
      features.append( "HASQUOTE" )
   if re.search ( "/", term ):
      features.append( "HASSLASH" )
   if re.match( r"[`~!@#$%\^&*()\-=_+\[\]{}|;':\",./<>?]+$", term ):
      features.append( "ISPUNCT" )
   if re.match( r"(-|\+)?[0-9,]+(\.[0-9]*)?%?$", term ):
      features.append( "REALNUMBER" )
   if re.match( '^-.*$', term ):
      features.append ( "STARTMINUS" )
   if re.match( r"^\+.*$", term ):
      features.append ( "STARTPLUS" )
   if re.match( r"^.*%$", term):
      features.append ( "ENDPERCENT" )
   if re.match( r"^[IVXDLCM]+$", term ):
      features.append( "ROMAN" )
   if re.match( r"^\s+$", term):
      features.append( "ISSPACE" )
#   print "\n" + str(features)
   return features


def addFeaturesPerl( mallet ):
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
      token = fs[len(fs)-2]
      m = re.match('TERM_(.*)', f)
      term = m.group(1)
      in_dict = checkDictionaries( term )
      if in_dict != '':
         #print "FOUND that [" + term + "] is in " + in_dict
         fvs[i] = in_dict + " " + fv
   features = "\n".join(fvs) #remake the string from the fvs
   return features

def checkDictionaries( term ):
   t = term.lower()
   in_dict = []
   #look through all of the dictionaries and add to in_dict array if match
   for k in DICTIONARY.keys():
      if t in DICTIONARY[k]:
         in_dict.append("IN_" + str(k))

   return "\t".join(in_dict)
   

def trainModel( modelfile, mallet ):
   #write a temporary file containing the mallet features file
   #train a CRF with the file, then delete it
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   #instead of using MALLET we can use CRFSuite.
   execme = "crfsuite learn -m " + modelfile + " " + tempfile.name + " 2>&1 >" + modelfile + ".log"

#   javaclasspath = EMORYCRFLIB + "emorycrf" + ":" + EMORYCRFLIB + "mallet/class/:" + EMORYCRFLIB + "mallet/lib/mallet-deps.jar"
#   javaargs = "-Xmx" + MAXMEM + " -cp \"" + javaclasspath + "\""
#   execme = 'java ' + javaargs + " EmoryCRF --fully-connected false --train true --model-file " + modelfile + " " + tempfile.name + " 2>" + modelfile + ".log"

   print >> sys.stderr, "executing " + execme
   prevtime = time.time()

   proc = subprocess.Popen( execme,
               shell=True,
               stdout=subprocess.PIPE,
            #   stderr=subprocess.PIPE,
               )
   stdout_value, stderr_value = proc.communicate()
   os.unlink(tempfile.name)
   currtime = time.time()
   passedtime = currtime - prevtime
   f = open(modelfile + ".log", 'a')
   f.write("\n\n" + str(passedtime))
   f.close()


def testModel (outfile, modelfile, mallet ):
   prevtime = time.time()
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   results = labelMallet( modelfile, mallet)

   print >> sys.stderr, "writing results to " + outfile;
   f = open( outfile , 'w' )
   f.write(results)
   f.close()
   print >> sys.stderr, "done writing results";
   currtime = time.time()
   passedtime = currtime - prevtime
   print "elapsed test time = " + str(passedtime)

   return results
   


def labelMallet( modelfile, mallet ):
   tempfile = NamedTemporaryFile(delete=False)
   tempfile.write(mallet)
   tempfile.close()

   #TODO update this to allow the user to specify the CRF to use.
#   javaclasspath = EMORYCRFLIB + "emorycrf" + ":" + EMORYCRFLIB + "mallet/class/:" + EMORYCRFLIB + "mallet/lib/mallet-deps.jar"
#   javaargs = "-Xmx" + MAXMEM + " -cp \"" + javaclasspath + "\""
#   execme = 'java ' + javaargs + " EmoryCRF --model-file " + modelfile + " " + tempfile.name

   execme = "crfsuite tag -m " + modelfile + " " + tempfile.name

   print >> sys.stderr, "executing " + execme

   proc = subprocess.Popen( execme,
               shell=True,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               )

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
      resultsmallet += r + "\t" + l + "\n"

   print "returning results"
   return resultsmallet

def getCRFNamesFromDir( dir ):
   context = []
   for fileName in os.listdir ( dir ):
      if re.search('\.crf$', fileName):
         context.append(fileName)
   return context

def getFVNamesFromDir( dir ):
   context = []
   for fileName in os.listdir ( dir ):
      if re.search('\.features$', fileName):
         context.append(fileName)
   return context

def getResultNamesFromDir( dir ):
   context = []
   for fileName in os.listdir ( dir ):
      if re.search('\.results$', fileName):
         context.append(fileName)
   return context

def getTags ( xml ):
#extracts all the tag names in the xml document
   dtags = dict()
   tags = re.findall( "<([^<>/]+)(\s+[^<>]+)?>", xml )
   for t in tags:
      a = t[0].split(' ')
      dtags[a[0]] = 1
   return dtags.keys()

def getTagsDict ( xml ):
#extracts all the tag names in the xml document
   dtags = dict()
   tags = re.findall( "<([^<>/]+)(\s+[^<>]+)?>", xml )
   for t in tags:
      a = t[0].split(' ')
      dtags[a[0].lower()] = 1
   return dtags

