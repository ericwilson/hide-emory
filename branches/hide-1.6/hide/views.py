# Create your views here.
from django.template import RequestContext
from django.http import Http404,HttpResponseRedirect,HttpResponse
from django.shortcuts import render_to_response
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

import time

from couchdbkit import *
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit.ext.django.loading import get_db
from restkit import BasicAuth
import datetime
import random
import simplejson as json
#from BeautifulSoup import BeautifulSoup
import hl7
import re
import os
import sys
import HIDE
import HIDEexperiment
from HIDE import SGMLToMallet, FeaturesToSGML, extractTags,doReplacement, getLegendSpec, getReplacements, loadConfig, getTags, getTagsDict, trainModel, addSomeFeatures, addFeatures, labelMallet
from tidylib import tidy_document
import subprocess
import xmlprinter
import StringIO
import xml.sax.saxutils
import shutil
import zipfile


from zipfile import ZipFile

from tempfile import NamedTemporaryFile
from models import Object

import tasks

from xml.sax import make_parser
from xml.sax.handler import ContentHandler 
from JSAXParser import ReportXMLHandler
from JSAXParser import i2b2XMLHandler
import caTIES





#first thing is to initialize the HIDE module from the config file
log = ''
try:
   log = loadConfig(getattr(settings,'HIDECONFIG', 'default'))
#   HIDELIB = HIDE.HIDELIB
   CRFMODELDIR = HIDE.CRFMODELDIR # getattr(settings, 'CRF_MODEL_DIR', '/tmp/')
   db = HIDE.HIDE_DB
   deiddb = HIDE.HIDE_DEID_DB
   if not os.path.isdir(CRFMODELDIR):
      os.mkdir( CRFMODELDIR )

   REPLACEMENTS = getReplacements()
   LEGEND = dict()
   print "Replacements for de-identification are " + str(REPLACEMENTS)
#   print log
except:
   print "Error initializing HIDE, there is probably something wrong with the configuration file at " + log
   print sys.exc_info()


def objlist(request):
   if request.user.is_authenticated():
      if request.method == "POST":
         Object.set_db(db)
         object = Object(
            author = request.user.username,
            title = request.POST['title'],
            date = datetime.datetime.utcnow(),
            )
         object.save()
         return HttpResponseRedirect(u"/hide/")
      else:
         items = db.view('by_title/title', descending=True)
         for item in items:
            if ( 'text' in item['value'] ):
               #item['value']['summary'] = item['value']['text'][0:100]
               item['value']['labels'] = ", ".join(getTags(item['value']['text']))
         context = {
            'rows' : list(items),
         }
      return render_to_response('hide/list.html',context, context_instance=RequestContext(request))
   else:
      return HttpResponseRedirect(u"/accounts/login/")

@login_required(redirect_field_name='next')
def add (request):
   if request.method == "POST":
#if the user specified an MIT file
      if 'i2b2file' in request.POST:
         print "import i2b2 file"
         f = request.FILES['file']
         tags = request.POST['tags']
         handle_uploaded_i2b2_file(f, tags)
      elif 'mitfile' in request.POST:
         print "importing MIT file"
         f = request.FILES['file']
         handle_uploaded_mit_file(f)
      elif 'xmlfile' in request.POST:
         print "importing XML file"
         f = request.FILES['file']
         tags = request.POST['tags']
         handle_uploaded_xml_file(f, tags)
      elif 'hl7file' in request.POST:
         f = request.FILES['file'] 
         tags = request.POST['tags']
         handle_uploaded_hl7_file(f, tags)
      elif 'caties' in request.POST:
         #hard code for now TODO fix later
         caTIES.importcaTIESData( db, 'localhost', 'caties', 'caties', 'CATIES36PRIVATE_TEST' )

      else:
         print "we are just adding a manual document"
         Object.set_db(db)
         object = Object(
            title = request.POST['title'],
            text = request.POST['text'],
            tags = request.POST['tags']
         )
         id = object.save()
      return HttpResponseRedirect(u"/hide/")
   else:
      context = {}
      return render_to_response('hide/newdoc.html', context, context_instance=RequestContext(request))

@login_required(redirect_field_name='next')
def analysislist( request ):
   #pull everything from the analysis folder
   folder = HIDE.CRFMODELDIR + "/test/"
   #tags = getalltags( db )
   gtags = getalltags(db)
   folders = getfolders(folder)

   utags = dict()

   for t in gtags:
      utags[t] = 1 
   for f in folders:
      utags[f] = 1 

   tags = sorted(utags.keys())
   
   context = {
     'tags':tags,
     'path':'analysis',
     'message':'Select the set you would like to analyze',
   }
   return render_to_response('hide/alltags.html', context, context_instance=RequestContext(request))

@login_required(redirect_field_name='next')
def analysis( request, tag ):
   k = 10
   print "getting statistics"

   context = { 'tag':tag, 'k':k }

   outdir = HIDE.CRFMODELDIR + "/test/" + tag
   if not os.path.exists(outdir):
      os.makedirs(outdir)

   SAVENAME = outdir + "/ALL.mallet"

   if ( request.method == "POST" ):
      if k in request.POST:
         k = request.POST['k'] 
      context['k'] = k

      print "viewing analysis page"

      if 'mallet' in request.POST:
         objects = db.view('tags/tags')
         trainset = dict()
         for obj in objects:
            if obj['key'] == tag:
               obj['value']['labels'] = ", ".join(getTags(obj['value']['text']))
               trainset[obj['id']] = obj
   
         features = [] 
         for key, object in trainset.iteritems():
            html = object['value']['text'].replace("<br>", "<br/>")
            mallettext = SGMLToMallet(html)
 #           features.append( addFeatures(mallettext) )
            suite = HIDE.MalletToSuite( mallettext )
            features.append(suite)

         HIDEexperiment.writeMalletSetToDisk( SAVENAME, features)

      if 'kfold' in request.POST:
         print "Creating " + str(k) + " sets"
         k = int(k)
         features = HIDEexperiment.readMalletSetFromDisk(SAVENAME)
         print "read in " + str(len(features)) + " documents from file"
         (trainset, testset) = HIDEexperiment.createKFold( features, k )
         #the trainset and testset contains indexes into the features
         # array
         for i in range(k):
            HIDEexperiment.writeFoldFileToDisk(outdir + "/TEST" + str(i) + ".fold", testset[i])
            HIDEexperiment.writeFoldFileToDisk(outdir + "/TRAIN" + str(i) + ".fold", trainset[i])

         #write the sets to disk
         #print "We got " + str(trainset)
