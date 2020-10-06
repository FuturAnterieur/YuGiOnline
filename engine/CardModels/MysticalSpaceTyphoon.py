from engine.Effect import Effect
import engine.Action
from engine.defs import CAUSE_EFFECT
from engine.CardModel import QuickPlaySpellCardModel

class MysticalSpaceTyphoonEffect(Effect):
    def __init__(self):
        super().__init__("MysticalSpaceTyphoonEffect", "Quick-Spell")

    def init(self, gamestate, card):
        super().init(card)
        self.spellspeed = 2
        self.args = {'targeted_spelltrap' : None, 'potential_targets' : []}

    def reqs(self, gamestate):
        #search for spell/trap cards on the field
        #put them in potential_targets
        #(check for immunities and bans)
        cards_except_MST_itself = [card for card in gamestate.yugi.spelltraps_on_field + gamestate.kaiba.spelltraps_on_field 
                                        if card != self.parent_card]

        self.args['potential_targets'].clear()
        
        for card in cards_except_MST_itself:
            HypotheticalTargetAction = engine.Action.Target()
            HypotheticalTargetAction.init(self.parent_card, [], self, 'targeted_spelltrap')
            HypotheticalTargetAction.args['chosen_target'] = card
            result1 = HypotheticalTargetAction.check_for_bans_and_immunities(card, gamestate)

            HypotheticalDestroyAction = engine.Action.ChangeCardZone()
            HypotheticalDestroyAction.init(engine.Action.CCZDESTROY, card, CAUSE_EFFECT, self)
            result2 = HypotheticalDestroyAction.check_for_bans_and_immunities(card, gamestate)

            result = result1 and result2

            if result:
                self.args['potential_targets'].append(card)

        return len(self.args['potential_targets']) > 0

    def Activate(self, gamestate):
        TargetAction = engine.Action.Target()
        TargetAction.init(self.parent_card, self.args['potential_targets'], self, 'targeted_spelltrap')
        TargetAction.run(gamestate)

    def Resolve(self, gamestate):
        #check if target still meets the requirements
        #if not, resolve without effect
        #otherwise resolve with effect
        if self.is_negated.get_value(gamestate) == False and self.args['targeted_spelltrap'].location == "Field":
            DestroyAction = engine.Action.ChangeCardZone()
            DestroyAction.init(engine.Action.CCZDESTROY, self.args['targeted_spelltrap'], CAUSE_EFFECT, self)
            
            if DestroyAction.check_for_bans_and_immunities(self.args['targeted_spelltrap'], gamestate):
                DestroyAction.run(gamestate)

MysticalSpaceTyphoon = QuickPlaySpellCardModel("Mystical Space Typhoon", "Target 1 spell/trap on the field; destroy it.", 'mystical_space_typhoon.jpg', MysticalSpaceTyphoonEffect)
