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
    def init(self, firstplayer, event_type):
        self.args = {}
        self.args['firstplayer'] = firstplayer
        self.args['secondplayer'] = firstplayer.other
        self.event_type = event_type

    def run(self, gamestate):
        
        step1 = engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'firstplayer', 'FirstplayerUsesRW')
        step2 = engine.HaltableStep.RunStepIfCondition(self, 
                engine.HaltableStep.OpenWindowForResponse(self, 'response_window:' + self.event_type, 'secondplayer', 'SecondplayerUsesRW'), 
                RunOtherPlayerWindowCondition, 'FirstplayerUsesRW')
        
        list_of_steps = [step1, step2]

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()

def TTRNonEmpty(gamestate, args):
    return len(gamestate.triggers_to_run) > 0


"""
The idea with RunTriggersCondition is that a further sequence of events (maybe including a chain) can always
be launched from the RunTriggers of the pre-existing one. Every time RunTriggers happens, 
the outer action stack level is raised by 1.
"""
def RunTriggersCondition(gamestate, args):
    return len(gamestate.action_stack) == gamestate.outer_action_stack_level + 1

def EndOfChainCondition(gamestate, args):
    return len(gamestate.chainlinks) == 0

def RunMAWForOtherPlayerCondition(gamestate, args):
    return gamestate.player_in_multiple_action_window == gamestate.otherplayer

def RunIfSaysYes(gamestate, args, answer_arg_name):
    answer = args[answer_arg_name]
    return answer == "Yes"

class ChainSendsToGraveyard(Action):
    def run(self, gamestate):
        self.args = {}
        
        gamestate.curspellspeed = 0

        list_of_steps = []
        cardcounter = 0

        for cardinfo in gamestate.cards_chain_sends_to_graveyard:
            card = cardinfo['card']
            if card.location != 'Graveyard' and card.location != 'Banished':
                #this check might be redundant but I'm keeping just in case a card gets sent to the graveyard
                #AFTER its call to AddCardToChainSendsToGraveyard
                self.args['card' + str(cardcounter)] = card
                self.args['tozone' + str(cardcounter)] = card.owner.graveyard 
            
                zonenum = card.zone.zonenum
                card.zonearray.pop_card(zonenum)
                card.owner.graveyard.add_card(card)

                list_of_steps.extend( [engine.HaltableStep.MoveCard(self, 'card' + str(cardcounter) , 'tozone' + str(cardcounter)),
                                        engine.HaltableStep.EraseCard(self, 'card' + str(cardcounter))])

                if (cardinfo['was_negated'] == False):
                    list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, CardLeavesFieldTriggers, 'card' + str(cardcounter)))
                
                
                list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, CardSentToGraveyardTriggers, 'card' + str(cardcounter)))
                #does the sending of cards to the graveyard at the end of chain activate triggers?
                #the wiki says these events are considered to be simultaneous to the last event in the chain.

                #the wiki also says that if an activation was negated, its corresponding card will be sent to the graveyard if necessary
                #at the end of the chain (as expected) but it will not count as having be sent there from the field.

            cardcounter += 1

        gamestate.cards_chain_sends_to_graveyard.clear()
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class RunTriggers(Action): #this function will always be ran at the end of a chain or sequence of events
    def __init__(self, for_what_event, at_end_of_events = True):
        self.at_end_of_events = at_end_of_events
        self.for_what_event = for_what_event

    def ask_trigger_steps_util(self, trigger, player_arg_name):
        return [engine.HaltableStep.AskQuestion(self, player_arg_name, 'want_to_activate_trigger:' + trigger.effect.name, 'Yes_No', 'want_to_activate_trigger_answer' ),
            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.AddTriggerToTTR(trigger), RunIfSaysYes, 'want_to_activate_trigger_answer') ]

    def run(self, gamestate):
        self.args = {}
        self.args['turnplayer'] = gamestate.turnplayer
        self.args['otherplayer'] = gamestate.otherplayer
        self.args['for_what_event'] = self.for_what_event

        if (self.at_end_of_events):
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


        
        #what happens when an optional effect is triggered and scheduled for a SEGOC chain?
        #the choice is given to the player to activate the effect or not,
        #and then, if there is more than one trigger in the category,
        #the player who owns them decides in which order they get stacked on the chain
        #(same principle as for mandatory effects).

        #in a SEGOC chain, VTP (visible when-triggers) and OTP (optional if-triggers) are treated as being in the same category

        
        #then run the chain

        list_of_steps.extend([engine.HaltableStep.ClearChainableWhenTriggers(self), #they'll be refreshed by the response windows that need them
                                engine.HaltableStep.ClearChainableIfTriggers(self), #we don't need those anymore 
                                engine.HaltableStep.ClearSavedIfTriggers(self),  #and not those too
                                engine.HaltableStep.RunStepIfElseCondition(self, 
                                            engine.HaltableStep.LaunchTTR(self), 
                                            engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'turnplayer', 'for_what_event'), 
                                            TTRNonEmpty)])
        if (self.at_end_of_events):
            list_of_steps.append(engine.HaltableStep.LowerOuterActionStackLevel(self))
        
        #the same structure of If-Else LaunchTTR vs RunResponseWindows can be used inside the Actions that constitute chain links

        #this will call the run of the first action in the triggers_to_run list

        #doing a run_steps should suffice after that.    

        #Actions that add to chains should have an option to specify another action that takes the place of their response window
        #so that pre-built SEGOC chains can be made

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()
       
