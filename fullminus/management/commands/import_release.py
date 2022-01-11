from django.core.management.base import BaseCommand
from postgres import Postgres
import datetime

from scripts import main
# from scripts import private_setting

class Command(BaseCommand):
	help = 'Imports teams and players rating from API for given release date.'

	def add_arguments(self, parser):
		parser.add_argument('api_release_id', type=int)

	def handle(self, *args, **options):
		main.import_release(options['api_release_id'])
