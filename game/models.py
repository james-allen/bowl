import json
import re
from collections import defaultdict

from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify


class Race(models.Model):
    singular = models.CharField(max_length=50)
    plural = models.CharField(max_length=50)
    reroll_cost = models.IntegerField()

    def __str__(self):
        return self.singular


class Team(models.Model):
    name = models.CharField(max_length=100)
    race = models.ForeignKey(Race)
    value = models.IntegerField(default=0)
    rerolls = models.IntegerField(default=0)
    cash = models.IntegerField(default=0)
    coach = models.ForeignKey(User)
    slug = models.SlugField(unique=True)
    color_home_primary = models.CharField(max_length=11)
    color_home_secondary = models.CharField(max_length=11)
    color_away_primary = models.CharField(max_length=11)
    color_away_secondary = models.CharField(max_length=11)

    def __str__(self):
        return self.slug

    def update_value(self):
        """Recalculate the value of the team."""
        value = 0
        for player in self.player_set.all():
            value += player.value
        value += self.rerolls * self.race.reroll_cost
        value += self.cash
        self.value = value
        self.save()
        return

    def valid_starting_team(self):
        """Return True if this is a valid starting team."""
        if self.player_set.count() < 11:
            return False
        if self.cash < 0:
            return False
        if self.value != 1000:
            return False
        if (self.color_home_primary == self.color_away_primary or
                self.color_home_primary == self.color_home_secondary or
                self.color_away_primary == self.color_away_secondary):
            return False
        if self.name == '':
            return False
        name_list = []
        position_tally = defaultdict(int)
        for player in self.player_set.all():
            if player.name == '':
                return False
            if player.name in name_list:
                return False
            name_list.append(player.name)
            position_tally[player.position.title] += 1
            if (position_tally[player.position.title] > 
                    player.position.max_quantity):
                return False

        return True

def create_team(name, race, coach, **kwargs):
    team = Team(name=name, race=race, coach=coach, **kwargs)
    slug = slugify(name)
    try:
        Team.objects.get(slug=slug)
    except Team.DoesNotExist:
        pass
    else:
        i = 1
        while True:
            try:
                slug = slugify(name) + '-' + str(i)
                Team.objects.get(slug=slug)
            except Team.DoesNotExist:
                break
            else:
                i += 1
    team.slug = slug
    return team


class Challenge(models.Model):
    challenger = models.ForeignKey(Team, related_name='challenges_issued')
    challengee = models.ForeignKey(Team, related_name='challenges_received')
    time_issued = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.challenger + ' vs ' + self.challengee


class Position(models.Model):
    title = models.CharField(max_length=30)
    team_race = models.ForeignKey(Race)
    race = models.CharField(max_length=50)
    max_quantity = models.IntegerField()
    cost = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    normal_skills = models.CharField(max_length=5)
    double_skills = models.CharField(max_length=5)

    def __str__(self):
        return self.team_race.singular + ' ' + self.title


class Player(models.Model):
    name = models.CharField(max_length=100)
    race = models.CharField(max_length=50)
    team = models.ForeignKey(Team)
    position = models.ForeignKey(Position)
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

    def __str__(self):
        return self.name

def create_player(team, position_title, name, number):
    position = Position.objects.get(
        title=position_title, team_race=team.race)
    player = Player(
        name=name,
        race=position.race,
        team=team,
        position=position,
        number=number,
        value=position.cost,
        ma=position.ma,
        st=position.st,
        ag=position.ag,
        av=position.av,
        skills=position.skills,
        normal_skills=position.normal_skills,
        double_skills=position.double_skills,
        )
    return player


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
    home_rerolls_total = models.IntegerField(default=0)
    away_rerolls_total = models.IntegerField(default=0)
    home_reroll_used_this_turn = models.BooleanField(default=False)
    away_reroll_used_this_turn = models.BooleanField(default=False)
    n_to_place = models.IntegerField(default=0)
    kicking_team = models.CharField(max_length=4)

    def __str__(self):
        return self.home_team.slug + ' vs ' + self.away_team.slug

    def as_dict(self):
        result_dict = {
            'id': self.id,
            'homeTeam': self.home_team.name,
            'awayTeam': self.away_team.name,
            'homeCoach': self.home_team.coach.username,
            'awayCoach': self.away_team.coach.username,
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
            'homeRerollsTotal': self.home_rerolls_total,
            'awayRerollsTotal': self.away_rerolls_total,
            'homeRerollUsedThisTurn': self.home_reroll_used_this_turn,
            'awayRerollUsedThisTurn': self.away_reroll_used_this_turn,
            'nToPlace': self.n_to_place,
            'kickingTeam': self.kicking_team,
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
        home_rerolls_total=home_team.rerolls,
        away_rerolls_total=away_team.rerolls,
        )
    match.save()
    for home_player in home_team.player_set.all():
        create_pig(home_player, match=match, xpos=0, ypos=0,
                   on_pitch=True, side='home').save()
    for away_player in away_team.player_set.all():
        create_pig(away_player, match=match, xpos=0, ypos=0,
                   on_pitch=True, side='away').save()
    set_kickoff(match, first_kicking_team)
    return match

