# Travel Planning — Algorithm Comparison

**Course:** CPE231 — Algorithms  
**Language:** Python (Jupyter Notebook)  
**Libraries:** NumPy, Matplotlib  
**Source:** [GitHub — FinalCPE231_Algorithm](https://github.com/cottonlnwza/FinalCPE231_Algorithm)

---

## Overview

Mini project comparing 5 algorithm strategies on a travel planning problem modeled as a **0/1 Knapsack variant**:

- **Constraint:** 14-day vacation budget
- **Goal 1:** Visit as many cities as possible
- **Goal 2:** Minimize total cost
- **Dataset:** 10 cities, each with a fixed number of days and cost

---

## Algorithms Implemented

| Algorithm | Approach | Time Complexity |
|---|---|---|
| Brute Force | Exhaustive search over all 2¹⁰ subsets | O(2ⁿ) |
| Dynamic Programming | 0/1 Knapsack DP table with backtracking | O(n × W) |
| Greedy | Sort by days/cost/ratio, greedily select | O(n log n) |
| Genetic Algorithm | Tournament selection, single-point crossover, bit-flip mutation | O(gen × pop × n) |
| PSO | Binary PSO with sigmoid-based position update | O(iter × particles × n) |

---

## Results

All 5 algorithms converged to the same optimal solution:

| Algorithm | Cities | Cost | Time |
|---|---|---|---|
| Brute Force | 6 | $334 | 0.000675s |
| Dynamic Programming | 6 | $334 | 0.000068s |
| Greedy | 6 | $334 | 0.000008s |
| Genetic Algorithm | 6 | $334 | 0.111949s |
| PSO | 6 | $334 | 0.053005s |

**Optimal plan:** City A, B, D, E, F, I — 14 days, $334

---

## Key Takeaways

- DP is the best balance of correctness and speed for this problem class
- Greedy is fastest but only guaranteed optimal when the problem structure allows it
- GA and PSO are overkill for n=10 but scale better to large, constrained combinatorial problems
- Brute Force guarantees the optimal but is impractical beyond n ≈ 20

---

→ [Back to Projects](../../projects.md)
