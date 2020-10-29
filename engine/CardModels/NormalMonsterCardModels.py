
from engine.Cards import NormalMonsterCard

dmdesc = "The ultimate wizard in terms of attack and defense."
medesc = "A mystical defensive elf"
addesc = "An attack dragon"
ssdesc = "Level 6 example monster"


class DarkMagician(NormalMonsterCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Dark Magician", dmdesc, 'dark_magician.jpg', "Dark",  "Spellcaster", 7, 2500, 2000, ID, owner, gamestate)

class MysticalElf(NormalMonsterCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Mystical Elf", medesc, 'mystical_elf.jpg', "Light", "Spellcaster", 4, 800, 2000, ID, owner, gamestate)

class AlexandriteDragon(NormalMonsterCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Alexandrite Dragon", addesc, 'alexandrite_dragon.jpg',"Light", "Dragon", 4, 2000, 100, ID, owner, gamestate)

class SummonedSkull(NormalMonsterCard):
    def __init__(self, ID, owner, gamestate):
        super().__init__("Summoned Skull", ssdesc, 'summoned_skull.jpg', "Dark", "Fiend", 6, 2500, 1200, ID, owner, gamestate)




