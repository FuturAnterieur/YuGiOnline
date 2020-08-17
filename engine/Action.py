import engine.HaltableStep
from engine.Cards import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT

class Action:
    def init(self, name, card):
        self.name = name
        self.card = card
        if card is not None:
            self.player = card.owner
        self.was_negated = False
        
    def checkbans(self, gamestate):
        unbanned = True
        for ban in gamestate.bannedactions:
            if ban.matches(self):
                unbanned = False
                break

        return unbanned

    def run_if_triggers(self, gamestate):
        gamestate.simultaneitycounter += 1
        for event in gamestate.triggerevents:
            if event.matches(self, gamestate):
                event.execute(gamestate)
        gamestate.simultaneitycounter -= 1

    def run(self, gamestate):  #I'll have to do the same for reqs
        self.__class__.run_func(self, gamestate)

class RunResponseWindows(Action):
    def init(self, firstplayer):
        self.args = {}
        self.args['firstplayer'] = firstplayer
        self.args['secondplayer'] = firstplayer.other

    def run(self, gamestate):
        
        step1 = engine.HaltableStep.OpenWindowForResponse(self, 'response_window', 'firstplayer', 'FirstplayerUsesRW')
        step2 = engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.OpenWindowForResponse(self, 'response_window', 'secondplayer', 'SecondplayerUsesRW'), RunOtherPlayerWindowCondition, 'FirstplayerUsesRW')
        
        list_of_steps = [step1, step2]

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


def TTRNonEmpty(gamestate, args):
    return len(gamestate.triggers_to_run) > 0

def RunTriggersCondition(gamestate, args):
    return len(gamestate.action_stack) == gamestate.outer_action_stack_level + 1

def EndOfChainCondition(gamestate, args):
    return len(gamestate.chainlinks) == 0

def RunMAWForOtherPlayerCondition(gamestate, args):
    return gamestate.player_in_multiple_action_window == gamestate.otherplayer

