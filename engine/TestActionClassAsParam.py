class Action1:
    def run(card):
        print(card.atk)


class Action2:
    def run(card):
        print(card.defense)


class Card:
    def __init__(self, atk, defense):
        self.atk = atk
        self.defense = defense

        self.actiondict = {}
        self.actiondict["1"] = Action1
        self.actiondict["2"] = Action2


Hamon = Card(4000, 3999)

Hamon.actiondict["1"].run(Hamon)
