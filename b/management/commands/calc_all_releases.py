from django.core.management.base import BaseCommand

from scripts import main

class Command(BaseCommand):
	help = 'Calculates all releases since Spetember 2021.'

	def handle(self, *args, **options):
		main.calc_all_releases()
