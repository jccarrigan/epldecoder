#!/usr/bin/python3
import requests
from requests import Request, Session
import json
import sys
import unicodedata
import logging

from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth
from six import iteritems
from six import itervalues

# logging setup
logging.basicConfig(level=logging.INFO)

FPL_API_URL = "https://fantasy.premierleague.com/drf/"
BST = "bootstrap"
BSS = "bootstrap-static"
BSD = "bootstrap-dynamic"
MYTEAM = "my-team/"
ENTRY = "entry/"
USER_SUMMARY_SUBURL = "element-summary/"
LCS_SUBURL = "leagues-classic-standings/"
LEAGUE_H2H_STANDING_SUBURL = "leagues-h2h-standings/"
PLAYERS_INFO_SUBURL = "bootstrap-static"
PLAYERS_INFO_FILENAME = "allPlayersInfo.json"
STANDINGS_URL = "https://fantasy.premierleague.com/drf/leagues-classic-standings/"
CLASSIC_PAGE = "&le-page=1&ls-page=1"

############################################
# note: Must be authourized by credentials
#
class fpl_bootstrap:
    """Base class for extracting the core game ENTRY dataset"""
    """This class requires valid credentials"""
    """but does not contain the full player private ENTRY dataset"""
    username = ""
    password = ""
    current_event = ""
    api_get_status = ""

    def __init__(self, playeridnum, username, password):
        self.playeridnum = str(playeridnum)
        self.username = username
        self.password = password
        fpl_bootstrap.username = username    # make USERNAME var global to class instance
        fpl_bootstrap.password = password    # make PASSWORD var global to class instance

        logging.info('fpl_bootstrap:: - create bootstrap ENTRY class instance for player: %s' % self.playeridnum )

        self.epl_team_names = {}    # global dict accessible from wihtin this base class
        s = requests.Session()
        user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0'}
        API_URL0 = 'https://fantasy.premierleague.com/a/login'
        API_URL1 = FPL_API_URL + BST

# WARNING: This cookie must be updated each year at the start of the season as it is changed each year.
# 2018 cookie - ({'pl_profile': 'eyJzIjogIld6VXNNalUyTkRBM01USmQ6MWZpdE1COjZsNkJ4bngwaGNUQjFwa3hMMnhvN2h0OGJZTSIsICJ1IjogeyJsbiI6ICJBbHBoYSIsICJmYyI6IDM5LCAiaWQiOiAyNTY0MDcxMiwgImZuIjogIkRyb2lkIn19'})
# 2019 cookie - ({'pl_profile': 'eyJzIjogIld6VXNNalUyTkRBM01USmQ6MWVOWUo4OjE1QWNaRW5EYlIwM2I4bk1HZDBqX3Z5VVk2WSIsICJ1IjogeyJsbiI6ICJBbHBoYSIsICJmYyI6IDgsICJpZCI6IDI1NjQwNzEyLCAiZm4iOiAiRHJvaWQifX0='})
# 2019 worked - ({'pl_profile': 'eyJzIjogIld6VXNNalUyTkRBM01USmQ6MWZpdE1COjZsNkJ4bngwaGNUQjFwa3hMMnhvN2h0OGJZTSIsICJ1IjogeyJsbiI6ICJBbHBoYSIsICJmYyI6IDM5LCAiaWQiOiAyNTY0MDcxMiwgImZuIjogIkRyb2lkIn19'})
        pl_profile_cookies = { \
                '1212166': 'eyJzIjogIld6VXNNalUyTkRBM01USmQ6MWZpdE1COjZsNkJ4bngwaGNUQjFwa3hMMnhvN2h0OGJZTSIsICJ1IjogeyJsbiI6ICJBbHBoYSIsICJmYyI6IDM5LCAiaWQiOiAyNTY0MDcxMiwgImZuIjogIkRyb2lkIn19', \
                '1136396': 'eyJzIjogIld6VXNOVGc0T0RnM05WMDoxZnYzYWo6WGkxd1lMMnpLeW1pbThFTTVFeGEzVFdUaWtBIiwgInUiOiB7ImxuIjogIkJyYWNlIiwgImZjIjogOCwgImlkIjogNTg4ODg3NSwgImZuIjogIkRhdmlkIn19' }

        for pl, cookie_hack in pl_profile_cookies.items():
            if pl == self.playeridnum:
                s.cookies.update({'pl_profile': cookie_hack})
                logging.info('fpl_bootstrap:: SET pl_profile cookie for userid: %s' % pl )
                logging.info('fpl_bootstrap:: SET pl_profile cookie to: %s' % cookie_hack )
                fpl_bootstrap.api_get_status = "GOODCOOKIE"
                break    # found this players cookie
            else:
                logging.info('fpl_bootstrap:: ERR userid is bad. No cookie found/set: %s' % pl )
                fpl_bootstrap.api_get_status = "FAILED"

        if fpl_bootstrap.api_get_status == "FAILED":
            return
        else:
            pass

