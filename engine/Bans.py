class BanishBan:
    def __init__(self):
        pass

    def bans_action(self, action, effect_state = 0):
        unacceptable = False
        if action.__class__.__name__ == "ChangeCardZone" and action.args['tozone'].type == "Banished" and action.intended_tozone.type == "Banished":
            unacceptable = True

        return unacceptable