def ActionStackEmpty(gamestate, args):
    return len(gamestate.action_stack) == 0

class RunMAWsAtEnd(Action):

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, gamestate.curphase)]

        if gamestate.player_in_multiple_action_window == gamestate.otherplayer:
            list_of_steps.append(engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, gamestate.curphase))
        
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
def run_for_trigger_action(action, gamestate):
    list_of_steps = [engine.HaltableStep.RunImmediateTriggers(action),
                    engine.HaltableStep.ProcessIfTriggers(action),
                    engine.HaltableStep.AppendToLRAIfRecording(action)]

    for i in range(len(list_of_steps) - 1, -1, -1):
        gamestate.steps_to_do.appendleft(list_of_steps[i])
        
    gamestate.run_steps()

class CardLeavesFieldTriggers(Action):
    def init(self, card):
        super(CardLeavesFieldTriggers, self).init("Card Leaves Field", card)
        self.args = {}

    def default_run(self, gamestate):
        #but its run_if_triggers has to be properly ordered in respect to other actions
        
        #gamestate.clear_lra_if_at_no_triggers() 
        #this is only a sequential sub-action (an intermediate step) so its LRA should be stacked with
        #already existing ones

        run_for_trigger_action(self, gamestate)

    run_func = default_run

class CardSentToGraveyardTriggers(Action):
    def init(self, card):
        super(CardSentToGraveyardTriggers, self).init("Card sent to Graveyard", card)
        self.args = {}

    def default_run(self, gamestate):
        run_for_trigger_action(self, gamestate)

    run_func = default_run
        
class DestroyCard(Action):
    
    def init(self, card, is_contained):
        super(DestroyCard, self).init("Destroy Card", card)
        self.args = {'destroyedcard' : card, 'fromzone' : card.zone, 'tozone' : card.owner.graveyard, 'this_action' : self}
        self.is_contained = is_contained

    def default_run(self, gamestate):
        print(self.card.name, "destroyed")
        
        if (self.card in gamestate.monsters_to_be_destroyed_by_battle):
            gamestate.monsters_to_be_destroyed_by_battle.remove(self.card)

        clear_lra_step = engine.HaltableStep.DoNothing(self) if self.is_contained else engine.HaltableStep.ClearLRAIfRecording(self)

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                            clear_lra_step,
                        engine.HaltableStep.MoveCard(self, 'destroyedcard', 'tozone'),
                            engine.HaltableStep.EraseCard(self, 'destroyedcard'),
                            engine.HaltableStep.DestroyCardServer(self, 'destroyedcard'),
                            engine.HaltableStep.InitAndRunAction(self, CardLeavesFieldTriggers, 'destroyedcard'),
                            engine.HaltableStep.InitAndRunAction(self, CardSentToGraveyardTriggers, 'destroyedcard'),
                            engine.HaltableStep.ProcessIfTriggers(self),
                            engine.HaltableStep.AppendToLRAIfRecording(self),
                            engine.HaltableStep.RunImmediateTriggers(self),
                            engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunTriggers('Card destroyed')), RunTriggersCondition),
                            engine.HaltableStep.PopActionStack(self),
                            engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        

        gamestate.run_steps()


    run_func = default_run


