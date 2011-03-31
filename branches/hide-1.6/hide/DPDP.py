#!/usr/bin/python

#This is the differentially private data publisher for HIDE
# this first iteration operates over tab separated files
# and generates count statistics for values of each column

import sys
import random
import math

#0 age: continuous.
#1 workclass: Private, Self-emp-not-inc, Self-emp-inc, Federal-gov, Local-gov, State-gov, Without-pay, Never-worked.
#2 fnlwgt: continuous.
#3 education: Bachelors, Some-college, 11th, HS-grad, Prof-school, Assoc-acdm, Assoc-voc, 9th, 7th-8th, 12th, Masters, 1st-4th, 10th, Doctorate, 5th-6th, Preschool.
#4 education-num: continuous.
#5 marital-status: Married-civ-spouse, Divorced, Never-married, Separated, Widowed, Married-spouse-absent, Married-AF-spouse.
#6 occupation: Tech-support, Craft-repair, Other-service, Sales, Exec-managerial, Prof-specialty, Handlers-cleaners, Machine-op-inspct, Adm-clerical, Farming-fishing, Transport-moving, Priv-house-serv, Protective-serv, Armed-Forces.
#7 relationship: Wife, Own-child, Husband, Not-in-family, Other-relative, Unmarried.
#8 race: White, Asian-Pac-Islander, Amer-Indian-Eskimo, Other, Black.
#9 sex: Female, Male.
#10 capital-gain: continuous.
#11 capital-loss: continuous.
#12 hours-per-week: continuous.
#13 native-country: United-States, Cambodia, England, Puerto-Rico, Canada, Germany, Outlying-US(Guam-USVI-etc), India, Japan, Greece, South, China, Cuba, Iran, Honduras, Philippines, Italy, Poland, Jamaica, Vietnam, Mexico, Portugal, Ireland, France, Dominican-Republic, Laos, Ecuador, Taiwan, Haiti, Columbia, Hungary, Guatemala, Nicaragua, Scotland, Thailand, Yugoslavia, El-Salvador, Trinadad&Tobago, Peru, Hong, Holand-Netherlands.

#DIMENSIONS = dict()
#DIMENSIONS['age'] = 0
#DIMENSIONS['fnlwgt'] = 2
#DIMENSIONS['education-num'] = 4
#DIMENSIONS['capital-gain'] = 10
#DIMENSIONS['capital-loss'] = 11
#DIMENSIONS['hours-per-week'] = 12

#DOMAIN = dict()
#DOMAIN['age'] = (0,130)
#DOMAIN['education-num'] = (0,16)
#DOMAIN['capital-gain'] = (0,1000000)
#DOMAIN['capital-loss'] = (0,1000000000)
#DOMAIN['hours-per-week'] = (0,140)

#DISCRETE = dict()
#DISCRETE['workclass'] = 1
#DISCRETE['education'] = 3
#DISCRETE['marital-status'] = 5
#DISCRETE['occupation'] = 6
#DISCRETE['race'] = 8
#DISCRETE['sex'] = 9
#DISCRETE['native-country'] = 13 


import numpy

class MaxGain:
   def __init__(self, g, i, j):
      self.gain = g
      self.dim = i
      self.offset = j

   def __str__(self):
      return str(self.gain) + " " + str(self.dim) + " " + str(self.offset)

#multi_for so we don't have to write nested for loops for each dimension
def multi_for(iterables):
     if not iterables:
         yield ()
     else:
         for item in iterables[0]:
             for rest_tuple in multi_for(iterables[1:]):
                 yield (item,) + rest_tuple


def buildValues( edges, permutation ):
   strs = list()
   for j in range(len(edges)):
      strs.append(str(edges[j][permutation[j]]))
   return ", ".join(strs)
      
def parseConfig( file ):
   f = open( file, 'r' )
   dims = dict()
   domains = dict()
   increment = dict()
   for line in f:
      l = line.rstrip()
      (name, index, low, high, inc) = l.split(" ")
      dims[name] = int(index)
      domains[name] = (int(low), int(high))
      increment[name] = int(inc)
   return (dims,domains, increment)

