
class CardModel:
    def __init__(self, name, text, cardclass, imgpath):
        self.name = name
        self.text = text
        self.cardclass = cardclass
        self.imgpath = imgpath

class MonsterCardModel(CardModel):
    def __init__(self, name, text, monsterclass, imgpath, attr, mtype, level, attack, defense, effects_classes):
        super().__init__(name, text, 'Monster', imgpath)
        self.monsterclass = monsterclass
        self.attr = attr
        self.type = mtype
        self.level = level
        self.attack = attack
        self.defense = defense
        self.effects_classes = effects_classes

class NormalMonsterCardModel(MonsterCardModel):
    def __init__(self, name, text, imgpath, attr, mtype, level, attack, defense):
        super().__init__(name, text, 'Normal', imgpath, attr, mtype, level, attack, defense, [])

class SpellTrapCardModel(CardModel):
    def __init__(self, name, text, imgpath,  subclass, effect_class):
        super().__init__(name, text, 'Spell/Trap', imgpath)
        self.subclass = subclass
        self.effect_class = effect_class

class TrapCardModel(SpellTrapCardModel):
    def __init__(self, name, text, imgpath, traptype, effect_class):
        super().__init__(name, text, imgpath, 'Trap', effect_class)
        self.traptype = traptype

class NormalTrapCardModel(TrapCardModel):
    def __init__(self, name, text, imgpath, effect_class):
        super().__init__(name, text, imgpath, 'Normal', effect_class)

class SpellCardModel(SpellTrapCardModel):
    def __init__(self, name, text, imgpath, spelltype, effect_class):
        super().__init__(name, text, imgpath, 'Spell', effect_class)
        self.spelltype = spelltype

class QuickPlaySpellCardModel(SpellCardModel):
    def __init__(self, name, text, imgpath, effect_class):
        super().__init__(name, text, imgpath, 'Quick-Play', effect_class)




