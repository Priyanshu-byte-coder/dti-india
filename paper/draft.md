# Measuring the Digital Task Intensity of Indian Occupations Using Large Language Models: Evidence on Wage Premiums and Labour Market Inequality from PLFS

Anuja Nair (Institute of Technology, Nirma University) · Gunjan Anand (Institute of Management, Nirma University) · Samik Shome (Institute of Management, Nirma University)

*Working draft. Status markers: **[PENDING-LLM]** = filled from the LLM scoring run on PARAM Shavak; **[PENDING-HUMAN]** = filled after the new round of human coding; **[PRELIMINARY]** = computed with the O\*NET-transferred measure and kept as the benchmark column once the LLM results exist. Numbers in the text come only from files in `reports/`; none are typed by hand.*

---

## Abstract

*(As submitted; to be updated with headline numbers once the results are final.)*

Digitalisation changes not only which occupations exist but also the tasks performed within them, yet Indian labour-force surveys record who works, where and for what pay, not the digital content of work. We construct an India-specific, multidimensional Digital Task Intensity (DTI) index from the official occupation descriptions of the National Classification of Occupations (NCO-2015), using a large language model (LLM) as a structured text-coding instrument governed by an explicit rubric, repeated-run stability tests, human validation and external benchmarking against O\*NET. We link the index to Periodic Labour Force Survey (PLFS) microdata for 2017-18 to 2023-24 and estimate the conditional wage premium associated with working in a digitally intensive occupation, and how that premium varies by gender, education, rural–urban location and employment formality.

---

## 1. Introduction

Digitalisation is transforming work by changing not only the types of occupations available in labour markets but also the tasks and skills required within occupations. The diffusion of computers, digital platforms, data-driven technologies, automation and artificial intelligence has raised the importance of digital capabilities across a broad range of occupations. Measuring the extent to which workers actually engage in digitally intensive work remains difficult, particularly in developing economies such as India. Labour-force surveys contain rich information on employment status, occupation, industry, education, wages, gender and location, but little direct information on the digital tasks workers perform. Understanding the labour-market returns to digitalisation therefore requires a credible occupation-level measure of digital-task intensity.

Task-based research on India provides the starting point. Vashisht and Dubey (2019) combine several rounds of the NSS Employment–Unemployment Survey with task measures from the US Occupational Information Network (O\*NET), assigning 16 task items to occupations and aggregating them into five dimensions (non-routine cognitive analytical, non-routine cognitive interactive, routine cognitive, routine manual and non-routine manual). Non-routine cognitive task intensity rose substantially between 1983-84 and 2011-12 while manual task intensity fell; unlike in the United States and Europe, routine cognitive intensity did not decline. This approach raises a measurement question. O\*NET describes the US labour market, and mapping its scores onto Indian occupations through crosswalks assumes that workers in equivalent occupational categories perform similar tasks in both countries. Existing task measures also distinguish cognitive, manual, routine and non-routine work rather than measuring *digital* task content directly.

This paper addresses that gap. We build an India-specific DTI index from the textual descriptions of Indian occupations in NCO-2015, using an LLM as a measurement instrument rather than as a predictor: the model applies an explicit, published rubric to the official text, quotes the words that justify each score, and is checked for run-to-run stability, cross-model agreement, agreement with human coders and correspondence with an O\*NET-based measure. We then link the index to PLFS microdata to estimate the conditional wage premium associated with digitally intensive occupations and its distribution across groups of workers.

**Research questions.**

- **RQ1.** Can occupational descriptions in India's NCO be transformed into a reliable and reproducible measure of digital-task intensity using LLMs?
- **RQ2.** To what extent does an India-specific measure of digital-task intensity differ from an equivalent measure transferred from O\*NET?
- **RQ3.** Is employment in a digitally intensive occupation associated with a wage premium after accounting for observable worker, occupation, industry and geographical characteristics?
- **RQ4.** Is this conditional digital occupational premium distributed uniformly, or does it vary by gender, educational attainment, rural–urban location, employment formality and other dimensions of labour-market segmentation?