def dumpUsage():
   print "Usage: DPDP.py epsilon configfile datafile entropy_threshold infogain_threshold out_histogram out_private_histogram"
   print "- DPDP.py will construct an epsilon-differentially private multidimensional data cube of a given data file according to the parameters provided. All parameters are necessary.\n\tepsilon = differential privacy parameter. lower number means more privacy.\n\tconfigfile = path to file that contains information about how to process hte datafile\n\tdatafile = path to file that contains space seperated column data where each line represents the data for one patient. Each row should have the same numbers of columns and correspond to the information provided in the configfile.\n\tentropy_threshold = the level of randomness in a subcube at which the algorithm decides not to split the subcube. (this parameter should be determined experimentally.)\n\tinfogain_threshold = the amount of information_gain that is necessary for the algorithm to split a subcube.\n\tout_histogram = the datacube without any added noise (the non-private aggregated datacube).\n\tout_private_histogram = the differentially private version of the datacube."
   quit()

def myrange(count):
   v = list()
   for i in xrange(count+1):
      v.append(i)
   return v

def generateHistogram(data, DIMENSIONS, DOMAIN, INCREMENT):
   a = numpy.array(data)
   offsets = sorted(DIMENSIONS.keys())
   intervals = list()
   dimnames = list()
   for k in sorted(DIMENSIONS.keys()):
      interval = getBins(DOMAIN[k][0],DOMAIN[k][1], INCREMENT[k])
      intervals.append(interval)
      dimnames.append(k)

   (mhist, edges) = numpy.histogramdd(a, intervals) #, None, intervals)

   dims = list()
   for i in range(len(edges)):
      dims.append(len(edges[i])-1)

   originalHist = dict()
   for i in multi_for(map(xrange, dims)):
      val = mhist[i]
      originalHist[i] = val 

   return originalHist


def generateDPHistogram(data, epsilon, DIMENSIONS, DOMAIN, INCREMENT):
   a = numpy.array(data)
   offsets = sorted(DIMENSIONS.keys())
   intervals = list()
   dimnames = list()
   for k in sorted(DIMENSIONS.keys()):
      interval = getBins(DOMAIN[k][0],DOMAIN[k][1], INCREMENT[k])
      intervals.append(interval)
      dimnames.append(k)

   (mhist, edges) = numpy.histogramdd(a, intervals) #, None, intervals)

   dims = list()
   for i in range(len(edges)):
      dims.append(len(edges[i])-1)

   originalHist = dict()
   for i in multi_for(map(xrange, dims)):
      val = mhist[i]
      originalHist[i] = val 

   noisyHist = addNoiseToHistogram(originalHist, epsilon)
   return noisyHist

def generateDPDPHistogram(data, epsilon, entropythresh, infogainthresh, MIN_DATA_SPLIT, DIMENSIONS, DOMAIN, INCREMENT):
   a = numpy.array(data)
   offsets = sorted(DIMENSIONS.keys())
   intervals = list()
   dimnames = list()
   for k in sorted(DIMENSIONS.keys()):
      interval = getBins(DOMAIN[k][0],DOMAIN[k][1], INCREMENT[k])
      intervals.append(interval)
      dimnames.append(k)

   (mhist, edges) = numpy.histogramdd(a, intervals) #, None, intervals)

   dims = list()
   for i in range(len(edges)):
      dims.append(len(edges[i])-1)

   originalHist = dict()
   for i in multi_for(map(xrange, dims)):
      val = mhist[i]
      originalHist[i] = val 

   noisyHist = addNoiseToHistogram(originalHist, epsilon/2)
   totalNoisyCount = getTotalCount(noisyHist)
   totalCount = getTotalCount(originalHist)

   MIN_DATA = totalNoisyCount * MIN_DATA_SPLIT

   print "MIN_DATA_POINTS in cell to split = " + str(totalCount) + " " + str(totalNoisyCount) + " " + str(MIN_DATA)

   if ( MIN_DATA < 1):
      MIN_DATA = 1

   originaldims = list()
   for k in range(len(dims)):
      originaldims.append(xrange(dims[k]))

   fulldims = multi_for(originaldims)

   #make it so we don't run out of our iterator
   listdims = list()
   for k in fulldims:
      listdims.append(k)


   partitions = generatePartitionsForHistogram(noisyHist, listdims, dimnames, 
                     entropythresh, infogainthresh, MIN_DATA )
   #we now have the paritions generated from the noisy histogram.
   #now we get the real values from the original and add some laplace noise

   print "num partitions = " + str(len(partitions))
   releaseHist = generateReleaseHistogram(mhist, partitions, epsilon/2)

   return releaseHist