class ChainSendsToGraveyard(Action):
    def run(self, gamestate):
        self.args = {}
        
        gamestate.curspellspeed = 0

        list_of_steps = []
        cardcounter = 0

        for card in gamestate.cards_chain_sends_to_graveyard:
            self.args['card' + str(cardcounter)] = card
            self.args['tozone' + str(cardcounter)] = card.owner.graveyard 
            
            zonenum = card.zone.zonenum
            card.zonearray.pop_card(zonenum)
            card.owner.graveyard.add_card(card)

            list_of_steps.extend( [engine.HaltableStep.MoveCard(self, 'card' + str(cardcounter) , 'tozone' + str(cardcounter)),
                                    engine.HaltableStep.EraseCard(self, 'card' + str(cardcounter)),
                                    engine.HaltableStep.InitAndRunAction(self, CardLeavesField, 'card' + str(cardcounter)),
                                    engine.HaltableStep.InitAndRunAction(self, CardSentToGraveyard, 'card' + str(cardcounter))] )
            #does the sending of cards to the graveyard at the end of chain activate triggers?
            #the wiki says these events are considered to be simultaneous to the last event in the chain

            cardcounter += 1

        gamestate.cards_chain_sends_to_graveyard.clear()
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class RunTriggers(Action): #this function will always be ran at the end of a chain or sequence of events
                                    
    def ask_trigger_steps_util(self, trigger, player_arg_name):
        return [engine.HaltableStep.AskQuestion(self, player_arg_name, 'want_to_activate_trigger:' + trigger.effect.name, 'Yes_No', 'want_to_activate_trigger_answer' ),
            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.AddTriggerToTTR(trigger), RunIfSaysYes, 'want_to_activate_trigger_answer') ]

    def run(self, gamestate):
        self.args = {}
        self.args['turnplayer'] = gamestate.turnplayer
        self.args['otherplayer'] = gamestate.otherplayer

        gamestate.outer_action_stack_level += 1

        engine.HaltableStep.refresh_chainable_when_triggers(gamestate)

        list_of_steps = []

        for trigger in gamestate.saved_if_triggers['MTP']:
            #if there is more than one trigger in a category and we are building a SEGOC chain, 
            #which we will always be doing since we are at the end of a previous chain, ask the player 
            #who owns the effects how he wants to order them in the chain
            gamestate.triggers_to_run.append(trigger)

        for trigger in gamestate.saved_if_triggers['MOP']: #meme principe pour les autres
            gamestate.triggers_to_run.append(trigger)

        
        for trigger in gamestate.saved_if_triggers['OTP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'turnplayer'))

        for trigger in gamestate.chainable_optional_when_triggers['VTP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'turnplayer'))

        for trigger in gamestate.saved_if_triggers['OOP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'otherplayer'))

        for trigger in gamestate.chainable_optional_when_triggers['VOP']:
            list_of_steps.extend(self.ask_trigger_steps_util(trigger, 'otherplayer'))



        #what happens when an optional effect is triggered through a SEGOC chain?
        #the choice is given to the player to activate the effect or not,
        #and then, if there is more than one trigger in the category,
        #the player who owns them decides in which order they get stacked on the chain
        #(same principle as for mandatory effects).

        #in a SEGOC chain, OWTP and OTP are treated as being in the same category

        
        #then run the chain

        list_of_steps.extend([engine.HaltableStep.ClearChainableWhenTriggers(self), #they'll be refreshed by the response windows that need them
                                engine.HaltableStep.ClearChainableIfTriggers(self), 
                                engine.HaltableStep.ClearSavedIfTriggers(self), 
                                engine.HaltableStep.RunStepIfElseCondition(self, 
                                            engine.HaltableStep.LaunchTTR(self), 
                                            engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'turnplayer'), 
                                            TTRNonEmpty), 
                                engine.HaltableStep.LowerOuterActionStackLevel(self),
                                engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, gamestate.curphase)]) 
        
        if gamestate.player_in_multiple_action_window == gamestate.otherplayer:
            list_of_steps.append(engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, gamestate.current_phase))

             
        #the same structure of If-Else LaunchTTR vs RunResponseWindows can be used inside the Actions that constitute chain links

        #this will call the run of the first action in the triggers_to_run list

        #doing a run_steps should suffice after that.    

        #Actions that add to chains should have an option to specify another action that takes the place of their response window
        #so that pre-built SEGOC chains can be made

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()
       




class DrawCard(Action):
    
    def init(self, player):
        super(DrawCard, self).init("Draw Card", None)
        self.player = player
        self.args = {'player' : player, 'fromzone' : player.deckzone, 'tozone' : player.hand}

    def reqs(self, gamestate):
        if len(self.player.deckzone.cards) > 0:
            return True
        else:
            return False

    def default_run(self, gamestate):
        list_of_steps = None
        if self.reqs(gamestate):
            list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                            engine.HaltableStep.DrawCardServer(self, 'drawncard'),
                            engine.HaltableStep.CreateCard(self, 'drawncard', 'fromzone'),
                            engine.HaltableStep.ChangeCardVisibility(self, ['player'], 'drawncard', '1'),
                            engine.HaltableStep.MoveCard(self, 'drawncard', 'tozone'),
                            engine.HaltableStep.ProcessIfTriggers(self),
                            engine.HaltableStep.AppendToLRAIfRecording(self),
                            engine.HaltableStep.RunImmediateTriggers(self),
                            engine.HaltableStep.PopActionStack(self)] #add a run triggers conditional step here?
        
            for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
            gamestate.run_steps()
        else:
            gamestate.end_duel(self.player.other)

    run_func = default_run

#reqs-less actions are there mostly just for triggers

