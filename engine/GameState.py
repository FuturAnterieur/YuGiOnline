import engine.Action
import engine.Cards
import engine.Effect
import engine.HaltableStep
import engine.Player
from engine.Event import Event

import engine.CardModels.NormalMonsterCardModels as NM
import engine.CardModels.TrapHole as TH
import engine.CardModels.MysticalSpaceTyphoon as MST
import engine.CardModels.MacroCosmos as MC
import engine.CardModels.ForbiddenLance as FL

import copy

from collections import deque



class Phase:
    def __init__(self, name, funclist):
        self.name = name
        self.funclist = funclist

    def execute(self):
        for func in self.funclist:
            func()


class GameState:
    def __init__(self, yugi_deck, kaiba_deck, sio, duel_id):
        self.sio = sio
        self.duel_id = duel_id

        self.zonesByName = {}
        
        self.yugi = engine.Player.Player(0, self)
        self.kaiba = engine.Player.Player(1, self)


        self.yugi.other = self.kaiba
        self.kaiba.other = self.yugi
        

        self.turnplayer = self.yugi
        self.otherplayer = self.kaiba
        
        self.normalsummonscounter = 0 #for the current turn
        self.lastaction = ""


        self.curphase = "None"

        self.battlephasebegan = False
        self.battlephaseended = False
        self.inbattlephase = False
        self.indamagestep = False
        self.current_battle_phase_step = "None"
        self.current_damage_step_timing = "None"
        
        self.curspellspeed = 0
        self.action_stack = []
        self.outer_action_stack_level = 0

        
        self.chainlinks = []
        self.cards_chain_sends_to_graveyard = []
        self.record_LRA = True
        self.lastresolvedactions = [] 
        
        self.action_waiting_for_a_choice = None
        self.answer_arg_name = None

        self.step_waiting_for_answer = None
        self.waiting_for_one_action_choice = False
        self.player_to_stop_waiting_when_run_action = None

        self.player_in_multiple_action_window = None

        self.spelltraps_that_were_set_this_turn = []
        
        self.monsters_that_attacked_this_turn = []
        self.monsters_that_changed_pos_this_turn = []
        self.monsters_that_were_summoned_this_turn = []
        self.monsters_to_be_destroyed_by_battle = []

        self.winners = []
        self.end_condition_reached = False
        self.can_end_now = True

        """
        Example scenario : 
        A single card effect causes both players to add all 5 pieces of "Exodia" to their hand, like 'Card Destruction'.

        In Exodia's effect, there is an immediate trigger for the Draw Action that does these things :
        If we are resolving an effect :
            - it sets gamestate.end_condition_reached to True
            - it appends the Exodia piece's owner to gamestate.winners
            - it adds a StopDuelIfVictoryConditionCheck to the left of the gamestate.steps_to_do deque.
              This covers the simple case where a single player draws one card and just happens to get the missing piece of Exodia.
        If we are activating an effect :
            - do nothing about the end conditions, but make sure there is a trigger that will check for these conditions
                at the next resolution of events. This on-resolution trigger can be placed at the same time as the Draw one, 
                or only in this "if we are activating an effect" clause if we wish to be more precise.


        Alternative : we create a VictoryCondition container in the gamestate
        And after each action resolution we check every victory condition in the container
        But that would require putting this VictoryConditionCheckStep at the end of every
        main action in the game

        hmmm
        

        In Card Destruction's effect's resolve, 
            there is a first set of discard actions that all happen simultaneously,
            then there is a set of draw actions that all happen simultaneously.

        This simultaneity, in regards to knowing when to end the duel, will be implemented through 
        the can_end_now variable. (there will also be a clear of LastResolvedActions between the set 
        of discards and the set of draws for the when-effects that they may trigger).

        Basically, the program structure will go like this :
            gamestate.can_end_now = False
            for i in range(n)
                steps.append(RunAction - Discard)

           steps.append(ClearLRA) 

            for i in range(n)
                steps.append(RunAction - Draw)
                
            steps.append(SetCanEndNowToTrue)
            
            and SetCanEndNowToTrue checks if the end condition was reached and stops the duel if it did.

        As far as I know, only a card effect can make several events happen 'exactly at the same time' (without first putting
        them on a chain, as in SEGOC) and, as such, will represent the only case of can_end_now being set to false.
            

        """
        
        self.phases = []
        self.steps_to_do = deque()
        self.keep_running_steps = True
        self.has_started = False

        self.dict_of_sids = {}
        self.waiting_for_players = set()
        self.spectator_count = 0
        self.cards_in_play = []
        self.spectators_to_refresh_view = []

        self.curphase = "Before startup"
        self.phase_transition_events = {'draw_phase' : [], 'standby_phase' : [], 'main_phase_1' : [],
                                'battle_phase' : [], 'main_phase_2' : [], 'end_phase' : [], 'turn_switch' : []}

        self.phase_transition_asked_funcs = {'battle_phase' : self.set_battle_phase, 'main_phase_2' : self.set_main_phase_2,
                'end_phase' : self.set_end_phase}
        

        self.bans = []
        self.modifiers = []
        self.CCZModifiers = []
        self.CCZBanModifiers = []

        
        self.trigger_events = [] #categories : MSS1, OSS1, OFast (i.e. Consolation Prize). MFast is considered as a respond event.
        self.flip_events = [] 
        
        self.is_building_a_chain = False

        self.respond_events = []  #categories : OSS1, MSS1 (does not exist, I think. Mandatory when-effects are actually trigger events), 
                                    #OFast (i.e. Trap Hole), and MFast (i.e. Doomcaliber Knight)
        self.immediate_events = []
    
        self.triggers_to_run = []

        self.saved_trigger_events = {'MSS1TP' : [], 'MSS1OP' : [], 'OSS1TP' : [], 'OSS1OP' : [], 'OFastTP' : [], 'OFastOP' : []}
        
        self.events_in_timing = {'respond_MSS1TP' : [], 'respond_MSS1OP' : [], 'respond_OSS1TP' : [], 'respond_OSS1OP' : [],
                                    'respond_OFast_LRA' : [], 'respond_OFast_CL' : [], 'respond_Oexclusive' : [],
                                'trigger_MSS1TP' : [],  'trigger_MSS1OP' : [], 'trigger_OSS1TP' : [], 'trigger_OSS1OP' : [],
                                'trigger_OFast' : []}

        self.events_meeting_reqs = {'respond_MSS1TP' : [], 'respond_MSS1OP' : [], 'respond_OSS1TP' : [], 'respond_OSS1OP' : [],
                                     'trigger_MSS1TP' : [],  'trigger_MSS1OP' : [], 'trigger_OSS1TP' : [], 'trigger_OSS1OP' : []}

        
        #Mandatory fast events go directly in self.triggers_to_run

        self.AttackReplayTrigger = Event("AttackReplayTrigger", None, 
                                    None, None, "immediate", None, self.MatchAttackConditionChanges)
        self.AttackReplayTrigger.funclist.append(self.SetReplayWasTriggered)

        self.cardsById = []

        self.cardcounter = 0
        
        for cardclass in yugi_deck:
            self.cardsById.append(cardclass(self.cardcounter, self.yugi, self))
            self.yugi.add_card_to_deck(self.cardsById[-1])
            self.cardcounter += 1
            
        for cardclass in kaiba_deck:
            self.cardsById.append(cardclass(self.cardcounter, self.kaiba, self))
            self.kaiba.add_card_to_deck(self.cardsById[-1])
            self.cardcounter += 1

        self.cur_card_choices = []

    def startup(self):
        self.has_started = True
        self.sio.emit('begin_duel', {}, room="duel" + str(self.duel_id) + "_public_info")
        
        for i in range(3):
            self.steps_to_do.append(engine.HaltableStep.RunInitialDraw(self.turnplayer))

        for i in range(3):
            self.steps_to_do.append(engine.HaltableStep.RunInitialDraw(self.otherplayer))

        self.turn_start()
        
    def initial_draw(self, player):
        DrawAction = engine.Action.DrawCard()
        DrawAction.init(player)
        DrawAction.run(self)

    def turn_start(self):
        self.steps_to_do.append(engine.HaltableStep.RunDrawPhase())
        self.steps_to_do.append(engine.HaltableStep.RunStandbyPhase())
        self.steps_to_do.append(engine.HaltableStep.SetMainPhase1())
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'main_phase_1'))
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.otherplayer, 'main_phase_1'))
        self.steps_to_do.append(engine.HaltableStep.LetTurnPlayerChooseNextPhase()) #ClickMode 0 won't allow Phase Buttons
        #They will be reserved for this step and ClickMode 3

        self.keep_running_steps = True
        self.run_steps();

    def phase_transition(self, phase_name):
        self.curphase = phase_name
        self.sio.emit('phase_change', {'phase_name' : phase_name}, room="duel" + str(self.duel_id) + "_public_info")
        self.lastresolvedactions.clear()
        for trigger in self.phase_transition_events[phase_name]: #phase transition triggers are also Events
            if trigger.matches(self): #but their matches function checks against the current gamestate, and not an action
                trigger.execute(self)

        self.lastresolvedactions.clear()

    def draw_phase(self):
        self.phase_transition('draw_phase')

        DrawAction = engine.Action.DrawCard()
        DrawAction.init(self.turnplayer)
        DrawAction.run(self)


    def standby_phase(self):
        self.phase_transition('standby_phase')
        #if cards can be activated (like Treeborn Frog), run a SetMultipleActionWindow for the turnplayer
        self.refresh_available_choices(self.turnplayer)
        list_of_steps = []


        if len(self.cur_card_choices) > 0:
            list_of_steps.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'standby_phase'))

        for i in range(len(list_of_steps) - 1, -1, -1):
            self.steps_to_do.appendleft(list_of_steps[i])
        
        self.keep_running_steps = True
        self.run_steps()



    def set_main_phase_1(self):
        self.phase_transition('main_phase_1')

    def set_battle_phase(self):
        self.phase_transition('battle_phase')
        self.battlephasebegan = True
        self.inbattlephase = True
        self.current_battle_phase_step = 'start_step'
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'battle_phase_start_step'))
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.otherplayer, 'battle_phase_start_step'))
        self.steps_to_do.append(engine.HaltableStep.SetBattleStep())
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'battle_phase_battle_step'))
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.otherplayer, 'battle_phase_battle_step'))
        self.steps_to_do.append(engine.HaltableStep.RunAction(None, engine.Action.BattleStepBranchOut()))
        #at the end of the damage step action, there will be a SetBattleStep as well as two SetMultipleActionWindow

        self.keep_running_steps = True
        self.run_steps()

    def set_main_phase_2(self):
        self.phase_transition('main_phase_2')
        self.battlephaseended = True
        self.inbattlephase = False
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'main_phase_2'))
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.otherplayer, 'main_phase_2'))
        self.steps_to_do.append(engine.HaltableStep.LetTurnPlayerChooseNextPhase())

        self.keep_running_steps = True
        self.run_steps()

    def set_end_phase(self):
        self.phase_transition('end_phase') #maybe I'll have to create steps for the end phase and turn switch transitions. We'll see.
        self.battlephaseended = True
        self.inbattlephase = False
        self.turn_switch()
    
    def turn_switch(self):
        self.phase_transition('turn_switch')
        self.reset_turn_variables()
        self.change_players()
        self.turn_start()

    def return_available_action_names(self, cardId):
        card = self.cardsById[cardId]
        return list(card.give_current_choices()) 

    def run_action_asked_for(self, cardId, action_name):
        if (self.player_to_stop_waiting_when_run_action is not None):
            stepname = self.step_waiting_for_answer.__class__.__name__
            print("Step waiting for answer on action choice : " + stepname)

            if stepname == "OpenWindowForResponse":
                engine.HaltableStep.clear_in_timing_respond_OFast_CL(self)
            elif stepname == "OpenWindowForExclusiveResponse":
                engine.HaltableStep.clear_in_timing_respond_Oexclusive(self)

            waiting_player = self.player_to_stop_waiting_when_run_action
            self.sio.emit('stop_waiting', {}, room =  "duel" + str(self.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
            self.player_to_stop_waiting_when_run_action = None

            self.keep_running_steps = True

        card = self.cardsById[cardId]
        action = card.actiondict[action_name]
        action.run(self)
    
    def process_answer(self, question_code, answer):
        step = self.step_waiting_for_answer
        aan = self.answer_arg_name
        step.args[aan] = answer

        stepname = self.step_waiting_for_answer.__class__.__name__

        if stepname == "OpenWindowForResponse" or stepname == "OpenWindowForExclusiveResponse":
            #no need for the question code if we use that
            
            
            responding_player = self.step_waiting_for_answer.args[self.step_waiting_for_answer.rpan]
            waiting_player = responding_player.other
            
            if (answer == "No"):
                if stepname == "OpenWindowForResponse":
                    engine.HaltableStep.clear_in_timing_respond_OFast_CL(self)
                else:
                    engine.HaltableStep.clear_in_timing_respond_Oexclusive(self)
                
                
                self.sio.emit('stop_waiting', {}, room =  "duel" + str(self.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
                
                self.keep_running_steps = True
                self.run_steps()

            elif (answer == "Yes"):
                self.waiting_for_one_action_choice = True
                self.player_to_stop_waiting_when_run_action = waiting_player
                
            
        elif stepname == "AskQuestion":
            self.keep_running_steps = True
            self.run_steps()
    
    def process_card_choice(self, cardid):
        ccan = self.answer_arg_name
        card = self.cardsById[cardid]
        self.action_waiting_for_a_choice.args[ccan] = card

        self.keep_running_steps = True
        self.run_steps()

    def process_zone_choice(self, zonename):
        zcan = self.answer_arg_name
        zone = self.zonesByName[zonename]
        self.action_waiting_for_a_choice.args[zcan] = zone

        self.keep_running_steps = True
        self.run_steps()

    def reset_turn_variables(self):
        self.battlephasebegan = False
        self.battlephaseended = False
        self.normalsummonscounter = 0
        
        for monstercard in self.monsters_that_attacked_this_turn:
            monstercard.attacks_declared_this_turn = 0
        self.monsters_that_attacked_this_turn.clear()

        for monstercard in self.monsters_that_changed_pos_this_turn:
            monstercard.changed_battle_position_this_turn = False
        self.monsters_that_changed_pos_this_turn.clear()

        for monstercard in self.monsters_that_were_summoned_this_turn:
            monstercard.was_summoned_this_turn = False
        self.monsters_that_changed_pos_this_turn.clear()

        for zonenum in self.turnplayer.spelltrapzones.occupiedzonenums:
            card = self.turnplayer.spelltrapzones.get_card(zonenum)
            print("End of turn review", card.name, card.cardclass, card.face_up, card.wassetthisturn)
            
        
        for spelltrap in self.spelltraps_that_were_set_this_turn:
            spelltrap.wassetthisturn = False

        self.spelltraps_that_were_set_this_turn.clear()
                

    def change_players(self):
        self.turnplayer = self.otherplayer
        self.otherplayer = self.turnplayer.other

    def refresh_available_choices(self, player, cards_to_check = None):
        card_choices = [] 

        if cards_to_check is not None:
            for card in cards_to_check:
                if len(card.refresh_and_give_current_choices(self)) > 0:
                    card_choices.append(card)

        else:
            for handcard in player.hand.cards:
                if len(handcard.refresh_and_give_current_choices(self)) > 0:
                    card_choices.append(handcard)
            
            counter = 0
            for monsterzone in player.monsterzones.listofzones:
                index = "monster" + str(counter)
                if counter in player.monsterzones.occupiedzonenums:
                    monstercard = monsterzone.cards[0]
                    if len(monstercard.refresh_and_give_current_choices(self)) > 0:
                        card_choices.append(monstercard)
                counter += 1

            counter = 0
            for magiczone in player.spelltrapzones.listofzones:
                if counter in player.spelltrapzones.occupiedzonenums:
                    magiccard = magiczone.cards[0]
                    #some continuous spell/trap cards have activatable effects
                    if len(magiccard.refresh_and_give_current_choices(self)) > 0:
                        card_choices.append(magiccard)
                counter += 1

            for gycard in player.graveyard.cards:
                if len(gycard.refresh_and_give_current_choices(self)) > 0:
                    card_choices.append(gycard)
        
        self.cur_card_choices = card_choices
        
    def add_ban(self, ban):
        self.bans.append(ban)

    def remove_ban(self, ban):
        if ban in self.bans:
            self.bans.remove(ban)

    def run_steps(self):
        while len(self.steps_to_do) > 0 and self.keep_running_steps == True:
            step = self.steps_to_do.popleft()
            print("running step " + step.__class__.__name__)
            step.run(self)
            

        if len(self.steps_to_do) == 0:
            print("Finished running scheduled steps")
            
    def MatchAttackConditionChanges(self, action, gamestate):
        if (action.__class__.__name__ == "CardLeavesZoneTriggers" and action.zone.type == "Field" 
                and action.card.owner == gamestate.otherplayer and action.card.cardclass == 'Monster'):
            return True
        elif (action.__class__.__name__ == "CardEntersZoneTriggers" and action.zone.type == "Field"
                and action.card.owner == gamestate.otherplayer and action.card.cardclass == "Monster"):
            return True

        return False
    
    def SetReplayWasTriggered(self, gamestate):
        gamestate.replay_was_triggered = True

        
    def stop_waiting_for_players(self):
        for spectator_id in self.spectators_to_refresh_view:
            self.refresh_view(spectator_id)

        self.spectators_to_refresh_view.clear()

        self.keep_running_steps = True
        self.run_steps()
        

    def refresh_view(self, spectator_id):
        #self.sio.emit('set_numcards_in_hands', {'0_Hand_numcards': len(self.yugi.hand.cards), 
           #                                 '1_Hand_numcards' : len(self.kaiba.hand.cards)}, 
           #                     room="duel" + str(self.duel_id) + "_spectator" + str(spectator_id) + "_info")

        cards_in_yugi_hand = []
        cards_in_kaiba_hand = []
        cards_on_field = []

        ciyh_ids = []
        ciyh_paths = []

        cikh_ids = []
        cikh_paths = []

        for card in self.cards_in_play:
            if card.zone.name == "0_Hand":
                cards_in_yugi_hand.append(card)
                ciyh_ids.append(str(card.ID))
                ciyh_paths.append(card.imgpath)
            elif card.zone.name == "1_Hand":
                cards_in_kaiba_hand.append(card)
                cikh_ids.append(str(card.ID))
                cikh_paths.append(card.imgpath)
            else:
                cards_on_field.append(card)

        self.sio.emit('create_cards_in_hand_spectator', {'player' : str(self.yugi.player_id), 'cardids' : ciyh_ids, 'imgpaths' : ciyh_paths},
                    room="duel" + str(self.duel_id) + "_spectator" + str(spectator_id) + "_info")

        self.sio.emit('create_cards_in_hand_spectator', {'player' : str(self.kaiba.player_id), 'cardids' : cikh_ids, 'imgpaths' : cikh_paths},
                    room="duel" + str(self.duel_id) + "_spectator" + str(spectator_id) + "_info")

        for card in cards_on_field:
            rotation = "Vertical"
            if card.__class__.__name__ == "MonsterCard":
                if card.position == "DEF":
                    rotation = "Horizontal"


            self.sio.emit('create_card', {'cardid' : str(card.ID), 'rotation': rotation, 'zone':card.zone.name, 
                                            'player' : str(card.owner.player_id), 'imgpath' : card.imgpath}, 
                                            room="duel" + str(self.duel_id) + "_spectator" + str(spectator_id) + "_info")

            self.sio.emit('change_card_visibility', {'cardid' : str(card.ID), 'visibility' : "1"}, 
                    room = "duel" + str(self.duel_id) + "_spectator" + str(spectator_id) + "_info")

    def add_player_to_winners(self, winner):
        if winner not in self.winners:
            self.winners.append(winner)

    def stop_duel(self):
        self.steps_to_do.clear()
        winner_id = self.winners[0].player_id if len(self.winners) == 1 else "DRAW"
        self.sio.emit('end_duel', {'winner' : str(winner_id)}, room = "duel" + str(self.duel_id) + "_public_info")

        

def get_default_gamestate(sio, duel_id):
    
    #yugi_deck = [NM.DarkMagician, NM.MysticalElf, TH.TrapHole]
    #kaiba_deck = [NM.MysticalElf, NM.SummonedSkull, NM.AlexandriteDragon]

    yugi_deck = [NM.DarkMagician, NM.MysticalElf, TH.TrapHole, MC.MacroCosmos, NM.AlexandriteDragon, FL.ForbiddenLance]
    kaiba_deck = [NM.MysticalElf, NM.SummonedSkull, NM.MysticalElf, TH.TrapHole, NM.AlexandriteDragon, MST.MysticalSpaceTyphoon]

    theduel = GameState(yugi_deck, kaiba_deck, sio, duel_id)


    return theduel