def main (argv):

   if (len(argv) != 8):
      dumpUsage()

   epsilon = float(argv[0])
   config = argv[1]

   (DIMENSIONS, DOMAIN, INCREMENT) = parseConfig(config)
   data = argv[2]
   entropyThreshold = float(argv[3])
   infoGainThreshold = float(argv[4])
   MIN_DATA_SPLIT = float(argv[5])
   originalFilename = argv[6]
   noisyFilename = argv[7]
   matrix = process(data, DIMENSIONS)

   histogram = generateHistogram(matrix, DIMENSIONS, DOMAIN, INCREMENT)
   nhistogram = generateDPHistogram(matrix, epsilon, DIMENSIONS, DOMAIN, INCREMENT)
   nhistogram2 = generateDPHistogram(matrix, epsilon/2, DIMENSIONS, DOMAIN, INCREMENT)
   phistogram = generateDPDPHistogram(matrix, epsilon, entropyThreshold, infoGainThreshold, MIN_DATA_SPLIT, DIMENSIONS, DOMAIN, INCREMENT)


   numcells = len(histogram)
   error = calculateL1Error( histogram, nhistogram )
   perror = calculateL1Error( histogram, phistogram )
   error2 = calculateL1Error( histogram, nhistogram2 )

   avgerr = error/numcells
   avgerr2 = error2/numcells
   pavgerr = perror/numcells

   print "****"
   print "num data points = " + str(len(matrix))
   print "privacy parameter epsilon = " + str(epsilon)

   print "histogram num cells = " + str(numcells)
   print "histogram L1 error before partitions = " + str(error)
   print "avg error per cell before partitions = " + str(avgerr)
   print "histogram L1 error 2 = " + str(error2)
   print "avg error per cell 2 = " + str(avgerr2)
   print "histogram L1 error after partitions = " + str(perror)
   print "avg error per cell after partitions = " + str(pavgerr)
   print "****"

   #(DIMENSIONS, DOMAIN, INCREMENT) = parseConfig(argv[1])
   saveHistogram(phistogram, noisyFilename, DIMENSIONS, DOMAIN, INCREMENT)
   saveHistogram(histogram, originalFilename, DIMENSIONS, DOMAIN, INCREMENT)
#   saveHistogram(originalHist, originalFilename)
   quit()

def calculateL1Error( originalHist, noisyHist ):
   error = 0
   for i in originalHist:
      val = originalHist[i]
      noisyCount = noisyHist[i]
      error += abs(noisyCount - val)
   return error

def getTotalCount( hist ):
   count = 0
   for k in hist:
      count += hist[k]
   return count

def addNoiseToHistogram(originalHist, epsilon):
   noisyHist = dict()
   for i in originalHist:
      val = originalHist[i]
      noisyCount = max(int(val + laplace( 1 / epsilon )),0)
      noisyHist[i] = noisyCount
   return noisyHist
   

