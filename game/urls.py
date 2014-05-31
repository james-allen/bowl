from django.conf.urls import patterns, url

from game import views

urlpatterns = patterns('',
    url(r'^(?P<match_id>\d+?)$', views.game_view, name='game_view'),
    url(r'^team/(?P<team_slug>.+?)$', views.team_view, name='team_view'),
    url(r'^create-team$', views.create_team_view, name='create_team_view'),
    url(r'^post_step$', views.post_step_view, name='post_step_view'),
	url(r'^issue_challenge$', views.issue_challenge_view,
		name='issue_challenge_view'),
	url(r'^accept_challenge/(?P<challenge_id>\d+?)$',
		views.accept_challenge_view, name='accept_challenge_view'),
	url(r'^reject_challenge/(?P<challenge_id>\d+?)$',
		views.reject_challenge_view, name='reject_challenge_view'),
)
