from engine.Effect import Effect
import engine.Action


class MysticalSpaceTyphoonEffect(Effect):
    def __init__(self):
        super().__init__("MysticalSpaceTyphoonEffect", "Quick-Spell")

    def init(self, gamestate, card):
        super().init(card)
        self.was_negated = False
        self.spellspeed = 2
        self.args = {'targeted_spelltrap' : None, 'potential_targets' : []}

    def reqs(self, gamestate):
        #search for spell/trap cards on the field
        #put them in potential_targets
        #(check for immunities and bans)
        players = [gamestate.yugi, gamestate.kaiba]

        self.args['potential_targets'].clear()
        for player in players:
            for card in player.spelltraps_on_field:
                HypotheticalTargetAction = engine.Action.Target()
                HypotheticalTargetAction.init(self.parent_card, [], self, 'targeted_spelltrap')
                HypotheticalTargetAction.args['chosen_target'] = card
                result1 = HypotheticalTargetAction.check_for_bans_and_immunities(card, gamestate, STATE_PRE_ACTIVATE)

                HypotheticalDestroyAction = engine.Action.ChangeCardZone()
                HypotheticalDestroyAction.init(engine.Action.CCZDESTROY, card, False, self)
                result2 = HypotheticalDestroyAction.check_for_bans_and_immunities(card, gamestate, STATE_PRE_ACTIVATE)

                result = result1 and result2

                if result:
                    self.args['potential_targets'].append(card)


    def Activate(self, gamestate):
        TargetAction = engine.Action.Target()
        TargetAction.init(self.parent_card, self.args['potential_targets'], self, 'targeted_spelltrap')
        TargetAction.run(gamestate)

    def Resolve(self, gamestate):
        #check if target still meets the requirements
        #if not, resolve without effect
        #otherwise resolve with effect


