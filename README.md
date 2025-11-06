# @pingv3 repo!

## Instructions

1. Fork this repository
2. Install Python
3. Run `pip install ping-game-theory`
4. Rename the file in submissions/ with your name and net id
5. Open the Python file in your text editor
6. Enter your SNU NetID in `self.author_netid`
7. Enter your strategy name in `self.strategy_name`
8. Describe your strategy name in `self.strategy_desc` (Optional, but it helps us judge your bot.)
9. Write your code under `def begin(self)` and `def turn(self, history: History)`
10. When you want to submit, open a pull request to this repository (make sure that you're only committing one Python file).

Do NOT change the name of the `class Bot`. If you do this, your submission will be invalidated (as we look for a `Bot` class in your code to run). Any failure to follow the instructions above may also lead to an invalid submission.

## Where do I write my code?

The `begin` function is what defines what move your bot plays first. For now it just plays `Move.COOPERATE` to start with.

The `turn` function is what defines what move your bot performs in any turns after. `History` is a list of `HistoryEntry`s, inside which `HistoryEntry.self` is the move your bot played for that turn and `HistoryEntry.other` is the move the opponent played. For now the bot only plays `Move.DEFECT`.

## How do I test my code?

Just run it bro.