def set_kickoff(match, kicking_team):
    """Set a kickoff for this match."""
    # Work out which side of the pitch each team is on
    if ((match.home_first_direction == 'right' and match.turn_number <= 8) or
        (match.home_first_direction == 'left' and match.turn_number >= 9)):
        xpos_home = 0
        xpos_away = 25
    else:
        xpos_home = 25
        xpos_away = 0
    # Start placing players at the top of the pitch
    ypos_home = 0
    ypos_away = 0
    for pig in match.playeringame_set.all():
        if pig.player.team == match.home_team:
            pig.xpos = xpos_home
            pig.ypos = ypos_home
            if ypos_home == 14:
                # Reached the bottom of the pitch, wrap back up to the top
                ypos_home = 0
                if xpos_home < 13:
                    xpos_home += 1
                else:
                    xpos_home -= 1
            else:
                ypos_home += 1
        else:
            pig.xpos = xpos_away
            pig.ypos = ypos_away
            if ypos_away == 14:
                # Reached the bottom of the pitch, wrap back up to the top
                ypos_away = 0
                if xpos_away < 13:
                    xpos_away += 1
                else:
                    xpos_away -= 1
            else:
                ypos_away += 1
            ypos_away += 1
        pig.down = False
        pig.stunned = False
        pig.stunned_this_turn = False
        pig.tackle_zones = True
        pig.has_ball = False
        pig.move_left = pig.ma
        pig.action = ''
        pig.finished_action = False
        pig.save()
    match.n_to_place = 2
    match.kicking_team = kicking_team
    match.current_side = kicking_team
    match.x_ball = None
    match.y_ball = None
    match.turn_type = 'placePlayers'
    match.save()


class PlayerInGame(models.Model):
    player = models.ForeignKey(Player)
    match = models.ForeignKey(Match)
    side = models.CharField(max_length=4)
    xpos = models.IntegerField()
    ypos = models.IntegerField()
    ma = models.IntegerField()
    st = models.IntegerField()
    ag = models.IntegerField()
    av = models.IntegerField()
    skills = models.TextField()
    effects = models.TextField()
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
    tackle_zones = models.BooleanField(default=True)

    def __str__(self):
        return self.player.name

    def as_dict(self):
        result_dict = {
            'side': self.side,
            'name': self.player.name,
            'num': self.player.number,
            'position': self.player.position.title,
            'race': self.player.race,
            'xpos': self.xpos,
            'ypos': self.ypos,
            'ma': self.ma,
            'st': self.st,
            'ag': self.ag,
            'av': self.av,
            'skills': self.skills.split(','),
            'effects': self.effects.split(','),
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
            'tackleZones': self.tackle_zones,
        }
        return result_dict

    def has_skill(self, skill):
        return skill in self.skills.split(',')
        
    def affected(self, effect):
        return effect in self.effects.split(',')
        
    def add_effect(self, effect):
        if not self.affected(effect):
            if len(self.effects) != 0:
                self.effects = self.effects + ','
            self.effects = self.effects + effect
            self.save()
            
    def remove_effect(self, effect):
        mat = re.match('^(.+,)?(?P<effect>'+effect+')(,.+)?$', self.effects)
        if not mat:
            return
        start = mat.start('effect')
        finish = mat.end('effect')
        if start > 0:
            # Also remove a preceding comma
            start -= 1
        else:
            if finish < len(self.effects):
                # Instead, remove a following comma
                finish += 1
            else:
                # There are no commas!
                pass
        self.effects = self.effects[:start] + self.effects[finish:]
        self.save()

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
    result = models.TextField()

    class Meta:
        unique_together = ('match', 'history_position')

    def __str__(self):
        return 'Match {} step {}'.format(self.match.id, self.history_position)

    def as_dict(self):
        if self.properties:
            step_dict = json.loads(self.properties)
        else:
            step_dict = {}
        if self.result:
            result_dict = json.loads(self.result)
        else:
            result_dict = {}
        step_dict['result'] = result_dict
        step_dict['stepType'] = self.step_type
        step_dict['matchId'] = self.match.id
        step_dict['historyPosition'] = self.history_position
        return step_dict



