# Causal forest for heterogeneity in the DTI wage premium (RQ4), using R `grf`.
# Input: reports/econ/grf_input.csv, written by `dti analysis` (step grf_input).
#   Y = log wage, W = DTI (standardised, continuous), cluster = occupation id,
#   X_* = covariates, A_* = pre-specified heterogeneity variables for the BLP.
#
#   install.packages(c("grf", "data.table"))
#   Rscript scripts/grf_causal_forest.R [reports/econ]
#
# NOTE: not executed by the authors of this script (no R in the dev environment);
# check the output against the DoubleML BLP in reports/econ/dml_blp.csv.

suppressPackageStartupMessages({ library(grf); library(data.table) })
args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "reports/econ"
d <- fread(file.path(dir, "grf_input.csv"))

X <- as.matrix(d[, grep("^(X_|A_)", names(d)), with = FALSE])
A <- as.matrix(d[, grep("^A_", names(d)), with = FALSE])
set.seed(1)
cf <- causal_forest(X, d$Y, d$W, clusters = d$cluster, num.trees = 2000)

ape <- average_treatment_effect(cf)                 # average partial effect for continuous W
blp <- best_linear_projection(cf, A)
cal <- test_calibration(cf)

fwrite(data.table(estimate = ape[["estimate"]], std.err = ape[["std.err"]]), file.path(dir, "grf_ape.csv"))
fwrite(data.table(term = rownames(blp), as.data.table(unclass(blp)[, 1:4])), file.path(dir, "grf_blp.csv"))
fwrite(data.table(term = rownames(cal), as.data.table(unclass(cal)[, 1:4])), file.path(dir, "grf_calibration.csv"))
vi <- variable_importance(cf)
fwrite(data.table(variable = colnames(X), importance = as.numeric(vi))[order(-importance)], file.path(dir, "grf_variable_importance.csv"))
cat("grf results written to", dir, "\n")
