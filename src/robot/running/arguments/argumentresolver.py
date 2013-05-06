#  Copyright 2008-2012 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot.errors import DataError

from .argumentvalidator import ArgumentValidator


class ArgumentResolver(object):

    def __init__(self, argspec, resolve_named=True,
                 resolve_variables_until=None):
        self._named_resolver = NamedArgumentResolver(argspec) \
            if resolve_named else NullNamedArgumentResolver()
        self._variable_replacer = VariableReplacer(resolve_variables_until)
        self._argument_validator = ArgumentValidator(argspec)

    def resolve(self, arguments, variables=None):
        positional, named = self._named_resolver.resolve(arguments)
        positional, named = self._variable_replacer.replace(positional, named,
                                                            variables)
        self._argument_validator.validate(positional, named)
        return positional, named


class NamedArgumentResolver(object):

    def __init__(self, argspec):
        self._argspec = argspec

    def resolve(self, arguments):
        positional = []
        named = {}
        for arg in arguments:
            if self._is_named(arg):
                self._add_named(arg, named)
            elif named:
                self._raise_positional_after_named()
            else:
                positional.append(arg)
        return positional, named

    def _is_named(self, arg):
        if not isinstance(arg, basestring) or '=' not in arg:
            return False
        name = arg.split('=')[0]
        if self._is_escaped(name):
            return False
        return name in self._argspec.positional or self._argspec.kwargs

    def _is_escaped(self, name):
        return name.endswith('\\')

    def _add_named(self, arg, named):
        name, value = arg.split('=', 1)
        name = self._verify_str(name)
        if name in named:
            self._raise_multiple_values(name)
        named[name] = value

    def _verify_str(self, name):
        # Python 2.5 doesn't handle Unicode at all and Jython 2.5 and 2.7b1 handle non-ASCII Unicode wrong.
        try:
            return str(name)
        except UnicodeError:
            raise DataError("Illegal characters in argument name: '%s'" % name)

    def _raise_multiple_values(self, name):
        raise DataError("%s '%s' got multiple values for argument '%s'."
                        % (self._argspec.type, self._argspec.name, name))

    def _raise_positional_after_named(self):
        raise DataError("%s '%s' got positional argument after named arguments."
                        % (self._argspec.type, self._argspec.name))


class NullNamedArgumentResolver(object):

    def resolve(self, arguments):
        return arguments, {}


class VariableReplacer(object):

    def __init__(self, resolve_until=None):
        self._resolve_until = resolve_until

    def replace(self, positional, named, variables=None):
        # `variables` is None when using Libdoc
        if variables:
            positional = variables.replace_list(positional, self._resolve_until)
            named = dict((name, variables.replace_scalar(value))
                         for name, value in named.items())
        return positional, named