def generateReleaseHistogram(mhist, partitions, epsilon):
   releaseHist = dict()
   for p in partitions:
      trueCount = 0
      fakeCount = 0
      for cell in p:
         trueCount += mhist[cell]
         fakeCount += p[cell]
      noisyCount = max(0, int(trueCount + laplace( 1 / epsilon )))
      cellSize = len(p)
      for cell in p:
         releaseHist[cell] = int(noisyCount/cellSize)
   return releaseHist


def getD( i, dim ):
   for k in dim:
      if dim[k] == i:
         return k
   return ""

def writeRanges( f,interval, dim, dom, inc ):
   print "interval = " + str(interval)
   f.write("(")
   i = 0
   for k in range(len(interval)):
      d = getD(k, dim)
      val = interval[k]
   #   print dim
   #   print d
   #   print "val = " + str(val)
      if d in dom:
         (min, max) = dom[d]
         h = inc[d]
         #print "min = " + str(min)
         #print "max = " + str(max)
         #print "inc = " + str(h)
         start = val * h + min
         end = (val+1) * h + min
         if ( i != 0 ):
            f.write(";")
         f.write("[" + str(start) + "," + str(end) +"]")
      i += 1
   f.write(")")


def saveHistogram( hist, filename, dim, dom, inc ):
   f = open( filename, 'w' )
   for key in sorted(hist.keys()):
   #   writeRanges(f, key, dim, dom, inc)
#      f.write(str(intervals[key[0]]) + " ")
      f.write(str(key) + "\t" + str(hist[key]) + "\n")
   f.close()
   
   
def loadHistogram( filename ):
   f = open( filename, 'r' )
   hist = dict()
   for line in f:
      clean = line.rstrip()
      (key, value) = clean.split("\t")
      hist[key] = value
   f.close()
   return hist
   

def pretty( hist ):
   for k in sorted(hist.keys()):
      print str(k) + " -> " + str(hist[k])

def printHistogram( hist, edges,dims, dimnames ):
   for i in multi_for(map(xrange, dims)):
      val = hist[i]
      print "(" + ", ".join(dimnames) + ") = (" + buildValues(edges,i) + ") -> " + str(val)

def generatePartitionsForHistogram( hist, dims, dimnames, et, infogain, MIN_DATA ):
   partitions = list()
   (lHist, rHist) = splitHistogramOnMaxGain( hist, dims, dimnames, et, infogain )
   #TODO - modify this to not split when size is below a certain threshold
   # not just 0.
   if ( len(lHist) >= MIN_DATA or len(rHist) >= MIN_DATA ):
#      print "size info : " + str(len(hist)) + " l = " + str(len(lHist)) + " r = " + str(len(rHist))
      for k in generatePartitionsForHistogram(lHist, getDims(lHist), dimnames, et, infogain, MIN_DATA):
         partitions.append(k)
      for k in generatePartitionsForHistogram(rHist, getDims(rHist), dimnames, et, infogain, MIN_DATA):
         partitions.append(k)
   else:
      partitions.append( hist )
   return partitions

def getDims( hist ):
   return hist.keys()

def splitHistogramOnMaxGain( hist, dims, dimnames, ENTROPY_THRESHOLD, MIN_INFO_GAIN ):
   #figure out which dimension and value gives the max info gain
   cMaxGain = getHistogramMaxGain(hist, dims, dimnames)

   #so lets split thie histogram on the dimension and index indicated
   # by cMaxGain

   lhist = dict()
   rhist = dict()
   
   #print "length = " + str(len(hist))
   entropy = computeEntropy(hist,dims)
   e = - math.log(float(1)/len(hist),2) 
   print "entropy = " + str(entropy)
   print "max_entropy = " + str(e)
   if ( e == 0 ):
      entropy = 1
   else:
      entropy /= e
   print "norm = " + str(e)
   #print "entropy norm = " + str(entropy)
   if ( cMaxGain.gain < MIN_INFO_GAIN or entropy > ENTROPY_THRESHOLD  ):
      return (lhist,rhist)

   for d in dims:
      if ( d[cMaxGain.dim] <= cMaxGain.offset ):
         lhist[d] = hist[d]
      else:
         rhist[d] = hist[d]
   return (lhist, rhist)

