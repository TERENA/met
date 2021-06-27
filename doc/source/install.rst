.. _index:

Metadata Explorer Tool Install
==============================

Install Python 3.7
******************


.. code-block:: bash

  # apt-get update
  # apt-get install python3
  # apt-get install python3-pip

Install requirements
********************

.. code-block:: bash

  # pip3 install -r requirements.txt

Make sure locales are correctly installed
*****************************************

.. code-block:: bash

  echo "LC_ALL=en_US.UTF-8" >> /etc/environment
  echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
  echo "LANG=en_US.UTF-8" > /etc/locale.conf
  locale-gen en_US.UTF-8

Create database
***************

postgresql :

.. code-block:: bash

  sudo su - postgres
  createuser -P met
  createdb --owner met met


Project deployment
******************

* Create a user ``met`` in the system:

  .. code-block:: bash

      sudo adduser met

* Add ``www-data`` into ``met`` group:

  .. code-block:: bash

      sudo adduser www-data met

* Change to ``met`` user:

  .. code-block:: bash

      sudo su - met

* Create a virtualenv and load it:

  .. code-block:: bash

      virtualenv met-venv
      source met-venv/bin/activate

* Clone git repository:

  .. code-block:: bash

      git clone git://github.com/GEANT/met.git

* Deploy met egg:

  .. code-block:: bash

      cd met
      python3.7 setup.py develop

* Configure ``local_settings`` and initialize met database (create models):

  .. code-block:: bash

      cp local_settings.py.example local_settings.py
      python3.7 manage.py migrate

* To initialize static files for admin page of Django execute:

  .. code-block:: bash

      python manage.py collectstatic


Apache configuration
********************

This is a basic template that assumes the project was deployed into ``met``
user's home.

A apache 2.2.18 or later is required (AllowEncodedSlashes NoDecode)
http://httpd.apache.org/docs/2.2/mod/core.html#allowencodedslashes

.. code-block:: text

    Alias /media/ /home/met/media/
    Alias /static/ /home/met/static/

    <Directory /home/met/media/>
    Order deny,allow
    Allow from all
    </Directory>

    <Directory /home/met/static/>
    Order deny,allow
    Allow from all
    </Directory>

    AllowEncodedSlashes NoDecode

    WSGIDaemonProcess <server name> home=/home/met
    WSGIProcessGroup <server name>

    WSGIScriptAlias / /home/met/met/met-wsgi.py

    <Directory /home/met/met/met-wsgi.py>
    Order allow,deny
    Allow from all
    </Directory>

    <Location /met/saml2/login >
    authtype shibboleth
    shibRequestSetting requireSession 1
    require valid-user
    </Location>


Enable memcached
****************

Memcached is disabled in the local_settings.example.py configuration. Find the
block *CACHES* in your local_settings.py file and set it as follow:


.. code-block:: python

   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
           'LOCATION': '127.0.0.1:11211',
       }
   }


Initialize media directory
**************************

Initialize media directory with proper permissions:

.. code-block:: bash

    python manage.py collectstatic
    mkdir ~/media
    chmod g+srw ~/media


Create directory for pyFF cache
*******************************

Create a cache directory for pyFF with proper permissions:

.. code-block:: bash

    mkdir /home/met/met/.cache
    chown www-data.www-data /home/met/met/.cache

Automatic refresh of federations' metadata
******************************************

Metadata of configured federations can be refreshed automatically. To achieve this
you just need to configure a cronjob on your server such as:

.. code-block:: bash

   0 * * * * cd /home/met/met && /home/met/met-venv/bin/python /home/met/met/automatic_refresh/refresh.py --log /home/met/met/automatic_refresh/pylog.conf

With the option --log the script will log as configured in the logging configuration file.

This cron code must be inserted for the met user, so to edit the proper cron file,
it is highly suggested you use the command:

.. code-block:: bash

   crontab -u met -e


Logrotate configuration
***********************

Logrotate can be configured to avoid the continuous growth of the refresh metadata script logging:

.. code-block:: javascript

   /var/log/met_refresh.log {
        rotate 7
        daily
        missingok
        notifempty
        delaycompress
        compress
        postrotate
                touch /var/log/met_refresh.log >/dev/null 2>&1 || true
                chown www-data.www-data /var/log/met_refresh.log >/dev/null 2>&1 || true
                reload rsyslog >/dev/null 2>&1 || true
        endscript
  }


Publishing Met Documentation
****************************

You have to install the Sphinx package inside a python virtualenv. You can install
Sphinx with this command:

.. code-block:: bash

   easy_install Sphinx

Now, you need to build the html from the rst pages:

.. code-block:: bash

   cd /home/met/met/doc
   make html

To publish the generated html in your MET site, you can add this block to your
apache site configuration:

.. code-block:: text

   Alias /doc /home/met/met/doc/build/html
   <Directory /home/met/met/doc/build/html>
      Options Indexes FollowSymlinks
      Order deny,allow
      Allow from all
   </Directory>


Customizations
==============

Customize /about page
*********************

We are going to create a new `about.html` template that overwrite the default
`about.html` template. To do this, you must ensure that this block exists in your
`local_settings.py` (it is already set in `local_settings.example.py` provided by
this package)

.. code-block:: python

  TEMPLATE_DIRS = (
      # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
      # Always use forward slashes, even on Windows.
      # Don't forget to use absolute paths, not relative paths.
      os.path.join(BASEDIR, 'templates'),
  )

`BASEDIR` is the directory where `local_settings.py` and `met-wsgi.py` are. Then
we need to create a directory called templates and a file called `about.html`
in it. The `about.html` file must have this structure:

::

  {% extends "base.html" %}

  {% block content %}
  <p>This is your custom content</p>
  {% endblock %}

You can add your custom html between the `block` and `endblock` tags.
