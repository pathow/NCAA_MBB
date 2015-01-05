__author__ = 'patrick'
from bs4 import BeautifulSoup
import urllib2
import html5lib
import re
import itertools
import pandas as pd
import numpy as np


def isplit(iterable,splitters):
    return [list(g) for k,g in itertools.groupby(iterable,lambda x:x in splitters) if not k]





class Game(object):
    def __init__(self, url, ua, tourney_df, ncaa_bool):

        request = urllib2.Request(url, headers = { 'User-Agent' : ua.random })
        try:
            page = urllib2.urlopen(request)
        except urllib2.URLError, e:
            try:
                wait_time = round(max(10, 15 + random.gauss(0,2.5)), 2)
                time.sleep(wait_time)
                page = urllib2.urlopen(request)
            except:
                try:
                    print "First attempt for %s failed" % url
                    wait_time = round(max(20, 24 + random.gauss(0,2.5)), 2)
                    time.sleep(wait_time)
                    page = urllib2.urlopen(request)
                except:
                    if hasattr(e, 'reason'):
                        print 'Failed to reach url'
                        print 'Reason: ', e.reason
                        sys.exit()
                    elif hasattr(e, 'code'):
                        if e.code == 404:
                            print 'Error: ', e.code
                            sys.exit()

        content = page.read()

        self.soup = BeautifulSoup(content, "html5lib")
        self.game_id = url.split("=")[1]

        self.tourney_df = tourney_df
        self.ncaa_bool = ncaa_bool
        if 'OT' in self.soup.find("p", {"class": "game-state"}).text:
            self.ot = True
        else:
            self.ot = False



    def get_raw(self):

        # Extracting things from the location/game time
        self.game_time_loc = self.soup.find("div", {"class": "game-time-location"}).text
        self.year = re.compile('20\d{2}').findall(self.game_time_loc)[0]
        splitted = self.game_time_loc.split(self.year)
        self.location = splitted[1]
        time = splitted[0].split(", ")
        self.tipoff = time[0]
        self.date = time[1]

        # Extracting things from the header, like school and record
        away = self.soup.find("div", {"class": "team away"})
        self.away_tm = away.a.text
        try:
            self.away_score = int(away.span.text)
            self.away_rank = np.nan
        except ValueError:
            rank_score = [i.text for i in away.find_all("span")]
            rank = re.compile("\d+").findall(rank_score[0])
            if self.ncaa_bool == True:
                self.tourney_df['Away_Seed'] = int(rank[0])
                self.away_rank = np.nan
            else:
                self.away_rank = int(rank[0])
            self.away_score = int(rank_score[1])
        # record after game finished
        self.away_rec = away.p.text
        if self.away_rec == u'\xa0':
            self.away_rec = np.nan

        home = self.soup.find("div", {"class": "team home"})
        self.home_tm = home.a.text
        try:
            self.home_score = int(home.span.text)
            self.home_rank = np.nan
        except ValueError:
            rank_score = [i.text for i in home.find_all("span")]
            rank = re.compile("\d+").findall(rank_score[0])
            if self.ncaa_bool == True:
                self.tourney_df['Home_Seed'] = int(rank[0])
                self.home_rank = np.nan
            else:
                self.home_rank = int(rank[0])
            self.home_score = int(rank_score[1])
        # record after game finished
        self.home_rec = home.p.text
        if self.home_rec == u'\xa0':
            self.home_rec = np.nan

        # Extracting team abbreviations and score by half
        linescore = self.soup.find("table", {"class": "linescore"})
        cells = [td.text for td in linescore.find_all("td")]
        # Table is variable length dependent on if a ranking appears for either team
        n_col = len(cells)/3
        shape = (3, n_col)
        cells = np.array(cells)
        cells = cells.reshape(shape)
        cells = np.delete(cells, 0, 0)
        cells = np.delete(cells, -1, 1)
        if sum(['#' in i for i in cells[:,0]]) > 0:
            cells = np.delete(cells, 0, 1)

        halves = cells[:, 0:3]
        try:
            ot = np.array(cells[:, 3:], dtype=int)
            self.ot = True
        except:
            self.ot = False

        self.away_abbrv = cells[0,0]
        self.home_abbrv = cells[1,0]
        try:
            self.away_1st = int(cells[0,1])
            self.away_2nd = int(cells[0,2])

            self.home_1st = int(cells[1,1])
            self.home_2nd = int(cells[1,2])
        except ValueError:
            # some games have no values in 2nd half score columns
            self.away_1st = np.nan
            self.away_2nd = np.nan

            self.home_1st = np.nan
            self.home_2nd = np.nan

        if self.ot == False:
            self.away_ot = np.nan
            self.home_ot = np.nan
        else:
            self.away_ot = sum(ot[0,:])
            self.home_ot = sum(ot[1,:])


        #######################################
        # Grabbing player specific data
        plyr_table = self.soup.find("div", id="my-players-table")
        try:
            plyr_rows = plyr_table.find_all("tr")
            split = [x for x in plyr_rows if x.find("th", colspan="13")]
            # divides into two lists of lists, first being away team, second is home team
            team_sep = isplit(plyr_rows, split)
            try:
                team_sep[1]
                self.includes_defreb = False
                self.complete = True
            except:
                split = [x for x in plyr_rows if x.find("th", colspan="14")]
                team_sep = isplit(plyr_rows, split)
                # marker to show column needs to be deleted
                self.includes_defreb = True
                self.complete = True
                try:
                    team_sep[1]
                except:
                    self.complete = False
        except:
            self.complete = False

        if self.complete:
            # Getting raw data cells by row for away team
            away_stats = [i.find_all("td") for i in team_sep[0] if not i.find("th")]
            # filters out the non-players rows, then cleaning them to just the text
            away_stats = [x for x in away_stats if re.match("^[A-Za-z]", x[0].text)]
            self.away_stats = [[x.text for x in r] for r in away_stats]

            # Same thing but for home team now
            home_stats = [i.find_all("td") for i in team_sep[1] if not i.find("th")]
            # filters out the non-players rows, then cleaning them to just the text
            home_stats = [x for x in home_stats if re.match("^[A-Za-z]", x[0].text)]
            self.home_stats = [[x.text for x in r] for r in home_stats]

            try:
                # This is what runs for 2008-2013
                # Messy multi-splits to get single string of Tech fouls, Officials and Attendance
                extras = self.soup.get_text().split(u'\xa0')[-1].split('\n')[0]
                first_cut = extras.split('Officials: ')
                tech_list = first_cut[0].split(': ')
                try:
                    officials_attendance = first_cut[1].split('Attendance: ')
                    self.technicals = tech_list[1]
                    self.officials = officials_attendance[0]
                    self.attendance = officials_attendance[1]
                except:
                    refs = self.soup.get_text().split(u'\xa0')[4]
                    self.officials = refs.split(': ')[1]
                    attend =  self.soup.get_text().split(u'\xa0')[5].split('\n')[0]
                    self.attendance = attend.split(': ')[1]

            except:
                # 2013 season and on
                # different html structure underlying the bottom of the page
                attendance = self.soup.get_text().split(u'\xa0')[-1].split('\n')[0]
                self.attendance = attendance.split(': ')[1]
                refs = self.soup.get_text().split(u'\xa0')[-2]
                self.officials = refs.split(': ')[1]
                technicals = self.soup.get_text().split(u'\xa0')[-3]
                start = technicals.find(":") + 2
                self.technicals = technicals[start:]


        # exception handling for cases when there's no player stats
        else:
            self.away_stats = 'N/A'
            self.home_stats = 'N/A'
            self.technicals = np.nan
            self.officials = np.nan
            self.attendance = np.nan


    def make_dataframes(self):
        # call the first function that parses the data
        self.get_raw()

        if self.away_stats != 'N/A' and self.home_stats != 'N/A':
            headers = ["Player", "Min", "FGM-A", "3PM-A", "FTM-A", "OREB", "REB", "AST", "STL",
                       "BLK", "TO", "PF", "PTS"]
            # Making standard columns, without defensive rebounds as separate category for now
            if self.includes_defreb == True:
                for row in self.away_stats:
                    del row[6]
                for row in self.home_stats:
                    del row[6]

            numeric_col = ['FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'OREB', 'REB',
                'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS']

            try:
                self.away_df = pd.DataFrame(self.away_stats, columns=headers)
                # Probably a more pythonic way of doing all this, but splitting all columns and setting as ints
                try:
                    self.away_df['Player'], self.away_df['Position'] = zip(*self.away_df['Player'].apply(lambda x: x.split(', ', 1)))
                except:
                    for i in self.away_df['Player']:
                        if ',' not in i:
                            try:
                                idx = np.where(self.away_df['Player'] == i)[0].item()
                                self.away_df['Player'][idx] += ', N/A'
                            except:
                                # Problematic when person with same names on same team,
                                # exception handling for them appearing twice
                                idx1 = np.where(self.away_df['Player'] == i)[0][0].item()
                                if ',' not in self.away_df['Player'][idx1]:
                                    self.away_df['Player'][idx1] += ', N/A'

                    self.away_df['Player'], self.away_df['Position'] = zip(*self.away_df['Player'].apply(lambda x: x.split(', ', 1)))

                self.away_df['FGM'], self.away_df['FGA'] = zip(*self.away_df['FGM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df['3PM'], self.away_df['3PA'] = zip(*self.away_df['3PM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df['FTM'], self.away_df['FTA'] = zip(*self.away_df['FTM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df[numeric_col] = self.away_df[numeric_col].astype(np.int64)
                self.away_df = self.away_df.drop(['FGM-A', '3PM-A', 'FTM-A'], axis=1)
                self.away_df['Game_ID'] = self.game_id
                self.away_df['Home_Away'] = 'Away'
                self.away_df['Team'] = self.away_abbrv

            except:
                # No minutes column in random games, and false positive on only having 13 columns,
                # so need to delete Defensive Rebounds
                headers.remove('Min')
                for row in self.away_stats:
                    del row[5]
                for row in self.home_stats:
                    del row[5]

                self.away_df = pd.DataFrame(self.away_stats, columns=headers)
                # Probably a more pythonic way of doing all this, but splitting all columns and setting as ints
                try:
                    self.away_df['Player'], self.away_df['Position'] = zip(*self.away_df['Player'].apply(lambda x: x.split(', ', 1)))
                except:
                    for i in self.away_df['Player']:
                        if ',' not in i:
                            try:
                                idx = np.where(self.away_df['Player'] == i)[0].item()
                                self.away_df['Player'][idx] += ', N/A'
                            except:
                                # Problematic when person with same names on same team,
                                # exception handling for them appearing twice
                                idx1 = np.where(self.away_df['Player'] == i)[0][0].item()
                                if ',' not in self.away_df['Player'][idx1]:
                                    self.away_df['Player'][idx1] += ', N/A'

                    self.away_df['Player'], self.away_df['Position'] = zip(*self.away_df['Player'].apply(lambda x: x.split(', ', 1)))

                self.away_df['FGM'], self.away_df['FGA'] = zip(*self.away_df['FGM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df['3PM'], self.away_df['3PA'] = zip(*self.away_df['3PM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df['FTM'], self.away_df['FTA'] = zip(*self.away_df['FTM-A'].apply(lambda x: x.split('-', 1)))
                self.away_df[numeric_col] = self.away_df[numeric_col].astype(np.int64)
                self.away_df = self.away_df.drop(['FGM-A', '3PM-A', 'FTM-A'], axis=1)
                self.away_df['Game_ID'] = self.game_id
                self.away_df['Home_Away'] = 'Away'
                self.away_df['Team'] = self.away_abbrv

            # Again, for the home team
            self.home_df = pd.DataFrame(self.home_stats, columns=headers)
            try:
                self.home_df['Player'], self.home_df['Position'] = zip(*self.home_df['Player'].apply(lambda x: x.split(', ', 1)))
            except:
                names = [i for i in self.home_df['Player']]
                for i in names:
                    if ',' not in i:
                        try:
                            idx = np.where(self.home_df['Player'] == i)[0].item()
                            self.home_df['Player'][idx] += ', N/A'
                        except:
                            idx1 = np.where(self.home_df['Player'] == i)[0][0].item()
                            if ',' not in self.home_df['Player'][idx]:
                                self.home_df['Player'][idx1] += ', N/A'
                            else:
                                idx2 = np.where(self.home_df['Player'] == i)[0][1].item()
                                self.home_df['Player'][idx2] += ', N/A'

                self.home_df['Player'], self.home_df['Position'] = zip(*self.home_df['Player'].apply(lambda x: x.split(', ', 1)))

            self.home_df['FGM'], self.home_df['FGA'] = zip(*self.home_df['FGM-A'].apply(lambda x: x.split('-', 1)))
            self.home_df['3PM'], self.home_df['3PA'] = zip(*self.home_df['3PM-A'].apply(lambda x: x.split('-', 1)))
            self.home_df['FTM'], self.home_df['FTA'] = zip(*self.home_df['FTM-A'].apply(lambda x: x.split('-', 1)))
            self.home_df[numeric_col] = self.home_df[numeric_col].astype(np.int64)
            self.home_df = self.home_df.drop(['FGM-A', '3PM-A', 'FTM-A'], axis=1)
            self.home_df['Game_ID'] = self.game_id
            self.home_df['Home_Away'] = 'Home'
            self.home_df['Team'] = self.home_abbrv

            self.players = pd.concat([self.away_df, self.home_df])

            # Making team totals dataframes
            data = np.array([np.arange(len(numeric_col))]) # empty row for filling in aggregated data
            self.a_totals = pd.DataFrame(data, columns=numeric_col)
            awayadded = self.away_df.sum(axis=0, numeric_only=True)
            for column in numeric_col:
                self.a_totals[column] = awayadded[column]
            self.a_totals['Team'] = self.away_tm
            self.a_totals['Home_Away'] = 'Away'
            self.a_totals['Game_ID'] = self.game_id

            data = np.array([np.arange(len(numeric_col))])
            self.h_totals = pd.DataFrame(data, columns=numeric_col)
            homeadded = self.home_df.sum(axis=0, numeric_only=True)
            for column in numeric_col:
                self.h_totals[column] = homeadded[column]
            self.h_totals['Team'] = self.home_tm
            self.h_totals['Home_Away'] = 'Home'
            self.h_totals['Game_ID'] = self.game_id

            self.gm_totals = pd.concat([self.a_totals, self.h_totals])



        #######################################
        # Making general game information dataframe
        info = ['Game_ID', 'Away_Abbrv', 'Home_Abbrv', 'Away_Score',
                'Home_Score', 'Away_Rank', 'Home_Rank', 'Away_Rec', 'Home_Rec', 'Away_1st', 'Away_2nd',
                'Home_1st', 'Home_2nd', 'Officials', 'Attendance', 'Game_Year', 'Game_Date','Game_Tipoff',
                'Game_Location', 'Game_Away', 'Game_Home', "Away_OT", "Home_OT"]
        data = np.array([np.arange(len(info))])
        self.info_df = pd.DataFrame(data, columns=info)

        self.info_df['Game_ID'] = self.game_id
        self.info_df['Game_Year'] = self.year
        self.info_df['Game_Date'] = self.date
        self.info_df['Game_Tipoff'] = self.tipoff
        self.info_df['Game_Location'] = self.location
        self.info_df['Game_Away'] = self.away_tm
        self.info_df['Away_Abbrv'] = self.away_abbrv
        self.info_df['Game_Home'] = self.home_tm
        self.info_df['Home_Abbrv'] = self.home_abbrv
        self.info_df['Away_Score'] = self.away_score
        self.info_df['Home_Score'] = self.home_score
        self.info_df['Away_Rank'] = self.away_rank
        self.info_df['Home_Rank'] = self.home_rank
        self.info_df['Away_Rec'] = self.away_rec
        self.info_df['Home_Rec'] = self.home_rec
        self.info_df['Away_1st'] = self.away_1st
        self.info_df['Away_2nd'] = self.away_2nd
        self.info_df['Away_OT'] = self.away_ot
        self.info_df['Home_1st'] = self.home_1st
        self.info_df['Home_2nd'] = self.home_2nd
        self.info_df['Home_OT'] = self.home_ot
        self.info_df['Officials'] = self.officials
        self.info_df['Attendance'] = self.attendance
        self.info_df = pd.concat([self.info_df, self.tourney_df], axis=1)


########################

########################

########################

# To-do:

# Tournament information...get from aggregate boxscores/date page and pass into class?
    # Need to set for switchover from ranks to NCAA seeds, etc.
    # Maybe make a small one-liner dataframe of that page's info that passes into and tacks onto info_df
        # since "season" is needed as well