**Contributions.** The first is a *measurement* contribution: an India-specific DTI derived directly from NCO occupation text, reducing reliance on the assumption that US task structures transfer to India. The second is *methodological*: a transparent use of generative AI for economic measurement, in which the LLM is a structured text-coding instrument governed by a taxonomy, repeated reliability testing, human validation and external benchmarking. The third is *empirical and policy-oriented*: evidence from nationally representative PLFS data on whether occupational digitalisation is associated with higher wages and whether these gains are shared across education, gender, geography and formal/informal employment.

## 2. Related literature

**Task content of Indian employment.** Vashisht and Dubey (2019) document the changing task content of Indian jobs using O\*NET task items mapped to NCO codes. Sharma, Gupta and Estupinan (2020) show that NCO occupation descriptions can be rated directly (for work-from-home feasibility) and linked to PLFS through NCO-2015 to NCO-2004 crosswalks, a route this paper follows for digital tasks.

**Digital task indices.** Cirillo et al. (2021) construct a digital-use index and a digital-task index for Italian occupations from the INAPP-ISTAT occupational survey and relate digitalisation and routineness to employment growth. Stöllinger and Guarascio (2025) replicate the digital task index for the United States from O\*NET task statements using a keyword approach and compare EU and US digital task endowments; the two indices correlate at 0.89 despite different sources and classifications. Muro et al. (2017) score US occupations on two O\*NET items (computer and electronics knowledge; working with computers).

**Digital skills and wages.** Adrjan et al. (2026) use an LLM to classify millions of online job postings in six Asia-Pacific economies by required digital proficiency, validate it against human annotators (about 80% agreement, comparable to agreement between humans), and estimate within-job-title wage premia of roughly 4%, 11% and 26% for basic, intermediate and advanced digital skills. Sami (2026) estimates returns to digital skills in Egypt with Mincer, quantile and selection models and finds larger returns for women.

**LLMs as measurement instruments.** LLMs have been used to score occupational exposure to AI (Eloundou et al., 2024) and to classify job ads (Adrjan et al., 2026). We use the same family of tools for a different purpose: converting official occupational text into a validated quantitative indicator where no survey measure exists.

## 3. Data

### 3.1 Occupation descriptions: NCO-2015

The National Classification of Occupations 2015 (Ministry of Labour and Employment) follows ISCO-08 to the four-digit unit-group level and extends it to eight-digit occupations. Volume II provides a textual description for each occupation. Our corpus contains all **3,450** eight-digit occupations with descriptions (Division 0, armed forces, has none), grouped into 373 four-digit families and 122 three-digit groups. Descriptions have a median length of 89 words. Only 5.7% of descriptions use any explicitly digital term (computer, software, internet, online, e-mail, programming, database, spreadsheet, CNC, CAD), ranging from 16.5% among professionals to 0% among skilled agricultural workers. This sparsity motivates the rubric design in Section 4.

### 3.2 Labour-market data: PLFS 2017-18 to 2023-24

We use the seven annual July–June rounds of the Periodic Labour Force Survey, first-visit person and household files. Occupation is recorded at the three-digit level in NCO-2004 up to 2020-21 and NCO-2015 from 2021-22. Each worker receives the DTI of the three-digit occupation in the round's classification (Section 4.5). Wages and occupation refer to the current weekly status (CWS). Hourly wages are monthly regular earnings divided by weekly hours × 4.33, weekly casual earnings divided by weekly hours, and (for the self-employed, analysed separately) earnings over the last 30 days divided by hours over 30/7 weeks; the top and bottom 0.5% are trimmed within each round. Survey weights follow the PLFS documentation (MULT/100 if NSS = NSC, otherwise MULT/200, divided by the number of quarters for annual estimates). Religion, social group and household composition come from the household file. The pooled data contain 2.95 million persons; the main analysis sample consists of regular and casual wage earners aged 15–64 with a valid hourly wage and a DTI (**see Table 1**). As a check on the harmonisation, our CWS unemployment rates for 2017-18 (8.9%) and 2018-19 (8.8%) reproduce the published estimates.

### 3.3 O\*NET

