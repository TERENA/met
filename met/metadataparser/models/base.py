##########################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
##########################################################################

from os import path
from lxml import etree
import simplejson as json

from django.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.core.files.base import ContentFile
from django.utils.translation import ugettext_lazy as _

from pyff.repo import MDRepository
from pyff.pipes import Plumbing

from met.metadataparser.xmlparser import MetadataParser
from met.metadataparser.utils import compare_filecontents


class JSONField(models.CharField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly

    The json spec claims you must use a collection type at the top level of
    the data structure.  However the simplesjon decoder and Firefox both encode
    and decode non collection types that do not exist inside a collection.
    The to_python method relies on the value being an instance of basestring
    to ensure that it is encoded.  If a string is the sole value at the
    point the field is instanced, to_python attempts to decode the sting because
    it is derived from basestring but cannot be encodeded and throws the
    exception ValueError: No JSON object could be decoded.
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase
    description = _("JSON object")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validators.MaxLengthValidator(self.max_length))

    @classmethod
    def get_internal_type(cls):
        return "TextField"

    @classmethod
    def to_python(cls, value):
        """Convert our string value to JSON after we load it from the DB"""
        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            return value

        return value

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""

        if not value or value == "":
            return None

        db_value = json.dumps(value)
        return super().get_prep_value(db_value)

    def get_db_prep_value(self, value, connection, prepared=False):
        """Convert our JSON object to a string before we save"""

        if not value or value == "":
            return None

        db_value = json.dumps(value)
        return super().get_db_prep_value(db_value, connection, prepared)


class Base(models.Model):
    """
    Class describing an entity that can be updated from metadata file.
    Each object parsed from the XML extends this base class that contains shared methods.
    """

    file_url = models.CharField(verbose_name='Metadata url',
                                max_length=1000,
                                blank=True, null=True,
                                help_text=_('Url to fetch metadata file'))
    file = models.FileField(upload_to='metadata', blank=True, null=True,
                            verbose_name=_('metadata xml file'),
                            help_text=_("if url is set, metadata url will be "
                                        "fetched and replace file value"))
    file_id = models.CharField(blank=True, null=True, max_length=500,
                               verbose_name=_('File ID'))

    registration_authority = models.CharField(verbose_name=_('Registration Authority'),
                                              max_length=200, blank=True, null=True)

    editor_users = models.ManyToManyField(User, blank=True,
                                          verbose_name=_('editor users'))

    class Meta:
        abstract = True

    class XmlError(Exception):
        pass

    def __unicode__(self):
        return self.url or "Metadata %s" % self.id

    def load_file(self):
        if not hasattr(self, '_loaded_file'):
            # Only load file and parse it, don't create/update any objects
            if not self.file:
                return None
            self._loaded_file = MetadataParser(filename=self.file.path)
        return self._loaded_file

    def _get_metadata_stream(self, load_streams):
        try:
            load = []
            select = []

            count = 1
            for stream in load_streams:
                curid = "%s%d" % (self.slug, count)
                load.append(f"{stream[0]} as {curid}")
                if stream[1] == 'SP' or stream[1] == 'IDP':
                    select.append(
                        f"{curid}!//md:EntityDescriptor[md:{stream[1]}SSODescriptor]")
                else:
                    select.append("%s" % curid)
                count = count + 1

            if len(select) > 0:
                pipeline = [{'load': load}, {'select': select}]
            else:
                pipeline = [{'load': load}, 'select']

            md = MDRepository()
            entities = Plumbing(pipeline=pipeline, id=self.slug).process(
                md, state={'batch': True, 'stats': {}})
            return etree.tostring(entities)
        except Exception as e:
            raise Exception(
                f'Getting metadata from {load_streams} failed.\nError: {e}')

    def fetch_metadata_file(self, file_name):
        file_url = self.file_url
        if not file_url or file_url == '':
            return

        metadata_files = []
        files = file_url.split("|")
        for curfile in files:
            cursource = curfile.split(";")
            if len(cursource) == 1:
                cursource.append("All")
            metadata_files.append(cursource)

        req = self._get_metadata_stream(metadata_files)

        try:
            self.file.seek(0)
            original_file_content = self.file.read()
            if compare_filecontents(original_file_content, req):
                return False
        except Exception:
            pass

        filename = path.basename("%s-metadata.xml" % file_name)
        self.file.delete(save=False)
        self.file.save(filename, ContentFile(req), save=False)
        return True

    @classmethod
    def process_metadata(cls):
        """
        Method that process the metadata file and updates attributes accordingly.
        """
        raise NotImplementedError()


class XmlDescriptionError(Exception):
    """
    Class representing an error in the XML file.
    """
    pass


class Dummy(models.Model):
    """
    Dummy object necessary to thest Django funcionalities.
    """
    pass
