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
engines include LLM extraction and local rule candidate extraction.

## Rule Candidate Triple

An evidence triple proposed by local rules for review, recall analysis, or
ablation. It is not canonical graph evidence until it is verified.

## Verified Rule Triple

A rule candidate triple that has been accepted by an LLM verifier or a human
reviewer as directly supported by the source text.

## Canonical Pipeline Output

The current output file consumed by the next pipeline stage. Canonical outputs
must keep a stable schema so downstream stages can run without internal changes.

## Reproduction Run Artifact

A dated record of one pipeline run, including logs, manifests, partial outputs,
and validation summaries. Run artifacts are evidence for reproducibility, not the
default input for downstream stages.

## Biomedical Schema

The project-level controlled vocabulary for accepted entity types, relation
types, relation aliases, relation polarity, and conflict rules. Extraction and
fusion stages use it to normalize or reject proposed evidence triples.

## Topic-Balanced Retrieval

A Stage 1 expansion step that uses topic clustering results to find
underrepresented literature themes and fetch additional PubMed candidates for
those themes without overwriting the original PubMed canonical output.

## Gold Standard Candidate

A review-ready extraction example selected for human validation before any
BioBERT, UIE-med, or other supervised relation extraction fine-tuning. It
contains source text, proposed entities, relation, evidence span, provenance,
and blank review labels.

## Relation Conflict

A case where the same meaningful entity pair has relations with incompatible
polarity, such as a drug improving and worsening the same phenotype. Relation
conflicts are marked for review instead of silently merged away.

## Evidence Context

A reviewable bundle of source abstracts, evidence triples, fused graph edges,
PMIDs, and provenance assembled to support an answer or a graph-quality decision.

## Graph RAG Answer

An answer generated from retrieved evidence context and graph context. It must
cite source PMIDs and avoid claims that are unsupported by the retrieved context.

## Conflict Adjudication

A decision about a relation conflict that classifies whether the conflict is
supported, context-dependent, caused by extraction error, caused by relation
normalization, or still unresolved. It does not rewrite canonical graph evidence
unless a later promotion step explicitly does so.
