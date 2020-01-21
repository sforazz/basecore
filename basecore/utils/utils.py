import argparse
import getpass


class Password(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):

        if values is None:
            values = getpass.getpass('Please type in your password: ')

        setattr(namespace, self.dest, values)