class FlipMonsterFaceUp(Action):
    def init(self, card):
        super(FlipMonsterFaceUp, self).init(card)
        self.args = {'monster' : card, 'player1' : card.owner, 'player2' : card.owner.other}

    def run(self, gamestate):
        #no ClearLRA because this will always be a sub-action
        list_of_steps = [engine.HaltableStep.ChangeCardVisibility(self, ['player1', 'player2'], 'monster', "1"),
                        engine.HaltableStep.ProcessFlipTriggers(self)]

        #flip effects in a summon situation :
        #they will be added to the saved if-triggers 
        #and will thus be triggered during the SEGOC chain building at the end of the summon.

        #in a battle situation,
        #the RunImmediateTriggers will add an if-trigger that triggers at AfterDamageCalculation

        #so a flip trigger's category is 'if' (either mandatory or optional), but it goes in the gamestate.flip_triggers container.
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()



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
            return False
        else:
            return True
    
    def default_run(self, gamestate):
                 
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self), engine.HaltableStep.ClearLRAIfRecording(self)]
        
        #'Monster' is not an arg from the args dict but a parameter indicating to choose among monster zones
        list_of_steps_for_one_tribute = [engine.HaltableStep.ChooseOccupiedZone(self, 'Monster', 'deciding_player', 'target_player', 'chosen_monster'),
                                         engine.HaltableStep.InitAndRunAction(self, DestroyCard, 'chosenmonster', 'destroy_is_contained')]

        for i in range(self.numtributesrequired):
            list_of_steps.extend(list_of_steps_for_one_tribute)

        ending_steps = [engine.HaltableStep.ProcessIfTriggers(self), engine.HaltableStep.AppendToLRAIfRecording(self), 
                        engine.HaltableStep.RunImmediateTriggers(self), 
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers('Monsters tributed')), RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
        
        list_of_steps.extend(ending_steps)
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        
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
                'otherplayer' : card.owner.other, 'event1' : 'Monster would be summoned'}

    def reqs(self, gamestate):
        player = self.card.owner

        if self.checkbans(gamestate) == False:
            return False
        
        if player != gamestate.turnplayer or (gamestate.curphase != 'main_phase_1' and gamestate.curphase != 'main_phase_2'):
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

        #TODO : steps (and javascript) for the selection of a free zone
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, self.TributeAction), 
                                                                                    RunTributeCondition, 'summonedmonster'),
                        engine.HaltableStep.AskQuestion(self, 'actionplayer', 'choose_position', 'ATK_DEF', 'ATK_or_DEF_answer'),  
                        engine.HaltableStep.InitAndRunAction(self, MonsterWouldBeSummonedTriggers, 'summonedmonster'),
                        engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'actionplayer', 'event1'), 
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, NormalSummonMonsterCore, 'summonedmonster', 'ATK_or_DEF_answer', 'this_action'), 
                            CheckIfNotNegated, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunTriggers('Tribute and monster summoned')), 
                                RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)] 
        #even if the summon is negated, we run RunTriggers, because there may be if-triggers that can be run, and even if there isn't any, some when triggers may be activatable (i.e. for the destroy that may have happened during the tribute).

        #the summon negation window must first be open to the action player, and then to the other player if the action player has chosen not to play anything for it.
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        
        gamestate.run_steps()

        """
        engine.HaltableStep.SetSummonNegationWindow(self),
                        engine.HaltableStep.OpenWindowForResponse(self, 'Summon Negation Window', 
                            'actionplayer', 'ActionPlayerUsesNegationWindow'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.OpenWindowForResponse(self, 'Summon Negation Window', 
                                'otherplayer', 'OtherPlayerUseNegationWindow'), 
                            RunOtherPlayerWindowCondition, 'ActionPlayerUsesNegationWindow'),
                        engine.HaltableStep.UnsetSummonNegationWindow(self),
        """

    run_func = default_run

class MonsterWouldBeSummonedTriggers(Action):
    def init(self, card):
        super(MonsterWouldBeSummonedTriggers, self).init("Monster would be summoned", card)
        self.args = {}

    def run(self, gamestate):
        run_for_trigger_action(self, gamestate)

