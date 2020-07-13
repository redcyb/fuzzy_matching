import logging

from django.db.models import Manager

from src import mfs

DEFAULT_ABSOLUTE_FUZZINESS = (3, "absolute")
DEFAULT_RELATIVE_FUZZINESS = (0.1, "relative")


def get_shift_for_value(value, fuzziness=DEFAULT_RELATIVE_FUZZINESS):
    fuzziness = fuzziness or 0
    if isinstance(fuzziness, (int, float)):
        shift = value * fuzziness
    elif fuzziness[1] == "relative":
        shift = value * fuzziness[0]
    else:
        shift = fuzziness[0]
    return shift


class AbstractCriteria:
    def get_details(self):
        raise NotImplementedError()


class Criteria(AbstractCriteria):
    first_obj = None
    second_obj = None
    first_field = None
    second_field = None
    match_type = None
    mem_func = None
    influence = None
    fuzziness = None
    penalty = None
    scale = "linear"
    hard_edge = None

    def __init__(self, first_obj, second_obj,
                 first_field=None, second_field=None, match_type=None,
                 mem_func=None, mem_func_name=None, scale=None, hard_edge=None, fuzziness=None, influence=None,
                 penalty=None):
        self.first_obj = first_obj
        self.second_obj = second_obj

        self.first_field = first_field or self.first_field
        self.second_field = second_field or self.second_field
        self.match_type = match_type or self.match_type
        self.mem_func = mem_func or self.mem_func
        self.scale = scale or self.scale
        self.penalty = penalty or self.penalty
        self.hard_edge = hard_edge or self.hard_edge
        self.fuzziness = fuzziness if fuzziness is not None else self.fuzziness
        self.influence = influence if influence is not None else self.influence
        self._match = None

        if mem_func_name:
            self.mem_func = getattr(mfs, mem_func_name)

        self.set_mem_func()

    def set_mem_func(self):
        if self.mem_func is not None:
            return
        raise NotImplementedError("Membership function is not set")

    def get_penalty(self):
        if not self.penalty:
            return 1.
        if self.penalty.get("type") == "absolute":
            return self.get_absolute_penalty()
        if self.penalty.get("type") == "relative":
            return self.get_relative_penalty()
        return 1.

    def get_value(self):
        try:
            return (self.mem_func(getattr(self.first_obj, self.first_field)) *
                    self.influence *
                    self.get_penalty())
        except Exception:
            logging.exception("Bad match value")
            return 0.

    def get_absolute_penalty(self):
        '''

            In this criteria we penalize objects by distance between first's and second's objects fields.
            Ex:

            penalty = penalty_function(abs(second_field - first_field))

            then for result value just use penalty:
            result = value * penalty
        '''

        b_val = getattr(self.second_obj, self.second_field)
        p_val = getattr(self.first_obj, self.first_field)

        if isinstance(b_val, dict):
            return self.get_absolute_penalty_for_range(b_val, p_val)

        if isinstance(b_val, (int, float)):
            return self.get_absolute_penalty_for_number(b_val, p_val)

        return 0.

    def get_relative_penalty(self):
        '''

            In this criteria we penalize objects by relative value. Ex:

            val = second_field_range[high] / first_field
            and
            val = first_field / second_field_range[low]

            penalty = penalty_function(val)

            then for result value just use penalty:
            result = value * penalty

        '''

        b_val = getattr(self.second_obj, self.second_field)
        p_val = getattr(self.first_obj, self.first_field)

        if isinstance(b_val, dict):
            return self.get_relative_penalty_for_range(b_val, p_val)

        if isinstance(b_val, (int, float)):
            return self.get_relative_penalty_for_number(b_val, p_val)

        return 0.

    def get_absolute_penalty_for_number(self, b_val, p_val):
        if p_val is None:
            return 0.

        if b_val == self.penalty.get("default"):
            return 0.

        low_penalty, high_penalty = self.penalty["low"], self.penalty["high"]
        penalty_function = getattr(mfs, self.penalty["func"])([low_penalty, high_penalty])
        return penalty_function(abs(p_val - b_val))

    def get_absolute_penalty_for_range(self, b_val, p_val):
        if p_val is None:
            return 0.

        low_penalty, high_penalty = self.penalty["low"], self.penalty["high"]
        penalty_function = getattr(mfs, self.penalty["func"])([low_penalty, high_penalty])

        high_b_val = b_val.get("high")
        low_b_val = b_val.get("low")

        if p_val <= 0:
            return 0.

        if high_b_val is not None and low_b_val is not None:
            penalty_for_high = penalty_function(abs(p_val - high_b_val))
            penalty_for_low = penalty_function(abs(p_val - low_b_val))
            return max((penalty_for_high, penalty_for_low))

        if low_b_val is not None and low_b_val > 0:
            return penalty_function(abs(p_val - low_b_val))

        if high_b_val is not None and high_b_val > 0:
            return penalty_function(abs(p_val - high_b_val))

        return 0.

    def get_relative_penalty_for_number(self, b_val, p_val):
        if p_val is None:
            return 0.

        if p_val <= 0 or b_val == self.penalty.get("default"):
            return 0.

        low, high = self.penalty["low"], self.penalty["high"]
        penalty_function = getattr(mfs, self.penalty["func"])([low, high])

        val = b_val / p_val if b_val > p_val else p_val / b_val
        return penalty_function(val)

    def get_relative_penalty_for_range(self, b_val, p_val):
        if p_val is None:
            return 0.

        if p_val <= 0:
            return 0.

        low, high = self.penalty["low"], self.penalty["high"]
        penalty_function = getattr(mfs, self.penalty["func"])([low, high])

        high_b_val = b_val.get("high")
        low_b_val = b_val.get("low")

        if high_b_val is not None and low_b_val is not None:
            penalty_for_high = penalty_function(high_b_val / p_val)
            penalty_for_low = penalty_function(p_val / low_b_val) if low_b_val > 0 else 0.
            return max((penalty_for_high, penalty_for_low))

        elif low_b_val is not None and low_b_val > 0:
            return penalty_function(p_val / low_b_val)

        elif high_b_val is not None and high_b_val > 0:
            return penalty_function(high_b_val / p_val)

        else:
            return 0.

    def get_match(self):
        if self._match is not None:
            return self._match
        raise NotImplementedError()

    def get_details(self):
        return {"first": self.first_field, "second": self.second_field, "match": self.get_match()}