#         HIDEexperiment.writeKToDisk( outdir, trainset, testset, int(k), '.mallet' )
      if 'features' in request.POST:
         k = int(k)

         ftypes = dict()
         flist = request.POST.getlist('ftype')
         for f in flist:
               ftypes[f] = 1
         

         print "creating files for the following:"
         print str(ftypes)

         trainindex = [None]*k
         testindex = [None]*k
         for z in range(k):
            trainindex[z] = []
            testindex[z] = []

         print "reading in mallet from disk"
         mallet = HIDEexperiment.readMalletSetFromDisk(SAVENAME)
         print "done reading in mallet from disk"
      
         #add features to each of the mallet documents
         print "adding features to mallet files"
         features = []
         j = 1
         for m in mallet:
            print "adding features to mallet file " + str(j)
            features.append(addSomeFeatures(m, ftypes))
            j += 1

         #build the feature files to be written to disk
         print "retrieving fold information from disk"
         for i in range(k):
            trainindex[i] = HIDEexperiment.readFoldFileFromDisk( outdir + "/TRAIN" + str(i) + ".fold" )
            testindex[i] = HIDEexperiment.readFoldFileFromDisk( outdir + "/TEST" + str(i) + ".fold" )

         trainset = [None]*k
         testset = [None]*k
         for z in range(k):
            trainset[z] = ''
            testset[z] = ''

         print "building sets from fold information"
         for i in range(k):
            for j in trainindex[i]:
               trainset[i] += features[j]
            for j in testindex[i]:
               testset[i] += features[j]
            
         outlabel = request.POST['outdir']
         tempoutdir = HIDE.CRFMODELDIR + "/test/" + outlabel
         print "writing sets to disk"
         #here we can do sampling
         HIDEexperiment.writeKToDisk( tempoutdir, trainset, testset, k, '.features' )
      if 'train' in request.POST:
         (trainset, testset, k) = HIDEexperiment.readSetsFromDisk( outdir )
         HIDEexperiment.runTrainOnDisk( outdir, trainset )
      if 'test' in request.POST:
         print "running test"
         (trainset, testset, k) = HIDEexperiment.readSetsFromDisk( outdir )
         HIDEexperiment.runTestOnDisk( outdir, testset )
      if 'results' in request.POST:
         print "getting results"
         results = HIDEexperiment.getTestInfoFromDisk( outdir )
         html = HIDEexperiment.calcAccuracyHTMLFromDisk( outdir )
         context['results'] = html
      if 'clear' in request.POST:
         shutil.rmtree( outdir )
      if 'sample' in request.POST:
         historySize = request.POST['historysize']
         oprob = request.POST['oprob']
         outlabel = request.POST['outdir']
         print "performing " + str(float(oprob)) + " sampling based training"
         (trainset, testset, k) = HIDEexperiment.readSetsFromDisk( outdir )
         trainset = HIDEexperiment.localSample( trainset, k, int(historySize), float(oprob) )
         outlabel = request.POST['outdir']
         tempoutdir = HIDE.CRFMODELDIR + "/test/" + outlabel
         print "writing sample sets to disk"
         HIDEexperiment.writeKToDisk( tempoutdir, trainset, testset, k, '.features' )

   (kfoldinfo,k) = HIDEexperiment.getKFoldInfoFromDisk( HIDE.CRFMODELDIR + "/test/" + tag )
   context['features'] = HIDEexperiment.getFeaturesInfoFromDisk( outdir )
   context['mallet'] = HIDEexperiment.getSetInfoFromDisk( outdir )
   context['kfoldsets'] = kfoldinfo
   context['trainsets'] = HIDEexperiment.getTrainInfoFromDisk( outdir )
   context['testsets'] = HIDEexperiment.getTestInfoFromDisk( outdir )
   context['k'] = k

   return render_to_response('hide/analysis.html', context, context_instance=RequestContext(request))


      

@login_required(redirect_field_name='next')
def exportlist( request ):
   tags = getalltags( db )
   context = {
     'tags':tags,
     'path':'export',
     'message':'Select the set you would like to export',
   }
   return render_to_response('hide/alltags.html', context, context_instance=RequestContext(request))

@login_required(redirect_field_name='next')
def export (request, tag):
   
   if ( request.method == "POST" ):
      print "about to do export"
      #those documents that are selected will be exported
      type = request.POST['type']
      selected = request.POST['selected']
      if selected != '':
         return handle_export( type, selected )
   
   objects = db.view('tags/tags')
   exportset = dict()
   for obj in objects:
      if obj['key'] == tag:
         obj['value']['labels'] = ", ".join(getTags(obj['value']['text']))
         exportset[obj['id']] = obj
   context = {
      'objects':exportset,
      'tags': tag,
   }
   return render_to_response('hide/exportcontinue.html', context, context_instance=RequestContext(request))
      

def handle_export ( type, ids ):
   #loop through the ids build a response string and send it back to the user.
   #we may want to set the filetype so that the correct download box opens for the user.
  # 'text/plain'
  # 'application/xml'
  # 'application/json'
   print "exporting"
   vals = ids.split(',')
   output = ""
   objects = []
   for v in vals:
      #get it from the couchdb
      object = db.get(v) 
      objects.append(object)

   format = "text/plain"
   output = ""
   if type == 'xml':
      output = buildXMLFromList(objects)
      format = "application/xml"
   elif type == 'json':
      output = ", \n".join(map(str, objects))
      format = "application/json"
   elif type == 'hl7':
      output = buildEmoryHL7FromList(objects)
      format = "text/plain"
   else:
      #TODO - provide other output formats
      output = ", \n".join(map(str, objects))

   response = HttpResponse(output, mimetype=format)
   return response