class NormalSummonMonsterCore(Action):
    def init(self, card, position, parentNormalSummonAction):
        super(NormalSummonMonsterCore, self).init("Normal Summon Monster", card)
        self.args = {'summonedmonster': card, 'position' : position, 'chosenzone' : card.owner.monsterzones.listofzones[2], 
                'action_player' : card.owner, 'other_player' : card.owner.other}
        self.parentNormalSummonAction = parentNormalSummonAction

    def run(self, gamestate):
         #optional when-effects for the destroy occuring in Tribute miss their timing
        list_of_steps = [ engine.HaltableStep.ClearLRAIfRecording(self),
                engine.HaltableStep.NSMCServer(self, 'summonedmonster', 'chosenzone', 'position'), 
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

        if self.player != gamestate.turnplayer or (gamestate.curphase != 'main_phase_1' and gamestate.curphase != 'main_phase_2'):
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
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers('Spell/Trap set')), 
                            RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]

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


def CheckIfCardOnField(gamestate, args, card_arg_name):
    card = args[card_arg_name]
    return card.location == "Field"

class ActivateNormalTrap(Action):
    
    def init(self, card, effect):
        super(ActivateNormalTrap, self).init("Activate Normal Trap", card)
        self.effect = effect
        self.args = {'this_action' : self, 'card' : card, 'effect' : effect, 'actionplayer' : card.owner, 'otherplayer' : card.owner.other, 'action1' : 'Normal trap activated'}

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
        
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.SetBuildingChain(self),
                         engine.HaltableStep.ActivateNormalTrapBeforeActivate(self, 'card', 'effect'),
                         engine.HaltableStep.ChangeCardVisibility(self, ['otherplayer', 'actionplayer'], 'card', "1"),
                         engine.HaltableStep.DisableLRARecording(self),
                         engine.HaltableStep.CallEffectActivate(self, 'effect'),
                         engine.HaltableStep.EnableLRARecording(self),
                         engine.HaltableStep.AppendToChainLinks(self),
                         engine.HaltableStep.RunStepIfElseCondition(self, engine.HaltableStep.LaunchTTR(self), 
                             engine.HaltableStep.InitAndRunAction(self, RunResponseWindows, 'otherplayer', 'action1'), TTRNonEmpty),  
                         engine.HaltableStep.UnsetBuildingChain(self),
                         engine.HaltableStep.PopChainLinks(self),
                         engine.HaltableStep.RunStepIfCondition(self, 
                                        engine.HaltableStep.InitAndRunAction(self, ResolveNormalTrapCore, 'card', 'effect'),
                                        CheckIfNotNegated, 'this_action'),
                         engine.HaltableStep.RunStepIfCondition(self,
                                        engine.HaltableStep.AddCardToChainSendsToGraveyard(self, 'card'),
                                        CheckIfCardOnField, 'card'),
                         engine.HaltableStep.RunStepIfCondition(self, 
                                                engine.HaltableStep.RunAction(self, ChainSendsToGraveyard()), EndOfChainCondition),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers('Chain resolved')), RunTriggersCondition),
                         engine.HaltableStep.PopActionStack(self),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
                         
            
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

class DeclareAttack(Action):

    def init(self, card):
        super(DeclareAttack, self).init("Declare Attack", card)
        self.args = {'this_action' : self, 'player' : self.card.owner, 'target_player' : self.card.owner.other, 'attacking_monster' : card, 'target_arg_name' : 'target'}


    def reqs(self, gamestate):
        if len(gamestate.action_stack) > 0:
            return False
        
        if gamestate.curphase != "battle_phase":
            return False

        if gamestate.current_battle_phase_step != "battle_step":
            return False
        
        if gamestate.attack_declared == True:
            return False

        if self.card.attacks_declared_this_turn >= self.card.max_attacks_per_turn:
            return False

        return True

    def default_run(self, gamestate):
        self.card.attacks_declared_this_turn += 1
        gamestate.attack_declared = True
        gamestate.attack_declared_action = self
        gamestate.replay_was_triggered = False

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.InitAndRunAction(self, SelectAttackTarget, 'attacking_monster', 'this_action', 'target_arg_name'),
                        engine.HaltableStep.InitAndRunAction(self, AttackDeclarationTriggers, 'this_action'),
                        engine.HaltableStep.InitAndRunAction(self, AttackTargetingTriggers, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunTriggers('Attack declared')), 
                            RunTriggersCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step')]
        
        for i in range(len(list_of_steps) - 1, -1, -1): 
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()

    run_func = default_run

