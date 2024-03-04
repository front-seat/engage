"""
URL configuration for city project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.urls import include, path
from django.views.static import serve

from .admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    path("", include("server.legistar.urls")),
]


def _serve_force_utf8(request, path, document_root, show_indexes):
    """Serve a file from the document root, forcing UTF-8 encoding."""
    response = serve(request, path, document_root, show_indexes)
    # CONSIDER: I'm not sure why I need to type: ignore these lines.
    # I assume it's because the django stubs aren't quite complete here?
    if response.headers.get("Content-Type") == "text/plain":  # type: ignore
        response.headers["Content-Type"] = "text/plain; charset=utf-8"  # type: ignore
    return response


if settings.DEBUG:
    urlpatterns += [
        path(
            "media/<path:path>",
            _serve_force_utf8,
            {"document_root": settings.MEDIA_ROOT, "show_indexes": True},
        ),
    ]