#   return render_to_response('hide/exportcomplete.html', context, context_instance=RequestContext(request))

def XMLifyContent ( content ):
   tokens = re.split( '(<([^<>]+)(\\s+[^<>]+)?>)(.*?)(</\\2>)' , content );
   newtext = ""
   i = 0
   while i < len(tokens):
      m = re.search( '^<([^/<>! ]+)(\\s*[^<>]+)?>', tokens[i] ) 
      if m:
         newtext += tokens[i]  #start tag
         i += 3
         if ( tokens[i] ):
            newtext += xml.sax.saxutils.escape(tokens[i]) #text
         i += 1
         newtext += tokens[i] #end tag
      else: 
         newtext += xml.sax.saxutils.escape(tokens[i]) #just text
      i += 1
   return newtext

def buildXMLFromList( objects ):
 try:
   print "Building xml"
#   raise Exception("Blah")
   fp = StringIO.StringIO()
   writer = xmlprinter.xmlprinter(fp)
   writer.startDocument()
   writer.startElement("reports")
   for o in objects:
      print "Building xml for object:"
      print str(o)
      writer.startElement("report")
      title = o['title']
      writer.startElement("title")
      writer.data(title) 
      writer.endElement("title")
      m = re.match(r"PhysioNet-(\d+)-(\d+)", title)
      if m:
        writer.startElement("pid")
        writer.data(m.group(1))
        writer.endElement("pid")
        writer.startElement("rid")
        writer.data(m.group(2))
        writer.endElement("rid")
      writer.startElement("content")
      content = XMLifyContent(o['text'])
      print "writing content =\n" + content
      writer.raw(content)
      writer.endElement("content")
      writer.endElement("report")
   writer.endElement("reports")
   writer.endDocument()
   reportXML = fp.getvalue()
   print "sending content =\n" + reportXML
   return reportXML 
 except:
   print "**** Warning **** Error building xml from list of objects"
   return "**** Warning **** Error building xml from list of objects" , sys.exc_info()




def handle_uploaded_hl7_file(f, tagi):
   print "handling hl7 file " + str(f) + " with tag " + tagi
   

   tempfile = NamedTemporaryFile(delete=False)
   tempfilename = tempfile.name

   print "creating tempfile at " + tempfilename

   for chunk in f.chunks():
      tempfile.write(chunk)
   tempfile.close()

   if ( zipfile.is_zipfile(tempfilename) ):
      print "importing zip of hl7 files"
      z = ZipFile(tempfilename, 'r')
      znames = z.namelist()
      for n in znames:
         print "extracting " + str(n)
         hl7file = z.open(n, 'rU')
         content = hl7file.read()
         processEmoryHL7( content, tagi )
         hl7file.close()
      
   else:
      print "importing non \"zipped\" hl7"

   os.unlink(tempfilename)


#different sections of the reports correspond
# to different codes in hl7

OBX = { 'ID':3 , 'VALUE': 5 }

PID = { 'INTERNALID':3, 'NAME': 5, 'DOB': 7, 'GENDER':8, 'ETHNICITY': 10, 'ADDRESS':11,
         'PHONE': 13, 'ACCOUNTNUM': 18, 'SSN':19 }

OBR = { 'ORDERNUM': 3, 'DEPARTMENT': 4, 'OBSDATE' : 7 , 'SPECDATE':14, 'SPECSOURCE':15, 'PRIINTERPRETER': 32, 'ASSTINTERPRETER': 33, 'SIGNOUTTIME':22 }

def processHL7( hl7input ):
   clean = hl7input
   #first we clean up the hl7 to be seperated by \n rather than \r
   #clean = hl7input.replace("\r", "\n")
   #clean = clean.replace("\n", "\r")
   #lines = clean.split("\n") #well this is not quite right
   #print "hl7 ="
   #print clean

   hl7report = dict()
   h = hl7.parse(clean)
   print "file has " + str(len(h)) + " messages"
   for i in h:
      print i
      field = str(i[0])
      print "we found " + field
      if field == 'OBX':
         id = i[OBX['ID']]
         for j in range(len(id)):
            print "id = " + id[j]
         val = i[OBX['VALUE']]
         for j in range(len(val)):
            print "val = " + val[j]


def processEmoryHL7 ( hl7input, tag ):
   clean = hl7input.replace('\n', '\r')
   hl7report = dict()
   h = hl7.parse(clean)
   print "file has " + str(len(h)) + " messages"
   for i in h:
      field = str(i[0])
      if field == 'MSH':
         if 'title' in hl7report:
            hl7report['tags'] = tag
            db.save_doc(hl7report)
         hl7report = dict()

#PID = { 'INTERNALID':3, 'NAME': 5, 'DOB': 7, 'GENDER':8, 'ETHNICITY': 10, 'ADDRESS':11,
#         'PHONE': 13, 'ACCOUNTNUM': 18, 'SSN':19 }
      if field == 'PID':
         for k in PID.keys():
            if k == 'ADDRESS':
               address = i[PID['ADDRESS']]
               hl7report['addr_street'] = address[0]
               hl7report['addr_other'] = address[1]
               hl7report['addr_city'] = address[2]
               hl7report['addr_state'] = address[3]
               hl7report['addr_zip'] = address[4]
               hl7report['addr_country'] = address[5]
            elif k == 'NAME':
               name = i[PID['NAME']]
               hl7report['LAST_NAME'] = name[0]
               hl7report['FIRST_NAME'] = name[1]
               if 2 in name:
                  hl7report['MIDDLE_NAME'] = name[2]
               if 3 in name:
                  hl7report['SUFFIX_NAME'] = name[3]
               if 4 in name:
                  hl7report['PREFIX_NAME'] = name[4]
            else:
               hl7report[k] = str(i[PID[k]])

