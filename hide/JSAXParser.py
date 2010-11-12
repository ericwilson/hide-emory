from xml.sax import make_parser
from xml.sax.handler import ContentHandler

import re

import urllib

class SGMLToMalletHandler( ContentHandler ):

  def __init__ (self):
     self.lastTag = 'O'
     self.first = True
     self.mallet = ""

  def startElement(self, name, attrs):
     name = name.lower()
     if name != 'report':
       self.lastTag = name
       self.first = True
     return

  def endElement( self, name):
     self.lastTag = 'O'
     return

  def characters(self, ch):
     chars = re.split( '(\W)', ch )
     for c in chars:
        if c == '':
           continue
        c = urllib.quote(c)
        if self.lastTag != 'O':
          if self.first:
           self.mallet += "TERM_" + c + " " + "B-" + self.lastTag + "\n"
           self.first = False
          else:
           self.mallet += "TERM_" + c + " " + "I-" + self.lastTag + "\n"
        else:
          self.mallet += "TERM_" + c + " O\n"
     return


class SGMLToSuiteHandler( ContentHandler ):

  def __init__ (self):
     self.lastTag = 'O'
     self.first = True
     self.mallet = ""

  def startElement(self, name, attrs):
     name = name.lower()
     if name != 'report':
       self.lastTag = name
       self.first = True
     return

  def endElement( self, name):
     self.lastTag = 'O'
     return

  def characters(self, ch):
     chars = re.split( '(\W)', ch )
     for c in chars:
        if c == '':
           continue
        if c == u'\u2028':
           c = " "
        if c == u'\xaf':
           c = " "
        c = urllib.quote(c)
        print c
        if self.lastTag != 'O':
          if self.first:
           self.mallet += "B-" + self.lastTag + "\tTERM_" + c + "\n"
           self.first = False
          else:
           self.mallet += "I-" + self.lastTag + "\tTERM_" + c + "\n"
        else:
          self.mallet += "O\tTERM_" + c + "\n"
     return

class i2b2XMLHandler(ContentHandler):
 reports = dict()
 title = ""
 content = ""
 pid = -1
 rid = -1

 def __init__ (self):
    self.in_report = 0
    self.in_pid = 0
    self.in_rid = 0
    self.in_title = 0
    self.in_content = 0
    self.lastTag = ''

 def startElement(self, name, attrs):
    name = name.lower()
#    print "start " + name
    if name == 'record':
       self.in_report += 1
       self.title = "i2b2-" + attrs.get('ID',"")
    elif name == 'text':
       self.in_content += 1
       self.content = ''
    elif name == 'phi':
       self.lastTag = attrs.get('TYPE', "")
#       print "type = " + self.lastTag
       self.content += '<' + self.lastTag + '>'
    elif name != 'reports':
       self.content += '<' + name + '>'
    return

 def endElement(self, name):
    name = name.lower()
#    print "end " + name
    if name == 'record':
       self.in_report -= 1
    elif name == 'text':
       print "processing " + self.title
       if '-1' not in self.reports:
          self.reports['-1'] = dict()
       print "adding " + self.title + " to dict"
       self.reports['-1'][self.title] = self.content
       self.in_content -= 1
    elif name == 'phi':
       self.content += '</' + self.lastTag + '>'
    elif name != 'reports':
       self.content += '</' + name + '>'
    return
 
 def characters(self, ch):
    if self.in_content > 0:
    #   print ch
       self.content += ch
    elif self.in_pid == 1:
    #   print ch
       self.pid = ch
       self.reports[self.pid] = dict()
    elif self.in_rid == 1:
    #   print ch
       self.rid = ch
    elif self.in_title == 1:
       self.title = ch
   # else:
   #    print "Parsing error: " + ch
    return




class ReportXMLHandler(ContentHandler):
 reports = dict()
 content = ""
 pid = -1
 rid = -1

 def __init__ (self):
    self.in_report = 0
    self.in_pid = 0
    self.in_rid = 0
    self.in_title = 0
    self.in_content = 0

 def startElement(self, name, attrs):
    #print "start " + name
    if name == 'report':
       self.in_report += 1
    elif name == 'pid':
       self.in_pid += 1
    elif name == 'rid':
       self.in_rid += 1
    elif name == 'title':
       self.in_title += 1
       print "start title " + str(self.in_title)
    elif name == 'content':
       self.in_content += 1
       self.content = ''
    elif name != 'reports':
       self.content += '<' + name + '>'
    return

 def endElement(self, name):
    #print "end " + name
    if name == 'report':
       self.in_report -= 1
    elif name == 'pid':
       self.in_pid -= 1
    elif name == 'rid':
       self.in_rid -= 1
    elif name == 'title':
       self.in_title -= 1
       print "end title " + str(self.in_title)
    elif name == 'content':
       if self.pid != -1:
          self.reports[self.pid][self.rid] = self.content 
       else:
          print "processing " + self.title
          if '-1' not in self.reports:
             self.reports['-1'] = dict()
          self.reports['-1'][self.title] = self.content
       self.in_content -= 1
    elif name != 'reports':
       self.content += '</' + name + '>'
    return
 
 def characters(self, ch):
    if self.in_content > 0:
    #   print ch
       self.content += ch
    elif self.in_pid == 1:
    #   print ch
       self.pid = ch
       self.reports[self.pid] = dict()
    elif self.in_rid == 1:
    #   print ch
       self.rid = ch
    elif self.in_title == 1:
       print "in title"
       print ch
       self.title = ch
   # else:
   #    print "Parsing error: " + ch
    return


