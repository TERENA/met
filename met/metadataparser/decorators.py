################################################################
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

import urlparse
from django.http import HttpResponseForbidden
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback

from django.conf import settings
from django.utils.decorators import available_attrs


def login_request(request, login_url=None):
    path = request.build_absolute_uri()
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse.urlparse(login_url or
                                                   settings.LOGIN_URL)[:2]
    current_scheme, current_netloc = urlparse.urlparse(path)[:2]
    if ((not login_scheme or login_scheme == current_scheme) and
            (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()
    from django.contrib.auth.views import redirect_to_login
    return redirect_to_login(path, login_url)


def user_can_edit(objtype, login_url=None, delete=False):
    """ based on user_passtest from django.contrib.auth.decorators"""
    def decorator(view_func):
        def _get_objid(kwargs):
            for key in kwargs.keys():
                if key.endswith('_id'):
                    return kwargs.get(key)
            return None

        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            path = request.build_absolute_uri()
            objid = _get_objid(kwargs)
            if objtype and objid:
                obj = objtype.objects.get(id=objid)
                if obj.can_edit(request.user, delete):
                    return view_func(request, *args, **kwargs)
            elif request.user.is_authenticated():
                return view_func(request, *args, **kwargs)

            if request.user.is_authenticated():
                return HttpResponseForbidden(u"You can't edit this object")

            return login_request(path, login_url)
        return _wrapped_view
    return decorator
