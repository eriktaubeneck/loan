from dataclasses import dataclass, field
from typing import Dict
from pprint import pprint
from copy import copy
from itertools import chain

from numpy_financial import pmt


CONFORMING_MAX = 776_250
INTEREST_DEDUCTION_MAX_BALANCE = 750_000


@dataclass(order=True)
class LoanMonth:
    loan: "Loan" = field(repr=False, compare=False)
    month_number: int = field(compare=False)
    remaining_months: int = field(init=False, compare=False)
    starting_balance: int = field(compare=False)
    ending_balance: int = field(init=False, compare=False)
    payment: int = field(init=False, compare=False)
    principle: int = field(init=False, compare=False)
    interest: int = field(init=False, compare=False)
    deductible_interest: int = field(init=False, compare=False)
    _prev_cumulative_principle: int = field(repr=False, compare=False)
    _prev_cumulative_interest: int = field(repr=False, compare=False)
    cumulative_principle: int = field(init=False, compare=False)
    cumulative_interest: int = field(init=False, compare=False)
    cumulative_cost: int = field(init=False, compare=True)

    def __post_init__(self):
        self.remaining_months = self.loan.years * 12 - self.month_number
        self.payment = -pmt(
            self.loan.interest_rate/12,
            self.remaining_months,
            self.starting_balance
        )
        self.interest = self.starting_balance * (self.loan.interest_rate/12)
        self.deductible_interest = min(1, INTEREST_DEDUCTION_MAX_BALANCE/self.starting_balance) * self.interest
        self.principle = self.payment - self.interest
        self.ending_balance = self.starting_balance - self.principle
        self.cumulative_principle = self._prev_cumulative_principle + self.principle
        self.cumulative_interest = self._prev_cumulative_interest + self.interest
        self.cumulative_cost = self.loan.upfront_cost + self.cumulative_interest + self.cumulative_principle

    def __str__(self):
        return super().__str__().replace(', ', ',\n     ')

    @classmethod
    def first_month(cls, loan: "Loan"):
        m = cls(
            loan=loan,
            month_number=0,
            starting_balance=loan.price - loan.down,
            _prev_cumulative_principle=0,
            _prev_cumulative_interest=0,
        )
        m.principle = m.principle + m.loan.down
        return m

    @classmethod
    def build_from_month(cls, loan: "Loan", previous_month: "LoanMonth"):
        return cls(
            loan=loan,
            month_number=previous_month.month_number+1,
            starting_balance=previous_month.ending_balance,
            _prev_cumulative_principle=previous_month.cumulative_principle,
            _prev_cumulative_interest=previous_month.cumulative_interest,
        )


@dataclass
class Loan:
    price: int
    down_rate: float
    years: int
    interest_rate: float
    points: float
    name: str = None
    down: int = field(init=False)
    closing_costs: int = field(init=False)
    loan_amount: int = field(init=False)
    points_fee: int = field(init=False)
    total_interest: int = field(init=False)
    total_cost: int = field(init=False)
    payment: int = field(init=False)
    conforming: bool = field(init=False)

    def __post_init__(self):
        self.down = self.price * self.down_rate
        self.closing_costs = self.down + self.price * 0.03
        self.loan_amount = self.price - self.down
        self.points_fee = self.loan_amount * self.points * 0.01
        self.conforming = self.loan_amount <= CONFORMING_MAX

        self.months = [
            LoanMonth.first_month(self)
        ]
        for i in range(1, self.years * 12):
            self.months.append(LoanMonth.build_from_month(
                loan=self,
                previous_month=self.months[i-1],
            ))
        self.total_interest = self.months[-1].cumulative_interest
        self.total_cost = self.months[-1].cumulative_cost
        self.payment = self.months[0].payment

    def __str__(self):
        return super().__str__().replace(', ', ',\n     ')

    @classmethod
    def min_conforming(
            cls,
            price,
            years,
            interest_rate,
            points,
            name=None,
    ):
        down_rate = 1 - CONFORMING_MAX / price
        return cls(price, down_rate, years, interest_rate, points, name)

    @classmethod
    def buy_points(cls, loan, points):
        return cls(
            loan.price,
            loan.down_rate,
            loan.years,
            loan.interest_rate - 0.00125 * points,
            loan.points + points,
            f'{loan.name} with {points} point(s)' if loan.name else None,
        )

    @classmethod
    def no_points(cls, loan):
        return cls.buy_points(loan, -loan.points)

    @property
    def upfront_cost(self):
        return self.down + self.points_fee

    def compare_points(self, points):
        other = self.__class__.buy_points(self, points)
        return other.compare(self)

    def compare(self, other: "Loan"):
        crossover = self.crossover(other)
        upfront_cost_diff = self.upfront_cost - other.upfront_cost
        total_cost_diff = self.total_cost - other.total_cost
        reference_rate_of_return = (-total_cost_diff / upfront_cost_diff) ** (1/self.years)

        principle_diff = (self.price - self.down) - (other.price - other.down)

        return (
            f"{self.interest_rate} vs {other.interest_rate}: \n"
            f"  total cost diff: ${total_cost_diff:0,.0f}; "
            f"${self.total_cost:0,.0f} vs ${other.total_cost:0,.0f}\n"
            f"  upfront cost diff ${upfront_cost_diff:0,.0f}; "
            f"${self.upfront_cost:0,.0f} vs ${other.upfront_cost:0,.0f}\n"
            f"  reference rate of return {reference_rate_of_return:0,.4f}\n"
            f"  principle diff {principle_diff:0,.0f}\n"
            f"  crossover in month {crossover} ({crossover/12:5.2f} years)\n"
        ).replace("$-", "-$")

    def crossover(self, other: "Loan"):
        months = self.years * 12
        min_loan = min(self.months[0], other.months[0]).loan
        for month, other_month in zip(self.months, other.months):
            next_min_loan = min(month, other_month).loan
            if next_min_loan != min_loan:
                return i
        return months


def escalation(start_loan, stop_price, step):
    for price in chain(range(start_loan.price, stop_price, step), [stop_price]):
        loan = copy(start_loan)
        loan.price = price
        loan.__post_init__()
        yield loan


if __name__ == "__main__":
    years = 30
    start_price = 1_360_000
    stop_price = 1_460_000
    step = 25_000

    start_loan = Loan(start_price, 0.2, years, 0.03125, 0.0)
    for loan in escalation(start_loan, stop_price, step):
        print(loan)

    # # compare buying points
    # loan = Loan(1_200_000, 0.2, years, 0.02625, 0.75)
    # baseline = Loan.no_points(loan)

    # print(baseline)
    # print(baseline.compare_points(-0.75))
    # print(baseline.compare_points(0.75))
    # print(baseline.compare_points(1.5))
    # print(baseline.compare_points(2))
    # print(baseline.compare_points(2.5))


    # # compare min conforming vs 20% down
    # price = 1_050_000

    # loan1 = Loan.min_conforming(price, years, 0.02625, 0.75)
    # loan2 = Loan(price, 0.2, years, 0.02875, 0.75)
    # print(loan1)
    # print(loan2)
    # print(loan2.compare(loan1))

    # offer = 1_200_000
    # total_loan = offer * 0.9
    # value_goal_post_remodel = total_loan / 0.8
    # loan = Loan(value_goal_post_remodel, 0.2, years, 0.03, 0.0)
    # print(loan)
    # # for i in range(30):
    #     print(i+1, sum(m.deductible_interest for m in loan.months[i*12:(i+1)*12]))
