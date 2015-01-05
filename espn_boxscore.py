__author__ = 'patrick'

from bs4 import BeautifulSoup
import re
import urllib2
import html5lib
from fake_useragent import UserAgent
from game_parse import Game
import pandas as pd
import numpy as np
import time
import random
import fileinput
from sqlalchemy import create_engine


ua = UserAgent()


def make_season(start_year):

    months = ['11', '12', '01', '02', '03', '04']

    # April stops at 4/8 currently, as post 2008 that's the latest the championship has been
    dates = {'11': range(31)[1:], '12': range(32)[1:], '01': range(32)[1:], '02': range(29)[1:],
             '03': range(32)[1:], '04': range(9)[1:]}

    all_season = []
    for month in months:
        if month in ['01', '02', '03', '04']:
                year = start_year + 1
                if year % 4 == 0:
                    dates['02'].append(29)
        else:
            year = start_year
        for d in dates[month]:
            day = str(d)
            if len(day) == 1:
                day = '0'+day
            date = str(year)+month+day
            all_season.append(date)

    f = open('Last_Day_Parsed', 'r')
    last = f.read()
    if last:
        st_idx = all_season.index(last)
        all_season = all_season[st_idx:]
    f.close()

    return all_season

# http://scores.espn.go.com/ncb/scoreboard?date=20081131&confId=50
def create_day_url(base, date):
    box_urls = []
    url = base + date + '&confId=50'
    box_urls.append(url)
    if date[4:6] == '03' or date[4:6] == '04':
        tourney_url = base + date + '&confId=100'
        box_urls.append(tourney_url)
    return box_urls

def get_data(game_url, ua, tourney_df, ncaa):

    game = Game(game_url, ua, tourney_df, ncaa)
    game.make_dataframes()
    # appending the new dataframes to the lists of dataframes
    gen_info = game.info_df
    try:
        players = game.players
        game_stats = game.gm_totals

    except:
        players = None
        game_stats = None
    print "Just finished: %s vs %s on %s" % (game.away_abbrv, game.home_abbrv, game.date)

    # build in wait times between getting games to prevent an overload
    wait_time = round(max(10, 15 + random.gauss(0,3)), 2)
    time.sleep(wait_time)

    return gen_info, players, game_stats

# new helper function to check for game cancellations/postponements???!!!!!!



