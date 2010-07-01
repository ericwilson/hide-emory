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
   trainset = [None]*k
   testset = [None]*k

   for z in xrange(k):
      trainset[z] = []
      testset[z] = []

   #arraycopy = copy.copy(marray)
   #random.shuffle(arraycopy)
   t = 0
   for i in random.sample( xrange( len(marray) ), len(marray) ):
      #for i in range(len(arraycopy)): 
      #decide which k-fold to put it in put it in the mod k one of course
      z = t%k
#      print "looking at " + str(z)
      testset[t%k].append(i)
#      print "we are adding " + str(i) + " to testset " + str(t % k)
      for j in xrange(k):
         if ( j != (t % k) ):
            if len(trainset[t%k]) == 0:
               trainset[t%k] = []
#            print "we are adding " + str(i) + " to trainset " + str(j)
            trainset[j].append(i)
      t += 1
   
#   for i in range(k):
#      print "testset " + str(i) + " = " + str(testset[i])
#      print "trainset " + str(i) + " = " + str(trainset[i])
   return ( trainset, testset )

def readFoldFileFromDisk( filename ):
   set = []
   f = open( filename, 'r')
   input = f.read()
   f.close()
   set = map( int, input.split('\n') )
   return set

def writeFoldFileToDisk( filename, set ):
   f = open( filename, 'w')
   f.write( "\n".join( map(str,set) ) )
   f.close()

def writeMalletSetToDisk( filename, set ):
   print "writing mallet to " + filename
   f = open( filename, 'w' )
   f.write( "-*-*-*-\n".join(set) )
   f.write( "\n" )
   f.close()

def readMalletSetFromDisk( filename ):
   f = open( filename, 'r' )
   input = f.read()
   f.close()

   set = input.split('-*-*-*-\n')
   return set


def writeKToDisk( dir, trainset, testset, k, ext ):
   #make sure the dir is there
   print >> sys.stderr, "writing to disk"
   if not os.path.exists(dir):
      os.makedirs(dir)
   for i in xrange(k):
      filename = dir + "/test" + str(i) + ext
      print >> sys.stderr, "writing " + filename+ " to disk"
 #     print "we have to split it up. and write it " + str(len(testset[i]))
      ftest = open( filename, 'w')
      ftest.write( testset[i] + "\n" )
      ftest.close()
      print >> sys.stderr, "done writing " + filename+ " to disk"
      filename = dir + "/train" + str(i) + ext
      print >> sys.stderr, "writing " + filename+ " to disk"
 #     print "we have to split it up. and write it " + str(len(trainset[i]))
      ftrain = open( dir + "/train" + str(i) + ext, 'w')
      ftrain.write( trainset[i] + "\n" )
      ftrain.close()
      print >> sys.stderr, "done writing " + filename+ " to disk"
   print >> sys.stderr, "done writing to disk"

def getSetInfoFromDisk(dir):
   files = []
   if os.path.exists(dir):
      for fileName in os.listdir ( dir ):
         m = re.match('ALL.mallet$', fileName)
         if m:
            files.append(fileName)
   return ", ".join( files )

def getFeaturesInfoFromDisk(dir):
   files = []
   if os.path.exists(dir):
      for fileName in os.listdir ( dir ):
         m = re.search('.features$', fileName)
         if m:
            files.append(fileName)
   return ", ".join( files )

def getKFoldInfoFromDisk( dir ):
   files = []
   if os.path.exists(dir):
      for fileName in os.listdir ( dir ):
         m = re.match('(.*).fold$', fileName)
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
#    if m:
#       files.append(fileName)
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
   for i in xrange(len(trainset)):
      modelfile = outdir + "/train" + str(i) + ".crf"
      HIDE.trainModel( modelfile, trainset[i] )

def runTestOnDisk( outdir, testset ):
   for i in xrange(len(testset)):
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

