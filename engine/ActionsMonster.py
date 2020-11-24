import engine.HaltableStep
from engine.defs import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE, FACEUPTOOPPONENT, CCZTRIBUTE, CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, CAUSE_BATTLE, CAUSE_CHAIN, CAUSE_TRIBUTE

from engine.Action import Action, ChainSendsToGraveyard, RunResponseWindows, RunExclusiveResponseWindows, RunEvents, RunMAWsAtEnd, ActionStackEmpty, EndOfChainCondition, RunEventsCondition, TTRNonEmpty, CheckIfNotNegated, steps_for_event_action, FlipMonsterFaceUp, ProcessFlipEvents, ChangeCardZone

class SummonMonster(Action):

    def init(self, name, card):
        super().init(name, card)
        

class TributeMonsters(Action):
    
    def init(self, card):
        super(TributeMonsters, self).init("Tribute Monsters", None)
        self.card = card
        self.player = card.owner
        self.args = {'deciding_player' : self.player, 'destroy_is_contained' : True, 'ccz_name' : CCZTRIBUTE, 
                        'destroy_cause' : CAUSE_TRIBUTE, 'parent_effect' : None, 'this_action' : self}
        
    def reqs(self, gamestate):
        self.player = self.card.owner
        if self.check_for_bans(gamestate) == False:
            return False

        if(len(self.player.monsterzones.occupiedzonenums) < self.card.numtributesrequired):
            return False
        else:
            self.args['possible_tributes'] = self.player.monsters_on_field

            return True
    
    def default_run(self, gamestate):
                 
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self), engine.HaltableStep.ClearLRAIfRecording(self)]
        
        list_of_steps_for_one_tribute = [engine.HaltableStep.ChooseOccupiedZone(self,'deciding_player', 'possible_tributes', 'chosen_monster'),
                                         engine.HaltableStep.InitAndRunAction(self, ChangeCardZone, 'ccz_name', 
                                                    'chosen_monster', 'destroy_cause', 'parent_effect', 'destroy_is_contained')]

        for i in range(self.card.numtributesrequired):
            list_of_steps.extend(list_of_steps_for_one_tribute)

        ending_steps = [engine.HaltableStep.ProcessTriggerEvents(self), engine.HaltableStep.AppendToLRAIfRecording(self), 
                        engine.HaltableStep.RunImmediateEvents(self), 
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Monsters tributed')), RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]
        
        list_of_steps.extend(ending_steps)
        
        self.run_steps(gamestate, list_of_steps)
        

    run_func = default_run


class NormalSummonMonster(SummonMonster):
    
    def init(self, card):
        super().init("Monster would be Normal Summoned", card)
        self.TributeAction = TributeMonsters()
        self.TributeAction.init(self.card)
        self.args = { 'this_action' : self, 'summonedmonster' : card, 'actionplayer' : card.owner, 
                'otherplayer' : card.owner.other, 'event1' : 'Monster would be summoned'}

    def reqs(self, gamestate):
        player = self.card.owner

        if self.check_for_bans(gamestate) == False:
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
        player = self.card.owner
        self.args['zone_choices'] = [zone for zone in player.monsterzones.listofzones if zone.zonenum not in player.monsterzones.occupiedzonenums]
        self.card.location = "Field - In Summon Process"
        
        #TODO : steps (and javascript) for the selection of a free zone
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, self.TributeAction), 
                                                                                    RunTributeCondition, 'summonedmonster'),
                        engine.HaltableStep.ChooseFreeZone(self, 'actionplayer', 'zone_choices', 'chosen_zone'),
                        engine.HaltableStep.AskQuestion(self, 'actionplayer', 'choose_position', ['ATK', 'DEF'], 'ATK_or_DEF_answer'),  
                        engine.HaltableStep.InitAndRunAction(self, RunExclusiveResponseWindows, 'actionplayer', 'event1', 'this_action'), 
                        engine.HaltableStep.RunStepIfCondition(self, 
                            engine.HaltableStep.InitAndRunAction(self, NormalSummonMonsterCore, 'summonedmonster', 'ATK_or_DEF_answer', 'chosen_zone', 'this_action'), 
                            CheckIfNotNegated, 'this_action'),
                        engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.RunAction(self, RunEvents('Tribute and monster summoned')), 
                                RunEventsCondition),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)] 
        #even if the summon is negated, we run RunEvents, because there may be if-triggers that can be run, and even if there isn't any, some when triggers may be activatable (i.e. for the destroy that may have happened during the tribute).

        #the summon negation window must first be open to the action player, and then to the other player if the action player has chosen not to play anything for it.
        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        
        gamestate.run_steps()

    run_func = default_run


