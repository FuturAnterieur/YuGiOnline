from engine.CardModel import NormalMonsterCardModel

dmdesc = "The ultimate wizard in terms of attack and defense."
medesc = "A mystical defensive elf"
addesc = "An attack dragon"
ssdesc = "Level 6 example monster"


DarkMagician = NormalMonsterCardModel("Dark Magician", dmdesc, 'barrel_dragon.png', "Dark",  "Spellcaster", 7, 2500, 2000)
MysticalElf = NormalMonsterCardModel("Mystical Elf", medesc, 'mystical_elf.jpg', "Light", "Spellcaster", 4, 800, 2000)
AlexandriteDragon = NormalMonsterCardModel("Alexandrite Dragon", addesc, 'alexandrite_dragon.jpg',"Light", "Dragon", 4, 2000, 100)
SummonedSkull = NormalMonsterCardModel("Summoned Skull", ssdesc, 'summoned_skull.jpg', "Dark", "Fiend", 6, 2500, 1200)


