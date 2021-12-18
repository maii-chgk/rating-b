create sequence player_rating_id_seq;

create schema fullminus;

create table release
(
	id bigserial not null primary key,
	title varchar(250) not null,
	date date not null
		constraint release_date_5a2512d7_uniq
			unique,
	updated_at timestamp with time zone not null
);

create table team_rating
(
	id bigserial not null
		constraint releases_pkey
			primary key,
	team_id integer not null,
	rating integer not null,
	trb integer not null,
	rating_change integer,
	release_id bigint not null references release deferrable initially deferred,
	place numeric(7,1),
	place_change numeric(7,1),
	rating_for_next_release integer,
	constraint team_rating_release_id_team_id_3d8be5ad_uniq
		unique (release_id, team_id)
);


create index releases_release_id_72319d1e
	on team_rating (release_id);

create table tournament_result
(
	id bigserial not null
		constraint tournament_results_pkey
			primary key,
	team_id integer not null,
	tournament_id integer not null,
	mp numeric(6,1) not null,
	bp integer not null,
	m numeric(6,1) not null,
	rating integer not null,
	d1 integer not null,
	d2 integer not null,
	rating_change integer not null,
	is_in_maii_rating boolean not null,
	r integer not null,
	rb integer not null,
	rg integer not null,
	rt integer not null,
	constraint tournament_result_tournament_id_team_id_494f1d26_uniq
		unique (tournament_id, team_id)
);


create index tournament_result_tournament_id_team_id_d1_a9f9a393_idx
	on tournament_result (tournament_id, team_id, d1);

create index tournament_result_tournament_id_team_id_bp_ff869e04_idx
	on tournament_result (tournament_id, team_id, bp);

create index tournament_result_tournament_id_team_id_m_c17d42fd_idx
	on tournament_result (tournament_id, team_id, m);

create index tournament_result_tournament_id_team_id_mp_f7791a54_idx
	on tournament_result (tournament_id, team_id, mp);

create index tournament_result_tournament_id_team_id_d2_0fffa968_idx
	on tournament_result (tournament_id, team_id, d2);

create index tournament_result_tournament_id_team_id_ra_954e687f_idx
	on tournament_result (tournament_id, team_id, rating_change);

create index tournament_result_tournament_id_team_id_rating_26057df6_idx
	on tournament_result (tournament_id, team_id, rating);

create table team_rating_by_player
(
	id bigserial not null
		constraint team_rating_by_player_pkey
			primary key,
	player_id integer not null,
	"order" smallint not null,
	contribution integer not null,
	team_rating_id bigint not null
		constraint team_rating_by_player_team_rating_id_7b018454_fk_releases_id
			references team_rating
				deferrable initially deferred,
	constraint team_rating_by_player_team_rating_id_player_id_4f054658_uniq
		unique (team_rating_id, player_id)
);


create index team_rating_by_player_team_rating_id_7b018454
	on team_rating_by_player (team_rating_id);

create index team_rating_by_player_team_rating_id_player_id_08ec8a7b_idx
	on team_rating_by_player (team_rating_id, player_id, "order");

create table player_rating_by_tournament
(
	id bigserial not null
		constraint player_rating_by_tournament_pkey
			primary key,
	player_id integer not null,
	weeks_since_tournament smallint not null,
	cur_score integer not null,
	release_id bigint not null
		constraint player_rating_by_tou_release_id_a4088cb4_fk_release_d
			references release
				deferrable initially deferred,
	tournament_result_id bigint
		constraint player_rating_by_tou_tournament_result_id_b1275051_fk_tournamen
			references tournament_result
				deferrable initially deferred,
	initial_score integer,
	tournament_id integer,
	constraint player_rating_by_tournam_release_id_player_id_tou_217c2530_uniq
		unique (release_id, player_id, tournament_result_id),
	constraint player_rating_by_tournam_release_id_player_id_tou_65bdbdd1_uniq
		unique (release_id, player_id, tournament_id)
);


create index player_rating_by_tournament_release_id_a4088cb4
	on player_rating_by_tournament (release_id);

create index player_rating_by_tournament_tournament_result_id_b1275051
	on player_rating_by_tournament (tournament_result_id);

create index player_rating_by_tournam_release_id_player_id_cur_0799d3f6_idx
	on player_rating_by_tournament (release_id, player_id, cur_score);

create table player_rating
(
	id bigserial not null
		constraint player_rating_pkey
			primary key,
	player_id integer not null,
	rating integer not null,
	rating_change integer,
	release_id bigint not null references release deferrable initially deferred,
	place numeric(7,1),
	place_change numeric(7,1),
	constraint player_rating_release_id_player_id_179cda25_uniq
		unique (release_id, player_id)
);

create index player_rating_release_id_52b7952e
	on player_rating (release_id);


create index player_rating_release_id_rating_idx
	on player_rating (release_id, rating);

create table team_lost_heredity
(
	id bigserial not null
		constraint team_lost_heredity_pkey
			primary key,
	season_id integer not null,
	team_id integer not null,
	date date not null,
	constraint team_lost_heredity_season_id_team_id_c3e8a97e_uniq
		unique (season_id, team_id)
);


create table tournament_in_release
(
	id bigserial not null
		constraint tournament_in_release_pkey
			primary key,
	tournament_id integer not null,
	release_id bigint not null
		constraint tournament_in_release_release_id_af6ae186_fk_release_id
			references release
				deferrable initially deferred,
	constraint tournament_in_release_release_id_tournament_id_1da45065_uniq
		unique (release_id, tournament_id)
);

create index tournament_in_release_release_id_af6ae186
	on tournament_in_release (release_id);