#OBR = { 'ORDERNUM': 3, 'DEPARTMENT': 4, 'OBSDATE':7, 'SPECDATE':14, 'PRIINTERPRETER': 32, 'ASSTINTERPRETER': 33 }
      if field == 'OBR':
         for k in OBR.keys():
            if k == 'ORDERNUM':
               hl7report['ACCESSION_NUM'] = i[OBR[k]][0]
               hl7report[k] = str( i[OBR[k]] )
            else:
               hl7report[k] = str( i[OBR[k]] )
         
#OBX = { 'ID':3 , 'VALUE': 5 }
      if field == 'OBX':
         id = i[OBX['ID']]
         val = i[OBX['VALUE']]
         hl7report['HL7ID'] = str( i[OBX['ID']] )
         hl7report['title'] = hl7report['HL7ID']
         if 'text' not in hl7report:
            text = str(val)
            hl7report['text'] = text.replace("\\T\\", '&') + "\n"
#            hl7report['text'] = str(val) + "\n"
         else:
            text = str(val)
            hl7report['text'] += text.replace("\\T\\", '&') + "\n"
   if 'title' in hl7report:
      print "Adding final report to DB"
      print hl7report['title']
      hl7report['tags'] = tag
      db.save_doc(hl7report)

def buildEmoryHL7FromList(objects):
   """This function builds HL7 similar to the COPATH reports at Emory."""
   output = ''
   dhticounter = 0
   for o in objects:
      dhticounter += 1
      currenttime = time.strftime("%Y%m%d%H%M%S")
      output += "MSH|^~\&|COPATHPLUS||HIS||" + currenttime + "||ORU^R01|" + str(dhticounter) + "|P|2.3.1\r"

      #PID|1||6010358^^^A||Test^TEST||19910101|M||4|4650 Sunny st.^^Canton^MA^02021^United States||(617)541-2140|||||0921800002^^^A|321-05-4879

      #build the PID variables
      internalid = "NA"
      if 'INTERNALID' in o:
         internalid =str(o['INTERNALID'])
      namearray = ["" for x in range(5)]
      nametypes = ['LAST_NAME', 'FIRST_NAME', 'MIDDLE_NAME', 'SUFFIX_NAME', 'PREFIX_NAME' ]
      for i in range(len(nametypes)):
         if nametypes[i] in o:
            namearray[i] = o[nametypes[i]]

      namestring = "^".join( namearray )
      dob = "00000000"
      if "DOB" in o:
         dob = o['DOB']
      gender= "U"
      if "GENDER" in o:
         gender = o['GENDER']

      addressarray = ["" for x in range(6)]
      addresstypes = ["addr_street", "addr_other", "addr_city", "addr_state", "addr_zip", "addr_country"]

      for i in range( len(addresstypes) ):
         if addresstypes[i] in o:
            addressarray[i] = o[addresstypes[i]]

      addressstring = "^".join( addressarray )

      ethnicity = 0
      if "ETHNICITY" in o:
         ethnicity = o['ETHNICITY']

      phone = "(000)000-0000"
      if "PHONE" in o:
         phone = o['PHONE']

      accountnum = "000^^^0"
      if "ACCOUNTNUM" in o:
         accountnum = o['ACCOUNTNUM']

      ssn = "000-00-0000"
      if "SSN" in o:
         ssn = o['SSN']

      output += "PID|1||" + internalid + "||" + namestring + "||" + dob +"|" + gender + "||" + ethnicity + "|" + addressstring + "||" + phone + "|||||" + accountnum + "|" + ssn + "\r"

      #build OBR message
      #OBR = { 'ORDERNUM': 3, 'DEPARTMENT': 4, 'OBSDATE' : 7 , 'SPECDATE':14, 'PRIINTERPRETER': 32, 'ASSTINTERPRETER': 33 }

      ordernum = "00^CoPathPlus"
      if "ORDERNUM" in o:
         ordernum = o['ORDERNUM']
      
      department = "D^Department"
      if "DEPARTMENT" in o:
         department = o['DEPARTMENT']

      obsdate = "000000000000"
      if "OBSDATE" in o:
         obsdate = o['OBSDATE']

      specdate = "000000000000"
      if "SPECDATE" in o:
         specdate = o['SPECDATE']

      specsource = "NA"
      if "SPECSOURCE" in o:
         specsource = o['SPECSOURCE']

      priinter = "0^STUFF^PRI"
      if "PRIINTERPRETER" in o:
         priinter = o['PRIINTERPRETER']

      asstinter = "0^STUFF^ASST" 
      if "ASSTINTERPRETER" in o:
         asstinter = o['ASSTINTERPRETER']

      signout = "000000000000"
      if "SIGNOUT" in o:
         signout = o['SIGNOUT']

      #OBR|1||C09-5^CoPathPlus|S^Surgical Pathology|||200908101522|||||||200908101522|LIV BX|||||||200908101541||SP|F|||||||11579^CDHT^Test1|e71^CDHT^Test^M
      output += "OBR|1||" + ordernum + "|" + department + "|||" + obsdate + "|||||||" + specdate + "|" + specsource + "|||||||" + signout + "||SP|F|||||||" + priinter + "|" + asstinter + "\r"

      #now build all the OBX
      #OBX|28|TX|C09-5&rpt^^99DHT||some future date by various physicians, including but not limited to||||||F

      mnum = 1
      text = o['text']
      hl7id = "NA"
      if 'HL7ID' in o:
         hl7id = o['HL7ID']

      lines = text.split('\n')
      for l in lines:
         clean = hl7escape(l)
         output += "OBX|" + str(mnum) + "|TX|" + hl7id + "||" + clean + "||||||F\r"
         mnum += 1

   return output

   
def hl7escape( t ):
   text = t.replace('&', "\\T\\")
   return text