def DirectAttackChoice(gamestate, args, da_arg_name):
    answer = args[da_arg_name]
    return answer == "Yes"

class SelectAttackTarget(Action):
    def init(self, card, parent_declare_attack_action, target_arg_name):
        super(SelectAttackTarget, self).init("Declare Attack", card)
        self.pdaa = parent_declare_attack_action
        self.taa = target_arg_name
        self.args = {}

    def run(self, gamestate):
        list_of_steps = []
        if len(self.card.owner.other.monsterzones.occupiedzonenums) == 0:
            self.pdaa.args[self.taa] = 'direct_attack'

        else:
            if self.card.can_attack_directly:
                list_of_steps.extend([engine.HaltableStep.AskQuestion(self.pdaa, 'player', "want_attack_directly", 'Yes_No', 'direct_attack_answer'),
                                    engine.HaltableStep.RunStepIfElseCondition(self.pdaa, 
                                        engine.HaltableStep.SetArgToValue(self.pdaa, self.taa, 'direct_attack'),
                                        engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'Monster', 'player', 'target_player', self.taa),
                                        DirectAttackChoice, 'direct_attack_answer')])

            else:
                list_of_steps.extend([engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'Monster', 'player', 'target_player', self.taa)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class AttackDeclarationTriggers(Action):
    def init(self, parent_declare_attack_action):
        super(AttackDeclarationTriggers, self).init("Attack declared", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        run_for_trigger_action(self, gamestate)


class AttackTargetingTriggers(Action):
    def init(self, parent_declare_attack_action):
        super(AttackTargetingTriggers, self).init("Attack targeting", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        run_for_trigger_action(self, gamestate)

def AttackTargetingReplayCondition(gamestate, args):
    return gamestate.replay_was_triggered


def RACWasNotCancel(gamestate, args, answer_arg_name):
    return args[answer_arg_name] != "CancelAttack"


class AttackTargetingReplay(Action):
    def init(self, original_declare_attack_action):
        super(AttackTargetingReplay, self).init("Attack replay", parent_declare_attack_action.card)
        self.odaa = original_declare_attack_action
        self.args = self.odaa.args
        self.args['this_action'] = self

    
    def default_run(self, gamestate):
        gamestate.replay_was_triggered = False
        gamestate.immediate_triggers.append(gamestate.AttackReplayTrigger)
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.AskQuestion(self, 'player', "replay_action_choice", 'CancelAttack_SelectTarget', 'rac_answer'),
                        engine.HaltableStep.RunStepsIfElseCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, ReselectTargetCore, 'this_action'),
                            engine.HaltableStep.CancelAttackInGamestate(self),
                            RACWasNotCancel, 'rac_answer'),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_battle_step'),
                        engine.HaltableStep.RunAction(self, BattleStepBranchOut())]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

    run_func = default_run

class ReselectTargetCore(Action):
    def init(self, parent_replay_action):
        super(ReselectTargetCore, self).init("Attack replay", parent_declare_attack_action.card)
        self.pra = parent_replay_action

    def run(self, gamestate):
        #a replay triggers for 'A monster is targeted by an attack' but not for 'a monster declares an attack'

        gamestate.attack_declared_action = self.pra
        list_of_steps = [engine.HaltableStep.InitAndRunAction(self, SelectAttackTarget, 'attacking_monster', 'this_action', 'target_arg_name'),
                        engine.HaltableStep.InitAndRunAction(self, AttackTargetingTriggers, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.RunAction(self, RunTriggers()), 
                            RunTriggersCondition)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()
    
"""
the battle step ends with BattleStepBranchOut
a replay also ends with this action

In it, we evaluate if a replay is needed through AttackTargetingReplayCondition 
(which just asks for the state of the gamestate.replay_was_triggered variable)

Setting this replay_was_triggered flag belongs to the gamestate.

For now, there is only a trigger checking if an opponent's monster has left the field, 
but we would also need to check for :

- Any situation where The number of monsters on the turn player's opponent's side of the field changes, no matter how briefly
    (so that also means to check if monsters are added to the opponent's side of the field, and to check if there are ownership switches)
This first condition can be dealt with with immediate triggers. But two other conditions can cause a replay :

- A monster is no longer able to attack.
- A monster that is attacking another monster gains the ability to attack directly due to a card effect.

These two conditions need the change to be permanent to actually cause the replay to happen, and cannot be dealt with with immediate triggers.

"""
class BattleStepBranchOut(Action):
    def run(self, gamestate):
        self.args = {}
        list_of_steps = []

        gamestate.immediate_triggers.remove(gamestate.AttackReplayTrigger)

        if gamestate.attack_declared == True:
            self.args['ad_action'] = gamestate.attack_declared_action
            list_of_steps.append(engine.HaltableStep.RunStepIfElseCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, AttackTargetingReplay, 'ad_action'),
                            engine.HaltableStep.InitAndRunAction(self, LaunchDamageStep, 'ad_action'), 
                            AttackTargetingReplayCondition))

        else:
            list_of_steps.append(engine.HaltableStep.RunAction(self, LaunchEndStep()))

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