For the external benchmark (RQ2) we use O\*NET 31.0: occupation descriptions and core task statements for 923 occupations, and the items "Working with Computers" (work activity 4.A.3.b.1), "Computers and Electronics" (knowledge 2.C.3.a) and e-mail frequency (work context 4.C.1.a.2.h). O\*NET-SOC 2019 codes are mapped to SOC 2010 with the O\*NET taxonomy crosswalk and to ISCO-08 with the BLS crosswalk; ISCO-08 unit groups coincide with NCO-2015 families. Many-to-many links are weighted by US employment (BLS OEWS). The mapping covers 360 of 373 NCO families and 97.9% of NCO occupations.

## 4. Constructing the Digital Task Intensity index

### 4.1 Dimensions and rubric

Inspired by DigComp and related taxonomies, each occupation is scored on five dimensions: (1) basic digital operation; (2) digital information processing; (3) digital communication and collaboration; (4) advanced or specialised digital-tool use; and (5) digital problem solving and content creation. Each dimension has an explicit ordinal scale from 0 (none) to 4 (core: the digital activity is the main work), with written anchors and Indian occupational examples for every level (Appendix A). The same rubric and the same worked example are given to the LLM and to human coders.

Scores are grounded in the official text: the model scores the title and description only, quotes the words that support each non-zero score, and records its confidence. Two readings of "text only" are implemented: a *strict* reading, in which only digital work the text names counts, and a *described-task* reading, in which tasks the text describes that the typical worker in India performs with digital tools also count, still requiring a quote from the text. **[PENDING: choice between the two after the pilot; the other is reported as robustness.]**

### 4.2 LLM scoring

The rubric is rendered into a fixed prompt; the model returns a JSON object validated against a schema (scores 0–4, confidence 1–3, evidence, and the remaining coder-form items). Every quoted piece of evidence is checked against the description; quotes not found in the text are flagged. Each occupation is scored five times per model (temperature 0.7, seeds 0–4) so that stability is tested rather than imposed; the consensus score per dimension is the median across runs. Two open-weight model families are used: Qwen2.5-14B-Instruct and Llama-3.1-8B-Instruct, run locally on a Quadro GP100 GPU (PARAM Shavak, Nirma University) through llama.cpp. Each output records a hash of the prompt, rubric and schema, so results from different instrument versions are never mixed.

### 4.3 Aggregation

Following the abstract (eq. 1), dimension scores are standardised and aggregated with equal weights, then re-standardised:

```latex
DTI_j = \sum_{k=1}^{5} w_k \, D_{jk}, \qquad w_k = 1/5
```

where *D_jk* is the standardised score of occupation *j* on dimension *k*. Alternative weights (principal components; weights implied by the holistic overall score) are robustness checks. As in Vashisht and Dubey (2019), the index aggregates several task items rather than relying on one.

### 4.4 Reliability and validation (RQ1)