#this function handles an uploaded xml file. The xml should be of the form
#<records>
#<record>
#<title>title</title>
#<content>The Text of the Record here</content>
#</records>
def handle_uploaded_xml_file(f, tagi):
   print "parsing " + f.name
   parser = make_parser()
   curHandler = ReportXMLHandler()
   parser.setContentHandler(curHandler)
   parser.parse(f)
   reports = curHandler.reports
   print str(reports)
   for k,v in sorted(reports.iteritems()):
      for x,y in sorted(v.iteritems()):
         #create an object and put it in the couchdb
       print "k -> " + k
       print "x -> " + x
       name = ""
       if ( k != '-1' ):
          name = "PhysioNet-" + k + "-" + x
       else:
          name = x
       print "adding " + name + " with tags = " + tags + " to CouchDB"
          #print y
       Object.set_db(db)
       object = Object(
            title = name,
            text = y,
            tags = tagi
       )
       #print "[" + currentRecord + "]" 
       object.save()
       print object['_id']
   #   print reports.keys()
   #   print reports.keys().sort()
   #   print curHandler.content
   return HttpResponse("Successful upload")

def handle_uploaded_i2b2_file(f, tagi):
   print "parsing " + f.name
   parser = make_parser()
   curHandler = i2b2XMLHandler()
   parser.setContentHandler(curHandler)
   parser.parse(f)
   reports = curHandler.reports
   #print reports
   for k,v in sorted(reports.iteritems()):
      for x,y in sorted(v.iteritems()):
         #create an object and put it in the couchdb
          print "k -> " + k
          print "x -> " + x
          name = x
          print "adding " + name + " to CouchDB"
          Object.set_db(db)
          object = Object(
               title = name,
               text = y,
               tags = tagi
          )
            #print "[" + currentRecord + "]" 
          id = object.save()
          print object['_id']
#   print reports.keys()
#   print reports.keys().sort()
#   print curHandler.content
   return HttpResponse("Successful upload")
   
def handle_uploaded_mit_file(f):
   print "parsing " + f.name
   #print "Content:"
   #loop through the file and generate an object for each and save it to the
   # CouchDB
#START_OF_RECORD=1||||1||||
#   O: 58 YEAR OLD FEMALE ADMITTED IN TRANSFER FROM CALVERT HOSPITAL FOR MENTAL STATUS CHANGES POST FALL AT HOME AND CONTINUED HYPOTENSION AT CALVERT HOSPITAL REQUIRING DOPAMINE; PMH: CAD, S/P MI 1992; LCX PTCA; 3V CABG WITH MVR; CMP; AFIB- AV NODE ABLATION; PERM PACER- DDD MODE; PULM HTN; PVD; NIDDM; HPI: 2 WEEK HISTORY LEG WEAKNESS; 7/22 FOUND BY HUSBAND ON FLOOR- AWAKE, BUT MENTAL STATUS CHANGES; TO CALVERT HOSPITAL ER- TO THEIR ICU; HEAD CT- NEG FOR BLEED; VQ SCAN- NEG FOR PE; ECHO- GLOBAL HYPOKINESIS; EF EST 20%; R/O FOR MI; DIGOXIN TOXIC WITH HYPERKALEMIA- KAYEXALATE, DEXTROSE, INSULIN; RENAL INSUFFICIENCY- BUN 54, CR 2.8; INR 7 ( ON COUMADIN AT HOME); 7/23 AT CALVERT- 2 FFP, 2 UNITS PRBC, VITAMIN K; REFERRED TO GH. 
#    ARRIVED IN TRANSFER APPROX. 2130; IN NO MAJOR DISTRESS; DOPAMINE TAPER, THEN DC; NS FLUID BOLUS GIVEN WITH IMPROVEMENT IN BP RANGE; SEE FLOW SHEET SECTION FOR CLINICAL INFORMATION; A: NO HEMODYNAMIC COMPROMISE SINCE TRANSFER; TOLERATING DOPAMINE DC; P: TREND BP RANGE; OBSERVE FOR PRECIPITOUS HYPOTENSION.
#
#    ||||END_OF_RECORD
#loop until we find start of record.
   currentRecord = ""
   name = ""
   for chunk in f.chunks():
      #split the chunk into lines and keep the whitespace
      lines = chunk.splitlines(1)
      for i in range(len(lines)):
         print "LOOKING AT LINE " + str(i)
         start = re.search( 'START_OF_RECORD=(\\d+)\|\|\|\|(\\d+)\|\|\|\|', lines[i])
         end = re.search( '\|\|\|\|END_OF_RECORD', lines[i] )
         if start:
            name = "MIT-rec-" + start.group(1) + "-" + start.group(2)
            currentRecord = ""
         elif end:
            print "adding " + name + " to CouchDB"
            Object.set_db(db)
            object = Object(
               title = name,
               text = currentRecord,
               tags = 'PhysioNet' 
            )
            #print "[" + currentRecord + "]" 
            id = object.save()
            print id
            name = ""
            currentRecord = "" 
         else:
            currentRecord += lines[i]
       

@login_required(redirect_field_name='next')
def index(request):
#   result = tasks.trainCRF.delay("exec something")   

#   while not result.ready():
#      print "waiting for task to finish"

#   print "task returned: " + str(result.result)

   return render_to_response('hide/index.html',{}, context_instance=RequestContext(request))
   
@login_required(redirect_field_name='next')
def delete(request,id):
    del db[id]
    return HttpResponseRedirect(u"/hide/")

def deidentifyblank(request):
   return deidentifyset(request, '')

@login_required(redirect_field_name='next')
def deidentifyset( request, tag ):
   if request.method == 'POST' or request.method == 'GET':
      try:
         print "De-identifying set " + tag 
         objects = db.view('tags/tags', keys=[tag])
         for obj in objects:
