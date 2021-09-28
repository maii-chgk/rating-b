from django.db import models

from scripts import constants

class Team(models.Model):
    title = models.CharField(verbose_name='Название', max_length=250)
    class Meta:
        db_table = "rating_team"

class Tournament(models.Model):
    title = models.CharField(verbose_name='Название', max_length=100)
    maii_rating = models.BooleanField(verbose_name='Учитывается ли в рейтинге МАИИ')
    start_datetime = models.DateTimeField(verbose_name='Начало отыгрыша')
    end_datetime = models.DateTimeField(verbose_name='Конец отыгрыша')
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
    date = models.DateField(verbose_name='Дата из мира игр', unique=True)
    updated_at = models.DateTimeField(verbose_name='Дата последнего изменения', auto_now=True)
    class Meta:
        db_table = "release"

class Team_rating(models.Model):
    release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
    team = models.ForeignKey(Team, verbose_name='Команда', on_delete=models.PROTECT, null=True)
    # team_id = models.IntegerField(verbose_name='Команда')
    rating = models.IntegerField(verbose_name='Рейтинг команды')
    rt = models.IntegerField(verbose_name='Технический рейтинг команды RT')
    rating_change = models.IntegerField(verbose_name='Изменение с прошлого релиза', null=True)
    place = models.DecimalField(verbose_name='Место в релизе', max_digits=7, decimal_places=1, null=True)
    place_change = models.DecimalField(verbose_name='Изменение места с прошлого релиза', max_digits=7, decimal_places=1, null=True)
    class Meta:
        db_table = "team_rating"
        unique_together = (("release", "team", ), )
        index_together = [
            ["release", "team", "rating"],
            ["release", "team", "rating_change"],
            ["release", "team", "place"],
            ["release", "team", "place_change"],
        ]

class Player_rating(models.Model):
    release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
    # player_id = models.IntegerField(verbose_name='Игрок')
    rating = models.IntegerField(verbose_name='Рейтинг игрока')
    rating_change = models.IntegerField(verbose_name='Изменение с прошлого релиза', null=True)
    place = models.DecimalField(verbose_name='Место в релизе', max_digits=7, decimal_places=1, null=True)
    place_change = models.DecimalField(verbose_name='Изменение места с прошлого релиза', max_digits=7, decimal_places=1, null=True)
    class Meta:
        db_table = "player_rating"
        unique_together = (("release", "player", ), )
        index_together = [
            ["release", "player", "rating"],
            ["release", "player", "rating_change"],
            ["release", "player", "place"],
            ["release", "player", "place_change"],
        ]

class Team_rating_by_player(models.Model):
    team_rating = models.ForeignKey(Team_rating, verbose_name='Рейтинг команды в релизе', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
    # player_id = models.IntegerField(verbose_name='Игрок')
    order = models.SmallIntegerField(verbose_name='Порядок игрока по рейтингу по убыванию, наибольший рейтинг получает 1')
    contribution = models.IntegerField(verbose_name='Вклад игрока в TRB команды')
    class Meta:
        db_table = "team_rating_by_player"
        unique_together = (("team_rating", "player", ), )
        index_together = [
            ["team_rating", "player", "order"],
        ]

class Tournament_result(models.Model):
    tournament = models.ForeignKey(Tournament, verbose_name='Турнир', on_delete=models.PROTECT, null=True)
    # tournament_id = models.IntegerField(verbose_name='Турнир')
    team = models.ForeignKey(Team, verbose_name='Команда', on_delete=models.PROTECT, null=True)
    # team_id = models.IntegerField(verbose_name='Команда')
    mp = models.DecimalField(verbose_name='Предсказанное место', max_digits=6, decimal_places=1)
    bp = models.IntegerField(verbose_name='Предсказанный балл')
    m = models.DecimalField(verbose_name='Занятое место', max_digits=6, decimal_places=1)
    rating = models.IntegerField(verbose_name='Набранный балл B')
    d1 = models.IntegerField(verbose_name='D1')
    d2 = models.IntegerField(verbose_name='D2')
    rating_change = models.IntegerField(verbose_name='Результат команды на турнире D')
    class Meta:
        db_table = "tournament_result"
        unique_together = (("tournament", "team", ), )
        index_together = [
            ["tournament", "team", "mp"],
            ["tournament", "team", "bp"],
            ["tournament", "team", "m"],
            ["tournament", "team", "rating"],
            ["tournament", "team", "d1"],
            ["tournament", "team", "d2"],
            ["tournament", "team", "rating_change"],
        ]

# We use either tournament_result (for new tournaments) or tournament+initial_score
class Player_rating_by_tournament(models.Model):
    release = models.ForeignKey(Release, verbose_name='Релиз', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, null=True)
    # player_id = models.IntegerField(verbose_name='Игрок')
    tournament_result = models.ForeignKey(Tournament_result, verbose_name='Результат команды на турнире', on_delete=models.CASCADE, null=True)
    tournament = models.ForeignKey(Tournament, verbose_name='Турнир', on_delete=models.PROTECT, null=True)
    # tournament_id = models.IntegerField(verbose_name='Турнир', null=True)
    initial_score = models.IntegerField(verbose_name='Бонус игрока за турнир', null=True)
    weeks_since_tournament = models.SmallIntegerField(verbose_name='Число недель, прошедших после турнира, начиная с 0')
    cur_score = models.IntegerField(verbose_name='Вклад в рейтинг игрока в этом релизе')
    raw_cur_score = None  # Float value for better precision
    class Meta:
        db_table = "player_rating_by_tournament"
        unique_together = (("release", "player", "tournament_result"), ("release", "player", "tournament"), )
        index_together = [
            ["release", "player", "cur_score"],
        ]
    def recalc_cur_score(self):
        self.weeks_since_tournament += 1
        self.raw_cur_score = self.initial_score * (constants.J ** self.weeks_since_tournament)
        self.cur_score = round(self.raw_cur_score)
