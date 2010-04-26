"""This module provides functionality for importing data from caTIES/caTissue style databases into HIDE"""

import MySQLdb
import MySQLdb.cursors

sectionHeaderCodes = [
   "CDX", "FIN",
   "ANF", "DXC",
   "ANC", "MDT",
   "ANM", "GDT",
   "ANG", "SBD",
   "ADX", "ADC",
   "FRO", "PDX",
   "ANP", "PCM",
   "RPC", "PIN",
   "ORD", "PRC",
   "ODX", "CDI",
   "ANT", "ANT",
   "ANT"
]

sectionHeaders = [
   "[Clinical History]", "[Final Diagnosis]",
   "[Final Neuropathological Diagnosis]", "[Diagnosis Comment]",
   "[Neuro Diagnosis Comment]", "[Microscopic Description]",
   "[Microscopic Neuropathology]", "[Gross Description]",
   "[Gross Neuropathology]", "[Consult Material Description]",
   "[Intraoperative Diagnosis]", "[Provisional Diagnosis]",
   "[Neuro Provisional Diagnosis]", "[Provisional Comment]",
   "[Report Comments]", "[Interpretation]",
   "[Other Related Clinical Data]", "[Results]",
   "[Other Diagnoses]", "[Summary Discussion]",
   "[Part Information]", "[Addendum]",
   "[Addendum Comment]"
]

def getSectionName( code ):
   for i in range( len(sectionHeaderCodes) ):
      if sectionHeaderCodes[i] == code:
         return sectionHeaders[i]
   return ""

def buildReport( reportdict ):
   reporttext = ''
   for i in range( len(sectionHeaderCodes) ):
      for k,v in reportdict.items():
         if v['name'] == sectionHeaderCodes[i]:
            sectionname = getSectionName(v['name'])
            print sectionname
            reporttext += "\n" + sectionname + "\n" + v['document_fragment']

   return reporttext


def importcaTIESData( couchdb,h, u, p, d ):
   db=MySQLdb.connect(host=h, user=u, passwd=p, db=d, cursorclass=MySQLdb.cursors.DictCursor)

   c = db.cursor()

   q = "select ident_patient.id as patient_id, ident_patient.medical_record_number as patient_mrn, ident_patient.first_name as patient_firstname, ident_patient.last_name as patient_lastname, ident_patient.middle_name as patient_middlename, ident_patient.social_security_number as patient_ssn, ident_patient.gender as patient_gender, race as patient_race, ethnicity as patient_ethnicity, marital_status as patient_maritalstatus, ident_patient.org_id as patient_org, ident_path_report.id as report_id, ident_section.id as section_id, ident_section.name, ident_section.document_fragment from ident_patient, ident_path_report, ident_section where ident_section.path_report_id = ident_path_report.id and ident_path_report.patient_id = ident_patient.id"
   c.execute(q)

   docs = dict()

   row = c.fetchone()
   while row:
      reportid = row['report_id']
      sectionid = row['section_id']
      if reportid not in docs:
         docs[reportid] = dict()
      docs[reportid][sectionid] = row
#      print "FOUND: " + getSectionName( row['name'] )
      row = c.fetchone()


   #we have processed all of the hl7 sections and now we need to build the reports.

   for k,v in docs.items():
      print "report " + str(k) + " :"
      print buildReport( v )
   

#   import pprint
#   pp = pprint.PrettyPrinter(indent=4)
#   pp.pprint(docs)
