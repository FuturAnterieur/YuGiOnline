import engine.Zones as Zones
import math

class Player:
    def __init__(self, pid):
        self.player_id = pid
        strpid = str(pid)
        self.deckzone = Zones.Zone(strpid + "_Deck", 50, self)
        self.hand = Zones.Hand(strpid + "_Hand",  self)
        self.monsterzones = Zones.FieldZoneArray(strpid + "_Monster", self, 5)
        self.spelltrapzones = Zones.FieldZoneArray(strpid + "_Spelltrap", self, 5) 
        self.pendulumlowzone = self.spelltrapzones.listofzones[0]
        self.pendulumhighzone = self.spelltrapzones.listofzones[4]
        self.graveyard = Zones.Graveyard(strpid + "_GY", self)
        self.fieldzone = Zones.Zone(strpid + "_Field", 1, self)
        self.lifepoints = 1000
        self.other = None
        self.normalsummonsperturn = 1
        self.gamestate = None

    def give_deck(self, listofcards):
        for card in listofcards:
            card.owner = self
            card.location = "Deck"
        self.deckzone.add_cards(listofcards)

    def init_card_actions_and_effects(self, gamestate):
        for card in self.deckzone.cards:
            card.init_actions_and_effects(gamestate)

   
    def add_life_points(self, gamestate, amount):
        self.lifepoints += amount
        print("Player" + str(self.player_id) + "'s lifepoints are now at " + str(self.lifepoints))
        if(self.lifepoints <= 0):
            
            gamestate.winner = self.other
        
