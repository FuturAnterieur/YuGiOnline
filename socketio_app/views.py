# set async_mode to 'threading', 'eventlet', 'gevent' or 'gevent_uwsgi' to
# force a mode else, the best mode is selected automatically from what's
# installed
async_mode = None

import os

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
import socketio

from socketio_app.models import Duel, Player
import engine.GameState
import engine.Player


sio = socketio.Server(async_mode=async_mode)
thread = None


gameStates = {}  #TODO : put this into a managing class
gameStatesBySid = {}

def index(request):
    #global thread
    #if thread is None:
    #    thread = sio.start_background_task(background_thread)

    return render(request, 'socketio_app/index.html', {})
    
def chat_space(request):
    return render(request, 'socketio_app/chat_space.html', {})

def create_new_duel(request):
    #create new duel and get its ID
    
    newduel = Duel.objects.create()
    print("new duel id ", newduel.id)
    newduel.duel_url = newduel.id
    newduel.save()
    
    gameStates[newduel.id] = engine.GameState.get_default_gamestate(sio, newduel.id)

    return HttpResponseRedirect(reverse('socketio_app:duel_lobby', args=(newduel.duel_url,)))

def duel_lobby(request, duel_url):
    duel = get_object_or_404(Duel, pk=duel_url)
    if (duel.player_set.count() >= 2):
        print("duel with 2 or more players")
        return HttpResponseRedirect(reverse('socketio_app:duel_room', args=(duel.id,)) + "?player_id=SPECTATOR")
    else:
        print("duel with less than two players")
        return render(request, 'socketio_app/duel_lobby.html', {'duel': duel})

def enter_duel_room(request, duel_url): #for entering the duel room as a player
    duel = get_object_or_404(Duel, pk=duel_url)
    nickname = request.POST['nickname']
    #check if nickname doesn't exist, if so
    if (duel.player_set.count() < 2):
        pnum =  duel.player_set.count()
        duel.player_set.create(nickname = nickname, player_number = pnum)
        theplayer = duel.player_set.last()
        return HttpResponseRedirect(reverse('socketio_app:duel_room', args=(duel.id,)) + "?player_id=" + str(theplayer.id))
    else:
        return render(request, 'socketio_app/duel_lobby.html', {'duel': duel, 'error_message':"The duel already has two players"})
    
def duel_room(request, duel_url):
    duel = get_object_or_404(Duel, pk=duel_url)
    player_id = request.GET.get('player_id')
    
    player_number = ""
    player_nickname = ""

    if player_id == "None" or player_id == "SPECTATOR":
        player_number = "SPECTATOR"
        player_nickname = "Spectator"
    else:
        player = get_object_or_404(Player, pk=int(player_id))
        player_number = player.player_number
        player_nickname = player.nickname

    return render(request, 'socketio_app/duel_room.html', {'duel' : duel, 'player_number': player_number, 'player_nickname' : player_nickname})


def background_thread():
    #Example of how to send server generated events to clients.
    count = 0
    while True:
        sio.sleep(10)
        count += 1
        sio.emit('my_response', {'data': 'Server generated event'},
                 namespace='/test')

def startup_GameState(duel_id):
    gameStates[duel_id].startup()
    
