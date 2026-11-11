# Full ZIP review — batch 007 (source files 1,501–1,750)

Date: 2026-11-11  
Repository: `CMKIXVI/AgentBox`  
Coverage: lexical source paths 1,501–1,750 of 2,571 Markdown files.

## Review method and limits

All 250 source entries in this batch were screened using their source path, headings, normalized content hash and user-authored excerpts. Repeated exports with matching normalized hashes were treated as duplicate provenance, not separate requirements. High-signal conversations were inspected at greater depth.

This is a first-pass semantic review. It does not claim every assistant response and every code block in all 250 files has been line-by-line adjudicated. Some long conversations (including LangChain development, UPI automation and leadership modules) need a later deep review before their detailed requirements can be considered final.

## 1. Digital action agents and action-model capability

**Source:** `2025/Large Action Models Overview.md`

The user explicitly asks for open-source digital action agents, browser automation with LLMs, how to create action models, and then states: “We will build for digital actions.”

**Related source:** `2025/IFTTT for AI Agents.md` asks for an IFTTT-like system for agents and an interactive flow builder.

**Candidate AgentBox requirements**
- Treat digital action execution as a first-class agent capability, not merely text generation.
- Model actions as typed, observable operations with preconditions, parameters, expected effects, permissions, idempotency and postcondition verification.
- Support browser/UI automation as one execution adapter alongside APIs and MCP tools.
- Add a trigger-condition-action rule builder, event subscriptions and reusable automation recipes.
- Capture action traces, screenshots or structured evidence where appropriate, with redaction of secrets and personal data.
- Require risk-tiered confirmation for irreversible, financial, external-communication or destructive actions.
- Distinguish a language model that proposes actions from the trusted runtime that validates and executes them.

**Disposition:** core runtime capability. Action-model research and browser/computer-use adapters are important, but the runtime remains the security and authorization authority.

## 2. Offline-first application and local AI runtime

**Sources**
- `2025/Hosting 1000+ Apps Offline.md`: the user asks how to host more than 1,000 applications in one offline app, selects Flutter, asks for a complete code structure, and explicitly requires offline data security and disconnection from outside interfaces.
- `2025/Offline AI Models PC.md`: requests a catalogue of 500 offline models and an automated download script for a specified PC.
- `2025/Offline AI Python Coders.md`: asks for offline code models, their capabilities and sizes, with a size constraint under 10 GB.
- `2025/Offline AI Tools Mobile.md` and variants: asks for minimum offline AI tools for phones, function ideas and an offline AI package built from scratch.
- `2025/Offline App Implementations.md`: multiple offline app modules, then asks for continued enhancements and separate tools without repeatedly changing the main app function.
- `2025/Offline Microlearning App.md`: offline microlearning, personalized learning paths, quizzes, reminders and content library.

**Candidate AgentBox requirements**
- Offline-capable package/app host with a local registry, dependency cache, signed bundles, version pinning and offline installation/update workflow.
- Strictly local mode that can disable network egress, not merely hide external connectors in the UI.
- Encrypted local data store, OS-backed key storage, device-bound credentials, backup/export controls and auditable access.
- Local model catalogue with model format, quantization, size, modality, license, hardware/runtime compatibility, memory estimate and integrity hash.
- Model download manager with resumable transfer, checksum/signature verification, storage budgeting and safe update/rollback.
- Mobile offline runtime with device capability detection, battery/thermal/resource limits and small-model routing.
- Offline synchronization is a separate mode from fully disconnected mode; when sync is enabled, conflict handling and data movement must be explicit.

**Disposition:** major differentiator and platform capability. The source contains an explicit offline-first and no-external-interface requirement for the multi-app host; preserve it as a distinct deployment/security profile.

## 3. Privacy-preserving computation and cryptographic services

