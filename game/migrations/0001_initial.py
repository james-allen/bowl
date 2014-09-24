# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Challenge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('time_issued', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('home_score', models.IntegerField(default=0)),
                ('away_score', models.IntegerField(default=0)),
                ('turn_number', models.IntegerField(default=1)),
                ('turn_type', models.CharField(default='placePlayers', max_length=12)),
                ('current_side', models.CharField(max_length=4)),
                ('first_kicking_team', models.CharField(max_length=4)),
                ('home_first_direction', models.CharField(max_length=5)),
                ('x_ball', models.IntegerField(null=True, default=None)),
                ('y_ball', models.IntegerField(null=True, default=None)),
                ('home_rerolls', models.IntegerField(default=0)),
                ('away_rerolls', models.IntegerField(default=0)),
                ('home_rerolls_total', models.IntegerField(default=0)),
                ('away_rerolls_total', models.IntegerField(default=0)),
                ('home_reroll_used_this_turn', models.BooleanField(default=False)),
                ('away_reroll_used_this_turn', models.BooleanField(default=False)),
                ('n_to_place', models.IntegerField(default=0)),
                ('kicking_team', models.CharField(max_length=4)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('race', models.CharField(max_length=50)),
                ('number', models.IntegerField()),
                ('value', models.IntegerField()),
                ('ma', models.IntegerField()),
                ('st', models.IntegerField()),
                ('ag', models.IntegerField()),
                ('av', models.IntegerField()),
                ('skills', models.TextField()),
                ('normal_skills', models.CharField(max_length=5)),
                ('double_skills', models.CharField(max_length=5)),
                ('games', models.IntegerField(default=0)),
                ('spps', models.IntegerField(default=0)),
                ('completions', models.IntegerField(default=0)),
                ('casualties', models.IntegerField(default=0)),
                ('interceptions', models.IntegerField(default=0)),
                ('touchdowns', models.IntegerField(default=0)),
                ('mvps', models.IntegerField(default=0)),
                ('niggles', models.IntegerField(default=0)),
                ('dead', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PlayerInGame',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('side', models.CharField(max_length=4)),
                ('xpos', models.IntegerField()),
                ('ypos', models.IntegerField()),
                ('ma', models.IntegerField()),
                ('st', models.IntegerField()),
                ('ag', models.IntegerField()),
                ('av', models.IntegerField()),
                ('skills', models.TextField()),
                ('effects', models.TextField()),
                ('action', models.CharField(max_length=8)),
                ('move_left', models.IntegerField()),
                ('finished_action', models.BooleanField(default=False)),
                ('down', models.BooleanField(default=False)),
                ('stunned', models.BooleanField(default=False)),
                ('stunned_this_turn', models.BooleanField(default=False)),
                ('has_ball', models.BooleanField(default=False)),
                ('on_pitch', models.BooleanField(default=False)),
                ('knocked_out', models.BooleanField(default=False)),
                ('casualty', models.BooleanField(default=False)),
                ('sent_off', models.BooleanField(default=False)),
                ('tackle_zones', models.BooleanField(default=True)),
                ('match', models.ForeignKey(to='game.Match')),
                ('player', models.ForeignKey(to='game.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('title', models.CharField(max_length=30)),
                ('race', models.CharField(max_length=50)),
                ('max_quantity', models.IntegerField()),
                ('cost', models.IntegerField()),
                ('ma', models.IntegerField()),
                ('st', models.IntegerField()),
                ('ag', models.IntegerField()),
                ('av', models.IntegerField()),
                ('skills', models.TextField()),
                ('normal_skills', models.CharField(max_length=5)),
                ('double_skills', models.CharField(max_length=5)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Race',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('singular', models.CharField(max_length=50)),
                ('plural', models.CharField(max_length=50)),
                ('reroll_cost', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('step_type', models.CharField(max_length=20)),
                ('action', models.CharField(max_length=20)),
                ('history_position', models.IntegerField()),
                ('properties', models.TextField()),
                ('result', models.TextField()),
                ('match', models.ForeignKey(to='game.Match')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('value', models.IntegerField(default=0)),
                ('rerolls', models.IntegerField(default=0)),
                ('cash', models.IntegerField(default=0)),
                ('slug', models.SlugField(unique=True)),
                ('color_home_primary', models.CharField(max_length=11)),
                ('color_home_secondary', models.CharField(max_length=11)),
                ('color_away_primary', models.CharField(max_length=11)),
                ('color_away_secondary', models.CharField(max_length=11)),
                ('coach', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('race', models.ForeignKey(to='game.Race')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='step',
            unique_together=set([('match', 'history_position')]),
        ),
        migrations.AddField(
            model_name='position',
            name='team_race',
            field=models.ForeignKey(to='game.Race'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='player',
            name='position',
            field=models.ForeignKey(to='game.Position'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='player',
            name='team',
            field=models.ForeignKey(to='game.Team'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='match',
            name='away_team',
            field=models.ForeignKey(to='game.Team', related_name='away_match'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='match',
            name='home_team',
            field=models.ForeignKey(to='game.Team', related_name='home_match'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='challenge',
            name='challengee',
            field=models.ForeignKey(to='game.Team', related_name='challenges_received'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='challenge',
            name='challenger',
            field=models.ForeignKey(to='game.Team', related_name='challenges_issued'),
            preserve_default=True,
        ),
    ]
