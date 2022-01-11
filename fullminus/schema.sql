create schema fullminus;

set search_path to fullminus;

create table release
(
	id bigserial not null primary key,
	title varchar(250) not null,
	date date not null unique,
	updated_at timestamp with time zone not null
);

create table team_rating
(
	id bigserial not null primary key,
	team_id integer not null,
	rating integer not null,
	trb integer not null,
	rating_change integer,
	release_id bigint not null references release deferrable initially deferred,
	place numeric(7,1),
	place_change numeric(7,1),
	rating_for_next_release integer,
	unique (release_id, team_id)
);
create index on team_rating (release_id);

create table tournament_result
(
	id bigserial not null primary key,
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
	unique (tournament_id, team_id)
);

create index on tournament_result (tournament_id, team_id);
create index on tournament_result (tournament_id, team_id, rating);

create table team_rating_by_player
(
	id bigserial not null primary key,
	player_id integer not null,
	"order" smallint not null,
	contribution integer not null,
	team_rating_id bigint not null references team_rating deferrable initially deferred,
	unique (team_rating_id, player_id)
);
create index on team_rating_by_player (team_rating_id);
create index on team_rating_by_player (team_rating_id, player_id, "order");

create table player_rating_by_tournament
(
	id bigserial not null primary key,
	player_id integer not null,
	weeks_since_tournament smallint not null,
	cur_score integer not null,
	release_id bigint not null references release deferrable initially deferred,
	tournament_result_id bigint references tournament_result deferrable initially deferred,
	initial_score integer,
	tournament_id integer,
	unique (release_id, player_id, tournament_result_id),
	unique (release_id, player_id, tournament_id)
);

create index on player_rating_by_tournament (release_id);
create index on player_rating_by_tournament (tournament_result_id);
create index on player_rating_by_tournament (release_id, player_id, cur_score);

create table player_rating
(
	id bigserial not null primary key,
	player_id integer not null,
	rating integer not null,
	rating_change integer,
	release_id bigint not null references release deferrable initially deferred,
	place numeric(7,1),
	place_change numeric(7,1),
	unique (release_id, player_id)
);
create index on player_rating (release_id);
create index on player_rating (release_id, rating);

create table team_lost_heredity
(
	id bigserial not null primary key,
	season_id integer not null,
	team_id integer not null,
	date date not null,
    unique (season_id, team_id)
);


create table tournament_in_release
(
	id bigserial not null primary key,
	tournament_id integer not null,
	release_id bigint not null references release deferrable initially deferred,
	unique (release_id, tournament_id)
);
create index on tournament_in_release (release_id);