#           print "about to label " + str(obj)
            html = '<pre>' + obj['value']['text'] + '</pre>'
            repl = dict()
            print "Replacing " + str(REPLACEMENTS)
            print "title = " + obj['value']['title']
            clean, errors = tidy_document( html,
               options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
         #   f =open('/tmp/set.xml', 'w')
         #   f.write( "<dontuseme>" + html + "</dontuseme>" )
         #   f.close()
            deid = doReplacement( clean, REPLACEMENTS, repl )
            print "replaced " + str(repl)
            xhtml = deid
            spre = re.compile('<pre>', re.I)
            epre = re.compile('</pre>', re.I)
            xhtml = re.sub(spre, '', xhtml)
            xhtml = re.sub(epre, '', xhtml)

            doc = dict()
            doc['text'] = xhtml 
            doc['tags'] = tag + '-deid'
            doc['title'] = obj['value']['title']
            print "saving " + doc['title'] + ' ' + doc['tags']
            db.save_doc(doc)
         return HttpResponseRedirect( '/hide/train/' + tag + '-deid' )
      except:  
         error = str(sys.exc_info())
         print error
         return errorpage( request, error )
   else:
      return HttpResponseRedirect( '/hide/train/' + tag )
#      request.method = 'GET';
#      return train(request, tag)

@login_required(redirect_field_name='next')
def deidentify( request, id ):
    try:
       doc = db[id]
    except ResourceNotFound:
       raise Http404
    doc['id'] = id
    html = doc['text'].replace("<br>", "<br/>")

    repl = dict()
    print "Replacing " + str(REPLACEMENTS)
    deid = doReplacement( "<dontuseme>" + html + "</dontuseme>", REPLACEMENTS, repl )
    print "replaced " + str(repl)
    xhtml = deid
    spre = re.compile('<dontuseme>', re.I)
    epre = re.compile('</dontuseme>', re.I)
    xhtml = re.sub(spre, '', xhtml)
    xhtml = re.sub(epre, '', xhtml)
    doc['text'] = xhtml

    LEGEND = getLegendSpec( getTagsDict(html) );
   
    models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
    referer = ''
    if 'referer' in request.POST:
      referer = request.POST['referer']
    if not referer:
       referer = request.META.get('HTTP_REFERER')
    if not referer:
       referer = '/hide/'
    context = {
       'row':doc,
       'displaytags':LEGEND,
       'models':models,
       'referer':referer,
      }
    return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))
   
@login_required(redirect_field_name='next')
def delete_label ( request, tag ):
   objects = db.view('tags/tags')
   for obj in objects:
      if obj['key'] == tag:
         id = obj['id']
         print "deleting " + str(id)
         try:
            del db[id]
         except:
            print "error deleting " + id + " but continuing"

@login_required(redirect_field_name='next')
def evaluate( request ):
   print "called evaluate"
   if request.method == "GET":
      crfs = HIDE.getCRFNamesFromDir( CRFMODELDIR )
      fvs = HIDE.getFVNamesFromDir( CRFMODELDIR )
      return render_to_response('hide/evaluate_continue.html',
         {'crfs':crfs, 'fvs':fvs}, context_instance=RequestContext(request))
   else:
      #check to make sure that user specified both
      # model and test set
      if 'crf' in request.POST and 'fv' in request.POST:
         crf = request.POST['crf']
         fv = request.POST['fv']
         #read in the data and label it using HIDE
         f = open( CRFMODELDIR + "/" + fv, 'r' )
         mallet = f.read()
         f.close()
         print "running evaluation on " + fv + " with " + crf
         outfilename = CRFMODELDIR + "/" + request.POST['outfile']
         #outfilename = CRFMODELDIR + "/" + fv + ".results"
         results = HIDE.testModel(outfilename, CRFMODELDIR + "/" + crf, mallet)
         print "calculating accuracy"
         html = HIDEexperiment.calcAccuracyHTML(results)
         print "done calculating accuracy"
         context = {'accuracy':html}
         return render_to_response('hide/accuracy.html', context, context_instance=RequestContext(request))
      else:
         error = "the training and testing sets aren't specified."
         context = {'error':error}
         return render_to_response('hide/error.html', context, context_instance=RequestContext(request))

@login_required(redirect_field_name='next')
def accuracy ( request ):
   if request.method == "GET":
      resultnames = HIDE.getResultNamesFromDir( CRFMODELDIR )
      return render_to_response('hide/accuracy_continue.html',
        { 'results':resultnames }, context_instance=RequestContext(request))
   else:
      resultsfile = request.POST['resultsfile']
      f = open( CRFMODELDIR + "/" + resultsfile, 'r') 
      results = f.read()
      f.close()
      html = HIDEexperiment.calcAccuracyHTML(results)
      context = {'accuracy':html, 'title': "Accuracy of " + resultsfile }
      return render_to_response('hide/accuracy.html', context, context_instance=RequestContext(request))
      

@login_required(redirect_field_name='next')
def autolabelset( request, tag ):
   if request.method == 'POST':
      try:
         crffile = request.POST['crf']
         print "Autolabeling set " + tag + " with " + crffile
         objects = db.view('tags/tags', keys=[tag])
         for obj in objects:
#            print "about to label " + str(obj)
            html = obj['value']['text'].replace("<br>", "<br/>")
            model = CRFMODELDIR + crffile 
            if not os.path.exists(model):
               error = "You have not yet trained " + model + ". Please train and try again."
               context = {'error':error}
               return render_to_response('hide/error.html', context, context_instance=RequestContext(request))
            suite = HIDE.SGMLToSuite(html)
            features = addFeatures(suite)
            features += "\n";
            resultsmallet = labelMallet( model, features )
            sgml = FeaturesToSGML(resultsmallet)
            doc = dict()
            doc['text'] = sgml
            doc['tags'] = tag + '-new'
            doc['title'] = obj['value']['title']
            print "saving " + doc['title'] + ' ' + doc['tags']
            db.save_doc(doc)
         return HttpResponseRedirect( '/hide/train/' + tag + '-new' )
      except:  
         error = str(sys.exc_info())
         print error
         return errorpage( request, error )
   else:
      request.method = 'GET';
      return train(request, tag)

def errorpage( request, error ):
   context = {'error':error}
   return render_to_response('hide/error.html', context, context_instance=RequestContext(request))
   