class TriggerCriteria(Criteria):
    mem_func = mfs.SingletonMF
    influence = 1.

    def set_mem_func(self):
        if self.mem_func is not None:
            return
        self.mem_func = mfs.SingletonMF

    def get_match(self):
        if self._match is None:
            p_val = getattr(self.first_obj, self.first_field)
            b_val = getattr(self.second_obj, self.second_field)
            self._match = 1 if (p_val == b_val) else -1
        return self._match


class InCriteria(Criteria):
    match_type = "exact"
    mem_func = ""
    influence = 1.

    def get_penalty(self):
        if not self.penalty:
            return 1.

        low, high = self.penalty["low"], self.penalty["high"]
        penalty_function = getattr(mfs, self.penalty["func"])([low, high])
        container = getattr(self.second_obj, self.second_field)

        try:
            val = len(container)
        except TypeError:
            val = container.count()

        return penalty_function(val)

    def get_value(self):
        try:
            value = getattr(self.first_obj, self.first_field)
            container = getattr(self.second_obj, self.second_field)
            if isinstance(container, Manager):
                container = container.all()
            self._match = 1 if value in container else -1

            return (int(value in container) *
                    self.influence *
                    self.get_penalty())
        except Exception:
            logging.exception("Bad match value")
            return 0.


class IntersectionCriteria(Criteria):
    match_type = "exact"
    mem_func = ""
    influence = 1.

    def get_value(self):
        self._match = -1

        try:
            p_container = getattr(self.first_obj, self.first_field)
            b_container = getattr(self.second_obj, self.second_field)

            if isinstance(p_container, Manager):
                p_container = p_container.all()
            if isinstance(b_container, Manager):
                b_container = b_container.all()

            p_len = len(p_container)
            b_len = len(b_container)

            if not (p_len and b_len):
                return 0

            intersection = set(p_container).intersection(set(b_container))
            if not intersection:
                return 0

            i_len = len(intersection)
            if i_len == p_len == b_len:
                self._match = 1
                return 1

            return i_len / b_len
        except Exception:
            logging.exception("Bad match value")
            return 0.


class GeoCriteria(Criteria):
    first_field = "location"
    second_field = "area"
    match_type = "exact"
    mem_func = ""
    influence = 1.

    def get_value(self):
        value = getattr(self.first_obj, self.first_field)
        container = getattr(self.second_obj, self.second_field)

        try:
            value_in_container = bool(value and container and container.covers(value))
        except Exception:
            value_in_container = False

        self._match = 1 if value_in_container else -1

        return int(value_in_container) * self.influence * self.get_penalty()


class CityCriteria(InCriteria):
    first_field = "city"
    second_field = "cities"
    match_type = "exact"
    membership_func = "rectangle"
    influence = 1.