#def calcAccuracyHTML( results ):
#     correct = 0
#     total = 0
#     predicted = dict()
#     classes = dict()
#     lines = results.split("\n") 
#     for l in lines:
#         l = l.rstrip()
#         if ( l == '' ):
#            continue
#         vals = l.split(' ') 
#         truel = vals[len(vals)-2]
#         predl = vals[len(vals)-1]
#         if ( (truel != 'O') or (predl != 'O') ):
#            if truel not in classes:
#              classes[truel] = dict()
#              classes[truel]['PRED'] = dict()
#              classes[truel]['CNT'] = 0
#            if predl not in classes[truel]['PRED']:
#               classes[truel]['PRED'][predl] = 0
#            total += 1
#            classes[truel]['CNT'] += 1
#            classes[truel]['PRED'][predl] += 1 
#
#            if ( truel == predl ):
#              correct += 1
#              if ( predl not in predicted ):
#                 predicted[predl] = 0
#              predicted[predl] += 1
#
#     print "acc: " + str(correct) + " / " + str(total)
#
#     acc = float(correct) / float(total)
#   
#     html = ""
#     html += "-- Accuracy: " + str(correct) + "/" + str(total) + " = " + str(acc) + "<br/>"
#     html += "-- Confusion matrix and Per-class accuracy: Precision, Recall, F1<br/>"
#     html += "<table>"
#     html += "<tr><td>True\\Pred</td>"
#     for c in sorted( classes.keys() ):
#        html += "<td>" + c + "</td>"
#  
#     html += "<td>Total</td><td>Prec</td><td>Rec</td><td>F1</td>"
#     html += "</tr>"
#     for c in sorted( classes.keys() ):
#        html += "<tr>"
#        html += "<td>" + c + "</td>"
#        tot = 0
#        for p in sorted( classes.keys() ):
#           if p in classes[c]['PRED']:
#              tot += classes[c]['PRED'][p]
#           if c == 'O' or p == 'O':
#              html += "<td>"+ str(classes[c]['PRED'][p]) + "(" + str(float(classes[c]['PRED'][p]) / classes[c]['CNT']) + ")</td>"
#           else:
#              html += "<td>" + str(classes[c]['PRED'][p]) + "</td>"
#        else:
#            html += "<td>0</td>"
#            html += "<td>" + str(tot) + "</td>"
#
#            prec = 0
#            rec = 0
#            f1 = 0
#  
#        if c in predicted:
#           prec = float(classes[c]['PRED'][c]) /  classes[c]['CNT']
#           if ( classes[c]['CNT'] != 0 ):
#              rec = float(predicted[c]) / classes[c]['CNT']
#           if ( prec + rec != 0 ):
#              f1 = (2.0 * prec * rec) / ( prec + rec )
#  
#        html += "<td>" + str(prec) + "</td><td>" + str(rec) + "</td><td>" + str(f1) + "</td><td>" + c + "</td>"
#  
#     html += "</tr>"
#     html += "<tr>"
#     html += "<td>Total:</td>"
#     sum = 0
#     for c in sorted( classes.keys() ):
#          if c in predicted:
#             html += "<td>" + str(predicted[c]) + "</td>"
#          sum += predicted[c]
#       else:
#          html += "<td>0</td>" 
#     html += "<td>" + str(sum) + "</td>"
#     html += "</tr>"
#     html += "</table>"
#     return html

