from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/users/', include("users.urls")),
    path('api/chat_services/', include("chat_services.urls")),
    path('api/health_records/', include("health_records.urls")),
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),

    # deploy
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
