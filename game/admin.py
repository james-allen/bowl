from django.contrib import admin
from game.models import Match, Team, Player, PlayerInGame, Challenge, Race
from game.models import Position, Step

admin.site.register(Match)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(PlayerInGame)
admin.site.register(Challenge)
admin.site.register(Race)
admin.site.register(Position)
admin.site.register(Step)