def calcAccuracyHTMLFromDisk(outdir):
   testinfo = getTestInfoFromDisk(outdir)
   testinfoa = testinfo.split(', ')
   resultsets = []

   print >> sys.stderr, "reading results from disk"
   for t in testinfoa:
       f = open ( outdir + "/" + t, 'r' )
       text = f.read()
       f.close()
       resultsets.append(text)
   print >> sys.stderr, "done reading results from disk"

   phicorrect = 0
   phiincorrect = 0
   phimissed = 0

   correct = 0
   total = 0
   stats = dict()
   k = len(resultsets)
   for i in range(k):
      lines = resultsets[i].split("\n") 
      for l in lines:
         l = l.rstrip()
         if ( l == '' ):
            continue
         vals = l.split("\t") 
         truel = vals[0]
         predl = vals[len(vals)-1]
         if ( (truel != 'O') or (predl != 'O') ):
            total += 1
            if ( truel == 'O' ):
               phiincorrect += 1
            elif ( predl == 'O' ):
               phimissed += 1
            else:
               phicorrect += 1
            if truel not in stats:
               stats[truel] = dict()
               stats[truel]['TP'] = 0
               stats[truel]['FP'] = 0
               stats[truel]['FN'] = 0
               stats[truel]['PRED'] = dict()

            if predl not in stats:
               stats[predl] = dict()
               stats[predl]['TP'] = 0
               stats[predl]['FP'] = 0
               stats[predl]['FN'] = 0
               stats[predl]['PRED'] = dict()

            if predl not in stats[truel]['PRED']:
               stats[truel]['PRED'][predl] = 0

            #store conf. matrix
            stats[truel]['PRED'][predl]+=1

            if ( truel == predl ):
               correct += 1
               stats[truel]['TP'] += 1
            else:
               stats[truel]['FN'] += 1
               stats[predl]['FP'] += 1

   print "k: " + str(k)
   print "acc: " + str(correct) + " / " + str(total)

   acc = float(correct) / float(total)

   phiprec = float(phicorrect) / float(total)
   phirec = float(total - phimissed) / float(total)
   phif1 = 0
   if ( phiprec + phirec != 0 ):
      phif1 = (2.0 * phiprec * phirec) / ( phiprec + phirec )


   
   html = ""
   html += "-- Accuracy: " + str(correct) + "/" + str(total) + " = " + str(acc) + "<br/>"
   html += "-- Phi. Prec: " + str(phiprec) + " Rec: " + str(phirec) + " F1: " + str(phif1) + "<br/>"
   html += "-- Confusion matrix and Per-class accuracy: Precision, Recall, F1<br/>"
   html += "<table>"
   html += "<tr><td>True\\Pred</td>"
   for c in sorted( stats.keys() ):
      html += "<td>" + c + "</td>"

   html += "<td>Total</td><td>Prec</td><td>Rec</td><td>F1</td>"
   html += "</tr>"
   for c in sorted( stats.keys() ):
      html += "<tr>"
      html += "<td>" + c + "</td>"
      tot = 0
      for p in sorted( stats.keys() ):
         if p in stats[c]['PRED']:
            tot += stats[c]['PRED'][p]
            html += "<td>"+ str(stats[c]['PRED'][p]) +"</td>"
         else:
            html += "<td>0</td>"
            
      html += "<td>" + str(tot) + "</td>"
      prec = 0
      rec = 0
      f1 = 0
      #print c + " TP: " + str(stats[c]['TP'])
      #print c + " FP: " + str(stats[c]['FP'])
      #print c + " FN: " + str(stats[c]['FN'])
      if ( stats[c]['TP'] + stats[c]['FP'] != 0 ):
         prec = float(stats[c]['TP']) /  float(stats[c]['TP'] + stats[c]['FP'])
      if ( stats[c]['TP'] + stats[c]['FN'] != 0  ):
         rec = float(stats[c]['TP']) / float(stats[c]['TP'] + stats[c]['FN'])
      if ( prec + rec != 0 ):
         f1 = (2.0 * prec * rec) / ( prec + rec )

      html += "<td>" + str(prec) + "</td><td>" + str(rec) + "</td><td>" + str(f1) + "</td><td>" + c + "</td>"
      html += "</tr>"
#   html += "<tr>"
#   html += "<td>Total:</td>"
#   sum = 0
#   for c in sorted( stats.keys() ):
#        if c in predicted:
#           html += "<td>" + str(predicted[c]) + "</td>"
#        sum += predicted[c]
#        else:
#      html += "<td>0</td>" 
#      html += "<td>" + str(sum) + "</td>"
#   html += "</tr>"
   html += "</table>"
   return html

def calcAccuracyHTML(results):
   phicorrect = 0
   phiincorrect = 0
   phimissed = 0

   correct = 0
   total = 0
   stats = dict()
   lines = results.split("\n") 
   for l in lines:
      l = l.strip()
      if ( l == '' ):
         continue
      vals = l.split("\t") 
      truel = vals[0]
      predl = vals[len(vals)-1]
      if ( (truel != 'O') or (predl != 'O') ):
         total += 1
         if ( truel == 'O' ):
            phiincorrect += 1
         elif ( predl == 'O' ):
            phimissed += 1
         else:
            phicorrect += 1
         if truel not in stats:
            stats[truel] = dict()
            stats[truel]['TP'] = 0
            stats[truel]['FP'] = 0
            stats[truel]['FN'] = 0
            stats[truel]['PRED'] = dict()

         if predl not in stats:
            stats[predl] = dict()
            stats[predl]['TP'] = 0
            stats[predl]['FP'] = 0
            stats[predl]['FN'] = 0
            stats[predl]['PRED'] = dict()

         if predl not in stats[truel]['PRED']:
            stats[truel]['PRED'][predl] = 0

         #store conf. matrix
         stats[truel]['PRED'][predl]+=1

         if ( truel == predl ):
            correct += 1
            stats[truel]['TP'] += 1
         else:
            stats[truel]['FN'] += 1
            stats[predl]['FP'] += 1