#generate the partitions
def generatePartitions( mdhist ):
   partitions = list()
   (lHist, rHist) = splitOnMaxGain( mdhist )
   if ( lHist != 0 ):
      for k in generatePartitions(lHist):
         partitions.append(k)
      for k in generatePartitions(rHist):
         partitions.append(k)
   else:
      partitions.append( mdhist )

   return partitions


#query the histogram
#TODO figure out how to get the counts for attributes dependent on other attributes.
# Right now I can only think of pulling from the original matrix but that seems like overkill
# Think of ways to efficently compute the new cubes.
def splitOnMaxGain( mdhist ):
   #find max gain split point for mdhist and return the two subcubes
   max = MaxGain(0,0) 
   maxDim = ""
   for k in sorted (mdhist.histogram.keys()):
      hist = mdhist.histogram[k]
      cMaxGain = getMaxGain(hist)
      if ( cMaxGain.gain > max.gain ):
         max = cMaxGain
         maxDim = k

   if ( max.gain < MIN_INFO_GAIN ):
      print "reached the bottom"
      return ( 0 , 0 )

   print "splitting on " + maxDim + " with gain " + str(max)
   #we build a left and right multidim histogram
   leftH = dict()
   rightH = dict()
   
   for k in sorted ( mdhist.histogram.keys() ):
      #loop over the intervals in histogram
      leftH[k] = dict()
      rightH[k] = dict()
      for interval in mdhist.histogram[k]:
         if ( (interval.low <= max.interval.low) and (interval not in leftH[k]) ):
            leftH[k][interval] = list()
         elif ( interval not in rightH[k] ):
            rightH[k][interval] = list()
         #loop over the points in the interval
         for p in mdhist.histogram[k][interval]:
#            print "comparing " + str(p.vals[maxDim]) + " to " + str(max.interval.low)
           if ( maxDim in p.vals ):
            if ( float(p.vals[maxDim]) <= max.interval.low ):
#               print "adding to left"
               if (interval not in leftH[k]):
                  leftH[k][interval] = list()
               leftH[k][interval].append(p)
            else:
#               print "adding to right"
               if (interval not in rightH[k]):
                  rightH[k][interval] = list()
               rightH[k][interval].append(p)
           else:
            #randomly put it in either left or right
            print "randomly assigning point " + str(p) + " because it doesn't really belong in this interval"
            if ( random.uniform(0,1) < .5 ):
               if (interval not in leftH[k]):
                  leftH[k][interval] = list()
               leftH[k][interval].append(p)
            else:
               if (interval not in rightH[k]):
                  rightH[k][interval] = list()
               rightH[k][interval].append(p)

   if ( len(leftH) < 1 or len(rightH) < 1 ):
      return (0,0)

   return( MultiDimHistogram(leftH), MultiDimHistogram(rightH) )
   

def buildMultiDimHistogram(matrix, DIMENSIONS, DOMAIN):
   mdhist = dict()
   intervals = dict()
   for dim in sorted(DIMENSIONS.keys()):
      column = DIMENSIONS[dim]
      intervals[dim] = getIntervals(DOMAIN[dim][0], DOMAIN[dim][1])
      dhist = getHistogram( matrix, DIMENSIONS[dim], intervals[dim]) 
      mdhist[dim] = dhist
   return mdhist


def buildMultiDimNoisyHistogram(matrix, DIMENSIONS, DOMAIN, epsilon):
   mdhist = dict()
   intervals = dict()
   for dim in sorted(DIMENSIONS.keys()):
      column = DIMENSIONS[dim]
      intervals[dim] = getIntervals(DOMAIN[dim][0], DOMAIN[dim][1])
      dhist = getHistogram( matrix, DIMENSIONS[dim], intervals[dim]) 
      mdhist[dim] = dhist
   #we now have cubes on each attribute.
   #now we have to this nasty join to create the cell partitions.

   nhist = getNoisyHistogram( dhist, epsilon, dim )
   return mdhist
   

   

