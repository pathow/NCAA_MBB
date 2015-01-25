-- Makes the game_stats table double wide, matching teams to their opponents to allow for information of a team's defense

create table team_stats as
		select a.game_id, a.team, b.team as opponent, a.home_away,
						a.pts as pts, a.fgm, a.fga, a.t_3pm, a.t_3pa, a.ftm, a.fta, a.oreb, a.reb, a.ast, a.stl, a.blk, a.turnover, a.pf,
						b.pts as pts_allowed, b.fgm as opp_fgm, b.fga as opp_fga, b.t_3pm as opp_3pm, b.t_3pa as opp_3pa, b.ftm as opp_ftm,
						b.fta as opp_fta, b.oreb as opp_oreb, b.reb as opp_reb, b.ast as opp_ast, b.stl as opp_stl, b.blk as opp_blk,
						b.turnover as opp_turnover, b.pf as opp_pf 
		from (select "FGM" as fgm, "FGA" as fga, "3PM" as t_3pm, "3PA" as t_3pa, "FTM" as ftm, "FTA" as fta,
							"OREB" as oreb, "REB" as reb, "AST" as ast, "STL" as stl, "BLK" as blk, "TO" as turnover, 
							"PF" as pf, "PTS" as pts, "Team" as team, "Game_ID" as game_id, "Home_Away" as home_away
					from game_stats) as a
		left join (select "FGM" as fgm, "FGA" as fga, "3PM" as t_3pm, "3PA" as t_3pa, "FTM" as ftm, "FTA" as fta,
							"OREB" as oreb, "REB" as reb, "AST" as ast, "STL" as stl, "BLK" as blk, "TO" as turnover, 
							"PF" as pf, "PTS" as pts, "Team" as team, "Game_ID" as game_id
					from game_stats) as b
		on a.game_id = b.game_id and a.team <> b.team;

commit;

select a.*, b."Game_Year"as year, b."Game_Date" as day, b."Game_Tipoff" as tipoff 
from team_stats as a
	left join (select "Game_Year", "Game_Date", "Game_ID", "Game_Tipoff" from gen_info) as b
	on a.game_id = b."Game_ID";




