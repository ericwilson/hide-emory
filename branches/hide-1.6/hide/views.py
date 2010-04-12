# Create your views here.
from django.template import RequestContext
from django.http import Http404,HttpResponseRedirect,HttpResponse
from django.shortcuts import render_to_response
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from couchdbkit import *
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit.ext.django.loading import get_db
from restkit import BasicAuth
import datetime
import random
import simplejson as json
#from BeautifulSoup import BeautifulSoup
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

import tasks

from xml.sax import make_parser
from xml.sax.handler import ContentHandler 
from JSAXParser import ReportXMLHandler
from JSAXParser import i2b2XMLHandler





#first thing is to initialize the HIDE module from the config file
log = loadConfig(getattr(settings,'HIDECONFIG', 'default'))

HIDELIB = HIDE.HIDELIB
EMORYCRFLIB = HIDE.EMORYCRFLIB # getattr(settings, 'EMORYCRFLIB', '/tmp/')
CRFMODELDIR = HIDE.CRFMODELDIR # getattr(settings, 'CRF_MODEL_DIR', '/tmp/')
if not os.path.isdir(CRFMODELDIR):
   os.mkdir( CRFMODELDIR )

SERVER = Server(getattr(settings,'COUCHDB_SERVER','http://127.0.0.1:5984'))
COUCHUSER = getattr(settings, 'COUCHDB_USER', 'none')
if ( COUCHUSER != "none" ):
   COUCHPASSWD = getattr(settings, 'COUCHDB_PASS', 'none')
   SERVER.add_authorization(BasicAuth(COUCHUSER, COUCHPASSWD))

REPLACEMENTS = getReplacements()
LEGEND = dict()

print REPLACEMENTS
print log

try:
   db = SERVER.get_or_create_db('hide_objects')
   deiddb = SERVER.get_or_create_db('hide_deid')
   couch_schema = getattr(settings, 'COUCHDB_SCHEMA', 'error')
   print "Syncing schema " + couch_schema
   loader = FileSystemDocsLoader(couch_schema)
   loader.sync(db)
   print "done syncing schema"
except :
   print "Couldn't connect to couchdb"



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

   tags = utags.keys()
   
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
         newtext += xml.sax.saxutils.escape(tokens[i]) #text
         i += 1
         newtext += tokens[i] #end tag
      else: 
         newtext += xml.sax.saxutils.escape(tokens[i]) #just text
      i += 1
   return newtext

def buildXMLFromList( objects ):
   print "Building xml"
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

#this function handles an uploaded xml file. The xml should be of the form
#<records>
#<record>
#<pid>number</pid>
#<rid>number</rid>
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
          print "adding " + name + " to CouchDB"
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
    deid = doReplacement( "<object>" + html + "</object>", REPLACEMENTS, repl )
    print "replaced " + str(repl)
   
    doc['text'] = deid

    LEGEND = getLegendSpec( getTagsDict(html) );
   
    models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
    context = {
       'row':doc,
       'displaytags':LEGEND,
       'models':models,
      }
    return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))
   
@login_required(redirect_field_name='next')
def delete_label ( request, tag ):
   objects = db.view('tags/tags')
   for obj in objects:
      if obj['key'] == tag:
         id = obj['id']
         print "deleting " + str(id)
         del db[id]

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
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models':models,
   }
   return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))


def detail(request,id):
   if not request.user.is_authenticated():
      return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
   try:
      doc = db[id]
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
   db[id] = doc
   doc['id'] = id
#   tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
   LEGEND = getLegendSpec( getTagsDict(doc['text']) )
   models = HIDE.getCRFNamesFromDir( CRFMODELDIR )
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models': models,
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
   context = {
      'row':doc,
      'displaytags':LEGEND,
      'models':models,
      }
   return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))

def trainblank(request):
   return train(request, '')

   
def train(request,tag):
   trainset = dict()
   count = 0

   message = ''
   if ( tag == '' ):
      message = "Please select a set to label from the left"
   else:
      objects = db.view('tags/tags')
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
      execme = "java -cp \"" + HIDELIB + "\" edu.emory.mathcs.Main 2"
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
   items = db.view('tags/tags')
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