# REST API I/O now... - 1st get authenticates, but must use critical cookie (i.e. "pl_profile")
# 2nd get does the data extraction if auth succeeds - failure = all JSON dicts/fields are empty
        rx0 = s.get( API_URL0, headers=user_agent, auth=HTTPBasicAuth(self.username, self.password) )
        rx1 = s.get( API_URL1, headers=user_agent, auth=HTTPDigestAuth(self.username, self.password) )
        self.auth_status = rx0.status_code
        self.gotdata_status = rx1.status_code
        logging.info('fpl_bootstrap:: - init - Logon AUTH url: %s' % rx0.url )
        logging.info('fpl_bootstrat:: - init - API data get url: %s' % rx1.url )

        rx0_auth_cookie = requests.utils.dict_from_cookiejar(s.cookies)
        logging.info('fpl_bootstrap:: AUTH login resp cookie: %s' % rx0_auth_cookie['pl_profile'] )

        if rx0.status_code != 200:    # failed to authenticate
            logging.info('fpl_bootstrap:: - init ERROR login AUTH failed with resp %s' % self.auth_status )
            return

        if rx1.status_code != 200:    # 404 API get failed
            logging.info('fpl_bootstrap:: - init ERROR API get failed with resp %s' % self.gotdata_status )
            return
        else:
            logging.info('fpl_bootstrap:: - Login AUTH success resp: %s' % self.auth_status )
            logging.info('fpl_bootstrap:: - API data GET resp is   : %s  ' % self.gotdata_status )
            # create JSON dict with players ENTRY data, plus other data thats now available
            # WARNING: This is a very large JSON data structure with stats on every squad/player in the league
            #          Dont load into memory multiple times. Best to insert into mongodb & access from there
            # EXTRACT JSON data/fields...
            # note: entry[] and player[] are not auto loaded when dataset lands (not sure why)
            t0 = json.loads(rx1.text)
            self.elements = t0['elements']              # big data-set for every EPL squad player full details/stats
            self.player = t0['player']                  # initially empty
            self.element_types = t0['element_types']
            self.next_event = t0['next-event']          # global accessor within data-set (do not modify)
            self.phases = t0['phases']
            self.stats = t0['stats']
            self.game_settings = t0['game-settings']
            self.current_event = t0['current-event']    # global accessor in class (do not modify)
            self.teams = t0['teams']                    # All details of EPL teams in Premieership league this year
            self.stats_options = t0['stats_options']
            self.entry = t0['entry']                    # initially empty
            self.next_event_fixtures = t0['next_event_fixtures']    # array of the next 10 fixtures (could be played across multiple days)
            self.events = t0['events']

            fpl_bootstrap.current_event = self.current_event    # set class global var so current week is easily accessible
        return

    def whois_element(self, elementid):
        """Scan main bootstrap data-set for a specific EPL squad player ID"""
        """and get the real firstname/last name of this EPL player"""

        self.element_target = str(elementid)
        logging.info('fpl_bootstrap:: whois_element() - scan target: %s' % elementid )
        for element in self.elements:
            if element['id'] == elementid:
                self.first_name = element['first_name']        # extract the pertinent data
                self.last_name = element['second_name']        # extract the pertinent data
                return self.first_name+" "+self.last_name
            else:
                pass
        return

    def element_gw_points(self, elementid):
        """get the GAMEWEEK poinmts of an EPL player reff'd by an element ID number"""

        self.e_target = str(elementid)
        logging.info('fpl_bootstrap:: element_gw_points() - scan target: %s' % self.e_target )
        #xxxx = self.elements[elementid]
        for element in self.elements:
            if element['id'] == elementid:
                self.gw_points_raw = element['event_points']    # note: raw points total, exlcuding bonus, multipliers & deductions
                return self.gw_points_raw
            else:
                pass
        return

    def upcomming_fixtures(self):
        """the bootstrap database holds a list of the next 10 gameweek fixtures"""
        """its just a quick way to  what fixtures are approaching in the near future"""

        logging.info('fpl_bootstrap: :upcomming_fixtures()...' )
        tn_idx = fpl_bootstrap.list_epl_teams(self)
        print ( "Next 10 fixtures..." )
        for fixture in self.next_event_fixtures:
            idx_h = int(fixture['team_h'])    # use INT to index into the team-name dict self.t that was populated in list_epl_teams()
            idx_a = int(fixture['team_a'])    # use INT to index into the team-name dict self.t that was populated in list_epl_teams()
            print ( "Game week:", fixture['event'], "Game day:", fixture['event_day'], "(", fixture['kickoff_time_formatted'], ") Teams - HOME:", self.epl_team_names[idx_h], "vs.", self.epl_team_names[idx_a], "AWAY" )
            #print ( "Home team:", self.t[idx_h] )
            #print ( "Away team:", self.t[idx_a] )
        return


    def list_epl_teams(self):
        """populate a small dict that holds epl team ID and real names"""
        """this dict is accessible via the base class fpl_bootstrap"""

        logging.info('fpl_bootstrap:: list_epl_teams()...setup a dict of team IDs + NAMES for easy reference' )
        for team_name in self.teams:
            #print ( "Team:", team_name['id'], team_name['short_name'], team_name['name'] )
            self.epl_team_names[team_name['id']] = team_name['name']    # populate the class dict, which is accessible within the class fpl_bootstrap()
        return
