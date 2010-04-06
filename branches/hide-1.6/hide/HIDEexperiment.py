import HIDE

import random
import copy
import sys
import os
import re

#takes an array a bunch of mallet formated reports and returns two 
#arrays corresponding to k-fold training and testing sets indexed from 0 to k-1.
def createKFold( marray, k ):
   #randomize the order of marray, create k folds, return the test and train sets
   print >> sys.stderr , "creating " + str(k) + "-fold data"
   trainset = [ "" for x in range(k) ]
   testset = [ "" for x in range(k) ]

   arraycopy = copy.copy(marray)
   random.shuffle(arraycopy)

   for i in range(len(arraycopy)): 
     #decide which k-fold to put it in put it in the mod k one of course
     testset[i % k] += arraycopy[i]
     for j in range(k):
        if ( j != (i % k) ):
           trainset[j] += arraycopy[i]
   return ( trainset, testset )

def writeKToDisk( dir, trainset, testset, k ):
   #make sure the dir is there
   if not os.path.exists(dir):
      os.makedirs(dir)
   for i in range(k):
      ftest = open( dir + "/test" + str(i) + ".features", 'w')
      ftest.write( testset[i] )
      ftest.close()
      ftrain = open( dir + "/train" + str(i) + ".features", 'w')
      ftrain.write( trainset[i] )
      ftrain.close()

def getKFoldInfoFromDisk( dir ):
   files = []
   if os.path.exists(dir):
      for fileName in os.listdir ( dir ):
         m = re.match('(.*).features$', fileName)
	 if m:
	    files.append(fileName)
   return [", ".join( files ), len(files) / 2]

def getModelInfoFromDisk( dir ):
   files = []
   if os.path.exists(dir):
      for fileName in os.listdir ( dir ):
         m = re.match('(.*).crf$', fileName)
	 if m:
	    files.append(fileName)
   return ", ".join( files )

#def getTestInfoFromDisk( dir ):
#   files = []
#   if os.path.exists(dir):
#      for fileName in os.listdir ( dir ):
#         m = re.match('(.*).results$', fileName)
#	 if m:
#	    files.append(fileName)
#   return ", ".join( files )

def readSetsFromDisk(dir):
   trainset = []
   testset = []
   if os.path.exists(dir):
      for fileName in os.listdir( dir ):
         testmatch = re.match('test(\d+).features$', fileName)
         trainmatch = re.match('train(\d+).features$', fileName)
         if testmatch:
	    f = open( dir + "/" + fileName, 'r')
	    val = f.read()
	    f.close()
            testset.append(val)
         elif trainmatch:
	    f = open( dir + "/" + fileName, 'r')
	    val = f.read()
	    f.close()
            trainset.append( val )

   return [trainset, testset, len(trainset)]

def runTrainOnDisk( outdir, trainset ):
   for i in range(len(trainset)):
      modelfile = outdir + "/train" + str(i) + ".crf"
      HIDE.trainModel( modelfile, trainset[i] )

def runTestOnDisk( outdir, testset ):
   for i in range(len(testset)):
      modelfile = outdir + "/train" + str(i) + ".crf"
      outfile = outdir + "/test" + str(i) + ".results"
      HIDE.testModel( outfile, modelfile, testset[i] )


def getTrainInfoFromDisk(dir):
   traininfo = []
   if os.path.exists(dir):
      for fileName in os.listdir( dir ):
         trainmatch = re.match('train(\d+).crf$', fileName)
         if trainmatch:
	    traininfo.append(fileName)
   return ", ".join(traininfo)

def getTestInfoFromDisk(dir):
   testinfo = []
   if os.path.exists(dir):
      for fileName in os.listdir( dir ):
         m = re.match('test(\d+).results$', fileName)
         if m:
	    testinfo.append(fileName)
   return ", ".join(testinfo)
   
def runKFoldTest( outdir, trainset, testset, k ):
   #train a classifier for each trainset and test against the
   # corresponding testset
   # returns the resulting mallet from the testsets
   print >> sys.stderr , "running test on " + str(k) + "-fold data"
   results = [ "" ] * k
   for i in range(k):
      ttext = trainset[i]
      modelfile = outdir + "/train" + str(i) + ".crf"
      f = open( outdir + "/train" + str(i) + ".features", 'w' )
      f.write(ttext)
      f.close()
      print >> sys.stderr , "creating classifier at " + modelfile
      HIDE.trainModel( modelfile, ttext )

   for i in range(k):
      ttext = testset[i]
      modelfile = outdir + "/train" + str(i) + ".crf"
      f = open( outdir + "/test" + str(i) + ".features", 'w' )
      f.write(ttext)
      f.close()
      results[i] = HIDE.labelMallet( modelfile, ttext )

   print >> sys.stderr, "done with runKFoldTest"
   return results