class CardLeavesField(Action):
    def init(self, card):
        super(CardLeavesField, self).init("Card Leaves Field", card)
        self.args = {}

    def default_run(self, gamestate):
        #but its run_if_triggers has to be properly ordered in respect to other actions
        
        #gamestate.clear_lra_if_at_no_triggers() 
        #this is only a sequential sub-action (an intermediate step) so its LRA should be stacked with
        #already existing ones

        #actually i'm starting to think that clearLRA should never be an automatic thing at the start of an action. 
        
        list_of_steps = [engine.HaltableStep.RunImmediateTriggers(self),
                        engine.HaltableStep.ProcessIfTriggers(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

    run_func = default_run

class CardSentToGraveyard(Action):
    def init(self, card):
        super(CardSentToGraveyard, self).init("Card sent to Graveyard", card)
        self.args = {}

    def default_run(self, gamestate):
        list_of_steps = [engine.HaltableStep.RunImmediateTriggers(self),
                        engine.HaltableStep.ProcessIfTriggers(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

    run_func = default_run
        
class DestroyCard(Action):
    
    def init(self, card, is_contained):
        super(DestroyCard, self).init("Destroy Card", card)
        self.args = {'destroyedcard' : card, 'fromzone' : card.zone, 'tozone' : card.owner.graveyard, 'this_action' : self}
        self.is_contained = is_contained

    def default_run(self, gamestate):
        print(self.card.name, "destroyed")
        
        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                            clear_lra_step,
                        engine.HaltableStep.MoveCard(self, 'destroyedcard', 'tozone'),
                            engine.HaltableStep.EraseCard(self, 'destroyedcard'),
                            engine.HaltableStep.DestroyCardServer(self, 'destroyedcard'),
                            engine.HaltableStep.InitAndRunAction(self, CardLeavesField, 'destroyedcard'),
                            engine.HaltableStep.InitAndRunAction(self, CardSentToGraveyard, 'destroyedcard'),
                            engine.HaltableStep.ProcessIfTriggers(self),
                            engine.HaltableStep.AppendToLRAIfRecording(self),
                            engine.HaltableStep.RunImmediateTriggers(self),
                            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers()), RunTriggersCondition),
                            engine.HaltableStep.PopActionStack(self)]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        

        gamestate.run_steps()


    run_func = default_run


class SummonMonster(Action):

    def init(self, name, card):
        super(SummonMonster, self).init(name, card)
        

class TributeMonsters(Action):
    
    def init(self, numtributesrequired, player):
        super(TributeMonsters, self).init("Tribute Monsters", None)
        self.player = player
        self.numtributesrequired = numtributesrequired
        self.args = {'deciding_player' : self.player, 'target_player' : self.player, 'destroy_is_contained' : True, 'this_action' : self}
        
    def reqs(self, gamestate):
        if self.checkbans(gamestate) == False:
            return False

        if(len(self.player.monsterzones.occupiedzonenums) < self.numtributesrequired):
                #print("Not enough monsters can be tributed.")
            return False
        else:
            return True
    
    def default_run(self, gamestate):
                 
        ending_steps = [engine.HaltableStep.ProcessIfTriggers(self), engine.HaltableStep.AppendToLRAIfRecording(self), 
                        engine.HaltableStep.RunImmediateTriggers(self), 
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers()), RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self)]

        #'Monster' is not an arg from the args dict but a parameter indicating to choose among monster zones
        list_of_steps_for_one_tribute = [engine.HaltableStep.ChooseOccupiedZone(self, 'Monster', 'deciding_player', 'target_player', 'chosen_monster'),
                                         engine.HaltableStep.InitAndRunAction(self, DestroyCard, 'chosenmonster', 'destroy_is_contained')]
                
        for i in range(len(ending_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(ending_steps[i])
        

        for i in range(self.numtributesrequired):
            for i in range(len(list_of_steps_for_one_tribute) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps_for_one_tribute[i])

        gamestate.steps_do_do.appendleft(engine.HaltableStep.ClearLRAIfRecording(self))
        gamestate.steps_to_do.appendleft(engine.HaltableStep.AppendToActionStack(self))
        

        gamestate.run_steps()
        
    run_func = default_run


def CheckIfNotNegated(gamestate, args, action_arg_name):
    action = args[action_arg_name]
    return not action.was_negated

def RunOtherPlayerWindowCondition(gamestate, args, answer_arg_name):
    answer = args[answer_arg_name]
    return answer == "No"

class NormalSummonMonster(SummonMonster):
    
    def init(self, card):
        super(NormalSummonMonster, self).init("Normal Summon Monster", card)
        self.TributeAction = TributeMonsters()
        self.TributeAction.init(self.card.numtributesrequired, self.card.owner)
        self.args = { 'this_action' : self, 'summonedmonster' : card, 'actionplayer' : card.owner, 
                'otherplayer' : card.owner.other}

    def reqs(self, gamestate):
        player = self.card.owner

        if self.checkbans(gamestate) == False:
            return False
        
        if player != gamestate.turnplayer or gamestate.inbattlephase:
            return False
        
        if self.card.location != "Hand":
            return False

        if gamestate.normalsummonscounter == 1:
            #print("You have already normal summoned a monster this turn.")
            return False

        if len(gamestate.action_stack) > 0: #equivalent to checking if the game state is open
            return False

        if self.card.numtributesrequired == 0:
            #check if a zone is left
            if len(player.monsterzones.occupiedzonenums) == 5:
                #print("Cannot summon a monster without tributes if no zones are left.")
                return False
            else:
                return True
        else:
            return self.TributeAction.reqs(gamestate)
            

    def default_run(self, gamestate):
        
        def RunTributeCondition(gamestate, args, card_arg_name):
            card = args[card_arg_name]
            return card.numtributesrequired > 0

        gamestate.normalsummonscounter += 1 #optional : put that in a dedicated step (that must go before the summon negation window)

        #TODO : les steps pour le choix de zone libre
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, self.TributeAction), 
                                                                                    RunTributeCondition, 'summonedmonster'),
                        engine.HaltableStep.AskQuestion(self, 'actionplayer', 'choose_position', 'ATK_DEF', 'ATK_or_DEF_answer'),  
                        engine.HaltableStep.SetSummonNegationWindow(self),
                        engine.HaltableStep.OpenWindowForResponse(self, 'Summon Negation Window', 
                            'actionplayer', 'ActionPlayerUsesNegationWindow'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.OpenWindowForResponse(self, 'Summon Negation Window', 
                                'otherplayer', 'OtherPlayerUseNegationWindow'), 
                            RunOtherPlayerWindowCondition, 'ActionPlayerUsesNegationWindow'),
                        engine.HaltableStep.UnsetSummonNegationWindow(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.InitAndRunAction(self, NormalSummonMonsterCore, 'summonedmonster', 'ATK_or_DEF_answer', 'this_action'), CheckIfNotNegated, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers()), RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self)] #even if the summon is negated, we run RunTriggers, because there may be if-triggers that can be run, and even if there isn't any, some when triggers may be activatable (i.e. for the destroy that may have happened during the tribute).

        #the summon negation window must first be open to the action player, and then to the other player if the action player has chosen not to play anything for it.
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        
        gamestate.run_steps()

    run_func = default_run