#def buildMultiDimNoisyHistogram():

def generateLoop( dimValue, i, dims ):
   loop = list()
   for j in multi_for(map(xrange, dims)):
#      print j
      blah = list(j)
      #print blah
      #print "inserting " + str(i) + " " + str(dimValue)
      blah.insert(i, dimValue)
      #print blah
      loop.append(tuple(blah))
   return loop

def getHistogramCount(hist, loop):
   count = 0
   for i in loop:
      count += hist[i]
   return count

#loop encodes the dimension
def computeEntropy( hist, dims):
   #print "computing entropy"
   prob = dict()
   total = 0
   keep = list()
   for loop in dims:
#      print "loop = " + str(loop)
      total += hist[loop]
      keep.append(loop)

   #print "total count = " + str(total)
   #we now have the counts for each and we can calulate the probabilities for each value x \in X
   # and we can calculate the entropy H(X) = - \sum_i=1^n p(x_i) * log_b(p(x_i))

   ent = 0.0
   if ( total > 0 ):
      for i in keep:
   #      print "computing prob for i " + str(i)
         prob[i] = float( hist[i] ) / total 
   #      print "p(" + str(i) + ") = " + str(prob[i])

         if ( prob[i] > 0 ):
            ent += prob[i] * math.log(prob[i], 2)
   #      print "ent = " + str(ent)

      ent = -ent
   else:
      ent = 100000
   return ent
   

#how do we compute the entropy in a multidimensional fashion
# 1.) compute the entropy along each dimension.


def informationGainHistogram( hist, dims, dim, splitpoint, e):
   #e is the entropy of the encompassing histogram
   ldims = list()
   rdims = list()

   #TODO - this is super slow - is there a better way to do this?
   for d in dims:
      if ( d[dim] <= splitpoint ):
         ldims.append(d)
      else:
         rdims.append(d)
   #L = multi_for(ldims)
   #R = multi_for(rdims)
   #print "L = " + str(L)
   e1 = computeEntropy(hist, ldims)
   e2 = computeEntropy(hist, rdims)
   ig = e1 + e2 - e
#   print "computing informationGain dim = " + str(dim) + " " + str(splitpoint)
#   print "IG = " + str(ig) + " " + str(splitpoint)
   return ig
   
   
def getHistogramMaxGain( hist, dims, dimnames ):
#   print "Computing max gain for histogram"
   maxGain = -1
   maxDim = -1;
   maxValIndex = -1;

   originaldims = list()

   numdims = 0
   dimMinMap = dict()
   dimMaxMap = dict()

   for k in dims:
#      print "blah " + str(k)
      originaldims.append(k)
      if (numdims < len(k)):
         numdims = len(k)
      for i in xrange(len(k)):
         if i not in dimMinMap:
            dimMinMap[i] = k[i]
         if i not in dimMaxMap:
            dimMaxMap[i] = k[i]
         if ( k[i] > dimMaxMap[i] ):
            dimMaxMap[i] = k[i]
         if ( k[i] < dimMinMap[i] ):
            dimMinMap[i] = k[i]

   #entropy of full histogram
#   fulldims = multi_for(originaldims)
   e = computeEntropy(hist,originaldims)


   #loop over the dims and split points
   for dim in xrange(numdims):
#      print "dim = " + str(dim)
      for splitpoint in xrange(dimMinMap[dim], dimMaxMap[dim]):
#         print "dim = " + str(dim) + " splitpoint = " + str(splitpoint)
         ig = informationGainHistogram( hist, originaldims, dim, splitpoint, e)
         if ( ig > maxGain ):
