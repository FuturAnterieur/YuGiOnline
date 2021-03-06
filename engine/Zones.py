from engine.defs import FACEDOWN, FACEUPTOCONTROLLER, FACEUPTOEVERYONE

class Zone:
    def __init__(self, name, cardlimit, owner, ztype, zonenum = 0):
        self.name = name
        self.cardlimit = cardlimit
        self.owner = owner
        self.cards = []
        self.type = ztype
        self.zonenum = zonenum

    def add_card(self, card):
        if(len(self.cards) < self.cardlimit):
            self.cards.append(card)
            card.zone = self

    def add_cards(self, cardlist):
        for c in cardlist:
            self.add_card(c)
    
    def pop_card(self):
        if(len(self.cards) > 0):
            return self.cards.pop()
        else:
            return None

    def remove_card(self, card):
        try:
            #i = self.cards.index(card)
            self.cards.remove(card)
            card.zone = None
            return card
        except ValueError as e:
            return None

class Graveyard(Zone):
    def __init__(self, name, owner):
        super(Graveyard, self).__init__(name, 75, owner, "Graveyard")

    def add_card(self, card):
        super(Graveyard, self).add_card(card)
        card.location = "Graveyard"
        card.face_up = FACEUPTOEVERYONE
        

class Banished(Zone):
    def __init__(self, name, owner):
        super().__init__(name, 75, owner, "Banished")

    def add_card(self, card, face_up = FACEUPTOEVERYONE):
        super().add_card(card)
        card.location = "Banished"
        card.face_up = face_up

class Deck(Zone):
    def __init__(self, name, owner):
        super().__init__(name, 60, owner, "Deck")

    def add_card(self, card):
        super().add_card(card)
        card.location = "Deck"
        card._face_up = FACEDOWN

class FieldZone(Zone):
    def __init__(self, name, owner, zonenum):
        super(FieldZone, self).__init__(name, 1, owner,  "Field", zonenum)

    def add_card(self, card):
        super(FieldZone, self).add_card(card)
        card.location = "Field"

    def pop_card(self):
        if (len(self.cards) > 0):
            #self.cards[-1].on_leave_field()
            self.cards[-1].zone = None
            return self.cards.pop()
        else:
            return None

class FieldZoneArray:
    def __init__(self, nameprefix, owner, numzones, cardlist):
        self.listofzones = [FieldZone(nameprefix + str(x), owner, x) for x in range(numzones)]
        self.allzonenums = set([x for x in range(numzones)])
        self.occupiedzonenums = set()
        self.cardlist = cardlist

    def get_card(self, zonenum):
        if zonenum in self.occupiedzonenums:
            return self.listofzones[zonenum].cards[0]
        else:
            return None

    def add_card(self, card, zonenum):
        card.zonearray = self
        self.listofzones[zonenum].add_card(card)
        self.occupiedzonenums.add(zonenum)
        self.cardlist.append(card)

    def pop_card(self, zonenum):
        card = self.listofzones[zonenum].pop_card()
        self.cardlist.remove(card)
        card.zonearray = None
        self.occupiedzonenums.discard(zonenum)
        return card
        
    def get_free_zonenums(self):
        return self.allzonenums - self.occupiedzonenums

    def choose_occupied_zone(self, numstoexclude = set()):
        settochoosefrom = self.occupiedzonenums - numstoexclude
        for zonenum in settochoosefrom:
            zone = self.listofzones[zonenum]
            print(str(zonenum) + " : " + zone.cards[0].name, end = ' ')

        chosenzonenum = -1
        while chosenzonenum not in settochoosefrom:
            chosenzonenum = int(input())
        return chosenzonenum
 

    def choose_free_zone(self):
        freezonenums = self.get_free_zonenums()
        for zonenum in freezonenums:
            print(zonenum, end = ' ')

        chosenzonenum = -1
        while chosenzonenum not in freezonenums:
            chosenzonenum = int(input())
            
        return chosenzonenum

class Hand(Zone):
    def __init__(self, name, owner):
        super(Hand, self).__init__(name, 75, owner, "Hand")
        

    def add_card(self, card):
        super(Hand, self).add_card(card)
        card.location = "Hand"
        card.face_up = FACEUPTOCONTROLLER


