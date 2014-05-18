from django.conf.urls import patterns, url

from game import views

urlpatterns = patterns('',
    url(r'^(?P<match_id>\d+?)$', views.game_view, name='game_view'),
    url(r'^team/(?P<team_slug>.+?)$', views.team_view, name='team_view'),
    url(r'^create-team$', views.create_team_view, name='create_team_view'),
    url(r'^post_step$', views.post_step_view, name='post_step_view'),
)
