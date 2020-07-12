import logging


# TODO Add description to this module.
"""
    "mfs" means "Membership Functions". Read more here: https://en.wikipedia.org/wiki/Fuzzy_set
"""


class MembershipFunctionTerm:
    form = None

    def __init__(self, form: tuple):
        """
        :param form: tuple of number that describe shape of MF:
        ex. (low, high) for SMF or (high, low) for ZMF
        """
        self.form = form

        self.validate()

    def __call__(self, val, *args, **kwargs):
        return self.get_value(val)

    def validate(self):
        raise NotImplementedError()

    def get_value(self, val):
        raise NotImplementedError()


class SMF(MembershipFunctionTerm):
    def validate(self):
        left, right = self.form
        assert isinstance(left, (int, float))
        assert isinstance(right, (int, float))
        assert left <= right

    def get_value(self, val):
        assert isinstance(val, (int, float))

        left, right = self.form

        if left == right == val:
            return 0
        if val <= left:
            return 0
        if val >= right:
            return 1

        return (val - left) / (right - left)


class ZMF(MembershipFunctionTerm):
    def validate(self):
        left, right = self.form
        assert isinstance(left, (int, float))
        assert isinstance(right, (int, float))
        assert left <= right

    def get_value(self, val):
        assert isinstance(val, (int, float))

        left, right = self.form

        if left == right == val:
            return 0
        if val <= left:
            return 1
        if val >= right:
            return 0

        return (right - val) / (right - left)


class TrapezoidMF(MembershipFunctionTerm):
    def validate(self):
        left, left_top, right_top, right = self.form
        assert isinstance(left, (int, float))
        assert isinstance(right, (int, float))
        assert isinstance(left_top, (int, float))
        assert isinstance(right_top, (int, float))
        assert left <= left_top <= right_top <= right

    def get_value(self, val):
        assert isinstance(val, (int, float))

        left, left_top, right_top, right = self.form

        if left == left_top == right_top == right:
            return 0

        if val <= left or val >= right:
            return 0
        if left_top <= val <= right_top:
            return 1
        if val < left_top:
            return (val - left) / (left_top - left)

        return (right - val) / (right - right_top)


class TriangleMF(MembershipFunctionTerm):
    def validate(self):
        left, top, right = self.form
        assert isinstance(left, (int, float))
        assert isinstance(right, (int, float))
        assert isinstance(top, (int, float))
        assert left <= top <= right

    def get_value(self, val):
        assert isinstance(val, (int, float))

        left, top, right = self.form

        if left == top == right:
            return 0

        if val <= left or val >= right:
            return 0
        if val < top:
            return (val - left) / (top - left)

        return (right - val) / (right - top)


class SingletonMF(MembershipFunctionTerm):
    def validate(self):
        single = self.form[0]
        assert isinstance(single, (int, float))

    def get_value(self, val):
        assert isinstance(val, (int, float))

        single = self.form[0]

        return float(val == single)
