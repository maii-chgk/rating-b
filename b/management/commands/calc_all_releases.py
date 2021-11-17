from django.core.management.base import BaseCommand

from scripts import main

class Command(BaseCommand):
	help = 'Calculates all releases since Spetember 2021.'

	def add_arguments(self, parser):
		parser.add_argument('--verbose', action='store_true')

	def handle(self, *args, **options):
		main.calc_all_releases(flag_verbose=options['verbose'])
