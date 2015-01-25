select * from team_stats;

-- Effective Field Goal Percentage
select game_id, team, ((fgm + 0.5*t_3pm)/fga) as efg
from team_stats;

-- Turnover Percentage (remove 100 for actual?)
select game_id, team, (100*(turnover/(fga + 0.475*fta + turnover))) as tovper
from team_stats;

-- Rebounding Percentage
-- Offensive
select game_id, team, (100*oreb/(oreb + (opp_reb-opp_oreb))) as offrebper
from team_stats;
--Defensive
select game_id, team, (100*(reb-oreb)/(opp_oreb + (reb-oreb))) as defrebper
from team_stats;

-- Free Throw Percentage
-- Offensive
select game_id, team, (100*ftm/fga) as oftrate
from team_stats;
-- Defensive
select game_id, team, (100*opp_ftm/opp_fga) as dftrate
from team_stats;

-- How to code for win/loss
select game_id, team, pts, pts_allowed, (case when pts > pts_allowed then 1 else 0 end) as win
from team_stats;

-- Games per season counts and points information to make Pythagorean Wins
select *  from gen_info;

select *, (wins - pyth_wins) as difference
from (select *, (games * pts^14.0 / (pts^14.0 + opp_pts^14.0)) as pyth_wins
		from (select team, season, count(team) as games, sum(pts) as pts, sum(pts_allowed) as opp_pts, sum(win) as wins
					from (select A.team, A.game_id, A.pts, A.pts_allowed, (case when A.pts > A.pts_allowed then 1 else 0 end) as win,
						B."Game_Date" as game_date, 
		 				(case 
		 					when B."Game_Date" like 'Nov%' then B.year+1
		 					when B."Game_Date" like 'Dec%' then B.year+1
		 					else B.year
		 				 end) as season
					from team_stats as A
					left join gen_info as B
					on A.game_id = B."Game_ID") as combined
					group by team, season) as pythag) as total
order by difference asc;
