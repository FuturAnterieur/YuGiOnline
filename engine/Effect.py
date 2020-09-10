
import engine.GameState
import engine.Action as Action
import engine.HaltableStep

class Effect:
    def __init__(self, name, etype, does_target):
        self.name = name
        self.type = etype
        self.does_target = does_target

def MatchOnADC(action, gamestate):
    return action.__class__.__name__ == "AfterDamageCalculationTriggers"

class FlipEffect(Effect):
    def __init__(self, name, etype, does_target):
        super(FlipEffect, self).__init__(name, etype, does_target)
        self.ADC_trigger = None

    def RemoveADCTriggerFromIfTriggers(self, gamestate):
        gamestate.if_triggers.remove(self.ADC_trigger)

#attempts at implementing certain immunities
class ImmuneToTrap(Effect):
    def __init__(self):
        super(ImmuneToTrap, self).__init__("ImmuneToTrap", "Immune", False)
    
    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blockeffect(self, effect):
        if effect.etype == "Trap" and self.is_negated == False:
            return True
        else:
            return False



#but what if a card cannot be targeted by an effect type?
class CantBeTargetedByTrap(Effect):
    def __init__(self):
        super(CantBeTargetedByTrap, self).__init__("CBTbTrap", "CantBeTargeted", False)

    def init(self, gamestate, card):
        self.card = card
        self.is_negated = False

    def blockeffect(self, effect):
        if effect.etype == "Trap" and effect.does_target == True and self.is_negated == False:
            return True
        else:
            return False


class TrapHoleEffect(Effect):
    def __init__(self):
        super(TrapHoleEffect, self).__init__("TrapHoleEffect", "Trap", True)
        
    def init(self, gamestate, card):
        self.THcard = card
        self.was_negated = False
        self.spellspeed = 2
        self.SummonedMonster = None

        self.potential_targets = []

        self.effect_trigger = engine.GameState.TriggerEvent("TrapHoleTrigger", self.THcard, self, "when", "I", self.MatchOnTHCompatibleSummon)
        self.effect_trigger.funclist.append(self.LaunchNormalTrapActivationForTH)

        self.set_trigger = engine.GameState.TriggerEvent("TrapHoleOnSet", self.THcard, self, "immediate", "", self.MatchOnTHSet)
        self.set_trigger.funclist.append(self.TurnOnTHTrigger)

        self.leaves_field_trigger = engine.GameState.TriggerEvent("TrapHoleOnLeaveField", self.THcard,
                                                                    self, "immediate", "", self.MatchOnTHLeavesField)
        self.leaves_field_trigger.funclist.append(self.TurnOffTHTrigger)

        gamestate.immediate_triggers.append(self.set_trigger)
        gamestate.immediate_triggers.append(self.leaves_field_trigger)

    def MatchOnTHSet(self, action, gamestate):
        return action.__class__.__name__ == "SetSpellTrap" and action.card == self.THcard

    def TurnOnTHTrigger(self, gamestate):
        gamestate.when_triggers.append(self.effect_trigger)

    def MatchOnTHLeavesField(self, action, gamestate):
        return action.__class__.__name__ == "CardLeavesFieldTriggers" and action.card == self.THcard

    def TurnOffTHTrigger(self, gamestate):
        gamestate.when_triggers.remove(self.effect_trigger)


    def MatchOnTHCompatibleSummon(self, action, gamestate):
        if action.name == "Normal Summon Monster" and action.card.face_up == True and action.card.attack >= 1000:
            self.potential_targets.append(action.card)
            return True
        else:
            return False

    def LaunchNormalTrapActivationForTH(self, gamestate):
        self.THcard.actiondict["Activate"].run(gamestate)

    def reqs(self, gamestate):
        #I'll still have to implement trap card immunity somewhere
        full_category = engine.HaltableStep.TranslateTriggerCategory(self.effect_trigger, gamestate)
        return self.effect_trigger in gamestate.chainable_optional_when_triggers[full_category]

        #Trap Hole actually works through the summon response window (but not the summon negation window) 
        #AND the summon response window will work through lastresolvedactions 
        
        return lastactionscontainmatch # or summonresponsewindowmatches 

    def Activate(self, gamestate):
        #choose the target if many choices are possible (which would only happen if 
        #many monsters are summoned at once, which I am not even sure is possible)
        
        self.TargetedMonster = self.potential_targets[0]

    def Resolve(self, gamestate):
        #blocked = False
        #if self.SummonedMonster.effect.etype == "Immune":
        #    if self.SummonedMonster.effect.blockeffect(self):
        #        blocked = True
        #if blocked == False:
        
        DestroyAction = Action.DestroyCard()
        DestroyAction.init(self.TargetedMonster, False)
        DestroyAction.run(gamestate)
    

#le blocage des cartes qui sont CantBeTargeted dans le resolve aurait l'air de ceci :
#for zone in zonearray:
#   if zone.card.effect.etype == "CantBeTargeted" and zone.card.effect.blockeffect(self)   
#       numstoexclude.add zone.zonenum

#ca pourrait etre encapsule dans une fonction qui retourne un set de numstoexclude



