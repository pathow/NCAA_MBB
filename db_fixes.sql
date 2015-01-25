-- Adding a column to the players table that turns the "text" type of the Min column into true integers
alter table players add column minutes integer;
update players
	set minutes = cast(nullif("Min", '') as int);
commit;

-- Turning the year in game dates to integers to allow for basic addition/subtraction of years
alter table gen_info add column year integer;
update gen_info
	set year = cast(nullif("Game_Year", '') as int);
commit;


-- Creating a view of the query required to calculated total minutes played by a full team in a single game
-- Query takes about 1min20sec to run
create view minutes_played as
select *
	from team_stats left join (select distinct * 
		from (select  "Home_Away", "Game_ID", sum(minutes) over (partition by "Home_Away", "Game_ID") as mp
			 from players) as A) as B on team_stats.game_id = B."Game_ID" and team_stats.home_away=B."Home_Away";


-- Adding a column to the team statistics table that uses a join to get the total team minutes played in a game
-- permenantly into the table, matched on game id number and home/away of the team
alter table team_stats add column team_mp int;
update team_stats as base
	set team_mp = temp.mp
	from minutes_played as temp
	where base.game_id = temp.game_id and base.home_away = temp.home_away;
commit;

select * from team_stats;

-- alter table team_stats drop column poss_estimate;  <-- in case adjustments needed to formula

-- Possession estimate as used by Ken Pomeroy for college basketball...rounded to nearest integer via data type;

alter table team_stats add column poss_estimate int;
update team_stats
	set poss_estimate = (0.5*((fga + 0.475*fta - oreb + turnover)
		 + (opp_fga + 0.475*opp_fta - opp_oreb +opp_turnover)));
commit;
