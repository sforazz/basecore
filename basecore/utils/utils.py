import argparse
import getpass


class Password(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        if values is None:
            if self.dest:
                print_arg = self.dest
            else:
                print_arg = 'Password:'
            values = getpass.getpass(print_arg)

        setattr(namespace, self.dest, values)