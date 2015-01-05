NCAA Men's Basketball
========

ESPN Box Score Scraper

Scraper that looks through a given date's game scores page and then crawls through every game's box scores to gather statistics on player and team levels.

Data are stored inside of the "Game" object and then called back in the form of Pandas dataframes, which are then uploaded to a SQL database in the __main__ loop. 

The current code setup accounts for the fact that ESPN's servers are not always reliable by progressively exporting to SQL whatever data has last been obtained, so saves the place where the code broke to the two separate files in the folder to mark day and game where the failure occurred to resume from that point and minimizes chances of duplication of data.
