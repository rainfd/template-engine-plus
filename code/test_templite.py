"""Tests for templite."""

import re
from templite import Templite, TempliteSyntaxError
from unittest import TestCase

# pylint: disable=W0612,E1101
# Disable W0612 (Unused variable) and
# E1101 (Instance of 'foo' has no 'bar' member)


class AnyOldObject(object):
    """Simple testing object.

    Use keyword arguments in the constructor to set attributes on the object.

    """
    def __init__(self, **attrs):
        for n, v in attrs.items():
            setattr(self, n, v)


class TempliteTest(TestCase):
    """Tests for Templite."""

    def try_render(self, text, ctx=None, result=None):
        """Render `text` through `ctx`, and it had better be `result`.

        Result defaults to None so we can shorten the calls where we expect
        an exception and never get to the result comparison.
        """
        actual = Templite(text).render(ctx or {})
        if result:
            self.assertEqual(actual, result)

    def assertSynErr(self, msg):
        pat = "^" + re.escape(msg) + "$"
        return self.assertRaisesRegex(TempliteSyntaxError, pat)

    def test_passthrough(self):
        # Strings without variables are passed through unchanged.
        self.assertEqual(Templite("Hello").render(), "Hello")
        self.assertEqual(
            Templite("Hello, 20% fun time!").render(),
            "Hello, 20% fun time!"
            )

    def test_variables(self):
        # Variables use {{var}} syntax.
        self.try_render("Hello, {{name}}!", {'name':'Ned'}, "Hello, Ned!")

    def test_undefined_variables(self):
        # Using undefined names is an error.
        with self.assertRaises(Exception):
            self.try_render("Hi, {{name}}!")

    def test_pipes(self):
        # Variables can be filtered with pipes.
        data = {
            'name': 'Ned',
            'upper': lambda x: x.upper(),
            'second': lambda x: x[1],
            }
        self.try_render("Hello, {{name|upper}}!", data, "Hello, NED!")

        # Pipes can be concatenated.
        self.try_render("Hello, {{name|upper|second}}!", data, "Hello, E!")

    def test_pipes_parameters(self):
        # Arguments to filters
        data = {
            'num': 1,
            'string': 'string',
            'add': lambda x, y: x + y,
        }
        self.try_render("{{ num|add:2 }}", data, '3')
        self.try_render("{{ string|add:'STRING' }}", data, 'stringSTRING')

    def test_reusability(self):
        # A single Templite can be used more than once with different data.
        globs = {
            'upper': lambda x: x.upper(),
            'punct': '!',
            }

        template = Templite("This is {{name|upper}}{{punct}}", globs)
        self.assertEqual(template.render({'name':'Ned'}), "This is NED!")
        self.assertEqual(template.render({'name':'Ben'}), "This is BEN!")

    def test_attribute(self):
        # Variables' attributes can be accessed with dots.
        obj = AnyOldObject(a="Ay")
        self.try_render("{{obj.a}}", locals(), "Ay")

        obj2 = AnyOldObject(obj=obj, b="Bee")
        self.try_render("{{obj2.obj.a}} {{obj2.b}}", locals(), "Ay Bee")

    def test_member_function(self):
        # Variables' member functions can be used, as long as they are nullary.
        class WithMemberFns(AnyOldObject):
            """A class to try out member function access."""
            def ditto(self):
                """Return twice the .txt attribute."""
                return self.txt + self.txt
        obj = WithMemberFns(txt="Once")
        self.try_render("{{obj.ditto}}", locals(), "OnceOnce")

    def test_item_access(self):
        # Variables' items can be used.
        d = {'a':17, 'b':23}
        self.try_render("{{d.a}} < {{d.b}}", locals(), "17 < 23")

    def test_loops(self):
        # Loops work like in Django.
        nums = [1,2,3,4]
        self.try_render(
            "Look: {% for n in nums %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 1, 2, 3, 4, done."
            )
        # Loop iterables can be filtered.
        def rev(l):
            """Return the reverse of `l`."""
            l = l[:]
            l.reverse()
            return l

        self.try_render(
            "Look: {% for n in nums|rev %}{{n}}, {% endfor %}done.",
            locals(),
            "Look: 4, 3, 2, 1, done."
            )

    def test_empty_loops(self):
        self.try_render(
            "Empty: {% for n in nums %}{{n}}, {% endfor %}done.",
            {'nums':[]},
            "Empty: done."
            )

    def test_multiline_loops(self):
        self.try_render(
            "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
            {'nums':[1,2,3]},
            "Look: \n\n1, \n\n2, \n\n3, \ndone."
            )

    def test_multiple_loops(self):
        self.try_render(
            "{% for n in nums %}{{n}}{% endfor %} and "
                                    "{% for n in nums %}{{n}}{% endfor %}",
            {'nums': [1,2,3]},
            "123 and 123"
            )

    def test_variables_loops(self):
        self.try_render(
            "{% for x,y in z %}{{x}},{{y}}{% endfor %}",
            {'z': [(1,2), (2,3)]},
            "1,22,3"
            )

    def test_comments(self):
        # Single-line comments work:
        self.try_render(
            "Hello, {# Name goes here: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
            )
        # and so do multi-line comments:
        self.try_render(
            "Hello, {# Name\ngoes\nhere: #}{{name}}!",
            {'name':'Ned'}, "Hello, Ned!"
            )

    def test_if(self):
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
            {'ned': 0, 'ben': 1},
            "Hi, BEN!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 0, 'ben': 0},
            "Hi, !"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 0},
            "Hi, NED!"
            )
        self.try_render(
            "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
            {'ned': 1, 'ben': 1},
            "Hi, NEDBEN!"
            )

    def test_complex_if(self):
        class Complex(AnyOldObject):
            """A class to try out complex data access."""
            def getit(self):
                """Return it."""
                return self.it
        obj = Complex(it={'x':"Hello", 'y': 0})
        self.try_render(
            "@"
            "{% if obj.getit.x %}X{% endif %}"
            "{% if obj.getit.y %}Y{% endif %}"
            "{% if obj.getit.y|str %}S{% endif %}"
            "!",
            { 'obj': obj, 'str': str },
            "@XS!"
            )

    def test_loop_if(self):
        self.try_render(
            "@{% for n in nums %}{% if n %}Z{% endif %}{{n}}{% endfor %}!",
            {'nums': [0,1,2]},
            "@0Z1Z2!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': [0,1,2]},
            "X@012!"
            )
        self.try_render(
            "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
            {'nums': []},
            "X!"
            )

    def test_elif(self):
        self.try_render(
            "{% if One %}One{% elif Two %}Two{% endif %}",
            {'One': False, 'Two': True},
            "Two"
            )
        self.try_render(
            "{% if One %}One{% elif Two %}Two{% endif %}",
            {'One': True, 'Two': True},
            "One"
            )
        self.try_render(
            "{% if One %}One"
                "{% if Two %}Two{% elif Three %}Three{% endif %}"
            "{% endif %}",
            {'One': True, 'Two': False, 'Three': True},
            "OneThree"
            )

    def test_else(self):
        self.try_render(
            "{% if One %}One{% else %}Two{% endif %}",
            {'One': False},
            'Two'
            )
        self.try_render(
            "{% if One %}"
                "{% if Two %}Two"
                "{% else %}Three"
                "{% endif %}"
            "{% endif %}",
            {"One": True, "Two": False},
            "Three"
            )

    def test_if_elif_else(self):
        self.try_render(
            "{% if One %}One{% elif Two %}Two{% else %}Three{% endif %}",
            {'One': False, 'Two': False},
            "Three"
            )

    def test_nested_loops(self):
        self.try_render(
            "@"
            "{% for n in nums %}"
                "{% for a in abc %}{{a}}{{n}}{% endfor %}"
            "{% endfor %}"
            "!",
            {'nums': [0,1,2], 'abc': ['a', 'b', 'c']},
            "@a0b0c0a1b1c1a2b2c2!"
            )

    def test_block(self):
        self.try_render(
            "{% block var %}{{ name }}{% endblock %}",
            {'name': 'Ned'},
            "Ned"
            )
        self.try_render(
            "{% block var %}"
            "{% if task %}"
                "Running!"
            "{% endif %}"
            "{% endblock %}",
            {'task': True},
            "Running!"
            )

    def test_extends(self):
        self.assertEqual(Templite("{% extends cnt %}", {'cnt': '1'}).render(), '1')
        self.assertEqual(Templite(
                "{% extends base %}"
                "{% block num %}one{% endblock %}",
                {'base': "A {% block num %}{% endblock %}"}).render(),
            "A one")

    def test_include(self):
        self.assertEqual(Templite("{% include tmp %}", {'tmp': 'hello'}).render(), 'hello')
        self.assertEqual(Templite(
                "{% include tmp %}",
                {'tmp': "{% block var %}Hello{% endblock %}"}).render(),
            'Hello')

    def test_exception_during_evaluation(self):
        # TypeError: Couldn't evaluate {{ foo.bar.baz }}:
        # 'NoneType' object is unsubscriptable
        with self.assertRaises(TypeError):
            self.try_render(
                "Hey {{foo.bar.baz}} there", {'foo': None}, "Hey ??? there"
            )

    def test_bad_names(self):
        with self.assertSynErr("Not a valid name: 'var%&!@'"):
            self.try_render("Wat: {{ var%&!@ }}")
        with self.assertSynErr("Not a valid name: 'filter%&!@'"):
            self.try_render("Wat: {{ foo|filter%&!@ }}")
        with self.assertSynErr("Not a valid name: '@'"):
            self.try_render("Wat: {% for @ in x %}{% endfor %}")
        with self.assertSynErr("Not a valid name: '@'"):
            self.try_render("Wat: {% block @ %}")
        with self.assertSynErr("Not a valid name: '@'"):
            self.try_render("{% extends @ %}")
        with self.assertSynErr("Not a valid name: '@'"):
            self.try_render("{% include @ %}")

    def test_bogus_tag_syntax(self):
        with self.assertSynErr("Don't understand tag: 'bogus'"):
            self.try_render("Huh: {% bogus %}!!{% endbogus %}??")

    def test_malformed_if(self):
        with self.assertSynErr("Don't understand if: '{% if %}'"):
            self.try_render("Buh? {% if %}hi!{% endif %}")
        with self.assertSynErr("Don't understand if: '{% if this or that %}'"):
            self.try_render("Buh? {% if this or that %}hi!{% endif %}")

    def test_malformed_elif(self):
        with self.assertSynErr("Don't understand elif: '{% elif %}'"):
            self.try_render(
                "{% if One %}One{% elif %}Two{% endif %}",
                {'One': True}
                )
        with self.assertSynErr("Don't understand elif: '{% elif a b c %}'"):
            self.try_render(
                "{% if One %}One{% elif a b c %}abc{% endif %}",
                {'One': True}
                )

    def test_malformed_else(self):
        with self.assertSynErr("Don't understand else: '{% else a %}'"):
            self.try_render("{% if One %}One{% else a %}a", {'One': True})

    def test_malformed_for(self):
        with self.assertSynErr("Don't understand for: '{% for %}'"):
            self.try_render("Weird: {% for %}loop{% endfor %}")
        with self.assertSynErr("Don't understand for: '{% for x from y %}'"):
            self.try_render("Weird: {% for x from y %}loop{% endfor %}")
        with self.assertSynErr("Don't understand for: '{% for x, y in z %}'"):
            self.try_render("Weird: {% for x, y in z %}loop{% endfor %}")

    def test_malformed_extends(self):
        with self.assertSynErr("Don't understand extends: '{% extends %}'"):
            self.try_render("{% extends %}")
        with self.assertSynErr("Don't understand extends: '{% extends x %}'"):
            self.try_render("Weird: {% extends x %}")

    def test_malformed_include(self):
        with self.assertSynErr("Don't understand include: '{% include %}'"):
            self.try_render("{% include %}")
        with self.assertSynErr("Don't understand include: '{% include x %}'"):
            self.try_render("{% include x %}")

    def test_invalid_extends(self):
        with self.assertSynErr("Not a valid name: 'unknown'"):
            self.try_render("{% extends unknown %}")
        with self.assertSynErr("Not a valid template: 'basic'"):
            self.assertEqual(Templite("{% extends basic %}", {'basic': 1}).render(),
                None)

    def test_bad_nesting(self):
        with self.assertSynErr("Unmatched action tag: 'if'"):
            self.try_render("{% if x %}X")
        with self.assertSynErr("Mismatched end tag: 'for'"):
            self.try_render("{% if x %}X{% endfor %}")
        with self.assertSynErr("Too many ends: '{% endif %}'"):
            self.try_render("{% if x %}{% endif %}{% endif %}")
        with self.assertSynErr("Unmatched action tag: 'elif'"):
            self.try_render("{% elif x %}")
        with self.assertSynErr("Unmatched action tag: 'else'"):
            self.try_render("{% else %}")
        with self.assertSynErr("Mismatched elif tag: 'for'"):
            self.try_render("{% for x in y %}{% elif x %}")
        with self.assertSynErr("Mismatched else tag: 'for'"):
            self.try_render("{% for x in y %}{% else %}")

    def test_malformed_end(self):
        with self.assertSynErr("Don't understand end: '{% end if %}'"):
            self.try_render("{% if x %}X{% end if %}")
        with self.assertSynErr("Don't understand end: '{% endif now %}'"):
            self.try_render("{% if x %}X{% endif now %}")
