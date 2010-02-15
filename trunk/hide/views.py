# Create your views here.
from django.template import RequestContext
from django.http import Http404,HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from couchdbkit import *
from restkit.httpc import BasicAuth
import datetime
import random
import simplejson as json
#import xml.dom.minidom
#from BeautifulSoup import BeautifulSoup
import re
import os
from HIDE import SGMLToMallet, MalletToSGML, extractTags,doReplacement, getLegend, getReplacements, loadConfig
from tidylib import tidy_document
import subprocess



class Object(Document):
	author = StringProperty()
	title = StringProperty()
	text = StringProperty()
	tags = StringProperty()

HIDELIB = getattr(settings,'HIDELIB', '/default/path/')
EMORYCRFLIB = getattr(settings, 'EMORYCRFLIB', '/tmp/')
CRFMODELDIR = getattr(settings, 'CRF_MODEL_DIR', '/tmp/')
if not os.path.isdir(CRFMODELDIR):
   os.mkdir( CRFMODELDIR )

SERVER = Server(getattr(settings,'COUCHDB_SERVER','http://127.0.0.1:5984'))
COUCHUSER = getattr(settings, 'COUCHDB_USER', 'none')
if ( COUCHUSER != "none" ):
   COUCHPASSWD = getattr(settings, 'COUCHDB_PASS', 'none')
   SERVER.add_authorization(BasicAuth(COUCHUSER, COUCHPASSWD))

HIDECONFIG = getattr(settings, 'HIDECONFIG', '/default/nothing.xml')

loadConfig( HIDECONFIG )
REPLACEMENTS = getReplacements()
LEGEND = getLegend()

print REPLACEMENTS
print LEGEND

db = SERVER.get_or_create_db('hide_objects')
deiddb = SERVER.get_or_create_db('hide_deid')



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
					item['value']['summary'] = item['value']['text'][0:100]
			context = {
				'rows' : list(items),
			}
		return render_to_response('hide/list.html',context, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect(u"/accounts/login/")

def add (request):
   if request.method == "POST":
#if the user specified an MIT file
      if 'mitfile' in request.POST:
         print "importing MIT file"
	 f = request.FILES['file']
	 handle_uploaded_mit_file(f)
      
      elif 'xmlfile' in request.POST:
         print "importing XML file"
	 f = request.FILES['file']
	 handle_uploaded_xml_file(f)
	
      else:
         print "we are just adding a manual document"
         Object.set_db(db)
         object = Object(
            title = request.POST['title'],
            text = request.POST['text'],
            tags = request.POST['tags']
         )
         id = object.save()
      return HttpResponseRedirect(u"/hide/list/")
   else:
      context = {}
      return render_to_response('hide/newdoc.html', context, context_instance=RequestContext(request))


#this function handles an uploaded xml file. The xml should be of the form
#<records>
#<record>
#<pid>number</pid>
#<rid>number</rid>
#<content>The Text of the Record here</content>
#</records>
from xml.sax import make_parser
from xml.sax.handler import ContentHandler 
from JSAXParser import ReportXMLHandler

def handle_uploaded_xml_file(f):
   print "parsing " + f.name
   parser = make_parser()
   curHandler = ReportXMLHandler()
   parser.setContentHandler(curHandler)
   parser.parse(f)
   reports = curHandler.reports
   #print reports
   for k,v in sorted(reports.iteritems()):
      for x,y in sorted(v.iteritems()):
         #create an object and put it in the couchdb
         print k + "." + x +"->",
	 print y
#   print reports.keys()
#   print reports.keys().sort()
#   print curHandler.content
   
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
	   # print "found record start at line " + str(i)
	    name = "MIT-rec-" + start.group(1) + "-" + start.group(2)
	   # print "Processing " + name
	    currentRecord = ""
	 elif end:
	  #  print "found end of record at line " + str(i)
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
	    
#      print chunk



@login_required(redirect_field_name='next')
def index(request):
	return render_to_response('hide/index.html',{}, context_instance=RequestContext(request))
	
def delete(request,id):
    if not request.user.is_authenticated():
	 return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
	
    del db[id]
    return HttpResponseRedirect(u"/hide/")

def deidentify( request, id ):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
	# read the non-deidentified data from the hide_objects table
	# we could then save the deidentified data into the hide_anon table
    try:
	    doc = db[id]
    except ResourceNotFound:
	    raise Http404
    doc['id'] = id
    html = doc['text'].replace("<br>", "<br/>")
#    repl = {'name' : "***NAME***", 
#	    'mrn' : "***MRN***",
#            'age' : "***AGE***",
#            'gender' : "***GENDER***",
#	    'date' : "***DATE***",
#	    'accountnum' : "***accountnum***",
#	    }


    
	
    deid = doReplacement( "<object>" + html + "</object>", REPLACEMENTS )
	
    doc['text'] = deid
	
#    tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
    context = {
	    'row':doc,
	    'displaytags':LEGEND,
		}
    return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))
	
