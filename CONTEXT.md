# Context Glossary

## SMA Knowledge Graph

A biomedical graph that represents Spinal Muscular Atrophy related entities and
relations from literature and external biomedical data sources.

## Evidence Triple

A directed biomedical statement extracted from a source record. It connects one
entity to another through a relation and carries evidence provenance such as a
PMID and extraction engine.

## Extraction Engine

A component that proposes evidence triples from text. In this project, extraction
engines include LLM extraction and local rule-based fallback extraction.

## Canonical Pipeline Output

The current output file consumed by the next pipeline stage. Canonical outputs
must keep a stable schema so downstream stages can run without internal changes.

## Reproduction Run Artifact

A dated record of one pipeline run, including logs, manifests, partial outputs,
and validation summaries. Run artifacts are evidence for reproducibility, not the
default input for downstream stages.
