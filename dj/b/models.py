from django.db import models

class Medal_order(models.Model):
	lname = models.CharField(verbose_name='Фамилия', max_length=100)
	fname = models.CharField(verbose_name='Имя', max_length=100)
	zipcode = models.CharField(verbose_name='Почтовый индекс', max_length=8, blank=True)
	address = models.CharField(verbose_name='Почтовый адрес', max_length=MAX_POSTAL_ADDRESS_LENGTH, blank=True)
	email = models.CharField(verbose_name='E-mail для связи', max_length=MAX_EMAIL_LENGTH)
	phone_number = models.CharField(verbose_name='Мобильный телефон', max_length=MAX_PHONE_NUMBER_LENGTH, blank=True)

	year = models.SmallIntegerField(verbose_name='Год КЛБМатча', default=models_klb.MEDAL_PAYMENT_YEAR)
	n_medals = models.SmallIntegerField(verbose_name='Число медалей', default=1)
	delivery_method = models.SmallIntegerField(verbose_name='Способ доставки', choices=[(a, b) for a, b, c in MEDAL_ORDER_CURRENT_CHOICES], default=2)
	with_plate = models.BooleanField(verbose_name='С шильдой, на которой будут имя и команда участника (бесплатно, но медаль приедет позже)', default=True, blank=True)

	comment = models.CharField(verbose_name='Комментарий', max_length=500, blank=True)

	payment = models.OneToOneField(Payment_moneta, verbose_name='Платёж, которым оплачено участие', on_delete=models.SET_NULL,
		null=True, blank=True, default=None)
	created_time = models.DateTimeField(verbose_name='Дата создания', default=datetime.datetime.now, db_index=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Кто добавил на сайт',
		on_delete=models.SET_NULL, default=None, null=True, blank=True)
	class Meta:
		db_table = "dj_medal_order"
	def to_show_name(self):
		return self.created_by and ((self.lname != self.created_by.last_name) or (self.fname != self.created_by.first_name))
	def get_delivery_method_short(self):
		return MEDAL_ORDER_DELIVERY_CHOICES[self.delivery_method][2]
