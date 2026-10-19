import json

import numpy as np
import pandas as pd
import pytest

from dti.aggregate import aggregate_level, build_dti, consensus, weighted_z
from dti.config import DIMENSIONS, load_rubric
from dti.crosswalk import nco2004_link
from dti.evidence import check_evidence
from dti.prompt import build_messages, prompt_version
from dti.reliability import alpha_ordinal, icc2, pairwise
from dti.schema import ParseError, json_schema, parse_coding

RUBRIC = load_rubric()
EXAMPLE = RUBRIC["worked_example"]


# --- schema / prompt -------------------------------------------------------

def test_worked_example_is_valid_coding():
    parse_coding(json.dumps(EXAMPLE["coding"]))


def test_parse_tolerates_code_fences():
    text = "```json\n" + json.dumps(EXAMPLE["coding"]) + "\n```"
    assert parse_coding(text).dimensions.D2.score == 3


@pytest.mark.parametrize("bad", ["", "no json here", '{"q1_detail": "Maybe"}'])
def test_parse_rejects_bad_output(bad):
    with pytest.raises(ParseError):
        parse_coding(bad)


def test_out_of_range_score_rejected():
    data = json.loads(json.dumps(EXAMPLE["coding"]))
    data["dimensions"]["D1"]["score"] = 5
    with pytest.raises(ParseError):
        parse_coding(json.dumps(data))


def test_schema_has_no_refs():
    assert "$ref" not in json.dumps(json_schema())


def test_prompt_contains_every_dimension_and_is_versioned():
    msgs = build_messages(RUBRIC, "Data Entry Operator", "Enters data into computer.")
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    for d in RUBRIC["dimensions"]:
        assert d["name"] in msgs[0]["content"]
    assert "Data Entry Operator" in msgs[-1]["content"]
    assert len(prompt_version(RUBRIC)) == 10


def test_example_evidence_is_grounded():
    for dim in EXAMPLE["coding"]["dimensions"].values():
        assert check_evidence(dim["evidence"], EXAMPLE["description"]) == "exact"


# --- evidence ---------------------------------------------------------------

@pytest.mark.parametrize(
    "evidence, expected",
    [
        ("", "empty"),
        ("Enters data into Computer", "exact"),
        ("enters data computer", "close"),               # small words dropped
        ("“enters data”; uses internet", "partial"),
        ("writes software", "not_found"),
        ("computer enters data", "not_found"),          # same words, invented order
    ],
)
def test_check_evidence(evidence, expected):
    assert check_evidence(evidence, "Enters data into computer, files records.") == expected


def test_check_evidence_real_case():
    text = "Process Design Engineer needs to design, develop, and evaluate integrated systems for achieving QCD."
    assert check_evidence("design, develop, evaluate integrated systems", text) == "close"
    assert check_evidence("uses CAD software to design systems", text) == "not_found"


# --- reliability ------------------------------------------------------------

def test_icc_perfect_agreement():
    m = np.array([[0, 0], [1, 1], [3, 3], [4, 4]])
    assert icc2(m) == pytest.approx((1.0, 1.0))


def test_icc_matches_shrout_fleiss_example():
    # Shrout & Fleiss (1979) table 2 data: ICC(2,1) = 0.29, ICC(2,4) = 0.62
    m = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])
    i1, ik = icc2(m)
    assert i1 == pytest.approx(0.29, abs=0.01)
    assert ik == pytest.approx(0.62, abs=0.01)


def test_alpha_perfect_and_pairwise():
    a = pd.Series([0, 1, 2, 3, 4, 2])
    assert alpha_ordinal(np.vstack([a, a])) == pytest.approx(1.0)
    stats = pairwise(a, a + 1)
    assert stats["within_1"] == 1.0 and stats["exact_agree"] == 0.0 and stats["mean_diff"] == 1.0


# --- aggregation ------------------------------------------------------------

def _runs():
    rows = []
    for code, base in [("A", 0), ("B", 2), ("C", 4)]:
        for run in range(3):
            row = {"model_name": "m", "prompt_version": "v", "nco2015": code, "run": run,
                   "q1_detail": "Yes", "q9_overall": base * 2, "q10_core": "Supporting", "q11_india_today": "Same"}
            for d in DIMENSIONS:
                row[d] = base + (1 if (code == "B" and run == 0) else 0)
                row[f"{d}_conf"] = 2
                row[f"{d}_evidence"] = "exact" if row[d] else "empty"
            rows.append(row)
    return pd.DataFrame(rows)


def test_consensus_median_and_sd():
    cons = consensus(_runs()).set_index("nco2015")
    assert cons.loc["B", "D1"] == 2  # median of 3, 2, 2
    assert cons.loc["B", "D1_sd"] > 0 and cons.loc["A", "max_sd"] == 0
    assert (cons["n_runs"] == 3).all()


def test_build_dti_standardised_and_ordered():
    occ = build_dti(consensus(_runs()), RUBRIC["aggregation"]["weights"])
    assert occ["dti_z"].mean() == pytest.approx(0, abs=1e-12)
    assert occ["dti_z"].std(ddof=0) == pytest.approx(1)
    assert list(occ.sort_values("dti_z")["nco2015"]) == ["A", "B", "C"]
    assert occ["dti_0_100"].min() == 0 and occ["dti_0_100"].max() == 100


def test_build_dti_rejects_bad_weights():
    with pytest.raises(ValueError):
        build_dti(consensus(_runs()), {d: 0.5 for d in DIMENSIONS})


def test_weighted_z_uses_weights():
    x = pd.Series([0.0, 10.0])
    z = weighted_z(x, pd.Series([3.0, 1.0]))
    assert np.average(z, weights=[3, 1]) == pytest.approx(0)


def test_aggregate_level_mean():
    occ = build_dti(consensus(_runs()), RUBRIC["aggregation"]["weights"])
    level_map = pd.DataFrame({"nco2015": ["A", "B", "C"], "group3": ["111", "111", "222"]})
    out = aggregate_level(occ, level_map, "group3").set_index("group3")
    assert out.loc["111", "n_occupations"] == 2
    assert out.loc["111", "D1"] == pytest.approx(1.0)


# --- crosswalk ----------------------------------------------------------------

def test_nco2004_link_fallbacks():
    corpus = pd.DataFrame({
        "nco2015": ["1.1", "1.2", "1.3", "2.1", "3.1"],
        "family4": ["F1", "F1", "F1", "F2", "F3"],
        "group3": ["G1", "G1", "G1", "G1", "G3"],
        "nco2004": ["4111.10", "4111.20", "", "", ""],
    })
    link = nco2004_link(corpus).set_index("nco2015")
    assert link.loc["1.1", "link"] == "direct"
    assert link.loc["1.3", "link"] == "family_mode" and link.loc["1.3", "nco2004_g3"] == "411"
    assert link.loc["2.1", "link"] == "group_mode"
    assert link.loc["3.1", "link"] == "none" and link.loc["3.1", "nco2004_g3"] == ""
