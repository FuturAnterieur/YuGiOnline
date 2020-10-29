
from engine.Cards import ContinuousTrapCard
from engine.Effect import Effect, getContinuousCardTurnOnEffectClass, PassiveEffect
import engine.Action
from engine.Event import Event
import engine.Bans
from engine.Parameter import CCZModifier

from engine.defs import CCZDESTROY, CCZBANISH, CCZDISCARD, CCZRETURNTOHAND, SCOPE_GLOBAL


class MacroCosmosPassiveEffect(PassiveEffect):
    
    def init(self, gamestate, card):
        super().init(card)
        self.spellspeed = 2

        self.intercepted_action = None
        self.MCOnCardSentToGraveyard = CCZModifier("MCOnGrave", self.parent_card, self, SCOPE_GLOBAL, True, self.MatchOnCardSentToGraveyard, self.ChangeDestToBanished)
        
    def MatchOnCardSentToGraveyard(self, action, gamestate):
        matched = False
        if action.args['tozone'].type == "Graveyard":
            self.intercepted_action = action
            print('Macro Cosmos matched on action')
            matched = True
        return matched

    def ChangeDestToBanished(self, action, gamestate):
        print('Macro cosmos applying to target ' + self.intercepted_action.args['card'].name)
        self.intercepted_action.args['tozone'] = self.intercepted_action.args['card'].owner.banished
            

    def TurnOn(self, gamestate):
        if self.is_on == False:
            self.is_on = True
            gamestate.CCZModifiers.append(self.MCOnCardSentToGraveyard)

    def TurnOff(self, gamestate):
        if self.is_on:
            gamestate.CCZModifiers.remove(self.MCOnCardSentToGraveyard)

        self.is_on = False


class MacroCosmos(ContinuousTrapCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Macro Cosmos",  "Redirect to banished", 'macro_cosmos.jpg', 
                getContinuousCardTurnOnEffectClass('MacroCosmosTurnOn', MacroCosmosPassiveEffect, 2), ID, owner, gamestate)
