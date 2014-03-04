from game.models import PlayerInGame

import random


def resolve(match, step_type, data):
    if step_type in ['move', 'push', 'followUp']:
        # A move step
        # Find out which player it is
        if data['side'] == 'home':
            team = match.home_team
        elif data['side'] == 'away':
            team = match.away_team
        num = data['num']
        player = PlayerInGame.objects.get(
            match=match, player__team=team, player__number=num)
        # Update the player's position in the database
        player.xpos = data['x1']
        player.ypos = data['y1']
        player.save()
        return {}
    elif step_type == 'block':
        # A block step
        # Find out which is the attacking player
        if data['side'] == 'home':
            attacking_team = match.home_team
            defending_team = match.away_team
        elif data['side'] == 'away':
            attacking_team = match.away_team
            defending_team = match.home_team
        print("Established teams")
        attacking_num = int(data['num'])
        print(attacking_num)
        defending_num = int(data['targetNum'])
        print(defending_num)
        attacking_player = PlayerInGame.objects.get(
            match=match, player__team=attacking_team, 
            player__number=attacking_num)
        defending_player = PlayerInGame.objects.get(
            match=match, player__team=defending_team,
            player__number=defending_num)
        print("Established players")
        print(attacking_player, attacking_player.player, attacking_player.player.st)
        print(defending_player, defending_player.player, defending_player.player.st)
        n_dice = 1
        if attacking_player.player.st > (2 * defending_player.player.st):
            n_dice = 3
        elif attacking_player.player.st > defending_player.player.st:
            n_dice = 2
        elif (2 * attacking_player.player.st) < defending_player.player.st:
            n_dice = 3
        elif attacking_player.player.st < defending_player.player.st:
            n_dice = 2
        print("Rolling dice")
        return roll_block_dice(n_dice)
    elif step_type == 'knockDown':
        print("Knockdown!")
        # A player knocked over
        # Find out which player it is
        if data['side'] == 'home':
            team = match.home_team
        elif data['side'] == 'away':
            team = match.away_team
        num = data['num']
        print(team, num)
        player = PlayerInGame.objects.get(
            match=match, player__team=team, player__number=num)
        print(player)
        # Knock the player over in the database
        player.down = True
        player.save()
        # Roll against armour
        print("about to roll for armour")
        armour_roll = roll_armour_dice(player)
        print(armour_roll)
        if armour_roll['success']:
            injury_roll = roll_injury_dice()
            print(injury_roll)
            if injury_roll['result'] == 'stunned':
                player.stunned = True
            elif injury_roll['result'] == 'knockedOut':
                player.knocked_out = True
                player.on_pitch = False
            elif injury_roll['result'] == 'casualty':
                player.casualty = True
                player.on_pitch = False
            else:
                raise ValueError('Injury roll returned unexpected result: ' + 
                                 injury_roll['result'])
            player.save()
        else:
            injury_roll = None
        return {'armourRoll': armour_roll, 'injuryRoll': injury_roll}
    elif step_type == 'endTurn':
        return {}

def roll_block_dice(n_dice):
    result_num = roll_dice(6, n_dice)
    block_dice_dict = {
        1: "attackerDown",
        2: "bothDown",
        3: "pushed",
        4: "pushed",
        5: "defenderStumbles",
        6: "defenderDown"
    }
    return {"nDice": n_dice,
        "dice": [block_dice_dict[num] for num in result_num["dice"]]}

def roll_armour_dice(player):
    dice = roll_dice(6, 2)
    print('dice:', dice)
    total = sum(dice['dice'])
    print('total:', total)
    success = (total > player.player.av)
    print('success:', success)
    return {'dice': dice, 'total': total, 'success': success}

def roll_injury_dice():
    dice = roll_dice(6, 2)
    total = sum(dice)
    if total <= 7:
        result = 'stunned'
    elif total <= 9:
        result = 'knockedOut'
    else:
        result = 'casualty'
    return {'dice': dice, 'total': total, 'result': result}

def roll_dice(n_sides, n_dice):
    return {"nDice": n_dice,
        "dice": [random.randint(1, n_sides) for i in range(n_dice)]}
        