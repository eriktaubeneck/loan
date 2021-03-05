# loan
simple mortgage loan calculator

Create a loan:
```
amount = 1_200_000
down_rate = 0.2
years = 30
interest_rate = 0.02625
points = 0.75

loan = Loan(amount, down_rate, years, interest_rate, points)
```

Print to see loan facts
```
print(loan)
```

Compare points
```
baseline = Loan.no_points(loan)

print(baseline)
print(baseline.compare_points(-0.75))
print(baseline.compare_points(0.75))
print(baseline.compare_points(1.5))
print(baseline.compare_points(2))
print(baseline.compare_points(2.5))
```
