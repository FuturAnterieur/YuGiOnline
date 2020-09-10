# YuGiOnline

## Overview

YuGiOh Online is a work-in-progress implementation of the Yu-Gi-Oh trading card
game that is playable online through a web browser. I don't plan on
implementing all the rules of the game as it stands now; I mostly see it as an
exercise in web programming and system design. 

The main frameworks it uses are Django and python-socketio.

## Setup 

YuGiOh Online currently uses Python 3.7, and pip and virtualenv to set up the
virtual environment necessary to run the program. 

To run from the command line on Windows :

cd to the repository's root (containing this Readme file)
```
   virtualenv venv
```
Get the activate batch file full path (it should be in venv/Scripts) and run it in the command line to activate the virtual environment. 
Then, in the virtual environment:
```
   pip install -r requirements.txt
   python manage.py makemigrations socketio_app
   python manage.py migrate
```
That will initialize the virtual environment, install the requirements and make Django run its required database
migrations. After that, to run the server :

1- Make sure the virtual environment is active (run the aforementioned batch
file)

2- Run 
```
   python manage.py runserver
```
After that, the server should be up and running at localhost:8000 (that should
be http://127.0.0.1:8000).

The system was only tested on Windows up to now.

## What is implemented

- Duel room formation through the sharing of a link
- Capacity to spectate a duel
- Basic phases of a turn 
- The different steps of the battle phase
- Support for creating effects that can respond to each other
- A few monsters and one trap card, Trap Hole, have been coded

## Notable things that are not implemented yet

- Capacity to create a user account
- Deck builder feature
- End of a duel (either by winning of forfeiting)
