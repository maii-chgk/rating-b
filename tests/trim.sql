--This trims a full Postgres backup to leave only data used in tests

drop table auth_group_permissions cascade;
drop table auth_user_groups cascade;
drop table auth_group cascade;
drop table auth_user_user_permissions cascade;
drop table auth_permission cascade;
drop table django_admin_log cascade;
drop table django_content_type cascade;
drop table django_migrations cascade;
drop table django_session cascade;
drop table auth_user cascade;
drop table b.team_lost_heredity cascade;
drop table b.team_rating_by_player cascade;
drop table ar_internal_metadata cascade;
drop table ndcg cascade;
drop table true_dls cascade;
drop table models cascade;
drop table schema_migrations cascade;
drop materialized view b.player_ranking;
drop materialized view b.team_ranking;
drop schema ia cascade;
drop schema random cascade;
drop schema quality cascade;
drop schema test0 cascade;

delete from b.player_rating_by_tournament
where release_id > 2;

delete from b.player_rating
where release_id > 2;

delete from b.team_rating
where release_id > 2;

delete from b.tournament_in_release
where release_id > 2;

delete from b.tournament_result
where tournament_id not in (6560, 6639, 7086, 7182, 7513, 6044, 6114, 7225, 7325);

delete from rosters
where tournament_id not in (6560, 6639, 7086, 7182, 7513, 6044, 6114, 7225, 7325);

delete from tournament_results
where tournament_id not in (6560, 6639, 7086, 7182, 7513, 6044, 6114, 7225, 7325);

delete from tournament_rosters
where tournament_id not in (6560, 6639, 7086, 7182, 7513, 6044, 6114, 7225, 7325);

delete from tournaments
where id not in (6560, 6639, 7086, 7182, 7513, 6044, 6114, 7225, 7325);

delete from base_rosters
where season_id != 56;

delete from b.release where id > 2;