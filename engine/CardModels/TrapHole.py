from engine.CardModel import NormalTrapCardModel
from engine.Effect import Effect
import engine.Action
from engine.Event import Event
import engine.Bans

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, CAUSE_EFFECT


class TrapHoleEffect(Effect):
    def __init__(self):
        super(TrapHoleEffect, self).__init__("TrapHoleEffect", "Trap")
        
    def init(self, gamestate, card):
        super().init(card)
        self.spellspeed = 2
        self.SummonedMonster = None

        self.potential_target = None
        self.args = {'target' : None}

        self.effect_event = Event("TrapHoleEvent", self.parent_card, self, "respond", "OFast", self.MatchOnTHCompatibleSummon)
        self.effect_event.funclist.append(self.LaunchNormalTrapActivationForTH)

        self.set_event = Event("TrapHoleOnSet", self.parent_card, self, "immediate", "", self.MatchOnTHSet)
        self.set_event.funclist.append(self.TurnOnTHEvent)

        self.leaves_field_event = Event("TrapHoleOnLeaveField", self.parent_card, self, "immediate", "", self.MatchTHTurnOff)
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
        if action.name == "Normal Summon Monster" and action.card.face_up == True and action.card.attack >= 1000:
            self.potential_target = action.card
            result = True

        return result

    def LaunchNormalTrapActivationForTH(self, gamestate):
        self.card.actiondict["Activate"].run(gamestate)

    def reqs(self, gamestate):

        if not self.effect_event.in_timing:
            return False

        result = False
        #do the check for the Activate's Target action too
        print("MatchOnTHCompatible found valid target. Checking immunities...")
        HypotheticalDestroyAction = engine.Action.ChangeCardZone()
        HypotheticalDestroyAction.init(engine.Action.CCZDESTROY, self.potential_target, False, self)
        if HypotheticalDestroyAction.check_for_bans_and_immunities(self.potential_target, gamestate):
            print("Immunity test passed. Target is valid.")
            result = True

        return result

        #Trap Hole actually works through the summon response window (but not the summon negation window) 
        #AND the summon response window will work through lastresolvedactions 
         
    def Activate(self, gamestate):
        #choose the target if many choices are possible (which would only happen if 
        #many monsters are summoned at once, which I am not even sure is possible)
        
        #Actually, according to the card text, only one target is possible (if another monster is summoned,
        #the first one misses the timing, I think).  

        self.args['target'] = self.potential_target
        
    def Resolve(self, gamestate):
        #effects that negate other effects (negating the effect, and not the activation) don't prevent them from activating
        if not self.is_negated.get_value(gamestate) and self.args['target'] is not None:
            
            DestroyAction = engine.Action.ChangeCardZone()
            DestroyAction.init(engine.Action.CCZDESTROY, self.args['target'], CAUSE_EFFECT, self, False, True)
        
            if DestroyAction.check_for_bans_and_immunities(self.args['target'], gamestate):
                DestroyAction.run(gamestate)


TrapHole = NormalTrapCardModel("Trap Hole",  "Dump a monster with 1000 or more ATK", 'trap_hole.jpg', TrapHoleEffect)