def delete_label ( request, tag ):
   objects = db.view('tags/tags')
   for obj in objects:
      if obj['key'] == tag:
         id = obj['id']
         print "deleting " + str(id)
         del db[id]
   
	
def autolabel( request, id ):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(u"/accounts/login/?next=%s" % request.path)
	try:
		doc = db[id]
	except ResourceNotFound:
		raise Http404

	if request.method == "GET":
	   #Display a list of the crf models to choose from
	   context = []
	   for fileName in os.listdir ( CRFMODELDIR ):
	      if re.search('\.crf$', fileName):
	         context.append(fileName)
	   return render_to_response('hide/crfpicker.html', 
	    {'crfs':context}, context_instance=RequestContext(request))	
	

	crffile = request.POST['crf']
	print "[" + crffile + "]"
	doc['id'] = id
	html = doc['text'].replace("<br>", "<br/>")
	#xhtml, errors = tidy_document( html,
	#	options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
	#print "xhtml:" + xhtml
	
	#convert the xhtml into mallet
	mallet = SGMLToMallet(html)
	
	#print mallet
	
	#save into file
	tempfile = '/tmp/workfile'
	f = open(tempfile, 'w')
	f.write(mallet)
	f.close()
	
	HIDEADDFEATURES = HIDELIB + "/HIDE-addfeatures.pl"

	
	#add features to the mallet file
	proc = subprocess.Popen("perl " + HIDEADDFEATURES + " " + tempfile,
		shell=True,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		)
	stdout_value, stderr_value = proc.communicate()

	#print mallettext
	#print str(stdout_value)
	featurefile = tempfile + ".features"
	f = open( featurefile, 'w')
	f.write(str(stdout_value))
	f.close()

	maxmem = "5000M"
	emorycrf = EMORYCRFLIB + "emorycrf"
	malletdir = EMORYCRFLIB + "mallet"
	javaclasspath = emorycrf + ":" + malletdir + "/class/:" + malletdir + "/lib/mallet-deps.jar"
	javaargs = "-Xmx" + maxmem + " -cp \"" + javaclasspath   + "\""
	
	
	#TODO update this to allow the user to specify the CRF to use.
	model = CRFMODELDIR + crffile
	if not os.path.exists(model):
	   error = "You have not yet trained the AutoLabeler. Please train and try again."
	   
	   context = {'error':error}
	   return render_to_response('hide/error.html', context, context_instance=RequestContext(request))

	
	execme = "java " + javaargs + " EmoryCRF --model-file " + model + " " + featurefile
	print "execing " + execme
	
	
	#open up EmoryCRF
	proc = subprocess.Popen( execme,
			shell=True,
#			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			)
	stdout_value, stderr_value = proc.communicate()
	#read output from EmoryCRF
	
	resultlabels = str(stdout_value)
	#print "LABEL RESULTS " + resultlabels
	
	#build the mallet file from the resulting labels and the original mallet
	#mallet is the original
	#resultlabels are the labels
	rows = mallet.split("\n")
	labels = resultlabels.split("\n")
	
	#print "rows length: " + str(len(rows))
	#print "labels length: " + str(len(labels)) #emory crf prints one extra newline at the end. 
	
	resultsmallet = ""
	
	for i in range(0, len(rows)):
		r = rows[i]
		vals = r.split("\t")
		for v in vals:
			p = re.compile("TERM_(.*)")
			m = p.match(v)
			if ( m ):
				resultsmallet += m.group(0) + " " + labels[i] + "\n"
				break
			#print "[" + v + "]",
		#print ""

	#print resultsmallet
	sgml = MalletToSGML(resultsmallet)
	
	#print resultsmallet
	#print sgml
	
	
	doc['text'] = sgml
	
	#print "error: " + str(stderr_value)
	
	#convert mallet back into xhtml
	
	#set the value as the text of the object
	
	#display the object
#	tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
	context = {
		'row':doc,
		'displaytags':LEGEND,
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
		doc['text'] = request.POST['tagtext']
		doc['tags'] = request.POST['newtags']
	db[id] = doc
	doc['id'] = id
#	tags = {'name' : '#FFC21A', 'MRN':'#99CC00', 'age' : '#CC0033', 'date' : '#00CC99', 'accountnum' : '#FFF21A', 'gender' : '#3399FF'}
	context = {
		'row':doc,
		'displaytags':LEGEND,
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
	context = {
		'row':doc,
		'displaytags':LEGEND,
		}
	return render_to_response('hide/detail.html', context, context_instance=RequestContext(request))

	
def train(request,tag):
	objects = db.view('tags/tags')
	trainset = dict()
	for obj in objects:
		if obj['key'] == tag:
			trainset[obj['id']] = obj
	
	context = {
	   'objects':trainset,
	   'tags': tag,
	}
	
	
	if ( request.method == "POST" ):
		print "about to do train"
		mallettext = ""
		for key, object in trainset.iteritems():
		    # add each object into one mallet formatted file
			# first convert the sgml into mallet and save
			#convert the xhtml into mallet
			html = object['value']['text'].replace("<br>", "<br/>")
			#options = dict(output_xhtml=1, add_xml_decl=0, indent=1, tidy_mark=0)
			#xhtml, errors = tidy_document( html,
			#	options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
			mallettext += SGMLToMallet(html)
		
		HIDEADDFEATURES = HIDELIB + "/HIDE-addfeatures.pl"
		
		#write to the tmp dir
		tempfile = CRFMODELDIR + tag + ".out"
		f = open(tempfile, 'w')
		f.write(mallettext)
		f.close()
		
#		print mallettext
		
		#add features to the mallet file
		proc = subprocess.Popen("perl " + HIDEADDFEATURES + " " + tempfile,
			shell=True,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			)
		stdout_value, stderr_value = proc.communicate()

		#print mallettext
#		print stdout_value
		print str(stderr_value)
		featurefile = CRFMODELDIR + tag + ".features"
		f = open( featurefile, 'w')
		f.write(stdout_value)
		f.close()
		
		
		#train classifier
		maxmem = "5000M"
		emorycrf = EMORYCRFLIB + "emorycrf"
		malletdir = EMORYCRFLIB + "mallet"
		javaclasspath = emorycrf + ":" + malletdir + "/class/:" + malletdir + "/lib/mallet-deps.jar"
		javaargs = "-Xmx" + maxmem + " -cp \"" + javaclasspath   + "\""
		
		
		model = CRFMODELDIR + tag + ".crf"
		
		execme = "java " + javaargs + " EmoryCRF --fully-connected false --train true --model-file " + model + " " + featurefile + " 2> " + model + ".log"
		print "execing " + execme
		
		#train using EmoryCRF
		proc = subprocess.Popen( execme,
				shell=True,
	#			stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				)
		stdout_value, stderr_value = proc.communicate()

		#print stdout_value
		#print stderr_value
				
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
		#	print key
		#	print object['value']['text']
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
			repl = REPLACEMENTS
			repl['age'] = subvals[keyid]['age']
			repl['gender'] = subvals[keyid]['gender']
			text = object['value']['text']
			html = "<object>" + text.replace("<br>", "<br/>") + "</object>"
			sgml, errors = tidy_document( html,
				options={'numeric-entities':1, 'output-xml':1, 'add-xml-decl':0, 'input-xml':1})
			deid = doReplacement( sgml, repl )
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
#	print "ADDING obj " + obj['id'] + " to anonset"
#	print json.dumps(obj['value'])
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
def managesets( request ):
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

	