class NormalSummonMonsterCore(Action):
    def init(self, card, position, zone, parentNormalSummonAction):
        super().init("Normal Summon Monster", card)
        self.args = {'summonedmonster': card, 'position' : position, 'chosen_zone' : zone, 
                'action_player' : card.owner, 'other_player' : card.owner.other}
        self.parentNormalSummonAction = parentNormalSummonAction

    def run(self, gamestate):

        self.parentNormalSummonAction.name = "Normal Summon Monster"
        
        #optional when-effects for the destroy occuring in Tribute miss their timing
        list_of_steps = [ engine.HaltableStep.ClearLRAIfRecording(self),
                engine.HaltableStep.NSMCServer(self, 'summonedmonster', 'chosen_zone', 'position'), 
                         engine.HaltableStep.MoveCard(self, 'summonedmonster', 'chosen_zone')]

        if (self.args['position'] == "ATK"):
            list_of_steps.append(engine.HaltableStep.ChangeCardVisibility(self, ['other_player'], 'summonedmonster', "1"))

        elif (self.args['position'] == "DEF"):
            self.args['rotation'] = "Horizontal"
            list_of_steps.extend([engine.HaltableStep.ChangeCardVisibility(self, ['action_player'], 'summonedmonster', "0"),
                                    engine.HaltableStep.RotateCard(self, 'summonedmonster', 'rotation')])

            
        list_of_steps.extend([engine.HaltableStep.ProcessTriggerEvents(self),
                              engine.HaltableStep.AppendToLRAIfRecording(self),
                              engine.HaltableStep.RunImmediateEvents(self)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class ChangeBattlePosition(Action):
    def init(self, card):
        super().init("Change battle position", card)
        self.args = {'card' : card, 'rotation' : "", 'this_action' : self}

    def reqs(self, gamestate):
        if len(gamestate.action_stack) > 0:
            return False

        if self.card.owner != gamestate.turnplayer:
            return False
        
        if self.card.location != "Field":
            return False

        if gamestate.curphase != "main_phase_1" and gamestate.curphase != "main_phase_2":
            return False

        if self.card.attacks_declared_this_turn > 0:
            return False

        if self.card.changed_battle_position_this_turn:
            return False

        if self.card.was_summoned_this_turn:
            return False

        if self.card.face_up == FACEDOWN:
            return False

        return True

    def default_run(self, gamestate):
        self.card.changed_battle_position_this_turn = True
        gamestate.monsters_that_changed_pos_this_turn.append(self.card)

        if self.card.position == "DEF":
            self.card.position = "ATK"
            self.args['rotation'] = "Vertical"
        else:
            self.card.position = "DEF"
            self.args['rotation'] = "Horizontal"
        
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                         engine.HaltableStep.ClearLRAIfRecording(self),
                         engine.HaltableStep.RotateCard(self, 'card', 'rotation'),
                         engine.HaltableStep.RunImmediateEvents(self),
                         engine.HaltableStep.ProcessTriggerEvents(self),
                         engine.HaltableStep.AppendToLRAIfRecording(self),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Monster changed position')), 
                            RunEventsCondition),
                         engine.HaltableStep.PopActionStack(self),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]

        self.run_steps(gamestate, list_of_steps)

    run_func = default_run

    

