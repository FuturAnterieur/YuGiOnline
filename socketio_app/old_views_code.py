@sio.event
def join_as_player(sid, message):
    print("Join as player event with ", message['data'], message['duel'])
    #sio.enter_room(sid, message['duel']) the intended destination are all the users 
    #viewing the current page
    duel = Duel.objects.get(pk=int(message['duel']))
    print("duel number", duel.id, ", number of players : ", duel.player_set.count())
    if (duel.player_set.count() == 0):
        duel.player_set.create(nickname = message['data'], player_number = 0)
        
    elif (duel.player_set.count() == 1):
        duel.player_set.create(nickname = message['data'], player_number = 1)
        duel.can_begin = True
        duel.save()
        sio.emit('begin_duel', {})


#unused view
def enter_duel(request, duel_url):
    duel = get_object_or_404(Duel, pk=duel_url)
    print(duel.id, duel.player_set.count(), duel.can_begin)
    #load the duel lobby if the duel hasn't started
    if (duel.can_begin == False):
        return render(request, 'socketio_app/duel_lobby.html', {'duel_url' : duel.id})
    #else go to the duel room
    else:
        return render(request, 'socketio_app/duel_room.html', {'duel_url' : duel.id})

