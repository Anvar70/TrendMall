from getpass import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Create a store admin with an interactive password.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--name', default='Store Admin')
        parser.add_argument('--phone', required=True)

    def handle(self, *args, **options):
        user = User(email=options['email'].strip().lower(), full_name=options['name'], phone=options['phone'], role='ADMIN')
        password = getpass('Password: ')
        if password != getpass('Confirm password: '):
            raise CommandError('Passwords do not match.')
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
            user.save()
        except ValidationError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS('Store admin created.'))