class FlipSummonMonster(Action):
    def init(self, card):
        super().init("Monster would be flip summoned", card)
        self.args = {'card' : card, 'player1' : card.owner, 'player2': card.owner.other, 'rotation' : "Vertical", 'this_action' : self, 'event1' : "Monster would be flip summoned"}
        

    def reqs(self, gamestate):
        if len(gamestate.action_stack) > 0:
            return False

        if self.card.owner != gamestate.turnplayer:
            return False
        
        if self.card.location != "Field":
            return False

        if gamestate.curphase != "main_phase_1" and gamestate.curphase != "main_phase_2":
            return False

        if self.card.attacks_declared_this_turn > 0:
            return False

        if self.card.changed_battle_position_this_turn:
            return False

        if self.card.was_summoned_this_turn:
            return False

        if self.card.face_up != FACEDOWN:
            return False

        return True

    def run(self, gamestate):
        self.card.position = "ATK"
        self.card.face_up = FACEUPTOEVERYONE

        self.card.changed_battle_position_this_turn = True
        gamestate.monsters_that_changed_pos_this_turn.append(self.card)

        self.card.location = "Field - In Summon Process"
        self.name = "Monster would be Flip Summoned"

        change_vis_step = engine.HaltableStep.ChangeCardVisibility(self, ['player1', 'player2'], 'card', "1")
        summon_neg_window = engine.HaltableStep.InitAndRunAction(self, RunExclusiveResponseWindows, 'player1', 'event1', 'this_action')
        flip_step = engine.HaltableStep.RunStepIfCondition(self, 
                                        engine.HaltableStep.InitAndRunAction(self, FlipSummonCore, 'this_action'),
                                        CheckIfNotNegated, 'this_action')
        
        
        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                         engine.HaltableStep.ClearLRAIfRecording(self),
                         engine.HaltableStep.RotateCard(self, 'card', 'rotation'),
                         change_vis_step,
                         summon_neg_window,
                         flip_step, 
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Flip Summon')), 
                            RunEventsCondition),
                         engine.HaltableStep.PopActionStack(self),
                         engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunMAWsAtEnd()), ActionStackEmpty)]

        self.run_steps(gamestate, list_of_steps)


class FlipSummonCore(Action):
    def init(self, parent_flip_summon_action):
        super().init("Flip Summon Monster", parent_flip_summon_action.card)
        self.args = parent_flip_summon_action.args

    def run(self, gamestate):
        self.args['card'].location = "Field"

        list_of_steps = [engine.HaltableStep.FlipSummonServer(self, 'card'),
                        engine.HaltableStep.InitAndRunAction(self, ProcessFlipEvents, 'card'),
                        engine.HaltableStep.RunImmediateEvents(self),
                         engine.HaltableStep.ProcessTriggerEvents(self),
                         engine.HaltableStep.AppendToLRAIfRecording(self)]

        self.run_steps(gamestate, list_of_steps)
                        

def AttackerCantAttackAnymore(gamestate, args):
    attacker = gamestate.attack_declared_action.card
    return attacker.location != "Field" or attacker.position != "ATK"

