# Descriptive Statistics and Sample Construction

*Generated from the PLFS microdata by `scripts/sample_flow.py` and `paper/sample_doc.py`; all counts are unweighted person records, all means are weighted with the PLFS annual weights.*

## Sample construction

The analysis uses the first-visit person files of the seven annual PLFS rounds from July 2017–June 2018 to July 2023–June 2024 (2,951,994 person records), merged with the first-visit household files. Table S1 reports the number of observations retained after each filtering step. Temporary visitors (person serial number 81 or higher, recorded from 2020-21) are dropped. Restricting to the working-age population aged 15–64 keeps 70% of records; of these, 49% are employed in the current weekly status (CWS). The wage analysis is limited to wage employees — regular salaried workers and casual labourers — because the self-employed report earnings that include returns to capital; they are analysed separately as a robustness check. Wage employees with zero or missing earnings or hours are dropped, and hourly wages are trimmed at the 0.5th and 99.5th percentiles within each round. Workers whose three-digit occupation code cannot be matched to a DTI score (mainly the armed forces and a few occupation groups without NCO descriptions) are excluded, as are 32 observations with missing covariates in the preferred specification. The final analytical sample comprises **466,095 wage employees** in 233 occupation groups (111 NCO-2004 groups in 2017-18 to 2020-21 and 122 NCO-2015 groups in 2021-22 to 2023-24), representing 160–196 million workers per year.

## Table S1. Sample construction: observations retained after each filter

Panel A. All rounds pooled

| Filter | Observations kept | Dropped at this step | Kept (% of previous step) | Kept (% of all records) |
|---|---|---|---|---|
| 1. All person records | 2,951,994 | — | — | 100.0% |
| 2. Usual members only | 2,949,407 | 2,587 | 99.9% | 99.9% |
| 3. Aged 15–64 | 2,065,295 | 884,112 | 70.0% | 70.0% |
| 4. Employed (CWS) | 1,002,899 | 1,062,396 | 48.6% | 34.0% |
| 5. Regular or casual wage employee | 473,521 | 529,378 | 47.2% | 16.0% |
| 6. Valid earnings and hours | 472,518 | 1,003 | 99.8% | 16.0% |
| 7. Wage outliers trimmed | 468,538 | 3,980 | 99.2% | 15.9% |
| 8. Occupation matched to DTI | 466,127 | 2,411 | 99.5% | 15.8% |
| 9. Positive weight | 466,127 | 0 | 100.0% | 15.8% |
| 10. Complete covariates (M4) | 466,095 | 32 | 100.0% | 15.8% |

Panel B. Observations kept, by PLFS round

| Step | 2017-18 | 2018-19 | 2019-20 | 2020-21 | 2021-22 | 2022-23 | 2023-24 |
|---|---|---|---|---|---|---|---|
| 1 | 433,339 | 420,757 | 418,297 | 413,405 | 428,525 | 419,512 | 418,159 |
| 2 | 433,339 | 420,757 | 418,297 | 410,818 | 428,525 | 419,512 | 418,159 |
| 3 | 304,831 | 296,350 | 293,457 | 290,882 | 298,313 | 291,666 | 289,796 |
| 4 | 135,215 | 133,466 | 132,632 | 138,706 | 147,604 | 155,018 | 160,258 |
| 5 | 67,642 | 66,711 | 63,083 | 64,847 | 69,102 | 70,493 | 71,643 |
| 6 | 67,586 | 66,641 | 62,292 | 64,837 | 69,083 | 70,471 | 71,608 |
| 7 | 67,055 | 66,062 | 61,739 | 64,257 | 68,495 | 69,891 | 71,039 |
| 8 | 66,310 | 65,908 | 61,037 | 64,096 | 68,231 | 69,688 | 70,857 |
| 9 | 66,310 | 65,908 | 61,037 | 64,096 | 68,231 | 69,688 | 70,857 |
| 10 | 66,310 | 65,876 | 61,037 | 64,096 | 68,231 | 69,688 | 70,857 |

