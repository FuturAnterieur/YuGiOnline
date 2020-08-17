import engine.Action
import engine.Cards
import engine.Effect
import engine.HaltableStep


from collections import deque

class Phase:
    def __init__(self, name, funclist):
        self.name = name
        self.funclist = funclist

    def execute(self):
        for func in self.funclist:
            func()

class TriggerEvent:
    def __init__(self, name, card, effect, triggertype, category, matches):
        self.card = card
        self.type = triggertype
        self.category = category
        self.name = name
        self.matches = matches
        self.funclist = []

    def execute(self, gamestate):
        for func in self.funclist:
            func(gamestate)

    def can_be_chained_now(self, gamestate): 
        if gamestate.is_building_a_chain == False:
            return False
        
        if gamestate.curspellspeed <= 1:
            return self.effect.spellspeed > gamestate.curspellspeed 

        elif gamestate.curspellspeed > 1:
            return self.effect.spellspeed >= gamestate.curspellspeed

class GameState:
    def __init__(self, firstplayer, otherplayer, sio, duel_id):
        self.sio = sio
        self.duel_id = duel_id
        firstplayer.other = otherplayer
        otherplayer.other = firstplayer
        self.turnplayer = firstplayer
        self.otherplayer = firstplayer.other
        firstplayer.gamestate = self
        otherplayer.gamestate = self

        self.cardsById = {}

        for card in self.turnplayer.deckzone.cards:
            self.cardsById[card.ID] = card

        for card in self.otherplayer.deckzone.cards:
            self.cardsById[card.ID] = card

        self.normalsummonscounter = 0 #for the current turn
        self.lastaction = ""


        self.curphase = "None"
        self.battlephasebegan = False
        self.battlephaseended = False
        self.inbattlephase = False
        self.indamagestep = False
        
        self.insummonnegationwindow = None
        
        self.inresponsewindow = None #response window for optional when-triggers
        
        self.ownerofcurrenteffect = None
        self.curspellspeed = 0
        self.action_stack = []
        self.outer_action_stack_level = 0

        
        self.chainlinks = []
        self.cards_chain_sends_to_graveyard = []
        self.record_LRA = True
        self.lastresolvedactions = [] 
        
        self.action_waiting_for_a_card_choice = None
        self.answer_arg_name = None

        self.step_waiting_for_answer = None
        self.waiting_for_one_action_choice = False
        self.player_to_stop_waiting_when_run_action = None

        self.player_in_multiple_action_window = None

        self.bannedactions = set()
        self.monstersthatattackedthisturn = []

        self.winner = None
        
        self.phases = []
        self.steps_to_do = deque()
        self.keep_running_steps = True
        self.has_started = False

        self.dict_of_sids = {}
        self.waiting_for_players = set()
        self.spectator_count = 0

        self.curphase = "Before startup"
        self.phase_transition_triggers = {'draw_phase' : [], 'standby_phase' : [], 'main_phase_1' : [],
                                'battle_phase' : [], 'main_phase_2' : [], 'end_phase' : [], 'turn_switch' : []}

        self.phase_transition_asked_funcs = {'battle_phase' : self.set_battle_phase, 'main_phase_2' : self.set_main_phase_2,
                'end_phase' : self.set_end_phase}
        
        self.if_triggers = []
        self.is_building_a_chain = False

        self.when_triggers = []
        self.immediate_triggers = []
    
        self.triggers_to_run = []

        self.saved_if_triggers = {'MTP' : [], 'MOP' : [], 'OTP' : [], 'OOP' : []}
        self.chainable_optional_if_triggers = {'OTP' : [], 'OOP' : []}

        self.chainable_optional_when_triggers = { 'VTP' : [], 'ITP' : [], 'VOP' : [], 'IOP' : [] }

        self.triggerevents = []

        firstplayer.init_card_actions_and_effects(self)
        otherplayer.init_card_actions_and_effects(self)
        
        #self.overridable_actions = {"tribute_monster" : tribute_monster, "draw_card" : draw_card}

        #self.overridable_checks = {"normal_summon_requirements" : normal_summon_requirements}

    def startup(self):
        self.has_started = True
        self.sio.emit('begin_duel', {}, room="duel" + str(self.duel_id) + "_public_info")
        self.turn_start()
        
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
        for trigger in self.phase_transition_triggers[phase_name]: #phase transition triggers are also TriggerEvents
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
        
    def set_main_phase_1(self):
        self.phase_transition('main_phase_1')

    def set_battle_phase(self):
        self.phase_transition('battle_phase')
        self.battlephasebegan = True
        self.inbattlephase = True
        
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.turnplayer, 'battle_phase_start_step'))
        self.steps_to_do.append(engine.HaltableStep.SetMultipleActionWindow(self.otherplayer, 'battle_phase_start_step'))
        self.steps_to_do.append(engine.HaltableStep.SetBattleStep())

    def set_main_phase_2(self):
        self.phase_transition('main_phase_2')
        self.battlephaseended = True
        self.inbattlephase = False

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
        return list(card.give_current_choices(self)) 

    def run_action_asked_for(self, cardId, action_name):
        if (self.player_to_stop_waiting_when_run_action is not None):

            if_trigger_cat_to_clear = 'OTP' if self.player_to_stop_waiting_when_run_action.other == self.turnplayer else 'OOP'

            engine.HaltableStep.clear_chainable_if_triggers(self, if_trigger_cat_to_clear)
            engine.HaltableStep.clear_chainable_when_triggers(self)

            waiting_player = self.player_to_stop_waiting_when_run_action
            self.sio.emit('stop_waiting', {}, room =  "duel" + str(self.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
            self.player_to_stop_waiting_when_run_action = None

            self.keep_running_steps = True

        #self.lastresolvedactions.clear() #i don't think this is appropriate here
        #if it would stay here, activating a new chain link could remove the LRA at the base of the chain

        card = self.cardsById[cardId]
        action = card.actiondict[action_name]
        action.run(self)
    
    def process_answer(self, question_code, answer):
        step = self.step_waiting_for_answer
        aan = self.answer_arg_name
        step.args[aan] = answer

        if self.step_waiting_for_answer.__class__.__name__ == "OpenWindowForResponse":
            #no need for the question code if we use that

            responding_player = self.step_waiting_for_answer.args[self.step_waiting_for_answer.rpan]
            waiting_player = responding_player.other
            
            if (answer == "No"):
                self.sio.emit('stop_waiting', {}, room =  "duel" + str(self.duel_id) + "_player" + str(waiting_player.player_id) + "_info")
                
                if_trigger_cat_to_clear = 'OTP' if responding_player == self.turnplayer else 'OOP'

                engine.HaltableStep.clear_chainable_if_triggers(self, if_trigger_cat_to_clear)
                engine.HaltableStep.clear_chainable_when_triggers(self)

                self.keep_running_steps = True
                self.run_steps()

            elif (answer == "Yes"):
                self.waiting_for_one_action_choice = True
                self.player_to_stop_waiting_when_run_action = waiting_player

            
        elif self.step_waiting_for_answer.__class__.__name__ == "AskQuestion":
            self.keep_running_steps = True
            self.run_steps()


    def end_duel(self, winner):
        self.curphase = "Duel ended"
        self.sio.emit('end_duel', {'winner' : str(winner.player_id)}, room="duel" + str(self.duel_id) + "_public_info")
    

    def reset_turn_variables(self):
        self.battlephasebegan = False
        self.battlephaseended = False
        self.normalsummonscounter = 0
        for monstercard in self.monstersthatattackedthisturn:
            monstercard.attackedthisturn = False
        self.monstersthatattackedthisturn.clear()

        for zonenum in self.turnplayer.spelltrapzones.occupiedzonenums:
            card = self.turnplayer.spelltrapzones.get_card(zonenum)
            print("End of turn review", card.name, card.cardclass, card.face_up, card.wassetthisturn)
            if card.wassetthisturn == True:
                card.wassetthisturn = False

    def change_players(self):
        self.turnplayer = self.otherplayer
        self.otherplayer = self.turnplayer.other

    def get_available_choices(self, player):
        counter = 0
        choices = {}
        choicesforcards = {}
        for handcard in player.hand.cards:
            index = "hand" + str(counter)
            choicesforcards[index] = handcard.give_current_choices(self)
            if len(choicesforcards[index]) > 0:
                choices[index] = handcard
            counter += 1

        counter = 0
        for monsterzone in player.monsterzones.listofzones:
            index = "monster" + str(counter)
            if counter in player.monsterzones.occupiedzonenums:
                monstercard = monsterzone.cards[0]
                choicesforcards[index] = monstercard.give_current_choices(self)
                if len(choicesforcards[index]) > 0:
                    choices[index] = monstercard
            counter += 1

        counter = 0
        for magiczone in player.spelltrapzones.listofzones:
            index = "spelltrap" + str(counter)
            if counter in player.spelltrapzones.occupiedzonenums:
                magiccard = magiczone.cards[0]
                #some continuous spell/trap cards have activatable effects
                choicesforcards[index] = magiccard.give_current_choices(self)
                if len(choicesforcards[index]) > 0:
                    choices[index] = magiccard
            counter += 1

        counter = 0
        for gycard in player.graveyard.cards:
            index = "GY" + str(counter)
            choicesforcards[index] = gycard.give_current_choices(self)
            if len(choicesforcards[index]) > 0:
                choices[index] = gycard
            counter += 1
    
        for i, card in choices.items():
            if card is None:
                print(i)
            else:
                print(i + " : " + card.name)

        return choices, choicesforcards
        

    def run_steps(self):
        while len(self.steps_to_do) > 0 and self.keep_running_steps == True:
            step = self.steps_to_do.popleft()
            print("running step " + step.__class__.__name__)
            step.run(self)
            

        if len(self.steps_to_do) == 0:
            print("Finished running scheduled steps")
            
    
    
        
        

def get_default_gamestate(sio, duel_id):
    yugi = engine.Player.Player(0)
    kaiba = engine.Player.Player(1)
    
    medesc0 = "A mystical defensive elf 0"
    addesc0 = "An attack dragon 0"
    dmdesc = "The ultimate wizard in terms of attack and defense."
    ssdesc = "Level 6 example monster"

    mysticalelf0 = engine.Cards.NormalMonsterCard("Mystical Elf", "Light", "Spellcaster", 4, 800, 2000, medesc0, 'kero_chill.png')
    alexdragon0 = engine.Cards.NormalMonsterCard("Alexandrite Dragon", "Light", "Dragon", 4, 2000, 100, addesc0, 'alexandrite_dragon.jpg')
    summonedskull0 = engine.Cards.NormalMonsterCard("Summoned Skull", "Dark", "Fiend", 6, 2500, 1200, ssdesc, 'barrel_dragon.png') 
    darkmagician0 = engine.Cards.NormalMonsterCard("Dark Magician", "Dark", "Spellcaster", 7, 2500, 2000, dmdesc, 'barrel_dragon.png')
    
    traphole0 = engine.Cards.TrapCard("Trap Hole", "Dump a monster with 1000 or more ATK", engine.Effect.TrapHoleEffect(), 'trap_hole.jpg')

    yugi.give_deck([darkmagician0, traphole0])
    kaiba.give_deck([summonedskull0, alexdragon0])

    return GameState(yugi, kaiba, sio, duel_id)