- **Intra-model stability:** ICC(2,1) and Krippendorff's ordinal α across the five runs; occupations with run-to-run SD above 0.5 on any dimension are reviewed manually.
- **Cross-model agreement:** quadratic-weighted κ, Spearman ρ and α between the two model families.
- **Human validation:** a stratified sample of occupations across skill levels and divisions is coded independently by human coders with the same rubric; agreement with the LLM is compared with agreement between humans (weighted κ, Krippendorff's α). **[PENDING-HUMAN]**
- **Grounding:** the share of non-zero scores whose evidence quote does not appear in the description.

### 4.5 From occupations to PLFS workers

Eight-digit scores are averaged to NCO-2015 families and three-digit groups (no employment counts exist below three digits, so occupations within a group are weighted equally; medians as robustness). For PLFS rounds coded in NCO-2004, each NCO-2015 occupation is linked to its NCO-2004 concordance code from NCO-2015 Volume I (2,657 occupations); occupations new in 2015 take the most common code of their siblings in the same family (759) or group (32). A robustness check keeps only NCO-2004 groups with at least 75% direct links. 98.8–99.8% of employed PLFS workers in each round receive a DTI; the unmatched are mainly armed forces and a few groups without Volume II descriptions.

### 4.6 India–US comparison (RQ2)

The O\*NET benchmark is constructed in two ways. The *same-instrument* version scores O\*NET occupation descriptions and core tasks with the identical prompt, so differences reflect the occupational texts rather than the method. The *conventional* version uses the O\*NET computer items (Muro et al., 2017) and the share of core tasks with digital keywords (Stöllinger and Guarascio, 2025). For each NCO family *j*:

```latex
DigitalGap_j = DTI_j^{O^*NET} - DTI_j^{NCO\text{-}LLM}
```

computed on the common 0–4 scale for the same-instrument version and as percentile-rank differences otherwise. Systematic positive or negative gaps by occupational division or skill level indicate where transferring US characteristics overstates or understates digital intensity implied by Indian descriptions.

## 5. Empirical strategy

### 5.1 Conditional digital occupational premium (RQ3)

```latex
\ln Wage_i = \alpha + \beta \, DTI_{j(i)} + \gamma X_i + \delta_s + \lambda_r + \tau_t + \epsilon_i
```

*X_i* contains age, age², gender, marital status, rural residence, education, social group and religion; δ, λ and τ are industry (NIC two-digit), state and year-quarter fixed effects. DTI is standardised across workers in the estimation sample, so β is the log-wage difference associated with a one-standard-deviation higher occupational DTI. The specification ladder adds controls and fixed effects step by step (M1–M4); the preferred specification (M4) adds occupational division fixed effects, so β compares occupations within the same broad skill group. M5 replaces the index with its five dimensions. Estimates are weighted by PLFS weights; standard errors are clustered by occupation, the level at which DTI varies, with a wild cluster bootstrap as a check.

β is interpreted as a **conditional digital occupational wage premium**, not as the causal return to digital skills: workers are not randomly assigned to occupations, and occupational sorting may depend on ability, family background and other unobservables. We report Oster (2019) bounds to gauge how strong selection on unobservables would need to be to explain the estimate away.

### 5.2 Robustness

Unweighted estimates; monthly earnings; regular and casual workers separately; NCO-2015 and NCO-2004 rounds separately; directly linked NCO-2004 groups only; DTI quintiles; the self-employed; Heckman selection into wage employment (exclusion restrictions: children under six in the household, household size, household head), for all workers and separately by gender; and the alternative DTI constructions of Section 4.

### 5.3 Distribution and heterogeneity (RQ4)

Unconditional quantile (RIF) regressions (Firpo, Fortin and Lemieux, 2009) and conditional quantile regressions trace the premium across the wage distribution. An Oaxaca–Blinder decomposition with pooled coefficients shows how much of the gender wage gap runs through occupational DTI. Heterogeneity is estimated, first, with DTI × group interactions for gender, rural residence, education band, age band, employment type and (for regular workers) formality, both with the preferred fixed effects and with full three-digit occupation fixed effects, which identify the interactions from within-occupation differences between groups; and second, with double/debiased machine learning (Chernozhukov et al., 2018): a partially linear model gives the average partial effect, the best linear projection of the effect on pre-specified covariates, and group average effects. A causal forest (Athey, Tibshirani and Wager, 2019) is estimated as a supplement. Heterogeneity dimensions are fixed in advance.

## 6. Results

### 6.1 The DTI index and its reliability (RQ1)

**[PENDING-LLM]** Distribution of DTI by division and skill level; most and least digital occupations; run stability (ICC, α); cross-model agreement; grounding rate; comparison of strict and described-task readings.

**[PENDING-HUMAN]** Human–LLM agreement relative to human–human agreement.

### 6.2 India-specific versus O\*NET-transferred intensity (RQ2)

**[PENDING-LLM]** Correlation between NCO-LLM DTI and O\*NET measures at the family level; DigitalGap by division and skill level.

### 6.3 The conditional digital occupational premium (RQ3)

<!-- RESULTS:RQ3 -->

### 6.4 Heterogeneity (RQ4)

<!-- RESULTS:RQ4 -->

## 7. Discussion and policy relevance

A DTI index gives policymakers a more granular picture of India's digital labour market than classifications based on education, occupation or industry alone. Identifying occupations with high and low digital-task intensity can inform digital-skilling programmes, vocational curricula and workforce-transition strategies. More importantly, identifying groups for whom occupational digitalisation does not translate into commensurate labour-market gains helps distinguish a *digital-skills gap* from a broader *digital-returns gap*. If the premium differs by education or formality, expanding access to basic digital training may be insufficient; complementary investment in advanced skills, certification, formalisation and access to digitally enabled firms may be required. Rural–urban or gender differences would indicate that the benefits of digitalisation depend on institutional and labour-market conditions beyond occupational digital requirements themselves. **[Final wording to follow the results.]**

## 8. Limitations

The DTI measures digital content as described in the 2015 classification, which may understate current practice; the coder item on whether an occupation is more digital today than its description suggests, and the described-task reading, address this. Occupation is observed at three digits in PLFS, so within-group variation in digital intensity is not used. The premium is a conditional association, not a causal effect. LLM scores carry model-dependent measurement error, which the stability, cross-model and human checks quantify but cannot remove.

## 9. Conclusion

**[To be written with the final results.]** Indian labour-market surveys record who works, where, in what occupation and for what pay, but little about the digital content of work. This study bridges that gap by combining official occupational descriptions, large language models and PLFS microdata. Its central claim is that AI can advance labour-market research not only by predicting outcomes but by measuring economically important constructs that are otherwise hard to observe.

## References

- Acemoglu, D. and Autor, D. (2011). Skills, tasks and technologies: Implications for employment and earnings. *Handbook of Labor Economics*, 4B, 1043–1171.
- Adrjan, P., Aoki, Y., Ciminelli, G., Döttling, R. and Garcia-Mandicó, S. (2026). Skills that pay: Digital skills demand and wage premia in Asia and the Pacific. ADB Economics Working Paper 850.
- Athey, S., Tibshirani, J. and Wager, S. (2019). Generalized random forests. *Annals of Statistics*, 47(2), 1148–1178.
- Autor, D., Levy, F. and Murnane, R. (2003). The skill content of recent technological change. *Quarterly Journal of Economics*, 118(4), 1279–1333.
- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W. and Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *Econometrics Journal*, 21(1), C1–C68.
- Cirillo, V., Evangelista, R., Guarascio, D. and Sostero, M. (2021). Digitalization, routineness and employment: An exploration on Italian task-based data. *Research Policy*, 50, 104079.
- Eloundou, T., Manning, S., Mishkin, P. and Rock, D. (2024). GPTs are GPTs: Labor market impact potential of LLMs. *Science*, 384(6702), 1306–1308.
- Firpo, S., Fortin, N. and Lemieux, T. (2009). Unconditional quantile regressions. *Econometrica*, 77(3), 953–973.
- Heckman, J. (1979). Sample selection bias as a specification error. *Econometrica*, 47(1), 153–161.
- Krippendorff, K. (2004). *Content Analysis: An Introduction to Its Methodology*. Sage.
- Muro, M., Liu, S., Whiton, J. and Kulkarni, S. (2017). *Digitalization and the American Workforce*. Brookings Institution.
- Oaxaca, R. (1973). Male–female wage differentials in urban labor markets. *International Economic Review*, 14(3), 693–709.
- Oster, E. (2019). Unobservable selection and coefficient stability. *Journal of Business & Economic Statistics*, 37(2), 187–204.
- Sami, M. (2026). Digital skills, gender, employment and wages in the Egyptian labor market. *International Journal of Manpower*, 47(2), 283–305.
- Sharma, M., Gupta, S. and Estupinan, X. (2020). An alternate to survey methods to measure work from home. IGIDR Working Paper WP-2020-028.
- Shrout, P. and Fleiss, J. (1979). Intraclass correlations: Uses in assessing rater reliability. *Psychological Bulletin*, 86(2), 420–428.
- Stöllinger, R. and Guarascio, D. (2025). Assessing digital leadership: Is the EU losing out to the US? *Open Economies Review*, 36, 329–371.
- Vashisht, P. and Dubey, J. D. (2019). Changing task contents of jobs in India: Implications and way forward. ICRIER Working Paper 355.

## Appendix A. Coding rubric

See `configs/rubric.yaml` (described-task reading) and `configs/rubric_strict.yaml` (strict reading); the human coder guide is `docs/DTI_Human_Coder_Guide.pdf`.
