from django.db import models
from couchdbkit import *

class Object(Document):
   author = StringProperty()
   title = StringProperty()
   text = StringProperty()
   tags = StringProperty()
   id = StringProperty()

# Create your models here.
