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
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    turn_number = models.IntegerField(default=0)
    turn_type = models.CharField(max_length=12, default='placePlayers')
    current_side = models.CharField(max_length=4)
    first_kicking_team = models.CharField(max_length=4)
    home_first_direction = models.CharField(max_length=5)
    x_ball = models.IntegerField(null=True, default=None)
    y_ball = models.IntegerField(null=True, default=None)
    home_rerolls = models.IntegerField(default=0)
    away_rerolls = models.IntegerField(default=0)
    home_reroll_used_this_turn = models.BooleanField(default=False)
    away_reroll_used_this_turn = models.BooleanField(default=False)

    def as_dict(self):
        result_dict = {
            'id': self.id,
            'homeTeam': self.home_team.name,
            'awayTeam': self.away_team.name,
            'homeScore': self.home_score,
            'awayScore': self.away_score,
            'turnNumber': self.turn_number,
            'turnType': self.turn_type,
            'currentSide': self.current_side,
            'firstKickingTeam': self.first_kicking_team,
            'homeFirstDirection': self.home_first_direction,
            'xBall': self.x_ball,
            'yBall': self.y_ball,
            'homeRerolls': self.home_rerolls,
            'awayRerolls': self.away_rerolls,
            'homeRerollUsedThisTurn': self.home_reroll_used_this_turn,
            'awayRerollUsedThisTurn': self.away_reroll_used_this_turn,
        }
        return result_dict

    def team(self, side):
        if side == 'home':
            return self.home_team
        elif side == 'away':
            return self.away_team
        else:
            raise ValueError('Unrecognised side: ' + side)

def start_match(home_team, away_team, first_kicking_team=None,
                home_first_direction=None):
    """Create a match between the two sides."""
    if first_kicking_team is None:
        # Replace this with a random selection
        first_kicking_team = 'home'
    if home_first_direction is None:
        # Replace this with a random selection
        home_first_direction = 'right'
    match = Match(
        home_team=home_team,
        away_team=away_team,
        current_side=first_kicking_team,
        first_kicking_team=first_kicking_team,
        home_first_direction=home_first_direction,
        home_rerolls=home_team.rerolls,
        away_rerolls=away_team.rerolls,
        )
    match.save()
    if home_first_direction == 'right':
        xpos_home = 0
        xpos_away = 25
    else:
        xpos_home = 25
        xpos_away = 0
    ypos = 0
    for home_player, away_player in zip(
            home_team.player_set.all(), away_team.player_set.all()):
        create_pig(
            home_player, match=match, xpos=xpos_home, ypos=ypos,
            on_pitch=True).save()
        create_pig(
            away_player, match=match, xpos=xpos_away, ypos=ypos,
            on_pitch=True).save()
        ypos += 1
    return match
        

class PlayerInGame(models.Model):
    player = models.ForeignKey(Player)
    match = models.ForeignKey(Match)
    xpos = models.IntegerField()
    ypos = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    action = models.CharField(max_length=8)
    move_left = models.IntegerField()
    finished_action = models.BooleanField(default=False)
    down = models.BooleanField(default=False)
    stunned = models.BooleanField(default=False)
    stunned_this_turn = models.BooleanField(default=False)
    has_ball = models.BooleanField(default=False)
    on_pitch = models.BooleanField(default=False)
    knocked_out = models.BooleanField(default=False)
    casualty = models.BooleanField(default=False)
    sent_off = models.BooleanField(default=False)

    def as_dict(self, side):
        result_dict = {
            'side': side,
            'num': self.player.number,
            'xpos': self.xpos,
            'ypos': self.ypos,
            'ma': self.ma,
            'st': self.st,
            'ag': self.ag,
            'av': self.av,
            'action': self.action,
            'moveLeft': self.move_left,
            'finishedAction': self.finished_action,
            'down': self.down,
            'stunned': self.stunned,
            'stunnedThisTurn': self.stunned_this_turn,
            'hasBall': self.has_ball,
            'onPitch': self.on_pitch,
            'knockedOut': self.knocked_out,
            'casualty': self.casualty,
            'sentOff': self.sent_off,
            'skills': self.skills.split(','),
        }
        return result_dict

def create_pig(parent, **kwargs):
    pig = PlayerInGame()
    pig.player = parent
    pig.ma = parent.ma
    pig.st = parent.st
    pig.ag = parent.ag
    pig.av = parent.av
    pig.skills = parent.skills
    pig.move_left = parent.ma
    for key, value in kwargs.items():
        setattr(pig, key, value)
    return pig


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