def TargetIsMonsterAndIsFaceDown(gamestate, args, target_arg_name):
    target = args[target_arg_name]
    res = False
    if target != 'direct_attack':
        if target.face_up == FACEDOWN:
            res = True

    return res

def TargetMonsterStillOnField(gamestate, args, target_arg_name):
    target = args[target_arg_name]
    res = False
    if target == 'direct_attack':
        res = True
    elif target.location == "Field":
        res = True

    return res


class LaunchDamageStep(Action):
    def init(self, attack_declare_action):
        self.ad_action = attack_declare_action
        self.args = self.ad_action.args
        self.args['ad_action'] = self.ad_action
        self.args['this_action'] = self

    def run(self, gamestate):
        gamestate.current_battle_phase_step = 'damage_step'
        gamestate.indamagestep = True
        list_of_steps = [engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.InitAndRunAction(self, StartOfDamageStepTriggers, 'this_action'), 
                        engine.HaltableStep.RunAction(self, RunTriggers('damage_step_start', False)), 
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_start'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_start'),
                        engine.HaltableStep.InitAndRunAction(self, BeforeDamageCalculationTriggers, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunTriggers('damage_step_BDC', False)), 
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.RunStepIfCondition(self,
                            engine.HaltableStep.InitAndRunAction(self, FlipMonsterFaceUp, 'target'), 
                            TargetIsMonsterAndIsFaceDown, 'target'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_BDC'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_BDC'),
                        engine.HaltableStep.RunStepIfCondition(self,
                            engine.HaltableStep.InitAndRunAction(self, DuringDamageCalculation, 'this_action'),
                                TargetMonsterStillOnField, 'target'),
                        engine.HaltableStep.InitAndRunAction(self, AfterDamageCalculationTriggers, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunTriggers('damage_step_ADC', False)), 
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_ADC'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_ADC'),
                        engine.HaltableStep.InitAndRunAction(self, BattleSendsMonstersToGraveyard, 'this_action'),
                        engine.HaltableStep.InitAndRunAction(self, EndOfDamageStepTriggers, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunTriggers('damage_step_end',False)),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'damage_step_end'),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'damage_step_end'),
                        engine.HaltableStep.InitAndRunAction(self, CeaseDuringDamageStepEffects, 'this_action')]

            #a flip effect will work as a mandatory or optional if-effect that triggers at AfterDamageCalculationTriggers.
            #Otherwise it could be triggered during the open window following BeforeDamageCalculation.
            #So FlipMonsterFaceUp can be fed immediate triggers that register the monster's flip effect
            #as having to be added to chainable_optional_when_triggers at AfterDamageCalculation.
            #It's either that or I implement a special gamestate container for flip-effect monsters 
            #having to trigger their flip-effect at the next AfterDamageCalculation.

            #D.D. Warrior Lady would be a Visible When-Trigger triggering after damage calculation.
            #And remember : Ryko the Lighstworn Hunter (a flip monster) and D.D. Warrior Lady go into a SEGOC chain
            #if they trigger during the same battle.


        list_of_steps.extend([engine.HaltableStep.SetBattleStep(),
                            engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step'),
                            engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_battle_step'),
                            engine.HaltableStep.RunAction(None, engine.Action.BattleStepBranchOut())])

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()
                            
class DamageStepTriggerAction(Action):
    def init(self, ds_action):
        self.name = self.__class__.__name__
        self.ds_action = ds_action
        self.args = self.ds_action.args

    def run(self, gamestate):
        run_for_trigger_action(self, gamestate)
        
