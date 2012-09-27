from functools import update_wrapper

import logging
import os

from django.core.urlresolvers import reverse
from django.db.models.base import ModelBase
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
#from django.views.decorators.csrf import csrf_protect

from freenasUI.freeadmin.options import BaseFreeAdmin

log = logging.getLogger('freeadmin.site')


class NotRegistered(Exception):
    pass


class FreeAdminSite(object):

    def __init__(self):
        self._registry = {}

    def register(self, model_or_iterable, admin_class=None,
            freeadmin=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use BaseFreeAdmin (default
        admin options). If keyword arguments are given they'll be applied
        as options to the admin class.
        """
        if not admin_class:
            admin_class = BaseFreeAdmin

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        admins = []
        for model in model_or_iterable:
            if model._meta.abstract:
                log.warn("Model %r is abstract and thus cannot be registered",
                    model)
                return None
            if model in self._registry:
                log.debug("Model %r already registered, overwriting...", model)

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            if options:
                # For reasons I don't quite understand, without a __module__
                # the created class appears to "live" in the wrong place,
                # which causes issues later on.
                options['__module__'] = __name__
                admin_class = type("%sAdmin" % model.__name__,
                    (admin_class, ),
                    options)

            # Instantiate the admin class to save in the registry
            admin_obj = admin_class(c=freeadmin, model=model, admin=self)
            self._registry[model] = admin_obj
            model.add_to_class('_admin', admin_obj)

            admins.append(admin_obj)

        return admins

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return request.user.is_active and request.user.is_staff

    def admin_view(self, view, cacheable=False):
        """
        Decorator to create an admin view attached to this ``AdminSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.

        You'll want to use this from within ``AdminSite.get_urls()``:

            class MyAdminSite(AdminSite):

                def get_urls(self):
                    from django.conf.urls import patterns, url

                    urls = super(MyAdminSite, self).get_urls()
                    urls += patterns('',
                        url(r'^my_view/$', self.admin_view(some_view))
                    )
                    return urls

        By default, admin_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                if request.path == reverse('admin:logout',
                                           current_app=self.name):
                    index_path = reverse('admin:index', current_app=self.name)
                    return HttpResponseRedirect(index_path)
                return self.login(request)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        #if not getattr(view, 'csrf_exempt', False):
        #    inner = csrf_protect(inner)
        return update_wrapper(inner, view)

    def get_urls(self):
        from django.conf.urls import patterns, url, include

        from freenasUI.freeadmin.api import resources
        from tastypie.api import Api

        v1_api = Api(api_name='v1.0')
        v1_api.register(resources.SysctlResource())

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        # Admin-site-wide views.
        urlpatterns = patterns('',
            url(r'^$',
                wrap(self.adminInterface),
                name='index'),
            url(r'^api/',
                include(v1_api.urls)),
            url(r'^menu\.json/$',
                wrap(self.menu),
                name="freeadmin_menu"),
            url(r'^alert/status/$',
                wrap(self.alert_status),
                name="freeadmin_alert_status"),
            url(r'^alert/$',
                wrap(self.alert_detail),
                name="freeadmin_alert_detail"),
        )

        # Add in each model's views.
        for model, model_admin in self._registry.iteritems():
            urlpatterns += patterns('',
                url(r'^%s/%s/' % (
                    model._meta.app_label,
                    model._meta.module_name,
                    ),
                    include(model_admin.urls))
            )
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()

    @never_cache
    def adminInterface(self, request):
        from freenasUI.freeadmin.views import adminInterface
        return adminInterface(request)

    @never_cache
    def menu(self, request):
        from freenasUI.freeadmin.navtree import navtree
        try:
            navtree.generate(request)
            final = navtree.dijitTree(request.user)
            json = simplejson.dumps(final)
        except Exception, e:
            log.debug("Fatal error while generating the tree json: %s", e)
            json = ""

        return HttpResponse(json, mimetype="application/json")

    @never_cache
    def alert_status(self, request):
        if os.path.exists('/var/tmp/alert'):
            current = 'OK'
            with open('/var/tmp/alert') as f:
                entries = f.readlines()
            for entry in entries:
                if not entry:
                    continue
                status, message = entry.split(': ', 1)
                if (status == 'WARN' and current == 'OK') or \
                  status == 'CRIT' and current in ('OK', 'WARN'):
                    current = status
            return HttpResponse(current)
        else:
            return HttpResponse('WARN')

    @never_cache
    def alert_detail(self, request):
        if os.path.exists('/var/tmp/alert'):
            with open('/var/tmp/alert') as f:
                entries = f.read().split('\n')
            alerts = []
            for entry in entries:
                if not entry:
                    continue
                status, message = entry.split(': ', 1)
                alerts.append({
                    'status': status,
                    'message': message,
                })

            return render(request, "freeadmin/alert_status.html", {
                'alerts': alerts,
                })
        else:
            return HttpResponse(
                _("It was not possible to retrieve the current status")
                )

site = FreeAdminSite()
