from celery.decorators import task
import HIDE

@task
def trainCRF( mallet ):
   return mallet

@task
def labelMallet( modelfile, mallet ):
   HIDE.labelMallet( modelfile, mallet )
  