class StartOfDamageStepTriggers(DamageStepTriggerAction):
    def init(self, ds_action):
        super(StartOfDamageStepTriggers, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "start"
        super(StartOfDamageStepTriggers,self).run(gamestate)

class BeforeDamageCalculationTriggers(DamageStepTriggerAction):
    def init(self, ds_action):
        super(BeforeDamageCalculationTriggers, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "before_damage_calculation"
        super(BeforeDamageCalculationTriggers,self).run(gamestate)

class DuringDamageCalculation(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "during_damage_calculation"
        list_of_steps = [engine.HaltableStep.RunImmediateTriggers(self),
                        engine.HaltableStep.ProcessIfTriggers(self),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.PerformDamageCalculation(self),
                        engine.HaltableStep.InitAndRunAction(self, MonstersMarkedTriggersForAll, 'this_action'),
                        engine.HaltableStep.RunAction(self, RunTriggers('during_damage_calculation', False)),
                        engine.HaltableStep.ClearLRAIfRecording(self)]
               
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

        #this will substract life points and place monsters in the monsters_to_be_destroyed_by_battle container
        #it will also run a MonsterMarkedToBeDestroyedByBattle trigger
        #which probably won't be used as most 'destroyed by battle' effects trigger during the end of the damage step,
        #when the monsters are actually sent to the graveyard.

class MonstersMarkedTriggersForAll(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        list_of_steps = []
        counter = 0
        for monster in gamestate.monsters_to_be_destroyed_by_battle:
            self.args['monster' + str(counter)] = monster
            list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, MonsterMarkedTriggers, 'monster' + str(counter)))
        
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

class MonsterMarkedTriggers(Action):
    def init(self, card):
        super(MonsterMarkedTriggers, self).init(card)

    def run(self, gamestate):
        run_for_trigger_action(self, gamestate)



class AfterDamageCalculationTriggers(DamageStepTriggerAction):
    def init(self, ds_action):
        super(AfterDamageCalculationTriggers, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "after_damage_calculation"
        super(AfterDamageCalculationTriggers,self).run(gamestate)

class EndOfDamageStepTriggers(DamageStepTriggerAction):
    def init(self, ds_action):
        super(EndOfDamageStepTriggers, self).init(ds_action)

    def run(self, gamestate):
        gamestate.current_damage_step_timing = "end"
        super(EndOfDamageStepTriggers,self).run(gamestate)


class BattleSendsMonstersToGraveyard(Action):
    def init(self, ds_action):
        self.ds_action = ds_action
        self.args = ds_action.args

    def run(self, gamestate):
        list_of_steps = []
        counter = 0
        for monster in gamestate.monsters_to_be_destroyed_by_battle:
            self.args['monster' + str(counter)] = monster
            gamestate.monsters_to_be_destroyed_by_battle.remove(monster)
            list_of_steps.append(engine.HaltableStep.InitAndRunAction(self, DestroyMonsterByBattle, 'monster' + str(counter)))

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

class DestroyMonsterByBattle(Action):
    def init(self, card):
        super(DestroyMonsterByBattle, self).init(card)
        self.args = {'monster' : card, 'DestroyActionIsContained' : True}
    
    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.InitAndRunAction(self, DestroyCard, 'monster', 'DestroyActionIsContained'),
                        engine.HaltableStep.AppendToLRAIfRecording(self),
                        engine.HaltableStep.ProcessIfTriggers(self),
                        engine.HaltableStep.RunImmediateTriggers(self),
                        engine.HaltableStep.PopActionStack(self)]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()


class CeaseDuringDamageStepEffects(DamageStepTriggerAction):
    def init(self, ds_action):
        super(CeaseDuringDamageStepEffects, self).init(ds_action)

    def run(self, gamestate):
        list_of_steps = [engine.HaltableStep.RunImmediateTriggers(self)]

        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()


class LaunchEndStep(Action):
    def run(self, gamestate):
        self.args = {}
        gamestate.current_battle_phase_step = 'end_step'
        list_of_steps = [engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_end_step'),
                         engine.HaltableStep.SetMultipleActionWindow(gamestate.otherplayer, 'battle_phase_end_step'),
                         engine.HaltableStep.LetTurnPlayerChooseNextPhase()]
        
        for i in range(len(list_of_steps) - 1, -1, -1):
                gamestate.steps_to_do.appendleft(list_of_steps[i])
        
        gamestate.run_steps()

