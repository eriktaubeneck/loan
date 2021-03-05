from dataclasses import dataclass, field
from typing import Dict
from pprint import pprint

from numpy_financial import pmt


CONFORMING_MAX = 776_250


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
    _prev_cumulative_principle: int = field(repr=False, compare=False)
    _prev_cumulative_interest: int = field(repr=False, compare=False)
    cumulative_principle: int = field(init=False, compare=False)
    cumulative_interest: int = field(init=False, compare=False)
    cumulative_cost: int = field(init=False, compare=True)

    def __post_init__(self):
        self.remaining_months = self.loan.years * 12 - self.month_number + 1
        self.payment = -pmt(
            self.loan.interest_rate/12,
            self.remaining_months,
            self.starting_balance
        )
        self.interest = self.starting_balance * (self.loan.interest_rate/12)
        self.principle = self.payment - self.interest
        self.ending_balance = self.starting_balance - self.principle
        self.cumulative_principle = self._prev_cumulative_principle + self.principle
        self.cumulative_interest = self._prev_cumulative_interest + self.interest
        self.cumulative_cost = self.loan.upfront_cost + self.cumulative_interest + self.cumulative_principle

    @classmethod
    def first_month(cls, loan: "Loan"):
        m = cls(
            loan=loan,
            month_number=1,
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
    loan_amount: int = field(init=False)
    points_fee: int = field(init=False)
    total_interest: int = field(init=False)
    total_cost: int = field(init=False)
    payment: int = field(init=False)
    conforming: bool = field(init=False)

    def __post_init__(self):
        self.down = self.price * self.down_rate
        self.loan_amount = self.price - self.down
        self.points_fee = self.loan_amount * self.points * 0.01
        self.conforming = self.loan_amount <= CONFORMING_MAX

        self.months = {
            1: LoanMonth.first_month(self)
        }
        for i in range(2, self.years * 12 + 1):
            self.months[i] = LoanMonth.build_from_month(
                loan=self,
                previous_month=self.months[i-1],
            )
        self.total_interest = self.months[self.years * 12].cumulative_interest
        self.total_cost = self.months[self.years * 12].cumulative_cost
        self.payment = self.months[1].payment

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
        min_loan = min(self.months[1], other.months[1]).loan
        for i in range(2, months+1):
            next_min_loan = min(self.months[i], other.months[i]).loan
            if next_min_loan != min_loan:
                return i
        return months



if __name__ == "__main__":
    years = 30

    # compare buying points
    loan = Loan(1_200_000, 0.2, years, 0.02625, 0.75)
    baseline = Loan.no_points(loan)

    print(baseline)
    print(baseline.compare_points(-0.75))
    print(baseline.compare_points(0.75))
    print(baseline.compare_points(1.5))
    print(baseline.compare_points(2))
    print(baseline.compare_points(2.5))


    # compare min conforming vs 20% down
    price = 1_050_000

    loan1 = Loan.min_conforming(price, years, 0.02625, 0.75)
    loan2 = Loan(price, 0.2, years, 0.02875, 0.75)
    print(loan1)
    print(loan2)
    print(loan2.compare(loan1))
