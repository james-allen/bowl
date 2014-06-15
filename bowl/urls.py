from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'bowl.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^game/', include('game.urls', namespace='game')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'bowl.views.logout_view', name='logout'),
    url(r'^accounts/profile/$', 'bowl.views.profile_view', name='profile'),
    url(r'^accounts/profile/(?P<username>.+?)/$', 'bowl.views.profile_view', name='user_profile'),
    url(r'^accounts/change_password/$', 'django.contrib.auth.views.password_change', {'post_change_redirect': 'profile'}, name='change_password'),
    url(r'^$', 'bowl.views.home_view', name='home'),
)