@login_required(redirect_field_name='next')
def autolabel( request, id ):
   try:
      doc = db[id]
   except ResourceNotFound:
      raise Http404

   if request.method == "GET":
      #Display a list of the crf models to choose from
      context = HIDE.getCRFNamesFromDir( CRFMODELDIR )
      return render_to_response('hide/crfpicker.html', 
       {'crfs':context}, context_instance=RequestContext(request))   
   

   crffile = request.POST['crf']
   print "[" + crffile + "]"
   doc['id'] = id
   html = doc['text'].replace("<br>", "<br/>")
   
   model = CRFMODELDIR + crffile
   
   #TODO update this to allow the user to specify the CRF to use.
   if not os.path.exists(model):
      error = "You have not yet trained the AutoLabeler. Please train and try again."
      context = {'error':error}
      return render_to_response('hide/error.html', context, context_instance=RequestContext(request))

   #convert the xhtml into mallet
   suite = HIDE.SGMLToSuite(html)
#   suite = HIDE.MalletToSuite( mallet )
   features = addFeatures(suite)
   features += "\n";
   #print features
   resultsmallet = labelMallet( model, features )
   sgml = FeaturesToSGML(resultsmallet)
#   print "SGML = " + sgml
   doc['text'] = sgml
   LEGEND = getLegendSpec( getTagsDict(sgml) )
   models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
   referer = ''
   if 'referer' in request.POST:
     referer = request.POST['referer']
   if not referer:
      referer = request.META.get('HTTP_REFERER')
   if not referer:
      referer = '/hide/'
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models':models,
      'referer':referer,
   }
   return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))


def detail(request,id):
   if not request.user.is_authenticated():
      return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
   try:
      doc = db.get(id)
   except ResourceNotFound:
      raise Http404        
   if request.method =="POST":
      tagtext = request.POST['tagtext']
      #pull out the wrapped pre tags from the report text before saving
      res = re.compile(r'<pre>(.*)</pre>', (re.M | re.I | re.S))
      m = res.search(tagtext)
      if m:
         tagtext = m.group(1)

      doc['text'] = tagtext
      doc['tags'] = request.POST['newtags']
      db.save_doc(doc)
   doc['id'] = id
#      db[id] = doc #save the document to the db.
#      doc['id'] = id
#   tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
   LEGEND = getLegendSpec( getTagsDict(doc['text']) )
   models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
   referer = ''
   if 'referer' in request.POST:
      referer = request.POST['referer']
   if not referer:
      referer = request.META.get('HTTP_REFERER')
   if not referer:
      referer = '/hide/'
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models': models,
      'referer':referer,
      }
   return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))

def anondoc(request,id):
   if not request.user.is_authenticated():
      return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
   try:
      doc = deiddb[id]
   except ResourceNotFound:
      raise Http404        
   if request.method =="POST":
      doc['text'] = request.POST['tagtext']
      doc['tags'] = request.POST['newtags']
   deiddb[id] = doc
   doc['id'] = id
   #tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
   LEGEND = getLegendSpec( getTagsDict(doc['text']) )
   models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
   referer = ''
   if 'referer' in request.POST:
      referer = request.POST['referer']
   if not referer:
      referer = request.META.get('HTTP_REFERER')
   if not referer:
      referer = '/hide/'
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models':models,
      'referer':referer,
      }
   return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))

def trainblank(request):
   return train(request, '')

   
def train(request,tag):
   trainset = dict()
   count = 0
   message = ''
   if ( tag == '' ):
      message = "Please select a set from the left"
   else:
      objects = db.view('tags/tags', keys=[tag])
      for obj in objects:
         if obj['key'] == tag:
            obj['value']['labels'] = ", ".join(getTags(obj['value']['text']))
            trainset[obj['id']] = obj
      count = len(trainset) 
   
   tags = getalltags(db)
   models = HIDE.getCRFNamesFromDir( CRFMODELDIR )

   context = {
      'message': message,
      'objects':trainset,
      'tags': tags,
      'count': count,
      'path': 'train',
      'models': models,
      'tag' : tag
   }
   
   if ( request.method == "POST" ):
      features = ""
      print "computing features"
      for key, object in trainset.iteritems():
         html = object['value']['text'].replace("<br>", "<br/>")
#         mallettext = SGMLToMallet(html)
#         suite = HIDE.MalletToSuite( mallettext )
         suite = HIDE.SGMLToSuite( html )
         features += addFeatures(suite)

      #save the features to file for debugging purposes
      #TODO - set a debug option in the config file
      #convert the features into suite format
      print "writing features to disk"
      featurefile = CRFMODELDIR + tag + ".features"
      f = open( featurefile, 'w')
      f.write(features + "\n")
      f.close()
      print "done writing features to disk"
      

      if 'writetodisk' in request.POST:
         return render_to_response('hide/traincontinue.html', context, context_instance=RequestContext(request))

      model = CRFMODELDIR + tag + ".crf"
      print "about to do train"
      trainModel( model, features )
      
      return render_to_response('hide/traincomplete.html', context, context_instance=RequestContext(request))
   
   else:
       return render_to_response('hide/traincontinue.html', context, context_instance=RequestContext(request))
      
   
   

