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
##########################################################################

import csv
from xml.dom.minidom import Document

from django.http import HttpResponse, HttpResponseBadRequest
from django.template.defaultfilters import slugify
import simplejson as json


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def _serialize_value_to_csv(value):
    if type(value) is list:
        vallist = [_serialize_value_to_csv(v) for v in value]
        serialized = ", ".join(vallist)
    elif type(value) is dict:
        vallist = [_serialize_value_to_csv(v) for v in value.values()]
        serialized = ", ".join(vallist)
    else:
        serialized = "%s" % value

    return serialized


def export_entity_csv(entity):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename=%s.csv'
                                       % slugify(entity))
    writer = csv.writer(response)
    edict = entity.to_dict()

    writer.writerow(edict.keys())
    # Write data to CSV file
    row = []
    for _, value in edict.items():
        row.append(_serialize_value_to_csv(value))
    row_ascii = [v.encode("ascii", "ignore") for v in row]

    writer.writerow(row_ascii)
    # Return CSV file to browser as download
    return response


def export_entity_json(entity):
    # Return JS file to browser as download
    serialized = json.dumps(entity.to_dict(), cls=SetEncoder)
    response = HttpResponse(serialized, content_type='application/json')
    response['Content-Disposition'] = ('attachment; filename=%s.json'
                                       % slugify(entity))
    return response


def export_entity_xml(entity):
    entity_xml = entity.xml

    # Return XML file to browser as download
    response = HttpResponse(str(entity_xml), content_type='application/xml')
    response['Content-Disposition'] = ('attachment; filename=%s.xml'
                                       % slugify(entity))
    return response


export_entity_modes = {
    'csv': export_entity_csv,
    'json': export_entity_json,
    'xml': export_entity_xml,
}


def export_entity(mode, entity):
    if mode in export_entity_modes:
        return export_entity_modes[mode](entity)
    else:
        content = "Error 400, Format %s is not supported" % mode
        return HttpResponseBadRequest(content)