def make_overall_df(start_year):

    gen_info = []
    players = []
    game_stats = []

    date_list = make_season(start_year)

    base_url = "http://scores.espn.go.com/ncb/scoreboard?date="
    for day in date_list:
        day_urls = create_day_url(base_url, day)

        for d in day_urls:

            #Standard urllib2 to BeautifulSoup request process
            request = urllib2.Request(d, headers = { 'User-Agent' : ua.random })
            try:
                page = urllib2.urlopen(request)
            except urllib2.URLError, e:
                try:
                    # wait a few seconds if failed, and try again
                    wait_time = round(max(10, 12 + random.gauss(0,1)), 2)
                    time.sleep(wait_time)
                    print "First attempt for %s failed. Trying again." % (d)
                    page = urllib2.urlopen(request)
                except:
                    if hasattr(e, 'reason'):
                        print 'Failed to reach url'
                        print 'Reason: ', e.reason
                        f = open('Last_Day_Parsed', 'r+')
                        previous = f.read()
                        for line in fileinput.input('Last_Day_Parsed', inplace=True):
                            line.replace(previous, day)
                        f.close()
                        return gen_info, players, game_stats
                    elif hasattr(e, 'code'):
                        if e.code == 404:
                            print 'Error: ', e.code
                            f = open('Last_Day_Parsed', 'r+')
                            previous = f.read()
                            for line in fileinput.input('Last_Day_Parsed', inplace=True):
                                line.replace(previous, d)
                            f.close()
                            return gen_info, players, game_stats

            content = page.read()

            soup = BeautifulSoup(content, "html5lib")

            # INSERT CHECK FOR 'NO GAMES' HERE, BREAK LOOP/CONTINUE IF THAT'S THE CASE
            no_game_check = [x.text.encode('ascii', 'ignore') for x in soup.find_all('div', {'class': 'mod-content'})]
            no_game_check = [i for i in no_game_check if 'Next game' in i]
            if len(no_game_check) > 0:
                print "No games on ", day
                continue

            boxscores = soup.findAll('a', attrs={'href': re.compile("^/ncb/boxscore")})
            links = [x.get("href") for x in boxscores if re.match(r'Box', x.text)]

            # For handling games that are cancelled/postponed, and thus have no stats
            status_head = [i.find("p") for i in soup.find_all("div", {"class": "game-header"})]
            ids = [x.get("id").split("-")[0] for x in status_head]
            status = [i.text for i in status_head]
            status_dict = {}
            for i in range(len(status)):
                status_dict[ids[i]] = status[i]

            # getting specific info (i.e. rounds) for tournament months
            if day[4:6] == '03' or day[4:6] == '04':
                game_notes = soup.find_all("div", {"class": "game-note border-top"})
            try:
                f2 = open('Failed_Game', 'r+')
                failure = f2.read()
                for line in fileinput.input('Failed_Game', inplace=True):
                    if line in links:
                        line.replace(failure, '')
                    else:
                        continue
                f2.close()
                if failure:
                    links = links[links.index(failure):]
            except:
                continue


            # Iterating through every boxscore url, fetching the data via creating Game objects
            for url in links:

                game_id = url.split("=")[-1]
                if status_dict[game_id] == 'Postponed' or status_dict[game_id] == 'Cancelled':
                    print "No Final Score for %s" % url
                    continue

                else:
                    # Making a small dataframe that contains tourney-specific information
                    tourney_col = ['Tournament', 'Round', 'Away_Seed', 'Home_Seed']
                    ncaa = False
                    data = np.array([np.repeat(np.nan,4)])
                    tourney_df = pd.DataFrame(data, columns=tourney_col)

                    # Get the relevant notes showing round, etc. from the day's scoreboard
                    #  if it's a tournament game
                    pos = links.index(url)
                    try:
                        note = game_notes[pos].text
                        tourney_split = note.split(' - ')
                        if tourney_split[0]:
                            tourney_df['Tournament'] = tourney_split[0]
                            # -1 to take last element, which is usually of format like
                            #  'QUARTERFINAL AT ...", but only the round information is really needed here
                            round_split = tourney_split[-1].split(' AT ')
                            # Check for ncaa tournament and store a boolean value...
                            # Necessary because 'rank' numbers become seed numbers on ESPN
                            if tourney_split[0] == "MEN'S BASKETBALL CHAMPIONSHIP":
                                ncaa = True
                            if round_split[0]:
                                tourney_df['Round'] = round_split[0]
                    except:
                        pass
                    # Now to extract the data from the boxscore's url
                    # Stored into a 'Game' object
                    game_url = 'http://scores.espn.go.com' + url
                    try:
                        gm_info, gm_players, gm_stats = get_data(game_url, ua, tourney_df, ncaa)
                        gen_info.append(gm_info)
                        if gm_players is not None:
                            players.append(gm_players)
                            game_stats.append(gm_stats)
                    except:
                        f = open('Last_Day_Parsed', 'w')
                        f.write(day)
                        f.close()
                        f2 = open('Failed_Game', 'w')
                        box = game_url.split('.com')[-1]
                        f2.write(box)
                        f2.close()
                        print "Broke off loop at ", game_url
                        return gen_info, players, game_stats


            # day-by-day 10% chance of a long wait/sleep time
            chance = range(100)
            choice = random.choice(chance)
            if choice < 10:
                big_wait_time = round(max(25, 28 + random.gauss(0,2)), 2)
                print "Big wait of %d seconds\n\n" % big_wait_time
                time.sleep(big_wait_time)

    return gen_info, players, game_stats



if __name__ == '__main__':

    start_year = 2013 # change this per season
    info_list, players_list, gm_stats_list = make_overall_df(start_year)
    final_info = pd.concat(info_list, ignore_index=True)
    final_players = pd.concat(players_list, ignore_index=True)
    final_gm_stats = pd.concat(gm_stats_list, ignore_index=True)

    engine = create_engine("postgresql://localhost:5432/ncaa")
    final_info.to_sql("gen_info", engine, if_exists='append', index=False)
    final_players.to_sql("players", engine, if_exists='append', index=False)
    final_gm_stats.to_sql("game_stats", engine, if_exists='append', index=False)

    print "\n\nFinished uploading to SQL"