#            print "found new max gain split point " + str(ig) + " " + str(dim) + " " + str(splitpoint)
            maxGain = ig
            maxDim = dim 
            maxValIndex = splitpoint

   return MaxGain( maxGain, maxDim, maxValIndex )

   for cell in originaldims:
      print "cell = " + str(cell)
      print str(len(i))
      blah = dims[i]
      del dims[i]
      totalcount = 0
      for k in range(blah):
        # loop = generateLoop( k, i, dims )
         #loop is an array of indexes into the histogram based on keeping
         # i static
#         count = getHistogramCount(hist, loop)
#         if ( count < 1 ):
#            continue
#         print "count for " + str(i) + " = " + str(k) + " " + str(count)
         #get the information gain at this split point

         ig = informationGainHistogram( hist, originaldims, i, k, e)
         if ( ig > maxGain ):
            print "found new max gain split point " + str(ig) + " " + str(i) + " " + str(k)
            maxGain = ig
            maxDim = i
            maxValIndex = k
      dims.insert(i,blah)
      #print "total count for " + dimnames[i] + " = " + str(totalcount)
   return MaxGain( maxGain, maxDim, maxValIndex )


def process( file, DIMENSIONS ):
   values = list()
   f = open( file, 'r' )
   for line in f:
      l = line.rstrip()
      vals = l.split("\t")
      keep = list()
      for k in sorted(DIMENSIONS.keys(), key=lambda blah: float(DIMENSIONS[blah])):
         keep.append(float(vals[DIMENSIONS[k]]))
      values.append(keep)
   return values

def getCount( matrix, column, value ):
   count = 0
   for row in matrix:
      val = row[column]
      if ( val == value ):
         count = count + 1
   return count

#this gets the intervals over a continuous value
# the choices of number of intervals can be sqrt(k) where k is the number of values
# or max - min / h where h is the desired width for the histogram
# for now we use width of 1

def getBins ( min , max, inc ):
   #calculated max and min
#   print str(max) + " " + str(min)
   intervals = list()
#   h = math.ceil( (max-min) / 100 )
   h = inc
   if ( h < 1 ):
      h = 1

   bins = int(math.ceil(float(max - min) / h))

   for i in range(0,bins):
#      interval = Interval(i * h + min, (i+1)*h + min)
      start = i * h + min
      end = (i+1) * h + min
      #interval = [start, end]
      #if ( end > max ):
      #   end = max
      intervals.append( end )

   intervals.append(max+0.000000001)

#   print intervals
   return intervals


def getIntervals( min, max ):
   #calculated max and min
#   print str(max) + " " + str(min)
   intervals = list()

   h = math.ceil( (max-min) / 100 )

   if ( h < 1 ):
      h = 1

   bins = int(math.ceil((max - min) / h))
   #print "creating " + str(bins) + " bins"
   #print "min = " + str(min) + " max = " + str(max)

   for i in range(0,bins):
#      interval = Interval(i * h + min, (i+1)*h + min)
      interval = [i * h + min, (i+1)*h + min]
      intervals.append(interval)

   return intervals
   
#getIntervals violates privacy
#modify this to either do diff private query or
# use static domain size information.
#def getIntervals( matrix, column ):

def getNoisyHistogram ( histogram, epsilon, dim ):
   noisyH = dict()
   error = 0
   for h in histogram.keys():
      count = len(histogram[h])
      noisyCount = max(0, int(count + laplace( 1 / epsilon )))
      err = int(noisyCount - count)
      error += err
      #take the points in the histogram and add them to noisyH.
      #randomly select err numbers of points in histogram[h] and add to noisyH[h]
      #                                                     or remove from noisyH
      noisyH[h] = list()

      newList = list()
      for b in histogram[h]:
         newList.append(b)
      while ( err > 0 ):
         err -= 1
         #generate a random value in the histogram with values between the range.
         pointvals = dict()
         pointvals[dim] = random.uniform( h.low, h.high ) #we need the domain and a value within the interval
         newList.append(Point(pointvals))

      if ( err < 0 ):
         #shuffle the list and select the first noisyCount
         random.shuffle(newList)

      print "err = " + str(err)
      print "noisyCount = " + str(noisyCount)
      print "real Count = " + str(count)

      print "len of newList = " + str(len(newList))
         
      for i in range(0, noisyCount):
         noisyH[h].append(newList[i])

   print "Total error = " + str(error)
   return noisyH