class NormalSummonMonsterCore(Action):
    def init(self, card, position, parentNormalSummonAction):
        super(NormalSummonMonsterCore, self).init("Normal Summon Monster", card)
        self.args = {'summonedmonster': card, 'position' : position, 'chosenzone' : card.owner.monsterzones.listofzones[2], 
                'action_player' : card.owner, 'other_player' : card.owner.other}
        self.parentNormalSummonAction = parentNormalSummonAction

    def run(self, gamestate):
         #optional when-effects for the destroy occuring in Tribute miss their timing
        list_of_steps = [ engine.HaltableStep.ClearLRAIfRecording(self),
                engine.HaltableStep.NSMCServer(self, 'summonedmonster', 'chosenzone'), 
                         engine.HaltableStep.MoveCard(self, 'summonedmonster', 'chosenzone')]

        if (self.args['position'] == "ATK"):
            list_of_steps.append(engine.HaltableStep.ChangeCardVisibility(self, ['other_player'], 'summonedmonster', "1"))

        elif (self.args['position'] == "DEF"):
            self.args['rotation'] = "Horizontal"
            list_of_steps.extend([engine.HaltableStep.ChangeCardVisibility(self, ['action_player'], 'summonedmonster', "0"),
                                    engine.HaltableStep.RotateCard(self, 'summonedmonster', 'rotation')])

            
        list_of_steps.extend([engine.HaltableStep.ProcessIfTriggers(self.parentNormalSummonAction),
                              engine.HaltableStep.AppendToLRAIfRecording(self.parentNormalSummonAction),
                              engine.HaltableStep.RunImmediateTriggers(self.parentNormalSummonAction)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()




class ActivateMonsterEffect(Action):
    
    def init(self, gamestate, card, effect):
        super(ActivateMonsterEffect, self).init("Activate Monster Effect", card)
        self.effect = effect

    def reqs(self, gamestate): #those reqs are meant for ignition effects, mostly
        
        if self.checkbans(gamestate) == False:
            return False
        
        if self.effect.spellspeed == 1 and gamestate.curspellspeed >= 1:
            return False

        elif self.effect.spellspeed > 1 and gamestate.curspellspeed > self.effect.spellspeed:
            return False

        if self.card.location != "Field": #some effects can be activated from the graveyard or the hand though
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        return True

    def default_run(self, gamestate):
        #no card to place on the field
        #gamestate.clear_lra_if_at_no_triggers()
        cachespellspeed = gamestate.curspellspeed
        gamestate.curspellspeed = self.effect.spellspeed
        self.effect.Activate(gamestate)
        
        #what about if triggers for "a monster effect has been activated"?
        
        gamestate.chained_effects_stack.append(self.effect)
        open_window_for_response(gamestate, self.player.other)
        gamestate.chained_effects_stack.pop()

        if self.effect.was_negated == False:
            gamestate.lastresolvedactions.clear()
            self.effect.Resolve(gamestate)
            #the effect will call a sequence of actions, each calling the appropriate run_if_triggers
            #and placing the correct series of latest actions in gamestate.lastresolvedactions

            self.run_if_triggers(gamestate) #for "A monster effect has been resolved"
            gamestate.lastresolvedactions.append(self)

        gamestate.curspellspeed = cachespellspeed

    run_func = default_run

class SetSpellTrap(Action):
    
    def init(self, card):
        super(SetSpellTrap, self).init("Set Spell/Trap card", card)
        player = card.owner
        self.args = {'set_card' : card, 'chosen_zone' : player.spelltrapzones.listofzones[3], 'player' : player}

    def reqs(self, gamestate):
        if self.checkbans(gamestate) == False:
            return False

        if self.player != gamestate.turnplayer or gamestate.inbattlephase:
            return False

        if len(gamestate.action_stack) > 0:
            return False

        if self.card.location != "Hand":
            return False

        return True

    def default_run(self, gamestate):
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.SetSpellTrapServer(self, 'set_card'),
                        engine.HaltableStep.MoveCard(self, 'set_card', 'chosen_zone'),
                        engine.HaltableStep.ChangeCardVisibility(self, ['player'], 'set_card', "0"),
                        engine.HaltableStep.ProcessIfTriggers(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.RunImmediateTriggers(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers()), 
                            RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()
                        

    run_func = default_run




def basic_reqs_for_trap(action, gamestate):
    if gamestate.curspellspeed > action.effect.spellspeed:
        return False

    if action.card.location != "Field":
        return False

    if action.card.wassetthisturn == True:
        return False

    return True


class ActivateNormalTrap(Action):
    
    def init(self, card, effect):
        super(ActivateNormalTrap, self).init("Activate Normal Trap", card)
        self.effect = effect
        self.args = {'this_action' : self, 'card' : card, 'effect' : effect, 'actionplayer' : card.owner, 'otherplayer' : card.owner.other}

    def reqs(self, gamestate):
        if self.checkbans(gamestate) == False:
            return False
        
        if basic_reqs_for_trap(self, gamestate) == False:
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        if self.card.face_up != FACEDOWN: #or I could put a 'once per chain' constraint
            return False

        return True
    
    def default_run(self, gamestate):
        print("run ActivateNormalTrap called")
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.SetBuildingChain(self),
                         engine.HaltableStep.ActivateNormalTrapBeforeActivate(self, 'card', 'effect'),
                         engine.HaltableStep.ChangeCardVisibility(self, ['otherplayer', 'actionplayer'], 'card', "1"),
                         engine.HaltableStep.DisableLRARecording(self),
                         engine.HaltableStep.CallEffectActivate(self, 'effect'),
                         engine.HaltableStep.EnableLRARecording(self),
                         engine.HaltableStep.AppendToChainLinks(self),
                         engine.HaltableStep.RunStepIfElseCondition(self, engine.HaltableStep.LaunchTTR(self), 
                             engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'otherplayer'), TTRNonEmpty),  
                         engine.HaltableStep.UnsetBuildingChain(self),
                         engine.HaltableStep.PopChainLinks(self),
                         engine.HaltableStep.RunStepIfCondition(self, 
                                        engine.HaltableStep.InitAndRunAction(self, ResolveNormalTrapCore, 'card', 'effect'),
                                        CheckIfNotNegated, 'this_action'),
                         engine.HaltableStep.AddCardToChainSendsToGraveyard(self, 'card'),
                         engine.HaltableStep.RunStepIfCondition(self, 
                                                engine.HaltableStep.RunAction(self, ChainSendsToGraveyard()), EndOfChainCondition),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers()), RunTriggersCondition),
                         engine.HaltableStep.PopActionStack(self)]
                         
            
        #To do : delay the sending of the card to the graveyard only at the end of the chain
        #so here, register the card as being 'to be sent to the grave'
        #and send it to the grave in a special step at the end of the chain.
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()
        


    run_func = default_run