def anonymize(request, tag):
   objects = db.view('tags/tags')
   #build the context
   anonset = dict()
   for obj in objects:
      #print obj
      if obj['key'] == tag:
         #extra data from the text
         html = "<object>" + obj['value']['text'] + "</object>"
         #options = dict(output_xhtml=1, add_xml_decl=0, indent=1, tidy_mark=0)
         xhtml, errors = tidy_document( html,
            options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
         #TODO change this to read from the config file
         tagstoa = [ 'age', 'gender', 'name' ]
         extracted = extractTags(xhtml, tagstoa)
         vals = extracted.split('\t')
         
         #print extracted
         
         for i in range(0, len(vals)):
            #print "working on " + str(i)
            if tagstoa[i] == 'gender':
               obj['value'][tagstoa[i]] = fixgender(vals[i])
            else:
               obj['value'][tagstoa[i]] = vals[i]
         
         anonset[obj['id']] = obj
   
   context = {
      'objects':anonset,
      'tags':tag,
      }

   if ( request.method == "POST" ):
      print "about to do anonymization"
      #extract the values from all of the objects in the anonset
      tagstoa = [ 'age', 'gender' ]
      stringtoanon = ''
      # make an internal mapping so we know which document corresponds
      # to which row in the anonymized set
      docmap = dict()
      i = 0
      for key,object in anonset.iteritems():
      #   print key
      #   print object['value']['text']
         #tidy up the object html
         text = object['value']['text']
         html = "<object>" + text.replace("<br>", "<br/>") + "</object>"
         #print "tidying up\n" + html
         #options = dict(output_xhtml=1, add_xml_decl=0, indent=1, tidy_mark=0)
         document, errors = tidy_document( html,
            options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
         #print document
         #print errors

         xhtml = document
         i += 1
         stringtoanon += extractTags(xhtml, tagstoa).replace("\t",",") + "," + str(i) + "\n"
         #print stringtoanon
         docmap[key] = i

      #print "SENDING"
      #print stringtoanon
      #we can either write the string to file and call the program with the filename
      # or just work over a pipe.

      context['error'] = "anonymizing " + stringtoanon
      print "sending " + stringtoanon
      #make sure classpath is set.
      execme = "java edu.emory.mathcs.Main 2"
      #do the kanonymization over system call
      proc = subprocess.Popen(execme,
         shell=True,
         stdin=subprocess.PIPE,
         stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,
         )
      stdout_value, stderr_value = proc.communicate(stringtoanon)

      #print '\tpass through:', repr(stdout_value)
      #print '\tstderr:', repr(stderr_value)

      subvals = dict()
      
      anonlist = str(stdout_value).split('\n')
      #process the output
      for a in anonlist:
         vals = a.split(',')
         if ( len(vals) > 1 ):
            print "results = " + str(vals)
            values = dict()
            gender = fixgender(vals[1])
            values['age'] = vals[0]
            values['gender'] = gender
            subvals[vals[2]] = values         
      
      for key,object in anonset.iteritems():
         #sub values back into the original document
         # we have to map the key value back to the text location where the
         # value was extracted.
         keyid = str(docmap[key])
         #print key + " -> " + keyid
         repl = REPLACEMENTS.copy()
         repl['age'] = subvals[keyid]['age']
         repl['gender'] = subvals[keyid]['gender']
         text = object['value']['text']
         html = "<object>" + text.replace("<br>", "<br/>") + "</object>"
         sgml, errors = tidy_document( html,
            options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
         dorepl = dict()
         deid = doReplacement( sgml, repl, dorepl )
         #print deid
         # we should store the deid content now in the hide_deid database
         Object.set_db(deiddb)
         obj = Object(
           title = object['value']['title'],
           text = deid,
           tags = object['value']['tags']
         )
         obj.save()
         id = obj['_id']
         #print "SAVING as " + str(id)
         object['deidid'] = id
         object['value']['age'] = subvals[keyid]['age']
         object['value']['gender'] = subvals[keyid]['gender']
         object['value']['name'] = "***NAME***"
             
      context['error'] = re.sub( '\n', '<br/>', str(stdout_value))
      #print context
      
      #context['error'] = "anonymizing " + stringtoanon
      
      # modify the context to include the anonymized and regular views
      # of the object so we can show them side by side.
      # in the view if necessary
      return render_to_response('hide/anoncomplete.html', context, context_instance=RequestContext(request))
   else:
#   print "ADDING obj " + obj['id'] + " to anonset"
#   print json.dumps(obj['value'])
      return render_to_response('hide/anoncontinue.html', context, context_instance=RequestContext(request))


def fixgender( gender ):
   if ( gender == "[0-0]" or gender == "0" ):
      return "[F]"
   elif ( gender == "[1-1]" or gender == "1"):
      return "[M]"

   return "[F-M]"
   

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc


@login_required(redirect_field_name='next')
def anonymizelist( request ):
   tags = getalltags( db )
   context = {
      'tags':tags,
      'path':'anonymize',
      'message':'Select the set you would like to anonymize',
   }
   return render_to_response('hide/alltags.html', context, context_instance=RequestContext(request))

def trainsets( request ):
    tags = getalltags(db)
    context = {
        'tags':tags,
        'path':'train',
      'message':'Select the set you would like to train the AutoLabeler',
    }
    return render_to_response('hide/alltags.html', context, context_instance=RequestContext(request))
   
def labeldocs( request ):
   tags = getalltags(db)
   context = {
      'tags':tags,
      'path':'train',
      'message':'Select the set you would like to label',
      }
   return render_to_response('hide/alltags.html', context, context_instance=RequestContext(request))


def getalltags( db ):
   alltags = dict()
   items = db.view('tags/justtags', group=True)
   for item in items:
      alltags[item['key']] = 1 
   keys = alltags.keys()
   keys.sort()
   return keys

def getfolders( folder ):
   folders = []
   for fileName in os.listdir ( folder ):
      print "checking on " + folder + "/" + fileName
      if os.path.isdir( folder + "/" + fileName ):
         folders.append(fileName)
   return folders
 

def randomReport( request ):
   #this randomly generates a record for the hide system
   first_names = dict()
   last_names = dict()
   
   first_names[0] = ['Sarah', 'Michelle', 'Kelly', 'Mary', 'Gertrude']
   last_names[0] = ['Marshall', 'Smith', 'Jones']
   first_names[1] = ['John', 'Mike', 'Gary', 'Jim', 'Frank', 'Oscar']
   last_names[1] = ['Fox', 'Doe', 'Jackson']

   #age must be between 25 and 80
   age = random.randint(25,80)
   gender = random.randint(0,1)

   MRN = random.randint(1000,2000)

   first = random.randint(0,len(first_names[gender])-1)
   last = random.randint(0,len(last_names[gender])-1)

   genderstring = 'F'
   if gender == 1:
      genderstring = 'M'

   context = {
      'firstname' : first_names[gender][first],
      'lastname' : last_names[gender][last],
      'age' : age,
      'gender' : genderstring,
      'MRN' : MRN,
   }

   return render_to_response('hide/report.html', context, context_instance=RequestContext(request))

def editsettings( request ):
   hideconfigfilepath = getattr(settings,'HIDECONFIG', 'default')
   context = { 'filepath' : hideconfigfilepath }
   return render_to_response('hide/settings.html', context, context_instance=RequestContext(request))