**Sources**
- `2025/Homomorphic Encryption Applications.md`: asks for patentable ideas and new techniques in homomorphic encryption.
- `2025/Homomorphic Encryption Overview.md`: asks about encryption types and schemes.
- `2025/ML-HyRM Code Cryptosystem.md` (path/title appears in this batch's source inventory): user supplies a proposed post-quantum rank-metric hybrid cryptosystem and asks for section-by-section explanation and technical definitions.
- `2025/India AI models comparison.md`: model landscape and locally relevant AI model comparison.

**Candidate AgentBox requirements**
- A cryptographic provider interface for encryption at rest/in transit, key management, signatures, hashes, and optional privacy-preserving computation.
- Data-classification and policy labels should determine whether data may be sent to external models or tools.
- Homomorphic encryption and secure multiparty computation are specialized privacy computation adapters; they should not be advertised as default protection for every workload.
- Post-quantum cryptography should be handled through replaceable crypto suites and algorithm agility, with independent cryptographic review.
- Agent manifests/packages should reference secret/key handles and crypto policy, never embed secret key material.

**Disposition:** cross-cutting security architecture plus advanced optional crypto services. The proposed cryptosystem in the source is an idea requiring cryptanalysis; it is not a validated standard and must not be adopted as a production primitive without expert review.

## 4. Model aggregation, ensembles and model operations

**Sources**
- `2025/MoA model overview.md`: asks whether Mixture-of-Agents can run on a personal GPU, mobile, SAP Joule and as a service platform.
- `2025/Large models list.md`: asks for large language models and analogous “large action model” and “large process model” categories.
- `2025/India AI models comparison.md`: comparison of Indian AI models and platforms.
- `2025/Offline AI Models PC.md`: broad local model inventory and automated acquisition.

**Candidate AgentBox requirements**
- A model service capable of selecting one model or an ensemble based on task, cost, latency, privacy, hardware and evaluation evidence.
- Explicit orchestration strategies: single model, fallback, parallel candidate generation, ranker/judge, mixture-of-agents and specialist routing.
- Ensemble outputs need provenance: which model contributed, prompts/inputs, aggregation strategy, latency, token/resource cost and evaluation results.
- Local/mobile deployment must be constrained by memory, compute, thermal and battery budgets.
- Treat “Large Process Model” and “Large Action Model” as research/product taxonomy candidates from the user's material, not established technical standards.

**Disposition:** core model plane. Avoid assuming multiple models automatically improve quality; compare against single-model baselines.

## 5. Agentic process automation and financial transaction workflows

**Sources**
- `2025/IFTTT for UPI.md`: very long conversation asking for an expanded, complete UPI automation platform with triggers, actions and production-ready code.
- `2025/Multi-Bank App Requirements.md` and duplicate: multi-bank app, Indian account aggregation, UPI/payment workflows, spam/no-spam reporting for bank accounts and UPI IDs.
- `2025/Multiple UPI Payments Guide.md`: bulk UPI payment options, payment slips/receipts, mobile-first bill payment and MilkBill automation.
- `2025/ICR Accrual Automation Proposal.md`: intercompany reconciliation and accrual posting; the user expands a Budget Bot to monitor SAP IM/PS budget issues, approval workflow, commitments, goods receipt/invoice process and invoice posting.
- `2025/IM program creation BRs.md`: spreadsheet mass upload, investment management program creation, budget update and WBS planning-level structure.
- `2025/Follow-Up Activity Rule.md` and earlier workflow sources: sequence/rule validation.

**Candidate AgentBox requirements**
- Event-triggered automation fabric: event source, condition, policy check, action plan, approval, execution, verification and compensation.
- Financial transaction actions must use approved payment/banking rails and explicit user/business authorization. A model must not originate or release payments based only on generated text.
- Payment workflow needs idempotency, limits, payee verification, maker-checker controls, fraud/risk signals, receipts and reconciliation.
- ERP process agents need business-object context and process state across budget, approval, commitment, procurement, receipt and invoice posting.
- Long-running process agents need durable checkpoints, waiting states, external event correlation and escalation.
- Sensitive financial identity/account data must be minimized and access-scoped.

**Disposition:** core automation runtime and connector/policy contracts; UPI, banking and SAP process bots are vertical packages.

## 6. Structured knowledge, education and assessment workflows

**Sources**
- `2025/Mock questions and answers.md`: requests file-grounded MCQs with 4 options, answer and brief explanation; specifies school exam level and Grade 8 Computer Science/C++ and insists on strict analysis of attached files.
- `2025/Leader_s Playbook Module.md`: requests an interactive, scenario-driven, metrics-focused leadership module, readable in 5–10 minutes; asks for separate appendable pages, dashboard and main menu.
- `2025/Legal AI Intelligence.md`: asks for a large Indian legal knowledge system, related-case mind maps, similar judgments, pre-closed cases, case valuation and verification of judgments.
- `2025/Legal Information Request.md`: asks for offline RAG for Indian legal information.
- `2025/Offline Microlearning App.md` and `2025/Online Learning Platform Guide.md`: learning paths, courses, quizzes, community and offline access.

**Candidate AgentBox requirements**
- Source-grounded knowledge tasks must cite the exact source documents and distinguish evidence from model inference.
- Assessment schemas should support question banks, multiple-choice options, correct answers, explanations, difficulty, grade/domain, source citation and version.
- Course/leadership modules should be independently packaged, appendable and navigable through a common app shell/dashboard.
- Legal knowledge requires jurisdiction, court, date, precedential status, source authority, citation verification and careful limits on AI conclusions; never claim that a model can independently overturn a judgment.
- Offline RAG should preserve document provenance and local data boundaries.

**Disposition:** reusable knowledge/evaluation primitives and packaged education/legal/leadership applications. The source-grounded requirement to analyze attachments strictly is a general ingestion/evaluation contract.

## 7. Developer tools, code generation and error-repair loops

**Sources**
- `2025/Online C++ compilers list.md`: compares online compilers and asks to create CodeGpt.online for C, C++, Java and Python initially.
- `2025/LangChain Application Development_1.md`: broad application use cases, document extraction, chatbots, RAG, agentic applications and framework alternatives.
- `2025/LangChain Frameworks Overview.md`: asks to implement a presentation-slide maker step by step.
- `2025/LangChain OCR Flutter Integration.md`, `2025/OCR and Scan Sum.md`, `2025/OCR and Package Fix.md`: asks for OCR, document extraction, spell correction, handwritten conversion, bill/voucher monetary value extraction and summation, Flutter/Dart integration; reports package incompatibilities and multiple compile errors.
- `2025/Image Analysis Request.md`: asks to build a GPT export organizer in React Native.
- `2025/My GPT Organizer Overview.md`: asks for Windows/macOS offline backup, search, folders/tags, editing notes and HTML/Markdown export.

**Candidate AgentBox requirements**
- Developer-agent lifecycle: inspect repository, understand dependencies, propose patch, edit, compile/lint/test, interpret diagnostics, repair and rerun tests.
- Sandboxed compiler/execution service for supported languages; strict CPU/memory/time/network/filesystem limits and no host credential access.
- Artifact generation should be complete and reproducible: project tree, dependency lock, build instructions, tests and exports.
- OCR pipeline should separate image preprocessing, OCR engine adapter, structured field extraction, currency/amount parsing, confidence, user correction and arithmetic reconciliation.
- Offline export organizer and local document/code search are knowledge-workspace packages.

**Disposition:** important developer tool package and agent self-repair capability. Do not execute generated code in the main AgentBox service process.

## 8. Open systems, interoperability and cross-platform service discovery

**Sources**
- `2025/Open Broadcast Network Ideas.md`: open broadcast network, decentralized news/education/public service and X2X “everything to everything” content exchange.
- `2025/Open Broadcast V2X Hardware_1.md`: broad OpenBroadcast V2X concept review.
- `2025/Open Map V2X Integration.md`: unified map to view ride-hailing, courier and logistics systems; standard V2X data for availability, price and route; one super app to view/book through integration with other apps.
- `2025/Open Map V2X Overview.md`: overview of mapping, V2X, data fusion, security/privacy and applications.
- `2025/Network Synergy Loop Theory.md`: explores an open system where participants interact directly without traditional aggregators.

**Candidate AgentBox requirements**
- A standardized capability/service discovery and exchange model with publisher identity, metadata, availability, price/quote, location/route where relevant, constraints and action endpoints.
- Cross-platform adapters and a canonical event/action schema for federated service composition.
- Open network participation requires trust, identity, reputation, rate limits, consent, dispute handling, revocation and clear responsibility.
- V2X and broadcast systems are specialized protocol/domain packages, not generic agent runtime functionality.

**Disposition:** interoperability and package discovery are core ecosystem themes; V2X/open broadcast are adjacent vertical/network programmes.

## 9. Domain-specific technical intelligence and industrial workflows

**Sources**
- `2025/Identifying Carbon in Products.md`: asks for a platform to identify product component lists, materials, processes and carbon emissions, with CBAM context.
- `2025/Kinaxis Replica in SAP.md`: explicitly says to build ground-up rather than use IBP; asks to compare software and combine the best features into a new product.
- `2025/ICR Accrual Automation Proposal.md`: enterprise finance automation.
- `2025/India AI models comparison.md`: model ecosystem.
- `2025/Hydranets Clarification Request.md`: multi-task learning for machine vision.
- `2025/Handwriting Tracking Device.md`: sensor/vision tracking and embedded device concepts.

**Candidate AgentBox requirements**
- Domain agent packages need typed domain ontology, data connectors, process rules, evaluation cases and domain-specific evidence sources.
- Industrial AI packages may need multimodal ingestion, sensor/time-series streams, computer vision and edge inference.
- Sustainability/CBAM workflows need component/material/process lineage, emission-factor provenance, calculation versioning and auditability.
- Planning/SCM agents need scenario models, constraints, simulation, collaboration and explainable recommendations.
- Domain packages must remain separately versioned and must not bloat the core execution kernel.

**Disposition:** strong vertical package ecosystem evidence.

## 10. Human decision support, leadership and ethical constraints

**Sources**
- `2025/Leadership and AI Ethics.md`: user says AI should identify leadership quality using responsibility, integrity, long-term impact and harm prevention, and should be difficult to game.
- `2025/Leader_s Playbook Module.md`: scenario-driven leadership development with measurable outcomes.
- `2025/Idea Acknowledgment Strategies.md`: asks how to handle ideas being used without acknowledgment in a company.

**Candidate AgentBox requirements**
- Human decision-support packages should expose evidence, uncertainty, competing interpretations and appeal/review paths.
- Evaluation of people or leadership must not rely on superficial confidence, popularity or persuasive language; criteria need transparency, context, fairness and human accountability.
- Scenario-based learning and coaching can be packaged with metrics and feedback, but should not be represented as objective psychological or leadership certification without validated evidence.

**Disposition:** governance/decision-support principles and optional learning packages; no autonomous high-impact person-ranking feature is justified by these sources alone.

## New candidate requirements

| Candidate ID | Requirement | Source anchors | Initial disposition |
|---|---|---|---|
| B007-R01 | Digital action execution with typed actions, postcondition verification and risk-tiered approvals | `2025/Large Action Models Overview.md`; `2025/IFTTT for AI Agents.md` | Core runtime |
| B007-R02 | Offline-first package/app host and network-isolated mode | `2025/Hosting 1000+ Apps Offline.md` | Core deployment profile |
| B007-R03 | Local model catalogue, download, integrity verification and hardware fit | Offline AI Models PC/Mobile files | Model/deployment plane |
| B007-R04 | Secure local storage and disconnected operation | `2025/Hosting 1000+ Apps Offline.md` | Security/runtime invariant |
| B007-R05 | Privacy-preserving compute and cryptographic agility | Homomorphic encryption and ML-HyRM files | Security extension |
| B007-R06 | Model ensemble/MoA orchestration with evidence and baseline comparison | `2025/MoA model overview.md` | Model plane |
| B007-R07 | Trigger-condition-action automation with durable events and approvals | `2025/IFTTT for UPI.md`; `2025/IFTTT for AI Agents.md` | Workflow/runtime |
| B007-R08 | Financial transaction authorization, reconciliation and audit | Multi-bank, UPI and ICR/Budget Bot files | Governed vertical connector contract |
| B007-R09 | Source-grounded assessment and knowledge applications | Mock questions, Legal AI, Legal RAG, microlearning | Knowledge/evaluation packages |
| B007-R10 | Developer agent with isolated compile/test/repair loop | CodeGpt.online, LangChain, OCR package fix files | Developer package |
| B007-R11 | OCR-to-structured-data with confidence and monetary reconciliation | OCR and Scan Sum files | Reusable document AI capability |
| B007-R12 | Offline local knowledge workspace and export organizer | GPT Organizer and Offline App files | Knowledge/experience package |
| B007-R13 | Federated service discovery and standardized action exchange | Open Map V2X and Open Broadcast files | Ecosystem interoperability |
| B007-R14 | Domain-specific industrial, sustainability, legal, SCM and finance packages | CBAM, Kinaxis, legal and SAP workflow files | Package ecosystem |
| B007-R15 | Evidence-based human decision support with fairness and appeal | Leadership and AI Ethics | Governance principles |

## Cross-batch architecture synthesis (batches 001–007)

The architecture hypothesis now needs to explicitly include these logical planes:

1. **Capability and package registry:** agents, skills, actions, tools, connectors, templates, datasets, model profiles and application packages.
2. **Authoring and composition:** agent builder, visual workflow/IFTTT, BPMN/process editor, app/code builder, rules, templates and optional DSL.
3. **Identity and governance:** user/workspace/tenant identity, policy, secret references, approvals, audit, provenance, sovereignty, privacy and trust.
4. **Action and execution runtime:** durable tasks, bounded loops, API/MCP/browser/UI actions, postcondition verification, retries, compensation and human approval.
5. **Multi-agent orchestration:** delegation, specialist selection, scoped shared state, dependency graphs and result aggregation.
6. **Model operations:** provider/model catalogue, routing, local inference, ensembles/MoA, model compatibility and evaluation.
7. **Knowledge and semantic layer:** ingestion, crawling, document/code search, RAG, memory, graph/ontology, source citations and content fingerprints.
8. **Data and process services:** schema registry, mapping/transformation, business rules, event/state machines, reconciliation and workflow simulation.
9. **Quality and evolution:** deterministic tests, evaluation profiles, benchmark evidence, feedback, experiments, bounded mutation, promotion and rollback.
10. **Offline/local/edge deployment:** signed packages, local app hosting, encrypted storage, no-network mode, local models, synchronization and later edge workers.
11. **Experience and developer surfaces:** chat, voice, accessibility, multilingual, visual builder, mobile/desktop/wearable and IDE/code workspace.
12. **Interoperability and ecosystem:** API/MCP adapters, service discovery, cross-platform exchange, publishing, marketplace, billing and package governance.
13. **Domain package portfolio:** education, legal, finance, SAP/ERP, SCM, sustainability, commerce, OCR/document AI, industrial vision, robotics and V2X.

These are logical boundaries. They do not imply 13 microservices. Keep a modular monolith/control plane initially and split components only where isolation, scaling or deployment requires it.

## Source-derived design principles reinforced

- The user repeatedly requests complete code and complete file/folder structures, and flags broken dependencies and compile errors. Delivery must include full build/test evidence, not just suggested snippets.
- Offline mode must have a real security boundary and optional network isolation, not only cached UI assets.
- Agent actions must be verifiable; successful API response is not necessarily successful business outcome.
- Financial and enterprise actions need authorization, idempotency, approval, audit and reconciliation.
- Local model catalogues must reflect real hardware constraints and model licensing.
- Domain products should reuse shared primitives and remain independently packaged.
- Preserve source chronology, user decisions and provenance; duplicate exports are not independent confirmation.

## Explicit exclusions and cautions

- General personal questions, children's diet, travel, domain-name valuation, personal debt, political explanations and unrelated image requests do not become AgentBox platform requirements.
- The user's cryptosystem proposal is not a proven secure algorithm.
- UPI/bank transaction workflows require regulated partner/API access and explicit authorization; do not infer permission from a conversation.
- The user asked for a centralized spam-reporting concept for UPI IDs/accounts; this needs accuracy, appeal, privacy and defamation safeguards if ever built as a separate product.
- OpenBroadcast/V2X and the decentralized exchange ideas are adjacent programmes, not mandatory v1 features.
- Offline hosting does not mean arbitrary third-party applications can safely execute; packages need signature, permissions, sandboxing and resource quotas.
- Leadership scoring and legal judgment evaluation are high-impact domains and require human oversight, validated evidence and appeal.

## Batch 007 conclusion

This batch adds several major concepts absent from the initial 85-file sample: **digital action models, IFTTT-style automation, a genuinely offline multi-app host, local AI model distribution, privacy-preserving computation, model ensembles, financial process agents, developer self-repair, OCR-to-finance workflows, and federated service exchange.**

The most important product-level clarification is that AgentBox must support both:
- **connected cloud agents and applications**, and
- **offline/local agents and applications with an enforceable disconnected mode**.

The same capability and package contracts should work across these environments, while the execution and security policies differ by deployment profile.

## Next

Batch 008: source paths 1,751–2,000.
