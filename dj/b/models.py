from django.db import models

class Team(models.Model):
	title = models.CharField(verbose_name='Название', max_length=250)
	class Meta:
		db_table = "rating_team"

class Tournament(models.Model):
	title = models.CharField(verbose_name='Название', max_length=100)
	class Meta:
		db_table = "rating_tournament"

class Player(models.Model):
	last_name = models.CharField(verbose_name='Фамилия', max_length=100)
	first_name = models.CharField(verbose_name='Имя', max_length=100)
	patronymic = models.CharField(verbose_name='Отчество', max_length=100)
	class Meta:
		db_table = "rating_player"

class Release(models.Model):
	title = models.CharField(verbose_name='Название', max_length=250)
	date = models.DateField(verbose_name='Дата из мира игр')
	updated_at = models.DateTimeField(verbose_name='Дата последнего изменения', auto_now=True)
	class Meta:
		db_table = "release_details"

class Team_rating(models.Model):
	team = models.ForeignKey(Team, verbose_name='Команда', on_delete=models.PROTECT, null=True)
	# team_id = models.IntegerField(verbose_name='Команда')
	release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
	rating = models.IntegerField(verbose_name='Рейтинг команды')
	rt = models.IntegerField(verbose_name='Технический рейтинг команды RT')
	rating_change = models.IntegerField(verbose_name='Изменение с прошлого релиза', null=True)
	class Meta:
		db_table = "releases"

class Player_rating(models.Model):
	player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
	# player_id = models.IntegerField(verbose_name='Игрок')
	release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
	rating = models.IntegerField(verbose_name='Рейтинг игрока')
	rating_change = models.IntegerField(verbose_name='Изменение с прошлого релиза', null=True)
	class Meta:
		db_table = "player_rating"

class Team_rating_by_player(models.Model):
	team_rating = models.ForeignKey(Team_rating, verbose_name='Рейтинг команды в релизе', on_delete=models.CASCADE)
	player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
	# player_id = models.IntegerField(verbose_name='Игрок')
	order = models.SmallIntegerField(verbose_name='Порядок игрока по рейтингу по убыванию, наибольший рейтинг получает 1')
	contribution = models.IntegerField(verbose_name='Вклад игрока в TRB команды')
	class Meta:
		db_table = "team_rating_by_player"

class Tournament_result(models.Model):
	team = models.ForeignKey(Team, verbose_name='Команда', on_delete=models.PROTECT, null=True)
	# team_id = models.IntegerField(verbose_name='Команда')
	tournament = models.ForeignKey(Tournament, verbose_name='Турнир', on_delete=models.PROTECT, null=True)
	# tournament_id = models.IntegerField(verbose_name='Турнир')
	mp = models.DecimalField(verbose_name='Предсказанное место', max_digits=6, decimal_places=1)
	bp = models.IntegerField(verbose_name='Предсказанный балл')
	m = models.DecimalField(verbose_name='Занятое место', max_digits=6, decimal_places=1)
	rating = models.IntegerField(verbose_name='Набранный балл B')
	d1 = models.IntegerField(verbose_name='D1')
	d2 = models.IntegerField(verbose_name='D2')
	rating_change = models.IntegerField(verbose_name='Результат команды на турнире D')
	class Meta:
		db_table = "tournament_results"

class Player_rating_by_tournament(models.Model):
	release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
	player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
	# player_id = models.IntegerField(verbose_name='Игрок')
	tournament_result = models.ForeignKey(Tournament_result, verbose_name='Результат команды на турнире', on_delete=models.CASCADE)
	weeks_since_tournament = models.SmallIntegerField(verbose_name='Число недель, прошедших после турнира, начиная с 0')
	cur_score = models.IntegerField(verbose_name='Вклад в рейтинг игрока в этом релизе')
	class Meta:
		db_table = "player_rating_by_tournament"
