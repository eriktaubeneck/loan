from dataclasses import dataclass, field
from typing import Dict
from pprint import pprint

from numpy_financial import pmt


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
        self.cumulative_cost = self.loan.fees + self.cumulative_interest

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
    down: int
    years: int
    interest_rate: float
    fees: int
    name: str = None
    total_interest: int = field(init=False)
    total_cost: int = field(init=False)

    def __post_init__(self):
        self.months = {
            1: LoanMonth.first_month(self)
        }
        for i in range(2, self.years * 12 + 1):
            self.months[i] = LoanMonth.build_from_month(
                loan=self,
                previous_month=self.months[i-1],
            )
        self.total_interest = self.months[self.years * 12].cumulative_interest
        self.total_cost = self.total_interest + self.fees

    def compare(self, other: "Loan"):
        crossover = self.crossover(other)
        upfront_cost_diff = (self.down + self.fees) - (other.down + other.fees)
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
down = int(price*0.2)
years = 30


# baseline = Loan(price, down, years, 0.03, 10099, name='baseline')
# low_rate = Loan(price, down, years, 0.02625, 21437, name='low_rate')

# print(f'{low_rate.compare(baseline)}')

# remodel = low_rate.fees - baseline.fees
# print(f'putting ${remodel} against remodel')
# baseline_finance_remodel= Loan(price+remodel, (price+remodel)*0.2, years, 0.03, 10099, name='baseline_finance_remodel')

# print(f'{low_rate.compare(baseline_finance_remodel)}')

loans = [
    Loan(price, down, years, 0.02625, 21437),
    Loan(price, down, years, 0.0275, 16925),
    Loan(price, down, years, 0.02875, 13325),
    Loan(price, down, years, 0.03, 10099),
    Loan(price, down, years, 0.03125, 7978),
    Loan(price, down, years, 0.0325, 7718),
    Loan(price, down, years, 0.03375, -1555),
    Loan(price, down, years, 0.035, -2093),
    Loan(price, down, years, 0.03625, -2928),
    Loan(price, down, years, 0.0375, -3763),
    Loan(price, down, years, 0.03875, -4550),
    Loan(price, down, years, 0.04, -5290),
    Loan(price, down, years, 0.04125, -6067),
    Loan(price, down, years, 0.0425, -6854),
]
baseline = loans[6]

for loan in loans:
    if loan != baseline:
        print(loan.compare(baseline))

# print(loans[0].compare(loans[1]))

# l0, l1 = loans[0], loans[7]
# print(l1.compare(l0))

# print(f"rate0: {l0.interest_rate}, rate1: {l1.interest_rate}")
# for i in range(1, 100, 10):
#     print(f"month: {i}, cost0: {l0.months[i].cumulative_cost}, cost1: {l1.months[i].cumulative_cost}")

# for loan, loan2 in zip(loans, loans[1:]):
#     print(loan2.compare(loan))
