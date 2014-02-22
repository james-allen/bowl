import json

from django.db import models


class Race(models.Model):
    singular = models.CharField(max_length=50)
    plural = models.CharField(max_length=50)


class Team(models.Model):
    name = models.CharField(max_length=100)
    race = models.ForeignKey(Race)
    value = models.IntegerField(default=0)
    rerolls = models.IntegerField(default=0)
    cash = models.IntegerField(default=0)


class Player(models.Model):
    name = models.CharField(max_length=100)
    race = models.ForeignKey(Race)
    team = models.ForeignKey(Team)
    number = models.IntegerField()
    value = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    normal_skills = models.CharField(max_length=5)
    double_skills = models.CharField(max_length=5)
    games = models.IntegerField(default=0)
    spps = models.IntegerField(default=0)
    completions = models.IntegerField(default=0)
    casualties = models.IntegerField(default=0)
    interceptions = models.IntegerField(default=0)
    touchdowns = models.IntegerField(default=0)
    mvps = models.IntegerField(default=0)
    niggles = models.IntegerField(default=0)
    dead = models.BooleanField(default=False)


class Match(models.Model):
    home_team = models.ForeignKey(Team, related_name='home_match')
    away_team = models.ForeignKey(Team, related_name='away_match')
    turn = models.IntegerField(default=0)
    first_kicking_team = models.CharField(max_length=4)

    def as_dict(self):
        result_dict = {
            'id': self.id,
            'homeTeam': self.home_team.name,
            'awayTeam': self.away_team.name,
            'turn': self.turn,
            'firstKickingTeam': self.first_kicking_team,
        }
        return result_dict
        

class PlayerOnPitch(models.Model):
    player = models.ForeignKey(Player)
    match = models.ForeignKey(Match)
    xpos = models.IntegerField()
    ypos = models.IntegerField()
    action = models.CharField(max_length=8)
    down = models.BooleanField(default=False)
    stunned = models.BooleanField(default=False)
    has_ball = models.BooleanField(default=False)

    def as_dict(self, side):
        result_dict = {
            'side': side,
            'num': self.player.number,
            'xpos': self.xpos,
            'ypos': self.ypos,
            'action': self.action,
            'down': self.down,
            'stunned': self.stunned,
            'hasBall': self.has_ball,
            'skills': self.player.skills,
        }
        return result_dict


class Step(models.Model):
    step_type = models.CharField(max_length=20)
    action = models.CharField(max_length=20)
    match = models.ForeignKey(Match)
    history_position = models.IntegerField()
    properties = models.TextField()

    class Meta:
        unique_together = ('match', 'history_position')

    def as_dict(self):
        if self.properties:
            result_dict = json.loads(self.properties)
        else:
            result_dict = {}
        result_dict['stepType'] = self.step_type
        result_dict['matchId'] = self.match.id
        result_dict['historyPosition'] = self.history_position
        return result_dict



