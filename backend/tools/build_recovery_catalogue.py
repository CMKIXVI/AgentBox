#!/usr/bin/env python3
"""Create a provenance-preserving AgentBox recovery candidate index from the extraction ZIP.

Discovery only: emitted artifacts remain Candidate until full source, context, dependencies,
duplicates, licensing and safety have been reviewed. No archive code is executed.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, zipfile
from collections import Counter
from pathlib import Path

TERMS = {
    "agent runtime":5, "agent lifecycle":5, "agent registry":5, "agent manifest":5,
    "agent dna":5, "agent genome":5, "agent factory":5, "agent builder":4,
    "agent clone":3, "agent mutation":4, "agent reproduction":4, "agent evaluation":4,
    "agent orchestration":4, "multi-agent":4, "cognitive architecture":4,
    "memory engine":4, "planning engine":4, "reasoning engine":4, "tool execution":3,
    "workflow execution":3, "capability system":3, "model routing":3,
    "identity and permissions":3, "policy engine":3, "lineage":2, "sandbox":2,
    "self-improvement":3, "evolution engine":4, "mutation engine":5,
    "reproduction engine":5, "selection engine":5, "fitness engine":5,
    "species engine":5, "artha engine":5, "aetheron":2, "yndra":2, "sakshi":4,
}
LINEAGES = {
    "agent_factory_os":("agent factory","agent dna","agent registry","agent lifecycle","universal agent definition"),
    "amge":("artificial model genetics","genome engine","mutation engine","reproduction engine","selection engine","fitness engine","species engine"),
    "cognition":("cognition engine","cognitive brain","cognitive architecture","reasoning engine","planning engine"),
    "meta_cognition_sakshi":("meta-cognition","metacognition","sakshi","witness layer","contradiction detection","drift detection"),
    "artha":("artha engine","policy reasoning","evidence engine"),
    "aetheron":("aetheron","cognitive substrate","context engine","memory hierarchy"),
    "yndra":("yndra","distributed intelligence","collective reasoning"),
    "agentbox":("agentbox","agent runtime","agent manifest","agent execution","agent cloning","agent evaluation"),
}
FIELDS = ["recovery_id","original_filename","original_code_filename","language","original_concept",
"functional_description","agentbox_subsystem","dependencies","source_provenance","original_hash",
"recovery_status","integration_status","relevance_score","matched_terms","artifact_type",
"normalised_filename","normalised_symbol","normalised_module","notes"]

def lineage_for(text):
    scores={name:sum(term in text for term in terms) for name,terms in LINEAGES.items()}
    name=max(scores,key=scores.get)
    return name if scores[name] else "unclassified"

def subsystem_for(text, lineage):
    if any(x in text for x in ("mutation","reproduction","selection","fitness","genome","species")): return "evolution/genetics"
    if any(x in text for x in ("manifest","registry","lifecycle","version","clone","builder","compiler")): return "agent-definition-registry-lineage"
    if any(x in text for x in ("memory","retrieval","rag","knowledge")): return "memory-knowledge-retrieval"
    if any(x in text for x in ("reasoning","planning","cognition","perception","meaning")): return "cognition-reasoning-planning"
    if any(x in text for x in ("policy","permission","identity","governance","consent")): return "security-policy-governance"
    if any(x in text for x in ("tool","workflow","orchestrat","runtime","execution")): return "runtime-tools-workflows-orchestration"
    return {"agent_factory_os":"agent-definition-registry-lineage","amge":"evolution/genetics",
    "cognition":"cognition-reasoning-planning","meta_cognition_sakshi":"meta-cognition-observability",
    "artha":"meaning-evidence-policy-reasoning","aetheron":"aetheron-lineage-review",
    "yndra":"distributed-orchestration-lineage-review","agentbox":"agentbox-core-review"}.get(lineage,"needs-manual-triage")

def build(archive_path, output_dir, limit=None):
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    records=[]; counts=Counter(); mismatches=0
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open("extraction_index.csv") as raw:
            reader=csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig",newline=""))
            for row in reader:
                path=row.get("output_path","")
                if not path: continue
                try: payload=archive.read(path)
                except KeyError: continue
                digest=hashlib.sha256(payload).hexdigest()
                if row.get("sha256") and digest!=row["sha256"]: mismatches+=1; continue
                content=payload.decode("utf-8","replace")
                heading=row.get("context_heading","")
                metadata=f'{row.get("archive_path","")} {heading} {path}'
                searchable=(metadata+"\n"+content).lower()
                matched=[term for term in TERMS if term in searchable]
                score=sum(weight for term,weight in TERMS.items() if term in searchable)
                lineage=lineage_for(searchable)
                if score<3 and lineage=="unclassified": continue
                score += 2 if lineage!="unclassified" else 0
                excerpt=re.sub(r"\\s+"," ",content).strip()[:220]
                records.append({
                    "recovery_id":"ABR-"+digest[:12],
                    "original_filename":Path(row.get("archive_path","")).name,
                    "original_code_filename":Path(path).name,
                    "language":row.get("detected_language","unknown"),
                    "original_concept":lineage+":"+heading,
                    "functional_description":"Candidate only; inspect complete source and context before acceptance.",
                    "agentbox_subsystem":subsystem_for((heading+" "+content).lower(),lineage),
                    "dependencies":"Not analysed",
                    "source_provenance":f'{row.get("archive_path","")}#block-{row.get("block_number","")}; archive:{path}',
                    "original_hash":digest,"recovery_status":"Candidate","integration_status":"Not started",
                    "relevance_score":score,"matched_terms":";".join(matched),
                    "artifact_type":row.get("artifact_type","unknown"),
                    "normalised_filename":"","normalised_symbol":"","normalised_module":"",
                    "notes":f"lineage={lineage}; bytes={len(payload)}; excerpt={excerpt}",
                })
                counts[row.get("artifact_type","unknown")]+=1
    records.sort(key=lambda x:(-int(x["relevance_score"]),x["source_provenance"],x["original_code_filename"]))
    if limit is not None: records=records[:limit]
    with (output_dir/"agentbox-recovery-candidates.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS); writer.writeheader(); writer.writerows(records)
    (output_dir/"agentbox-recovery-candidates.json").write_text(json.dumps(records,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={"archive":Path(archive_path).name,"candidate_count":len(records),
    "artifact_type_counts":dict(counts),"hash_mismatches_skipped":mismatches,
    "lineages":sorted({x["original_concept"].split(":",1)[0] for x in records}),
    "status_policy":"All entries remain Candidate / Not started; keyword scoring never accepts code."}
    (output_dir/"agentbox-recovery-catalogue-summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path); parser.add_argument("--output-dir",type=Path,default=Path("research/archive"))
    parser.add_argument("--limit",type=int,default=None); args=parser.parse_args()
    print(json.dumps(build(args.archive,args.output_dir,args.limit),indent=2))
