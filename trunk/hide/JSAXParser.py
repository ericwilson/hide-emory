from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class ReportXMLHandler(ContentHandler):
 reports = dict()
 content = ""
 def __init__ (self):
    self.in_report = 0
    self.in_pid = 0
    self.in_rid = 0
    self.in_content = 0

 def startElement(self, name, attrs):
    #print "start " + name
    if name == 'report':
       self.in_report += 1
    elif name == 'pid':
       self.in_pid += 1
    elif name == 'rid':
       self.in_rid += 1
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
    elif name == 'content':
       self.reports[self.pid][self.rid] = self.content 
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
   # else:
   #    print "Parsing error: " + ch
    return