# unncomment this to include O in the precision and recall calculations.
#      else:
#         total += 1
#         phicorrect += 1

   print "acc: " + str(correct) + " / " + str(total)

   acc = float(correct) / float(total)

   phiprec = float(phicorrect) / float(total)
   phirec = float(total - phimissed) / float(total)
   phif1 = 0

   if ( phiprec + phirec != 0 ):
      phif1 = (2.0 * phiprec * phirec) / ( phiprec + phirec )
   
   #print "made it past the loop"
   html = ""
   html += "-- Accuracy: " + str(correct) + "/" + str(total) + " = " + str(acc) + "<br/>"
   html += "-- Phi. Prec: " + str(phiprec) + " Rec: " + str(phirec) + " F1: " + str(phif1) + "<br/>"
   html += "-- Confusion matrix and Per-class accuracy: Precision, Recall, F1<br/>"
   html += "<table>"
   html += "<tr><td>True\\Pred</td>"
   for c in sorted( stats.keys() ):
      html += "<td>" + c + "</td>"

   html += "<td>Total</td><td>Prec</td><td>Rec</td><td>F1</td>"
   html += "</tr>"
   for c in sorted( stats.keys() ):
      html += "<tr>"
      html += "<td>" + c + "</td>"
      tot = 0
      for p in sorted( stats.keys() ):
         if p in stats[c]['PRED']:
            tot += stats[c]['PRED'][p]
            html += "<td>"+ str(stats[c]['PRED'][p]) +"</td>"
         else:
            html += "<td>0</td>"
            
      html += "<td>" + str(tot) + "</td>"
      prec = 0
      rec = 0
      f1 = 0
      #print c + " TP: " + str(stats[c]['TP'])
      #print c + " FP: " + str(stats[c]['FP'])
      #print c + " FN: " + str(stats[c]['FN'])
      if ( stats[c]['TP'] + stats[c]['FP'] != 0 ):
         prec = float(stats[c]['TP']) /  float(stats[c]['TP'] + stats[c]['FP'])
      if ( stats[c]['TP'] + stats[c]['FN'] != 0  ):
         rec = float(stats[c]['TP']) / float(stats[c]['TP'] + stats[c]['FN'])
      if ( prec + rec != 0 ):
         f1 = (2.0 * prec * rec) / ( prec + rec )

      html += "<td>" + str(prec) + "</td><td>" + str(rec) + "</td><td>" + str(f1) + "</td><td>" + c + "</td>"
      html += "</tr>"
   html += "</table>"
   #print "made it past the html"
   return html

def contextSample( set, historySize, probkeep ):
   print >>sys.stderr, "building context sample"
   keep = dict()
   set = set.strip()
   fvs = set.split("\n")
   fvslen = len(fvs)
   res = re.compile('\\t')
   for i in xrange(fvslen):
      fvs[i] = fvs[i].strip()
      if fvs[i] == '':
         print >>sys.stderr, "warning we have an empty FV"
         continue
      features = res.split(fvs[i])
      label = features[0]
      if label == "O":
         #keep it with probablity probkeep
         r = random.random()
         if r < probkeep:
            keep[i] = 1
      else:
         #definitely keep it and keep history about it
         for l in xrange((i-historySize), min( [ fvslen, (i+historySize+1) ] )):
            keep[l] = 1
   
   #build sample for sampleset j
   set = []
   for k in sorted(keep.keys()):
      set.append(fvs[k])
   sampleset = "\n".join( set ) + "\n"
   return sampleset


def localSample ( trainset, k, historySize, probkeep ):
   sampleset = [None] * len(trainset)
   for j in xrange(len(trainset)):
      print "building " + str(j) + " training set"
      sampleset[j] = contextSample( trainset[j], historySize, probkeep ) 
   return sampleset
