# Overview #
HIDE is a [Django](http://djangoproject.com) application with a [CouchDB](http://couchdb.apache.org) document store. We recommend installing the latest versions of Django and CouchDB from source.

# Installation Instructions #
Overview of installation:
  * Install Python v2.6. (Python 3.0 and higher doesn't work with Django)
  * Install CouchDB. (details coming soon)
  * Install the Django Framework. (details coming soon)
  * Install [CRFSuite](http://www.chokkan.org/software/crfsuite/).
  * Create a Django project and reference the HIDE application.
  * Download the HIDE application from source.
  * Activate the HIDE application in the Django project.
  * Configure HIDE to communicate with CouchDB and the underlying anonymization and extraction utilities.

## Creating a Django Project ##
Django provides some command line utilities for managing the directory structure necessary to create a Django project.

Open up a command line and move to the top-level directory where you want to install the Django project. Below is an example:
```
cd /path/to/Code
django-admin.py startproject hide_proj
```
Replace the /path/to/ with the destination directory you prefer.

This will create a directory with the necessary files for the `hide_proj` Django project.

You know need to inform Django where the database for managing usernames and other aspects of the system. Open the `settings.py` file in the `hide_proj` directory and modify it to read:
```
DATABASE_ENGINE = 'sqlite3'           
DATABASE_NAME = '/path/to/Code/hide_proj/hide.db'       
```
You may safely ignore the other `DATABASE*` lines.

## Enable the project to support csrf tokens ##

Set the middleware classes in the settings.py file.

Set the middleware classes:
```
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)
```

## Enable Django to serve site media ##
Site media refers to stylesheets (css), javascript and images that are necessary for some user interface aspects of HIDE. This section outlines how to enable Django to serve this data. Note: This is not recommended for a production environment. If you are installing this system for multiple users you will need to [configure Django to work with a web server](http://docs.djangoproject.com/en/dev/howto/deployment/). We recommend [Apache HTTP Server](http://httpd.apache.org/).

Modify `settings.py`:
```
MEDIA_ROOT = '/path/to/Code/hide_proj/media'
ADMIN_MEDIA_PREFIX = '/media/'
```

See the example below how to update the `urls.py` file to serve the site media.

## Installing and Activating the HIDE application ##
After creating a Django project it is easy to activate the HIDE application by placing it in a directory below the `/path/to/Code/hide_proj` directory and by modifying the `settings.py` file of the created Django project.

**Download the latest version of HIDE to the hide\_proj directory.
```
svn checkout http://hide-emory.googlecode.com/svn/branches/hide-1.6/ hide-emory
```
Note: this link will allow you to run `svn update` periodically to obtain the latest versions of the software. It will not allow you to commit updates to the code. If you wish to contribute to the system, please contact [James Gardner](http://mathcs.emory.edu/~jgardn3). Create a symbolic link to the code in the `hide_proj` directory.
```
cd /path/to/hide_proj
ln -s /path/to/src/hide-emory/hide ./hide
```**

Install the django-registration app from
http://bitbucket.org/ubernostrum/django-registration

Here are the [install instructions for django-registration](http://bitbucket.org/ubernostrum/django-registration/src/tip/INSTALL).

Install HTML Tidy from http://tidy.sourceforge.net/. Note that on Windows you will need to install the dll somewhere that the system can find it.

Install necessary python modules.
```
elementtree
datetime
simplejson
pytidylib
couchdbkit
celery
hl7
xmlprinter
pysqlite
xmlprinter
MySQLdb
```

Most of the above can be installed using easy\_install.
Download for [xmlprinter](http://sourceforge.net/projects/py-xmlprinter/files/).
Download for [MySQLdb](http://sourceforge.net/projects/mysql-python/).

### Configure the `settings.py` file ###
  * Activate the HIDE application by adding the following lines to the `INSTALLED_APPS` list:
```
'hide_proj.hide',
'registration',
```

  * Configure HIDE to access the CouchDB by adding the following line:
```
COUCHDB_SERVER = 'http://127.0.0.1:5984'
```

> If you configured CouchDB with a password, then add the following lines:
```
COUCHDB_USER = 'your_username'
COUCHDB_PASS = 'your_password'
```


  * Let HIDE know where the underlying software powering the user interface is by specifying the configuration file:
```
HIDECONFIG = '/path/to/HIDE-config.xml'
```
Change `/path/to` to the location you put the config file.






### Configure the `urls.py` file ###
An example urls.py file follows:
```
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.conf import settings
admin.autodiscover()

urlpatterns = patterns('',
   (r'^hide/', include('hide.urls')),
   (r'^admin/', include(admin.site.urls)),
   (r'^accounts/', include('registration.urls')),
   (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', #enables site_media
   {'document_root': settings.MEDIA_ROOT}),
)
```

Refer to the [Django docs](http://docs.djangoproject.com/en/dev/) for more information on configuring the `urls.py` for your purposes.

If anything is missing from this document or following the instructions does not work, please do not hesitate to contact [James Gardner](http://mathcs.emory.edu/~jgardn3/).

After installation you will probably want to check out the [Using HIDE](http://mathcs.emory.edu/hide/doc/) page.

©2010 Emory University. All rights reserved.