def getHistogramDiscrete(matrix, column):
   count = dict()
   for row in matrix:
      val = row[column]
      if ( not val in count ):
         count[val] = 0
      count[val] += 1

   return count

def getHistogram( matrix, column, intervals ):
   hist = dict()
   for row in matrix:
      val = float(row[column])
      for interval in intervals:
         if ( interval not in hist ):
            hist[interval] = list()
         #print str(interval)
         if ( interval.inInterval(val) ):
            pvals = dict()
            for d in DIMENSIONS:
               pvals[d] = row[DIMENSIONS[d]]
            hist[interval].append(Point(pvals))
   return hist





#this works over a single dimension histogram
#TODO - get this to work on multi-dimensions
#   just change the histogram to be a multilevel dictionary one for each dimension
def informationGain ( histogram, splitpoint ):
   #the information gain is the sum of the entropies of each partition subtracted
   # from the entropy of the one big partition

   e = compute_entropy(histogram)

   #build histograms
   h1 = dict()
   h2 = dict()

   #send the ones in the splitpoint to m1 all others go to m2
   for row in histogram:
      if ( row.low <= splitpoint.low ):
         h1[row] = histogram[row]
      else:
         h2[row] = histogram[row]

   e1 = compute_entropy(h1)
   #print "original = " + str(e)
   #print "left = " + str(e1)
   e2 = compute_entropy(h2)
   #print "right = " + str(e2)

   ig = e1 + e2 - e
   #print "IG = " + str(ig) + " " + str(splitpoint)
   return ig
   
      
def compute_entropy( histogram ):
   prob = dict()
   total = 0
   for i in histogram:
#      print str(i) + " increasing total by " + str(histogram[i])
      total += len(histogram[i])

#   print "total = " + str(total)

   #we now have the counts for each and we can calulate the probabilities for each value x \in X
   for i in histogram:
      if ( total > 0 ):
         prob[i] = float(len(histogram[i])) / total
      else:
         prob[i] = 0

   #now that we have the probs we can compute the entropy
   #H(X) = - \sum_i=1^n p(x_i) * log_b(p(x_i))
   ent = 0.0
   for d in prob.keys():
      if ( prob[d] > 0 ):
         ent += prob[d] * math.log(prob[d], 2)

   ent = -ent
   return ent


def printMaxAndMin( matrix, column ):
   min = sys.float_info.max
   max = sys.float_info.min
   for row in matrix:
      val = float(row[column])
      if ( val < min ):
         min = val
      if ( val > max ):
         max = val
      
   print "min = " + str(min) + " max = " + str(max)

#entopy is the expected value of the information content of a random variable
#domain is a list of intervals
def entropy( matrix, column, domain ):
   #first compute the probability of each cell value
   count = dict()
   total = 0

   #count the number of rows with a given value
   for row in matrix:
      val = float(row[column])
      for d in domain:
         if (d.inInterval(val)):
            if ( not d in count ):
               count[d] = 0
            count[d] += 1
            break
      total += 1

   return compute_entropy( count )


def laplace(b): #mu will normally be 0
#   print "adding noise with variance " + str(b)
   mu = 0
   u = random.uniform(-0.5,0.5)
#   print "u = " + str(u)
   z = mu - b * sign(u) * math.log(1 - 2 * math.fabs(u))
#   print "amoung of noise = " + str(z)
   return z 

def sign( num ):
  if ( num > 0 ):
    return 1;
  elif ( num < 0 ):
    return -1;
  else:
    return 0
   
        #    return stddev * Math.Sign(uniform) * Math.Log(1 - 2.0 * Math.Abs(uniform));


if __name__ == "__main__":
   main(sys.argv[1:])
