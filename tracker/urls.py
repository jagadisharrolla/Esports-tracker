from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login_page'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register-org/', views.register_org, name='register_org'),
    path('register-player-account/', views.register_player_account, name='register_player_account'),
    path('home/', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('compare/', views.compare, name='compare'),
    path('add-player/', views.add_player, name='add_player'),
    path('delete-player/<str:username>/', views.delete_player, name='delete_player'),
    path('player/<str:username>/', views.player_profile, name='player_profile'),
    path('add-match/<str:username>/', views.add_match, name='add_match'),
    path('match/<str:username>/<str:match_id>/', views.match_detail, name='match_detail'),
    path('tournaments/', views.tournament_list, name='tournament_list'),
    path('tournaments/create/', views.tournament_create, name='tournament_create'),
    path('tournaments/<str:slug>/', views.tournament_detail, name='tournament_detail'),
    path('tournaments/<str:slug>/register/', views.tournament_register, name='tournament_register'),
    path('tournaments/<str:slug>/result/', views.tournament_add_result, name='tournament_add_result'),
    path('tournaments/<str:slug>/status/', views.tournament_update_status, name='tournament_update_status'),
    path('org/', views.org_dashboard, name='org_dashboard'),
     path('teams/', views.teams_hub, name='teams_hub'),
    path('tournament/<slug:slug>/bracket/', views.generate_bracket_view, name='generate_bracket'),
]   