Notes: unweighted person records. Step 1: all records in the first-visit person files. Step 5: regular salaried or casual labour in the CWS. Step 6: positive earnings and hours, so an hourly wage can be computed. Step 9: positive survey weight. Step 2 removes temporary visitors (serial number ≥ 81), recorded from the 2020-21 round. Step 4 uses the current weekly status (principal activity in the reference week). Step 7: the trimming percentiles are computed within each round. Step 8: rounds up to 2020-21 code occupation in NCO-2004 and are linked to the NCO-2015-based DTI through the NCO-2015 → NCO-2004 concordance; unmatched codes are mainly armed forces (NCO-2004 010/099) and a few groups without Vol II descriptions. Step 10 equals the number of observations in the preferred regression (M4).

## Table S2. Descriptive statistics of the analytical sample (pooled 2017-18 to 2023-24)

| Variable | Mean / share | SD | Median | Min – max | N |
|---|---|---|---|---|---|
| Log hourly wage (outcome; nominal Rs.) | 3.87 | 0.67 | 3.91 | 1.64 – 6.18 | 466,095 |
| Hourly wage, Rs. (nominal) | 61.96 | 56.82 | 50.00 | 5.13 – 481.14 | 466,095 |
| Monthly earnings, Rs. (nominal) | 12,661 | 11,783 | 10,000 | 87 – 150,000 | 466,095 |
| Hours worked per week | 47.57 | 13.39 | 48.00 | 1.00 – 140.00 | 466,095 |
| DTI mean dimension score (0-4) | 0.21 | 0.37 | 0.07 | 0.00 – 1.98 | 466,095 |
| DTI (z-score across occupations) | -0.34 | 0.56 | -0.55 | -0.66 – 2.16 | 466,095 |
| D1 basic digital operation (0-4) | 0.30 | 0.43 | 0.13 | 0.00 – 1.93 | 466,095 |
| D2 information processing (0-4) | 0.35 | 0.60 | 0.09 | 0.00 – 3.29 | 466,095 |
| D3 communication (0-4) | 0.08 | 0.21 | 0.00 | 0.00 – 1.17 | 466,095 |
| D4 specialised tools (0-4) | 0.22 | 0.45 | 0.07 | 0.00 – 2.85 | 466,095 |
| D5 problem solving / content (0-4) | 0.12 | 0.43 | 0.00 | 0.00 – 2.86 | 466,095 |
| Age (years) | 36.77 | 11.20 | 36.00 | 15.00 – 64.00 | 466,095 |
| Female | 23.6% |  |  |  | 466,095 |
| Currently married | 74.1% |  |  |  | 466,095 |
| Rural | 62.8% |  |  |  | 466,095 |
| Education: up to primary | 39.5% |  |  |  | 466,095 |
| Education: middle / secondary | 41.0% |  |  |  | 466,095 |
| Education: tertiary (graduate+) | 19.5% |  |  |  | 466,095 |
| Social group: Scheduled Tribe | 10.3% |  |  |  | 466,095 |
| Social group: Scheduled Caste | 25.1% |  |  |  | 466,095 |
| Social group: Other Backward Class | 40.2% |  |  |  | 466,095 |
| Social group: Others | 24.3% |  |  |  | 466,095 |
| Regular salaried | 51.1% |  |  |  | 466,095 |
| Casual labour | 48.9% |  |  |  | 466,095 |
| Social-security coverage (regular workers only) | 42.7% |  |  |  | 284,397 |
| Household size | 4.54 | 1.97 | 4.00 | 1.00 – 33.00 | 466,095 |
| Observed in an NCO-2015 round (2021-24) | 46.6% |  |  |  | 466,095 |

Notes: means, shares and SDs weighted with PLFS annual weights; median and range unweighted. Wages and earnings are nominal rupees (no CPI deflator applied; year-quarter fixed effects absorb common inflation in the regressions). Hourly wage = monthly earnings / (weekly hours × 4.33) for regular workers and weekly earnings / weekly hours for casual workers. DTI = Digital Task Intensity of the worker's 3-digit occupation from the LLM coding of NCO-2015 texts (Qwen2.5-14B, strict rubric); dimensions on a 0–4 scale; the regressor is DTI standardised across workers (mean 0, SD 1). Social-security coverage is defined for regular salaried workers only.

## Table S3. Key characteristics by PLFS round