@sio.event
def join_duel_room(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    sio.enter_room(sid, "duel" + str(duel.id) + "_public_info")
    gameStatesBySid[sid] = gameStates[duel.id]

    if (message['pnum'] == "0" and duel.player_zero_joined == False):
        playerzero = duel.player_set.get(player_number = 0)
        playerzero.sid = sid
        playerzero.save()
        duel.player_zero_joined = True
        duel.save()
        print("Player 0 joined")
        sio.enter_room(sid, "duel" + str(duel.id) + "_player0_info")
        gameStates[duel.id].dict_of_sids[0] = sid
 
    elif (message['pnum'] == "1" and duel.player_one_joined == False):
        playerone = duel.player_set.get(player_number = 1)
        playerone.sid = sid
        playerone.save()
        duel.player_one_joined = True
        duel.save()
        print("Player 1 joined")
        sio.enter_room(sid, "duel" + str(duel.id) + "_player1_info")
        gameStates[duel.id].dict_of_sids[1] = sid
    
    elif (message['pnum'] == "SPECTATOR"):
        print("Spectator joined")
        spectator_id = gameStates[duel.id].spectator_count
        sio.enter_room(sid, "duel" + str(duel.id) + "_spectator_info")
        sio.enter_room(sid, "duel" + str(duel.id) + "_spectator" + str(spectator_id) + "_info")
        gameStates[duel.id].dict_of_sids['spectator' + str(spectator_id)] = sid
        gameStates[duel.id].spectator_count += 1

        if len(gameStates[duel.id].waiting_for_players) > 0:
            gameStates[duel.id].spectators_to_refresh_view.append(spectator_id)
        else:
            gameStates[duel.id].refresh_view(spectator_id)

        
    
    if duel.player_one_joined == True and duel.player_zero_joined == True and gameStates.get(duel.id) is not None:
        if gameStates.get(duel.id).has_started == False:
            print(duel.id, "beginning")
            startup_GameState(duel.id)


@sio.event
def ask_for_action_choices(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))

    if (message['pnum'] != 'SPECTATOR'):
        theplayer = duel.player_set.get(player_number = int(message['pnum']))
        if (theplayer.sid == sid):
            print("ask for action choices on card", message['cardid'])
            
            action_name_list = gameStates[duel.id].return_available_action_names(int(message['cardid']))
        
            print(action_name_list)
            sio.emit('display_action_choices', {'cardid': message['cardid'], 'actions': action_name_list}, room=sid)
        else:
            print("Fake player attempted to create action list")

@sio.event
def button_activated(sid, message):
    print("Button unclicked event for player", message['pnum']) 

@sio.event
def ask_run_action(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))
    
    if (theplayer.sid == sid): #ask_for_action_choices already asked for that
       gameStates[duel.id].run_action_asked_for(int(message['cardid']), message['action_name'])


@sio.event
def move_complete(sid, message): #this should actually be called animation_complete
   
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    #theplayer = duel.player_set.get(player_number = int(message['pnum']))
    already_removed = False
    try:
        gameStates[duel.id].waiting_for_players.remove(sid)
    except KeyError:
        already_removed = True
        
    #the already_removed condition check is an attempt to thwart an 'unsolicited response' bug
    if already_removed == False and len(gameStates[duel.id].waiting_for_players) == 0:
        gameStates[duel.id].stop_waiting_for_players()
        

@sio.event
def target_card_chosen(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))

    if (theplayer.sid == sid):
        gameStates[duel.id].process_card_choice(int(message['cardid']))

@sio.event
def target_zone_chosen(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))

    if (theplayer.sid == sid):
        gameStates[duel.id].process_zone_choice(message['zonename'])

@sio.event
def send_answer(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))

    if (theplayer.sid == sid):
        print(message['question'] + message['answer'])
        gameStates[duel.id].process_answer(message['question'], message['answer'])

@sio.event
def ask_phase_change(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))

    if (theplayer.sid == sid):
        gameStates[duel.id].phase_transition_asked_funcs[message['phase']]()

@sio.event
def pass_action(sid, message):
    duel = get_object_or_404(Duel, pk=int(message['duelid']))
    theplayer = duel.player_set.get(player_number = int(message['pnum']))

    if (theplayer.sid == sid):
        gameStates[duel.id].keep_running_steps = True
        gameStates[duel.id].run_steps()



@sio.event
def connect(sid, environ):
    sio.emit('my_response', {'data': 'Connected', 'count': 0}, room=sid)


@sio.event
def disconnect(sid):
    print('Client disconnected')
    theGameState = gameStatesBySid[sid]
    was_waiting_for_player = True
    try:
        theGameState.waiting_for_players.remove(sid)
    except KeyError:
        was_waiting_for_player = False

    list_of_pnums_to_delete = []
    for pnum in theGameState.dict_of_sids.keys():
        if theGameState.dict_of_sids[pnum] == sid:
            list_of_pnums_to_delete.append(pnum)

    for pnum in list_of_pnums_to_delete:
        del theGameState.dict_of_sids[pnum]
    
    #Add an "end the duel if the leaving player was a duelist

    #This is there to catch the case where the last player the gamestate
    #was waiting for was a spectator and this player leaves the room before the waiting is finished.
    if was_waiting_for_player and len(theGameState.waiting_for_players) == 0:
        theGameState.stop_waiting_for_players()



