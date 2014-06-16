from django.contrib import admin
from game.models import Match, Team, Player, PlayerInGame, Challenge, Race
from game.models import Position, Step

class PositionInline(admin.TabularInline):
    model = Position

class RaceAdmin(admin.ModelAdmin):
    inlines = [PositionInline]

class StepInline(admin.TabularInline):
    model = Step

class MatchAdmin(admin.ModelAdmin):
    inlines = [StepInline]

admin.site.register(Match, MatchAdmin)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(PlayerInGame)
admin.site.register(Challenge)
admin.site.register(Race, RaceAdmin)
