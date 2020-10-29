class BanishBan:
    def __init__(self, parent_effect):
        self.parent_effect = parent_effect
        self.parent_card = parent_effect.parent_card
        pass

    def bans_action(self, action, gamestate):
        banned = False
        is_negated = self.parent_effect.is_negated.get_value(gamestate)
        if not is_negated and action.__class__.__name__ == "ChangeCardZone" and action.args['tozone'].type == "Banished":
            banned = True
        #do not check for unaffected here
        

        return banned
