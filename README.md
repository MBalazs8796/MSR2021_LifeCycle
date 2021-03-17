# On the Rise and Fall of Simple Stupid Bugs: a Life-Cycle Analysis of SStuBs

## Purpose

This repository stores the scripts and statistics showcased in our MSR2021 mining challenge submission titled **On the Rise and Fall of Simple Stupid Bugs: a Life-Cycle Analysis of SStuBs**.

## Contents

- bugs: the small version of the [ManySStuBs4J](https://arxiv.org/abs/1905.13334) dataset
- checkpoint.json: the partial result of our mining, it adds to new field to the bugs dataset called blameData, which is the SStuB's source
- blamer.py and blame_source.py: these scripts are responsible for generating the blameData field
- pmd_check.py and statMaker.py: these scripts are responsible for creating the statistics shown our paper
- pmd_found_perc.txt and stub_stats.csv: the results shown in the paper 
- rules.xml: rules used for pmd