class ResolveNormalTrapCore(Action):
    def init(self, card, effect):
        super(ResolveNormalTrapCore, self).init("Activate Normal Trap", card)
        self.effect = effect
        self.args = {'effect' : effect}

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.ClearLRAIfRecording(self),
                         engine.HaltableStep.CallEffectResolve(self, 'effect')] #the Effect Resolve will call its own trigger-setting steps
                         #engine.HaltableStep.ProcessIfTriggers(self),
                         #engine.HaltableStep.AppendToLRAIfRecording(self), #for the actual action of resolving the card
                         #engine.HaltableStep.RunImmediateTriggers(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()

class ActivateContinuousPassiveSpell(Action):

    def init(self, gamestate, card, effect):
        super(ActivateContinuousPassiveSpell, self).init("Activate Continuous Passive Spell", card)
        self.effect = effect

    def reqs(self, gamestate):
        if self.checkbans(gamestate) == False:
            return False
        
        if gamestate.curspellspeed >= 1:
            return False

        if self.player != gamestate.turnplayer or gamestate.inbattlephase:
            return False

        if self.card.location != "Field" and len(self.player.spelltrapzones.occupiedzonenums) == 5:
            return False

        if self.card.location == "Field" and self.card.face_up == True:
            return False

        if self.effect.reqs(gamestate) == False:
            return False

        return True

    def default_run(self, gamestate):
        #gamestate.clear_lra_if_at_no_triggers()
        player = self.player

        if self.card.location == "Hand":
            player.hand.remove_card(self.card)
            self.card.face_up = FACEUPTOEVERYONE

            chosenzonenum = player.spelltrapzones.choose_free_zone()
            player.spelltrapzones.add_card(self.card, chosenzonenum)
            self.card.wassetthisturn = True

        elif self.card.location == "Field":
            self.card.face_up = FACEUPTOEVERYONE
        
        cachespellspeed = gamestate.curspellspeed
        gamestate.curspellspeed = self.effect.spellspeed

        self.effect.Activate(gamestate)
    
        gamestate.chained_effects_stack.append(self.effect)
        open_window_for_response(gamestate, self.player.other)
        gamestate.chained_effects_stack.pop()
        
        if self.effect.was_negated == False:
            gamestate.lastresolvedactions.clear()
            self.effect.Resolve(gamestate) #this is where the passive effect will be turned on
            #the effect will call a sequence of actions, each calling the appropriate run_if_triggers
            #and placing the correct series of latest actions in gamestate.lastresolvedactions

            self.run_if_triggers(gamestate) #for "A passive spell card has been activated"
            gamestate.lastresolvedactions.append(self)
        
        
        gamestate.curspellspeed = cachespellspeed

    run_func = default_run