class LowToHighRangeCriteria(Criteria):
    match_type = "fuzzy"
    fuzziness = (0.1, "relative")
    influence = 1.

    def set_mem_func(self):
        if self.mem_func is not None:
            return

        p_val = getattr(self.first_obj, self.first_field)
        b_val = getattr(self.second_obj, self.second_field)

        # Only HIGH
        if {"low", "high"}.difference(b_val.keys()) == {"low"}:
            high = b_val["high"]
            highest = high + get_shift_for_value(high, self.fuzziness)

            self._match = 1 if p_val <= high else -1

            if self.hard_edge in ("right", "both"):
                high = highest

            self.mem_func = mfs.ZMF((high, highest))

        # Only LOW
        elif {"low", "high"}.difference(b_val.keys()) == {"high"}:
            low = b_val["low"]
            lowest = low - get_shift_for_value(low, self.fuzziness)

            self._match = 1 if p_val >= low else -1

            if self.hard_edge in ("left", "both"):
                low = lowest

            self.mem_func = mfs.SMF((lowest, low))

        # Both margins
        else:
            high = b_val["high"]
            highest = high + get_shift_for_value(high, self.fuzziness)
            low = b_val["low"]
            lowest = low - get_shift_for_value(low, self.fuzziness)

            if self.hard_edge in ("left", "both"):
                low = lowest

            if self.hard_edge in ("right", "both"):
                high = highest

            try:
                self._match = 1 if high >= p_val >= low else -1
            except TypeError:
                self._match = -1

            self.mem_func = mfs.TrapezoidMF((lowest, low, high, highest))


class FromORUptoRangeCriteria(Criteria):
    match_type = "fuzzy"
    fuzziness = (0.1, "relative")
    influence = 1.
    direction = "from"

    def __init__(self, *args, **kwargs):
        self.direction = kwargs.get("direction", self.direction)
        super().__init__(*args, **kwargs)

    def set_mem_func(self):
        if self.mem_func is not None:
            return

        p_val = getattr(self.first_obj, self.first_field)
        b_val = getattr(self.second_obj, self.second_field)

        if self.direction == "from":
            self._match = 1 if p_val >= b_val else -1

            low = b_val
            lowest = low - get_shift_for_value(low, self.fuzziness)
            self.mem_func = mfs.SMF((lowest, low))

        else:
            self._match = 1 if p_val <= b_val else -1

            high = b_val
            highest = high + get_shift_for_value(high, self.fuzziness)
            self.mem_func = mfs.ZMF((high, highest))


class AlmostNumberCriteria(Criteria):
    match_type = "fuzzy"
    fuzziness = (0.1, "relative")
    influence = 1.
    direction = "from"

    def __init__(self, *args, **kwargs):
        self.direction = kwargs.get("direction", self.direction)
        super().__init__(*args, **kwargs)

    def set_mem_func(self):
        p_val = getattr(self.first_obj, self.first_field)
        b_val = getattr(self.second_obj, self.second_field)

        self._match = 1 if p_val == b_val else -1

        if self.mem_func is not None:
            return

        self.mem_func = mfs.TriangleMF((b_val - get_shift_for_value(b_val, self.fuzziness),
                                        b_val,
                                        b_val + get_shift_for_value(b_val, self.fuzziness)))


class OrConditionSuperCriteria(AbstractCriteria):
    criteria = None

    def __init__(self, first_obj, second_obj, influence=1., **kwargs):
        condition = kwargs["condition"]
        true_criteria = kwargs["true_criteria"]
        false_criteria = kwargs["false_criteria"]

        self.influence = influence
        self.criteria = (true_criteria
                         if self.check_condition(condition, first_obj, second_obj) else
                         false_criteria)

    def get_value(self):
        return self.criteria.get_value()

    def check_condition(self, condition, first, second):
        if len(condition) == 1:
            return self.check_single_condition(condition, first, second)

        acc = None
        i = 0

        while i + 3 <= len(condition):
            if i == 0:
                condition_triplet = condition[i:i + 3]
            else:
                condition_triplet = acc, *condition[i + 1:i + 3]

            acc = self.check_triplet_condition(condition_triplet, first, second)
            i += 2

        return acc

    def check_triplet_condition(self, condition, first, second):
        first = self.check_single_condition(condition[0], first, second)
        second = self.check_single_condition(condition[2], first, second)
        return first or second if condition[1] == "or" else first and second

    @staticmethod
    def check_single_condition(condition, first, second):
        if isinstance(condition, bool):
            return condition
        key, val = tuple(condition.items())[0]
        key_lst = key.split("__")
        target = second if key_lst[0] == "second" else first
        return getattr(target, key_lst[1]) == val

    def get_details(self):
        return self.criteria.get_details()


class SuperCriteria(AbstractCriteria):
    def get_details(self):
        return [c.get_details() for c in self.criteria]


class OrSuperCriteria(SuperCriteria):
    criteria = []
    influence = 1.

    def __init__(self, *criteria, influence=1):
        self.criteria = criteria
        self.influence = influence

    def get_value(self):
        # T-Norm
        return max(c.get_value() for c in self.criteria)


class AndSuperCriteria(SuperCriteria):
    criteria = []
    influence = 1.

    def __init__(self, *criteria):
        self.criteria = criteria

    def get_value(self):
        # T-Co-norm or S-Norm
        return min(c.get_value() for c in self.criteria)
