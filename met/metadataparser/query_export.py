#################################################################
# MET v2 Metadate Explorer Tool
#
# This Software is Open Source. See License: https://github.com/TERENA/met/blob/master/LICENSE.md
# Copyright (c) 2012, TERENA All rights reserved.
#
# This Software is based on MET v1 developed for TERENA by Yaco Sistemas, http://www.yaco.es/
# MET v2 was developed for TERENA by Tamim Ziai, DAASI International GmbH, http://www.daasi.de
# Current version of MET has been revised for performance improvements by Andrea Biancini,
# Consortium GARR, http://www.garr.it
#########################################################################################

import csv
from xml.dom.minidom import Document

from django.http import HttpResponse, HttpResponseBadRequest
from django.template.defaultfilters import slugify
import simplejson as json


## Taken from http://djangosnippets.org/snippets/790/
def export_csv(model, filename, fields):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename=%s.csv'
                                       % slugify(filename))
    writer = csv.writer(response)
    # Write headers to CSV file

    writer.writerow(fields)

    # Write data to CSV file
    for obj in model:
        row = []
        for field in fields:
            row.append("%s" % obj[field])
        writer.writerow(row)
    # Return CSV file to browser as download
    return response


def export_json(model, filename, fields):
    objs = []

    for obj in model:
        item = {}
        for field in fields:
            if type(obj[field]) == set:
                item[field] = list(obj[field])
            else:
                item[field] = obj[field]

        objs.append(item)
    # Return JS file to browser as download
    serialized = json.dumps(objs)
    response = HttpResponse(serialized, content_type='application/json')
    response['Content-Disposition'] = ('attachment; filename=%s.json'
                                       % slugify(filename))
    return response


def _parse_xml_element(xml, father, structure):
    if type(structure) == dict:
        for k in structure:
            tag = xml.createElement(k)
            father.appendChild(tag)
            _parse_xml_element(xml, tag, structure[k])
    elif type(structure) == tuple:
        tag_name = father.tagName
        for l in list(structure):
            tag = xml.createElement(tag_name)
            _parse_xml_element(xml, tag, l)
            father.appendChild(tag)
    elif type(structure) == list:
        tag_name = father.tagName
        for l in structure:
            tag = xml.createElement(tag_name)
            _parse_xml_element(xml, tag, l)
            father.appendChild(tag)
    elif type(structure) == set:
        tag_name = father.tagName
        for l in list(structure):
            tag = xml.createElement(tag_name)
            _parse_xml_element(xml, tag, l)
            father.appendChild(tag)
    else:
        if type(structure) == unicode:
            data = structure.encode("ascii", errors="xmlcharrefreplace")
        else:
            data = str(structure)
        tag = xml.createTextNode(data)
        father.appendChild(tag)


def export_xml(model, filename, fields=None):
    xml = Document()
    root = xml.createElement(filename)
    for obj in model:
        elem = xml.createElement("entity")
        _parse_xml_element(xml, elem, obj)
        root.appendChild(elem)
    xml.appendChild(root)

    # Return xml file to browser as download
    response = HttpResponse(xml.toxml(), content_type='application/xml')
    response['Content-Disposition'] = ('attachment; filename=%s.xml'
                                       % slugify(filename))
    return response


export_modes = {
            'csv': export_csv,
            'json': export_json,
            'xml': export_xml,
        }


def export_query_set(mode, qs, filename, fields=None):
    if mode in export_modes:
        return export_modes[mode](qs, filename, fields)
    else:
        content = "Error 400, Format %s is not supported" % mode
        return HttpResponseBadRequest(content)
