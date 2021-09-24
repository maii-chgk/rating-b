from django.core.management.base import BaseCommand
from postgres import Postgres
import datetime

from scripts import main

class Command(BaseCommand):
	help = 'Sends individual Message_from_site by id'

	def add_arguments(self, parser):
		parser.add_argument('new_release_date')

	def handle(self, *args, **options):
		new_release_date = datetime.date(*map(int, options['new_release_date'].split('-')))
		main.calc_release(new_release_date)
