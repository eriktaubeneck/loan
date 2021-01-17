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
        self.cumulative_cost = self.loan.points_fee + self.cumulative_interest

    @classmethod
    def first_month(cls, loan: "Loan"):
        return cls(
            loan=loan,
            month_number=1,
            starting_balance=loan.price - loan.down,
            _prev_cumulative_principle=0,
            _prev_cumulative_interest=0,
        )

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
        self.total_cost = self.total_interest + self.points_fee
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

    def compare_points(self, points):
        other = self.__class__.buy_points(self, points)
        return self.compare(other)

    def compare(self, other: "Loan"):
        crossover = self.crossover(other)
        upfront_cost_diff = (self.down + self.points_fee) - (other.down + other.points_fee)
        total_cost_diff = self.total_cost - other.total_cost
        reference_rate_of_return = (-total_cost_diff / upfront_cost_diff) ** (1/self.years)

        principle_diff = (self.price - self.down) - (other.price - other.down)

        return (
            f"{self.interest_rate} vs {other.interest_rate}: \n"
            f"  total cost diff {total_cost_diff}\n"
            f"  upfront cost diff {upfront_cost_diff}\n"
            f"  reference rate of return {reference_rate_of_return}\n"
            f"  principle diff {principle_diff}\n"
            f"  crossover in month {crossover} ({crossover/12:5.2f} years)\n"
        )

    def crossover(self, other: "Loan"):
        months = self.years * 12
        min_loan = min(self.months[1], other.months[1]).loan
        for i in range(2, months+1):
            next_min_loan = min(self.months[i], other.months[i]).loan
            if next_min_loan != min_loan:
                return i
        return months


price = 985000
down = 0.2
years = 30


# loans = [
#     # Loan(1_000_000, down, years, 0.02825, 0.75),
#     # Loan(1_000_000, down+0.05, years, 0.02625, 0.75),
#     # Loan(1_000_000, down+0.1, years, 0.02625, 0.75),
#     Loan(1_050_000, down, years, 0.02825, 0.75),
#     Loan(1_050_000, down+0.05, years, 0.02625, 0.75),
#     Loan.min_conforming(1_050_000, years, 0.02625, 0.75),
#     Loan(1_100_000, down, years, 0.02825, 0.75),
#     Loan(1_100_000, down+0.05, years, 0.02625, 0.75),
#     # Loan.min_conforming(1_100_000, years, 0.02625, 0.75),
#     Loan(1_150_000, down, years, 0.02825, 0.75),
#     Loan(1_150_000, down+0.05, years, 0.02625, 0.75),
#     # Loan.min_conforming(1_150_000, years, 0.02625, 0.75),
# ]

# for loan in loans:
#     print(loan)
#     print('')

# print('\n compare points')
# l = loans[-2]

# print(Loan.buy_points(l, 1))
# print(l.compare_points(1))

loan = Loan.min_conforming(1_020_000, years, 0.2625, 0.75)
baseline = Loan.no_points(loan)
print(baseline.compare_points(0.75))
print(baseline.compare_points(1.5))
print(baseline.compare_points(2))
print(baseline.compare_points(2.5))
