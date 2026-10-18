# PLFS data: what we received, how it is organised, what the loader does

Seven annual July–June rounds, MoSPI CSV releases from microdata.gov.in. The data are
**not in git** (MoSPI terms; `data/raw/` is ignored). They are shared privately as a zip
that unpacks to `data/raw/plfs/`.

## Folder layout

```
data/raw/plfs/<round>/
  data/   per_fv_<round>.csv   person, first visit        <- used
          hh_fv_<round>.csv    household, first visit     <- used (religion, social group, hh size)
          per_rv_<round>.csv   person, revisits (urban)   <- not used
          hh_rv_<round>.csv    household, revisits        <- not used
  docs/   data layout, instruction manuals, README, estimation procedure, district codes, notes
```

MoSPI file names differ every year; they were renamed to this pattern by content (record
id `FVP*`/`FVH*` = first visit, `RVP*`/`RVH*` = revisit). Values are untouched.

## Rounds

| Round | Persons (first visit) | Occupation codes | Column naming | Checked |
|---|---|---|---|---|
| 2017-18 | 433,339 | NCO-2004 | `*_per_fv` / `*_hh_fv` | CWS UR 8.9% = published 8.9% |
| 2018-19 | 420,757 | NCO-2004 | as 2017-18; household FV file uses `*_hh_rv` names | CWS UR 8.8% = published 8.8% |
| 2019-20 | 418,297 | NCO-2004 | as 2017-18 | CWS UR 9.2% (check vs report; includes Apr–Jun 2020 lockdown) |
| 2020-21 | 413,405 (410,818 after dropping visitors) | NCO-2004 | new schedule: `*_perv1` / `*_hhv1`, quarters Q5–Q8, migration block 7 | CWS UR 7.7% (check vs report) |
| 2021-22 | 428,525 | **NCO-2015** | `*_perv1`, extra block-5 items, daily columns misnamed (see below), codes as floats | CWS UR 6.7% (check vs report) |
| 2022-23 | 419,512 | NCO-2015 | as 2020-21 without block 7; quarters Q5–Q8 | CWS UR 5.2% (check vs report) |
| 2023-24 | 418,159 | NCO-2015 | identical to 2022-23 | CWS UR 5.0% (check vs report) |

Pooled: 2,949,407 persons; 466,127 regular + casual wage earners aged 15–64 with a valid
hourly wage and a DTI. DTI coverage of employed workers: 98.8–99.8% per round.

## Quirks found and how the loader handles them

| Issue | Rounds | Handling |
|---|---|---|
| Religion, social group, household size only in the household file | all | household file merged onto persons (`household:` block in `configs/plfs.yaml`) |
| Household key columns named differently in person and household files | all | key map person column → household column |
| First-visit household file carries revisit (`_hh_rv`) column names | 2018-19 | mapped by those names; content verified as first visit (FVH1, V1) |
| Person serial ≥ 81 = temporary visitor (not a household member) | 2020-21 on | dropped (`codes.temporary_visitor_serial_min: 81`) |
| Codes stored as floats (`611.0`, `1.0`) | 2021-22 | normalised (state `01`, occupation `611`, NIC `01`); merge keys normalised |
| Daily hours/wage columns of activity 1 and 2 have swapped names | 2021-22 | casual earnings = sum over both activities and 7 days, so the swap has no effect |
| Quarters coded Q5–Q8 | 2020-21, 2022-23 | year-quarter FE built as `<year>Q<n>`; unique within a round |
| CWS industry code is 2-digit (NIC division) | all | used as is for industry FE |
| Contract / paid leave / social security only for usual principal activity | all | formality measured from block 5.1 (principal status), wages from CWS block 6 |
| District codes repeat across states | all | district = state + district |
| Very large (correct) multiplier for one Assam village | 2022-23 | kept; compare weighted vs unweighted results (`robustness.csv`) |
| Unmatched occupation codes | all | listed in `plfs_harmonised_dti_coverage.csv`: armed forces (0xx) and NCO groups without Vol II descriptions (NCO-2004: 113, 348; NCO-2015: 323, 523, 632–634; 970–990 in 2017-18) |

## Weights

From the PLFS README: combined sub-samples weight = MULT/100 if NSS = NSC, else MULT/200;
for annual estimates divide by the number of quarters (`No_Qtr`). Implemented as
`weights.rule: plfs_annual`.

## Variables built (CWS = current weekly status, reference week)

- Employment type from CWS status: self-employed 11/12/21, regular 31, casual 41/42/51, unemployed 81/82.
- Occupation and industry: CWS block 6 codes (3-digit NCO, 2-digit NIC).
- Hourly wage: regular = last month's earnings / (weekly hours × 4.33); casual = sum of daily
  wage earnings over the week / weekly hours; self-employed = last 30 days' earnings / (weekly hours × 30/7).
  Weekly hours = sum of daily "total hours actually worked". Top and bottom 0.5% trimmed per round.
- Deflation: by state × sector × year CPI if `data/raw/cpi.csv` is supplied; otherwise nominal
  (year-quarter fixed effects absorb the national price level).

## Still to do

- Compare each round's CWS unemployment rate and worker shares with the official annual
  report tables (2019-20 to 2023-24 marked "check" above).
- Optional CPI file for real wages.
