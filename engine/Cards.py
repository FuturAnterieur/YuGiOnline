import engine.Effect as Effect
import engine.Action as Action
import engine.ActionsSpellTrap as ActionsSpellTrap



FACEDOWN = 0
FACEUPTOCONTROLLER = 1
FACEUPTOEVERYONE = 2
FACEUPTOOPPONENT = 3

def generate_card(cardmodel, gamestate, ID, owner):
    cardclassname = cardmodel.__class__.__name__.replace("Model", '')
    new_card = globals()[cardclassname](cardmodel, ID, owner, gamestate)
    return new_card


class Card:
    def __init__(self, name, text, cardclass, imgpath, ID, owner, gamestate): 
        
        self.ID = ID
        self.name = name
        self.face_up = FACEDOWN
        self.text = text
        self.cardclass = cardclass
        self.imgpath = imgpath

        self.owner = owner
        self.location = ""
        self.zone = None
        self.zonearray = None
        self.actiondict = {}
        self.curchoices = set()

    def give_current_choices(self, gamestate):
        self.curchoices.clear()
        for action_name in self.actiondict.keys():
            if self.actiondict[action_name].reqs(gamestate):
                self.curchoices.add(action_name)

        return self.curchoices




class MonsterCard(Card):
    def __init__(self, name, attr, mtype, level, attack, defense, text, monsterclass, effects_classes, imgpath, ID, owner, gamestate):
        super().__init__(name, text, 'Monster', imgpath, ID, owner, gamestate)
        self.attribute = attr
        self.type = mtype
        self.level = level
        self.attack = attack
        self.originalattack = attack
        self.defense = defense
        self.originaldefense = defense
        self.monsterclass = monsterclass
        self.effects_classes = []
        self.effects = []
        
        self.numtributesrequired = 0
        self.position = "None"
        self.attacks_declared_this_turn = 0
        self.max_attacks_per_turn = 1
        self.summonmethod = "Normal"

        self.actiondict["Normal Summon"] = Action.NormalSummonMonster()
        self.actiondict["Attack"] = Action.DeclareAttack()

        self.actiondict["Normal Summon"].init(self)
        self.actiondict["Attack"].init(self)
        
        for effect_class in self.effects_classes:
            self.effects.append(effect_class())
            if self.effects[-1].type == "Ignition":
                self.actiondict["Activate Effect"] = Action.ActivateMonsterEffect()
                self.actiondict["Activate Effect"].init(gamestate, self, self.effect)


class NormalMonsterCard(MonsterCard):
    def __init__(self, cm, ID, owner, gamestate):
        super().__init__(cm.name, cm.attr, cm.type, cm.level, cm.attack, cm.defense, 
                cm.text, cm.monsterclass, cm.effects_classes, cm.imgpath, ID, owner, gamestate)
        if(self.level > 4 and self.level <= 6):
            self.numtributesrequired = 1
        elif(self.level > 6):
            self.numtributesrequired = 2


class SpellTrapCard(Card):
    def __init__(self, name, subclass, text, effect_class, imgpath, ID, owner, gamestate):
        super().__init__(name, text, "Spell/Trap", imgpath, ID, owner, gamestate)
        self.wassetthisturn = False
        self.spelltrapsubclass = subclass
        self.effect = effect_class()
        self.actiondict["Set"] = ActionsSpellTrap.SetSpellTrap()
        self.actiondict["Set"].init(self)
        self.effect.init(gamestate, self)
        

class NormalTrapCard(SpellTrapCard):
    def __init__(self, cm, ID, owner, gamestate):
        super().__init__(cm.name, cm.subclass, cm.text, cm.effect_class, cm.imgpath, ID, owner, gamestate)
        self.actiondict["Activate"] = ActionsSpellTrap.ActivateNormalTrap()
        self.actiondict["Activate"].init(self, self.effect)

class ContinuousSpellCard(SpellTrapCard):
    def __init__(self, cm, ID, owner, gamestate):
        super().__init__(cm.name, cm.subclass, cm.text, cm.effect_class, cm.imgpath, ID, owner, gamestate)
        if self.effect.type == "Passive":
            self.actiondict["Activate"] = ActionsSpellTrap.ActivateContinuousPassiveSpell()
            self.actiondict["Activate"].init(gamestate, self, self.effect)