| Round | Occupation code | N | Weighted (million) | Occ. groups | Hourly wage (Rs.) | Log wage | Hours/week | DTI (0–4) | Female | Rural | Tertiary | Casual | Soc. security (regular) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017-18 | NCO-2004 | 66,310 | 160.3 | 111 | 46.4 | 3.59 | 51.5 | 0.21 | 22.0% | 62.3% | 18.1% | 49.8% | 40.0% |
| 2018-19 | NCO-2004 | 65,876 | 165.4 | 111 | 51.2 | 3.70 | 49.4 | 0.21 | 22.1% | 61.1% | 19.1% | 48.2% | 40.4% |
| 2019-20 | NCO-2004 | 61,037 | 161.8 | 111 | 56.2 | 3.76 | 48.3 | 0.21 | 25.3% | 61.9% | 18.9% | 49.8% | 41.1% |
| 2020-21 | NCO-2004 | 64,096 | 166.9 | 111 | 59.1 | 3.83 | 47.3 | 0.21 | 24.6% | 63.8% | 18.7% | 51.2% | 42.7% |
| 2021-22 | NCO-2015 | 68,231 | 179.4 | 122 | 66.6 | 3.97 | 46.2 | 0.21 | 22.8% | 63.4% | 19.8% | 48.8% | 43.7% |
| 2022-23 | NCO-2015 | 69,688 | 194.6 | 122 | 71.4 | 4.04 | 45.6 | 0.21 | 23.3% | 65.0% | 19.4% | 49.4% | 44.4% |
| 2023-24 | NCO-2015 | 70,857 | 196.2 | 122 | 77.5 | 4.11 | 45.7 | 0.22 | 24.6% | 62.1% | 21.8% | 45.6% | 45.5% |

## Table S4. Key characteristics by group

| By | Group | N | Weighted share | Hourly wage (Rs.) | DTI (0–4) | Female | Rural | Tertiary | Soc. security (regular) |
|---|---|---|---|---|---|---|---|---|---|
| Employment type | Casual labour | 181,698 | 48.9% | 42.4 | 0.03 | 24.1% | 84.6% | 1.8% | — |
| Employment type | Regular salaried | 284,397 | 51.1% | 80.6 | 0.39 | 23.1% | 42.0% | 36.4% | 42.7% |
| Sex | Men | 357,949 | 76.4% | 65.2 | 0.22 | 0.0% | 62.4% | 19.2% | 43.2% |
| Sex | Women | 108,146 | 23.6% | 51.5 | 0.18 | 100.0% | 64.3% | 20.3% | 41.0% |
| Sector | Urban | 234,898 | 37.2% | 82.3 | 0.37 | 22.7% | 0.0% | 33.4% | 46.6% |
| Sector | Rural | 231,197 | 62.8% | 49.9 | 0.12 | 24.1% | 100.0% | 11.2% | 37.3% |
| Education | Middle / secondary | 219,383 | 41.0% | 53.7 | 0.17 | 15.3% | 62.6% | 0.0% | 32.9% |
| Education | Tertiary | 106,531 | 19.5% | 122.9 | 0.63 | 24.5% | 36.3% | 100.0% | 68.8% |
| Education | Up to primary | 140,181 | 39.5% | 40.5 | 0.05 | 31.7% | 76.2% | 0.0% | 15.5% |

## What the tables show

- **Who is in the sample.** Wage employees are about half regular salaried (51%) and half casual labourers; 24% are women, 63% live in rural areas, 40% have at most primary education and 19% are graduates. Average age is 37 years and the average work week is 48 hours.
- **Wages.** The mean hourly wage is Rs. 62 (median Rs. 50); it rises from Rs. 46 in 2017-18 to Rs. 78 in 2023-24 in nominal terms. Regular salaried workers earn about twice as much per hour as casual labourers, graduates about three times as much as workers with at most primary education, and men about 27% more than women.
- **Digital task intensity.** The average worker's occupation scores 0.21 on the 0–4 scale (median 0.07): most Indian wage employees work in occupations whose official descriptions mention little digital work. DTI is far higher for regular than casual workers (0.39 vs 0.03), for urban than rural workers (0.37 vs 0.12) and for graduates (0.63) than for workers with at most primary education (0.05). It is stable across rounds (0.21–0.22), because it is a property of occupations: changes over time come only from shifts in the occupational composition of employment.
- **Comparability across rounds.** Sample sizes (61–71 thousand per round) and composition are similar in the NCO-2004 rounds (2017-18 to 2020-21) and the NCO-2015 rounds (2021-22 to 2023-24), which supports pooling them with round-specific (year-quarter) fixed effects.
