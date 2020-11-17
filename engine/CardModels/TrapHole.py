
from engine.Cards import NormalTrapCard
from engine.Effect import Effect
import engine.Action
from engine.Event import Event
import engine.Bans

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, CAUSE_EFFECT, STATE_ACTIVATE, STATE_RESOLVE, FACEUPTOEVERYONE


class TrapHoleEffect(Effect):
    def __init__(self, gamestate, card):
        super().__init__("TrapHoleEffect", "Trap", card)
        
        self.spellspeed = 2
        self.SummonedMonster = None

        self.args = {'potential_target' : None, 'target' : None}

        self.effect_event = Event("TrapHoleEvent", self.parent_card, self, [self.parent_card.actiondict, "Activate"], "respond", "OFast", self.MatchOnTHCompatibleSummon)
        self.effect_event.funclist.append(self.LaunchNormalTrapActivationForTH)

        self.set_event = Event("TrapHoleOnSet", self.parent_card, self, None, "immediate", "", self.MatchOnTHSet)
        self.set_event.funclist.append(self.TurnOnTHEvent)

        self.leaves_field_event = Event("TrapHoleOnLeaveField", self.parent_card, self, None, "immediate", "", self.MatchTHTurnOff)
        self.leaves_field_event.funclist.append(self.TurnOffTHEvent)

        gamestate.immediate_events.append(self.set_event)
        gamestate.immediate_events.append(self.leaves_field_event)

    def MatchOnTHSet(self, action, gamestate):
        return action.__class__.__name__ == "SetSpellTrap" and action.card == self.parent_card

    def TurnOnTHEvent(self, gamestate):
        gamestate.respond_events.append(self.effect_event)

    def MatchTHTurnOff(self, action, gamestate):
        return action.__class__.__name__ == "TurnOffPassiveEffects" and action.zone.type == "Field" and action.card == self.parent_card
        #if it was a CardLeavesZoneEvents, it wouldn't work in all cases, because if an effect is negated, 
        #the destruction of its card does not call a CardLeavesZoneEvents step


    def TurnOffTHEvent(self, gamestate):
        if (self.effect_event in gamestate.respond_events):
            gamestate.respond_events.remove(self.effect_event)


    def MatchOnTHCompatibleSummon(self, action, gamestate):
        result = False
        if action.name == "Normal Summon Monster" and action.card.face_up == FACEUPTOEVERYONE and action.card.attack >= 1000:
            self.args['potential_target'] = action.card
            result = True

        return result

    def LaunchNormalTrapActivationForTH(self, gamestate):
        self.card.actiondict["Activate"].run(gamestate)

    def reqs(self, gamestate):

        if not self.effect_event.in_timing:
            return False

        result = False
        #do the check for the Activate's Target action too
        #being unaffected cannot prevent an effect from being activated
        print("reqs found valid target. Checking blocks and bans...")
        HypotheticalTargetAction = engine.Action.Target()
        HypotheticalTargetAction.init(self.parent_card, [], self, 'target')
        HypotheticalTargetAction.args['chosen_target'] = self.args['potential_target']

        HypotheticalDestroyAction = engine.Action.ChangeCardZone()
        HypotheticalDestroyAction.init(engine.Action.CCZDESTROY, self.args['potential_target'], False, self)
        
        action_desc_list = [{'action' : HypotheticalDestroyAction, 'card' : self.args['potential_target'], 'in_activate_or_resolve' : STATE_RESOLVE},
                {'action' : HypotheticalTargetAction, 'card' : self.args['potential_target'], 'in_activate_or_resolve' : STATE_ACTIVATE}]
        if self.check_if_activation_is_allowed(action_desc_list, gamestate):
            print("Blocks and bans test passed. Target is valid.")
            result = True

        return result

    def Activate(self, gamestate):
        #choose the target if many choices are possible (which would only happen if 
        #many monsters are summoned at once, which I am not even sure is possible)
        
        #Actually, according to the card text, only one target is possible (if another monster is summoned,
        #the first one misses the timing, I think).  

        self.args['target'] = self.args['potential_target']
        
    def check_if_target_still_valid(self):
        return self.args['target'] is not None and self.args['target'].face_up == FACEUPTOEVERYONE and self.args['target'].location == "Field" and self.args['target'].attack >= 1000

    def Resolve(self, gamestate):
        print(self.is_negated.get_value(gamestate))
        print(self.check_if_target_still_valid())
        print(self.affects_card(self.args['target'], gamestate))

        if not self.is_negated.get_value(gamestate) and self.check_if_target_still_valid() and self.affects_card(self.args['target'], gamestate):
            print("Trap Hole neg/unaff test passed")

            DestroyAction = engine.Action.ChangeCardZone()
            DestroyAction.init(engine.Action.CCZDESTROY, self.args['target'], CAUSE_EFFECT, self, False, True)
        
            action_desc_list = [{'action': DestroyAction, 'card': self.args['target']}]

            if self.check_if_resolve_is_blocked(action_desc_list, gamestate):
                print("Block test passed. Trap Hole Resolve will be called.")
                DestroyAction.run(gamestate)


class TrapHole(NormalTrapCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Trap Hole",  "Dump a monster with 1000 or more ATK", 'trap_hole.jpg', TrapHoleEffect, ID, owner, gamestate)