class DeclareAttack(Action):

    def init(self, card):
        super().init("Declare Attack", card)
        self.args = {'odaa' : self, 'player' : self.card.owner, 'target_player' : self.card.owner.other, 
                        'attacking_monster' : card, 'target_arg_name' : 'target'}

        #odaa stands for original declare attack action
    def evaluate_potential_target_monsters(self, gamestate):
       
        list_of_possible_target_monsters = []
        for monster in self.args['target_player'].monsters_on_field:
            compatible = True
            dummy_attack = DeclareAttack()
            dummy_attack.init(self.card)
            dummy_attack.args['target'] = monster

            unbanned = dummy_attack.check_for_bans(gamestate)
            if unbanned == False:
                compatible = False

            else:
                not_blocked = dummy_attack.check_for_blocks(monster, gamestate)
                if not_blocked == False:
                    compatible = False

            if compatible:
                list_of_possible_target_monsters.append(monster)

        return list_of_possible_target_monsters

    def evaluate_if_target_can_still_be_attacked(self, gamestate):
        unbanned = self.check_for_bans(gamestate)
        
        if self.args['target'] == 'direct_attack':
            return unbanned
        else:
            if unbanned == False:
                return False

            compatible = self.check_for_blocks(self.args['target'], gamestate)
            
            return compatible
    
    def is_direct_attack_possible(self, gamestate):
        sample_direct_attack = DeclareAttack()
        sample_direct_attack.init(self.card)
        sample_direct_attack.args['target'] = 'direct_attack'

        return (self.card.can_attack_directly or len(self.args['target_player'].monsters_on_field) == 0) and sample_direct_attack.check_for_bans(gamestate)

    def reqs(self, gamestate):
        if len(gamestate.action_stack) > 0:
            return False
        
        if gamestate.curphase != "battle_phase":
            return False

        if gamestate.current_battle_phase_step != "battle_step":
            return False

        if self.card.owner != gamestate.turnplayer:
            return False

        if self.card.location != "Field":
            return False
        
        if gamestate.attack_declared == True:
            return False

        if self.card.attacks_declared_this_turn >= self.card.max_attacks_per_turn:
            return False

        if self.check_for_bans(gamestate) == False:
            return False
        
        self.args['possible_targets'] = self.evaluate_potential_target_monsters(gamestate)
        
        is_direct_attack_possible = self.is_direct_attack_possible(gamestate)

        if not is_direct_attack_possible and len(self.args['possible_targets']) == 0:
            return False

        self.card_could_attack_directly = is_direct_attack_possible
        
        return True

    def default_run(self, gamestate):
        gamestate.monsters_that_attacked_this_turn.append(self.card)
        self.card.attacks_declared_this_turn += 1
        gamestate.attack_declared = True
        gamestate.attack_declared_action = self
        gamestate.replay_was_triggered = False

        list_of_steps = [engine.HaltableStep.AppendToActionStack(self),
                        engine.HaltableStep.ClearLRAIfRecording(self),
                        engine.HaltableStep.InitAndRunAction(self, SelectAttackTarget, 'attacking_monster', 'odaa', 'target_arg_name'),
                        engine.HaltableStep.InitAndRunAction(self, AttackDeclarationEvents, 'odaa'),
                        engine.HaltableStep.InitAndRunAction(self, AttackTargetingEvents, 'odaa'),
                        engine.HaltableStep.RunStepIfCondition(self, engine.HaltableStep.RunAction(self, RunEvents('Attack declared')), 
                            RunEventsCondition),
                        engine.HaltableStep.RunStepIfCondition(self, 
                                engine.HaltableStep.CancelAttackInGamestate(self),
                                AttackerCantAttackAnymore),
                        engine.HaltableStep.PopActionStack(self),
                        engine.HaltableStep.SetMultipleActionWindow(gamestate.turnplayer, 'battle_phase_battle_step')]
        
        self.run_steps(gamestate, list_of_steps)

    run_func = default_run

def DirectAttackChoice(gamestate, args, da_arg_name):
    answer = args[da_arg_name]
    return answer == "Yes"

class SelectAttackTarget(Action):
    def init(self, card, parent_declare_attack_action, target_arg_name):
        super().init("Select attack target", card)
        self.pdaa = parent_declare_attack_action #could replace that with gamestate.attack_declared_action
        self.taa = target_arg_name
        self.args = {}

    def run(self, gamestate):
        list_of_steps = []
        if len(self.pdaa.args['possible_targets']) == 0:
            self.pdaa.args[self.taa] = 'direct_attack'

        else:
            if self.card.can_attack_directly:
                list_of_steps.extend([engine.HaltableStep.AskQuestion(self.pdaa, 'player', "want_attack_directly", ['Yes', 'No'], 'direct_attack_answer'),
                                    engine.HaltableStep.RunStepIfElseCondition(self.pdaa, 
                                        engine.HaltableStep.SetArgToValue(self.pdaa, self.taa, 'direct_attack'),
                                        engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'player', 'possible_targets', self.taa),
                                        DirectAttackChoice, 'direct_attack_answer')])

            else:
                list_of_steps.extend([engine.HaltableStep.ChooseOccupiedZone(self.pdaa, 'player', 'possible_targets', self.taa)])

        for i in range(len(list_of_steps) - 1, -1, -1):
            gamestate.steps_to_do.appendleft(list_of_steps[i])

        gamestate.run_steps()


class AttackDeclarationEvents(Action):
    def init(self, parent_declare_attack_action):
        super(AttackDeclarationEvents, self).init("Attack declared", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)


class AttackTargetingEvents(Action):
    def init(self, parent_declare_attack_action):
        super(AttackTargetingEvents, self).init("Attack targeting", parent_declare_attack_action.card)
        self.pdaa = parent_declare_attack_action
        self.args = self.pdaa.args

    def run(self, gamestate):
        los = steps_for_event_action(self, gamestate)
        self.run_steps(gamestate, los)