def calcAccuracyHTML( results ):
     correct = 0
     total = 0
     predicted = dict()
     classes = dict()
     lines = results.split("\n") 
     for l in lines:
        l = l.rstrip()
	if ( l == '' ):
	   continue
        vals = l.split(' ') 
        truel = vals[len(vals)-2]
        predl = vals[len(vals)-1]
        if ( (truel != 'O') or (predl != 'O') ):
           if truel not in classes:
              classes[truel] = dict()
              classes[truel]['PRED'] = dict()
              classes[truel]['CNT'] = 0
	   if predl not in classes[truel]['PRED']:
              classes[truel]['PRED'][predl] = 0
           total += 1
           classes[truel]['CNT'] += 1

           classes[truel]['PRED'][predl] += 1 
           if ( truel == predl ):
              correct += 1
              if ( predl not in predicted ):
                 predicted[predl] = 0
              predicted[predl] += 1

     print "acc: " + str(correct) + " / " + str(total)

     acc = float(correct) / float(total)
   
     html = ""
     html += "-- Accuracy: " + str(correct) + "/" + str(total) + " = " + str(acc) + "<br/>"
     html += "-- Confusion matrix and Per-class accuracy: Precision, Recall, F1<br/>"
     html += "<table>"
     html += "<tr><td>True\\Pred</td>"
     for c in sorted( classes.keys() ):
        html += "<td>" + c + "</td>"
  
     html += "<td>Total</td><td>Prec</td><td>Rec</td><td>F1</td>"
     html += "</tr>"
     for c in sorted( classes.keys() ):
        html += "<tr>"
        html += "<td>" + c + "</td>"
        tot = 0
        for p in sorted( classes.keys() ):
           if p in classes[c]['PRED']:
  	    tot += classes[c]['PRED'][p]
  	    if c == 'O' or p == 'O':
                 html += "<td>"+ str(classes[c]['PRED'][p]) + "(" + str(float(classes[c]['PRED'][p]) / classes[c]['CNT']) + ")</td>"
  	    else:
                 html += "<td>" + str(classes[c]['PRED'][p]) + "</td>"
  	   else:
  	    html += "<td>0</td>"
        html += "<td>" + str(tot) + "</td>"
        prec = 0
        rec = 0
        f1 = 0
  
        if c in predicted:
           prec = float(classes[c]['PRED'][c]) /  predicted[c]
           if ( classes[c]['CNT'] != 0 ):
              rec = float(classes[c]['PRED'][c]) / classes[c]['CNT']
           if ( prec + rec != 0 ):
              f1 = (2.0 * prec * rec) / ( prec + rec )
  
        html += "<td>" + str(prec) + "</td><td>" + str(rec) + "</td><td>" + str(f1) + "</td><td>" + c + "</td>"
  
     html += "</tr>"
     html += "<tr>"
     html += "<td>Total:</td>"
     sum = 0
     for c in sorted( classes.keys() ):
          if c in predicted:
             html += "<td>" + str(predicted[c]) + "</td>"
  	     sum += predicted[c]
  	  else:
  	     html += "<td>0</td>" 
     html += "<td>" + str(sum) + "</td>"
     html += "</tr>"
     html += "</table>"
     return html

def calcAccuracyHTMLFromDisk(outdir):
   testinfo = getTestInfoFromDisk(outdir)
   testinfoa = testinfo.split(', ')
   resultsets = []
   for t in testinfoa:
       f = open ( outdir + "/" + t, 'r' )
       text = f.read()
       f.close()
       resultsets.append(text)

   correct = 0
   total = 0
   predicted = dict()
   classes = dict()
   k = len(resultsets)
   for i in range(k):
     lines = resultsets[i].split("\n") 
     for l in lines:
        l = l.rstrip()
	if ( l == '' ):
	   continue
        vals = l.split(' ') 
        truel = vals[len(vals)-2]
        predl = vals[len(vals)-1]
        if ( (truel != 'O') or (predl != 'O') ):
           if truel not in classes:
              classes[truel] = dict()
              classes[truel]['PRED'] = dict()
              classes[truel]['CNT'] = 0
	   if predl not in classes[truel]['PRED']:
              classes[truel]['PRED'][predl] = 0
           total += 1
           classes[truel]['CNT'] += 1

           classes[truel]['PRED'][predl] += 1 
           if ( truel == predl ):
              correct += 1
              if ( predl not in predicted ):
                 predicted[predl] = 0
              predicted[predl] += 1

   print "k: " + str(k)
   print "acc: " + str(correct) + " / " + str(total)

   acc = float(correct) / float(total)
   
   html = ""
   html += "-- Accuracy: " + str(correct) + "/" + str(total) + " = " + str(acc) + "<br/>"
   html += "-- Confusion matrix and Per-class accuracy: Precision, Recall, F1<br/>"
   html += "<table>"
   html += "<tr><td>True\\Pred</td>"
   for c in sorted( classes.keys() ):
      html += "<td>" + c + "</td>"

   html += "<td>Total</td><td>Prec</td><td>Rec</td><td>F1</td>"
   html += "</tr>"
   for c in sorted( classes.keys() ):
      html += "<tr>"
      html += "<td>" + c + "</td>"
      tot = 0
      for p in sorted( classes.keys() ):
         if p in classes[c]['PRED']:
	    tot += classes[c]['PRED'][p]
	    if c == 'O' or p == 'O':
               html += "<td>"+ str(classes[c]['PRED'][p]) + "(" + str(float(classes[c]['PRED'][p]) / classes[c]['CNT']) + ")</td>"
	    else:
               html += "<td>" + str(classes[c]['PRED'][p]) + "</td>"
	 else:
	    html += "<td>0</td>"
      html += "<td>" + str(tot) + "</td>"
      prec = 0
      rec = 0
      f1 = 0

      if c in predicted:
         prec = float(classes[c]['PRED'][c]) /  predicted[c]
         if ( classes[c]['CNT'] != 0 ):
            rec = float(classes[c]['PRED'][c]) / classes[c]['CNT']
         if ( prec + rec != 0 ):
            f1 = (2.0 * prec * rec) / ( prec + rec )

      html += "<td>" + str(prec) + "</td><td>" + str(rec) + "</td><td>" + str(f1) + "</td><td>" + c + "</td>"

   html += "</tr>"
   html += "<tr>"
   html += "<td>Total:</td>"
   sum = 0
   for c in sorted( classes.keys() ):
        if c in predicted:
           html += "<td>" + str(predicted[c]) + "</td>"
	   sum += predicted[c]
	else:
	   html += "<td>0</td>" 
   html += "<td>" + str(sum) + "</td>"
   html += "</tr>"
   html += "</table>"
   return html
