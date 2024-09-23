An implementation of Settlers of Catan in Python with a Tkinter GUI. The game code is in active development. 

After the game mechanics are finished, the goal is to create an interface for machine learning agents.
While similar in scope to [catanatron](https://github.com/bcollazo/catanatron) (which I would recommend for Catan AI research over this repo), this project is unique in that the GUI will allow you and your friends to play against the bots.
This is a passion project of mine; if you are interested in contributing or just want to share ideas, send me a message on Telegram.

## Usage

Run the game:

```python
python game.py
```

Currently, the GUI only renders the board and allows you to perform the setup phase (build first 2 settlements and roads). 
The board creation is random but adheres to Catan standards (one desert tile, correct hex and port distribution, no 6/8 chits are adjacent).
