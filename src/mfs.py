import logging


# TODO Add description to this module.
"""
    "mfs" means "Membership Functions". Read more here: https://en.wikipedia.org/wiki/Fuzzy_set
"""


class MembershipFunctionTerm:
    form = None

    def __init__(self, form):
        self.form = form

    def __call__(self, val, *args, **kwargs):
        return self.get_value(val)

    def get_value(self, val):
        raise NotImplementedError()


class SMF(MembershipFunctionTerm):
    def get_value(self, val):
        a, b = self.form
        a, b = max(a, 0), max(b, 0)
        try:
            return 0 if val <= a else 1 if val > b else ((val - a) / (b - a))
        except ZeroDivisionError:
            logging.exception("", extra={"value": val, "form": self.form, "class": type(self)})
            return 0


class ZMF(MembershipFunctionTerm):
    def get_value(self, val):
        a, b = self.form
        a, b = max(a, 0), max(b, 0)
        try:
            return 1 if val < a else 0 if val >= b else ((b - val) / (b - a))
        except ZeroDivisionError:
            logging.exception("", extra={"value": val, "form": self.form, "class": type(self)})
            return 0


class TrapezoidMF(MembershipFunctionTerm):
    def get_value(self, val):
        a, b, c, d = self.form
        a, b, c, d = max(a, 0), max(b, 0), max(c, 0), max(d, 0)

        if None in (val, a, b, c, d):
            return 0

        try:
            return (
                0 if val <= a or val >= d else
                1 if b < val < c else
                ((val - a) / (b - a)) if val < b else
                ((d - val) / (d - c))
            )
        except (ZeroDivisionError, TypeError):
            logging.exception("", extra={"value": val, "form": self.form, "class": type(self)})
            return 0


class TriangleMF(MembershipFunctionTerm):
    def get_value(self, val):
        a, b, c = self.form
        a, b, c = max(a, 0), max(b, 0), max(c, 0)

        if None in (val, a, b, c):
            return 0

        try:
            return (
                0 if val <= a or val >= c else
                ((val - a) / (b - a)) if val <= b else
                ((c - val) / (c - b))
            )
        except ZeroDivisionError:
            logging.exception("", extra={"value": val, "form": self.form, "class": type(self)})
            return 0


class SingletonMF(MembershipFunctionTerm):
    def get_value(self, val):
        a = self.form[0]
        return int(val == a)
