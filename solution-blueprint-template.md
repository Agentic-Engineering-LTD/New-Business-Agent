# Solution Blueprint — Customer Handover Template

A standardised template for the deliverable Agentic Engineering's project CTOs produce at the end of every 10-Day Workforce Build. Produces a 15-page max document the customer's executive team can read in 25 minutes and reference for the next 12 months.

---

## What this document is

**Name:** *Solution Blueprint — \[Customer Name\]*

**Purpose:** Hand over the agent team you've built in a way that the customer's executive team (most of whom are non-technical) can understand, govern, and operate confidently without needing further explanation from you.

**Length:** 12-15 pages. No exceptions. Longer documents get filed, not read.

**Audience:** Primary: customer CEO, COO, operations lead. Secondary: customer CTO/IT lead if they have one. Tertiary: any new hires who inherit the system in 6+ months.

**Format:** PDF, designed in \[Pages / Google Docs / Notion exported to PDF\]. Brand colours: dark navy header, single accent colour. No clip-art, no stock photography, no AI-generated illustrations.

**Voice:** Plain English. Outcomes over architecture. Specific over vague. Same voice as agentic-engineering.io — direct, founder-led, no consultancy hedging.

**When to deliver:** During the final session of the 10-Day Build, walked through page-by-page with the customer's executive sponsor. Never emailed cold.

---

## Recommended structure (9 sections, page budget shown)

| \# | Section | Page budget | Audience |
| :---- | :---- | :---- | :---- |
| 1 | Executive summary | 1 page | CEO / Board |
| 2 | What we built | 1-2 pages | Everyone |
| 3 | How each workflow runs | 3-4 pages | Operations lead |
| 4 | How you govern it | 1-2 pages | CEO, CFO |
| 5 | How you operate it day-to-day | 1 page | Ops lead |
| 6 | What we deliberately didn't automate | 1 page | CEO |
| 7 | Costs and commercials | 1 page | CFO |
| 8 | Technical architecture (appendix) | 1-2 pages | CTO if any |
| 9 | Where to grow next | 1 page | CEO |

**Total: 12-15 pages.** Anything over 15 means a section is bloated — find the cut.

---

## Section-by-section guide

### 1\. Executive Summary (1 page)

**Purpose:** The CEO reads this page only. Everything else in the document supports it.

**Must include:**

- **The business outcome.** One sentence. *"We've built a digital workforce of \[N\] AI agents that now handle \[specific workflows\], freeing \[team\] to focus on \[higher-leverage work\]."*  
- **The headline numbers.** Three at most. *"60% reduction in \[process\] hours. End-to-end completion in \[time\]. Zero errors in the \[N\]-day pilot."*  
- **The commercial summary.** *"Build delivered: £10,000 (fixed-fee). Ongoing platform: £\[X\]/month. LLM costs paid direct to providers (estimated £\[Y\]/month at current volumes)."*  
- **The governance summary.** *"You retain approval on \[N\] decision points. All agent actions are logged. Kill-switch is operational."*  
- **The next step.** *"Recommended check-in: 30 days post-handover."*

**Length:** Exactly one page. If it spills, cut.

---

### 2\. What We Built (1-2 pages)

**Purpose:** Show the agent team visually, in plain terms.

**Must include:**

- **Agent organisation diagram.** Boxes for each agent, arrows for workflow handovers, dotted boxes around the human approval points. Title each agent by JOB, not technical name. ("Customer Email Triage Agent" not "agent\_v2\_triage\_email\_handler.py").  
- **One-line role description per agent.** *"Receives inbound email, classifies by priority, drafts a response for human review, files in CRM."*  
- **The boundary.** What sits inside the agent team (in scope) and what sits outside (not touched). This protects you from scope-creep accusations and clarifies what you've actually delivered.

**Visual to include:**

```
[Manager Agent]
       ↓
   ┌───┴───┐
   ↓       ↓
[Agent A] [Agent B] ──→ [Agent C]
   ↓                       ↑
[Human approval]──────────┘
```

Use a clean diagramming tool (Whimsical, Excalidraw, or similar). Avoid technical UML — the customer doesn't read UML.

---

### 3\. How Each Workflow Runs (3-4 pages)

**Purpose:** For each workflow you've automated, walk through what now happens end-to-end.

**For each workflow, include:**

- **Workflow name** — what the customer's team would have called this internally.  
- **Trigger** — what kicks it off. *"New job posting goes live in Workable."*  
- **Step-by-step what happens** — 4-7 steps, plain English. Mark which steps are agent-driven and which require human approval. Use a simple swim-lane visual.  
- **What the human does** — explicit. *"Hiring manager approves the candidate shortlist. Two clicks. \~3 minutes per shortlist."*  
- **Failure handling** — what happens if something goes wrong. *"If the agent can't classify a candidate with confidence, the shortlist routes to manual review with the agent's flagged concerns attached."*  
- **Expected volume** — *"\~40 candidate shortlists per week at current hiring volume."*  
- **Time saved** — *"Previous manual process: \~25 minutes per shortlist. New: \~3 minutes per shortlist of human review. Net saving: \~14 hours/week."*

**Three workflows max per page.** If the build covers more than 6 workflows, split this section into two parts.

---

### 4\. How You Govern It (1-2 pages)

**Purpose:** This is the section that converts a customer from "we just bought AI" to "we have an AI strategy." Lean into it.

**Must include:**

- **The "you're the board" framing.** *"This agent team operates under your authority. Every consequential action runs through approval gates you control."* Mirror the language from your campaign and About page.  
    
- **Approval gate map.** Visual table:


| Action | Trigger threshold | Who approves | SLA |
| :---- | :---- | :---- | :---- |
| Send external email | All outbound | Operations Lead | Within 4 working hours |
| Spend over £100 | Per transaction | Finance Lead | Within 1 working day |
| New customer added | All | Account Owner | Within 2 working hours |


- **Audit logs.** Where the customer sees what's happened. Screenshot of the logging dashboard.  
    
- **Budget ceilings.** Hard caps that prevent runaway behaviour. *"The agent team will not consume more than £\[X\] in LLM costs per day. Hard stop."*  
    
- **Kill switch.** One-click stop. Document where it lives and who can use it.

**Don't include:** Technical configuration files, infrastructure-as-code, agent prompt details. None of that belongs in this document.

---

### 5\. How You Operate It Day-to-Day (1 page)

**Purpose:** The customer's operations lead opens this page every week for the first month.

**Must include:**

- **Daily checks** (5 minutes/day max). *"Glance at the dashboard for any flagged items. Approve queued actions."*  
- **Weekly checks** (15 minutes/week max). *"Review the weekly digest email. Spot-check 3 random actions."*  
- **Monthly checks** (30 minutes/month max). *"Review LLM spend vs forecast. Check agent performance metrics. Spot any patterns to flag for expansion."*  
- **The owner.** Name the person on the customer side who owns this day-to-day. (You'll have agreed this during Strategy Day; document it formally here.)  
- **When to call us back.** Explicit triggers. *"If LLM spend exceeds £\[X\]/month sustained. If error rate exceeds \[Y\]%. If you're considering expanding to a new workflow. If your team's role has materially changed and the agents need to know."*

---

### 6\. What We Deliberately Didn't Automate (1 page)

**Purpose:** This is the most strategically important section in the document. It does three things:

1. Sets the scope of what you delivered (protects against "but we expected X" arguments later).  
2. Demonstrates judgement (you're the consultant who knows what NOT to automate — directly references your Strategy Day positioning).  
3. Sets up expansion conversations (the "future backlog" naturally becomes the next engagement).

**Must include:**

- **Workflows kept human, deliberately.** Specific. *"Final negotiation calls with candidates. Custom proposals over £25K. Anything involving the Founder personally."* Plus a one-line reason for each.  
- **Workflows in the "deferred" backlog.** Things we identified in Strategy Day but didn't build because they were lower-leverage or higher-risk for this phase. *"Onboarding automation — deferred to phase 2 once the hiring agents have been in production for 90 days."*  
- **Out of scope.** Anything the customer might have assumed was included but wasn't. *"Anything beyond the recruitment workflow. CRM data migration. Existing manual processes outside hiring."*

**Phrase the section affirmatively.** Not "we ran out of time." More like *"We deliberately scoped the build to deliver maximum leverage on the highest-value workflows first. The following are protected as human-only for good reasons."*

---

### 7\. Costs and Commercials (1 page)

**Purpose:** The CFO opens this page. Clarity wins. Hedging costs you renewal trust.

**Must include:**

- **One-off costs paid.** Strategy Day fee (credited), 10-Day Build fee. Total.  
- **Ongoing monthly costs.** Platform fee from Agentic Engineering (the £499/£1,499 tier they're on). Estimated LLM costs based on the workflow volumes in Section 3\.  
- **LLM cost model.** A simple table: *"At 40 shortlists/week, estimated LLM consumption: \~£\[X\]/month. At 80 shortlists/week, estimated: \~£\[Y\]/month."* Helps the CFO sanity-check.  
- **What's included in your monthly fee.** Infrastructure, monitoring, model failover, weekly digest, \[N\] hours of customer support per month, free model upgrades when better/cheaper models become available.  
- **What's not included.** Anything that would be a separate engagement: scope expansion, new workflow builds, integration to new tools.  
- **Renewal/exit terms.** Monthly rolling. 30 days notice to exit. Your data and configuration are portable.

---

### 8\. Technical Architecture (Appendix, 1-2 pages)

**Purpose:** For the customer's CTO or IT lead if they have one. If they don't have one, this section is the page that won't be read — and that's fine.

**Must include:**

- **Stack overview.** Paperclip (open-source orchestration), LLM providers used (with customer's BYO key arrangement noted), cloud the agents run in (customer's cloud or yours), integration tools (MCP servers used, etc.).  
- **Data residency.** Where customer data is stored. UK / EU / other. GDPR implications.  
- **Security model.** API key management, secrets, access controls.  
- **Integrations list.** Every external system the agent team connects to.  
- **Monitoring and observability.** How an engineer can debug if needed.

**Voice shifts to technical here.** This is the only section in the document that uses technical language. Keep it tight — 1-2 pages, not 10\.

---

### 9\. Where to Grow Next (1 page)

**Purpose:** Sets up the next commercial conversation. Don't skip this — most consultancies leave the customer wondering "what's next" and lose the expansion opportunity.

**Must include:**

- **The next obvious workflow.** What you identified in Strategy Day as the second-priority automation that you didn't build in phase 1\. Now is when it goes back on the table.  
- **The performance trigger.** What needs to be true for the customer to consider expanding. *"Once the hiring agents have run smoothly for 60 days, the natural next step is onboarding."*  
- **Scope ladder.** Where they currently sit on your Process / Function / Department scope ladder, and what scaling up looks like. *"You're currently running 'a function.' The next phase would scale this to 'a department.'"*  
- **How to start the conversation.** *"Book a 30-min check-in call at \[link\]. We typically run a half-day scoping session at no cost to map the next phase."*

---

## Voice and formatting rules

- **No headers like "Solution Overview" or "Project Deliverables."** Those are consultancy filler. Use plain English headers that describe what's actually on the page.  
- **No bullet lists longer than 5 items.** If you need more than 5 bullets, the section needs subheadings, not more bullets.  
- **Numbers where possible.** Specific time savings, specific costs, specific volumes. Vague claims ("significant improvement") undermine trust. Specific claims build it.  
- **Every page should be standalone-useful.** A customer printing one page and showing it to a colleague should still get value.  
- **Visual elements every 2-3 pages.** A document of pure prose feels dense even if it isn't. Diagrams, tables, swim-lanes — alternate with text to keep the eye moving.

---

## Visual elements specification

Five visuals must appear in every Solution Blueprint:

1. **Agent organisation diagram** (Section 2\) — boxes, arrows, human approval points  
2. **Workflow swim-lanes** (Section 3\) — one per workflow, agent steps vs human steps  
3. **Approval gate map** (Section 4\) — table format, action / threshold / approver / SLA  
4. **Cost model table** (Section 7\) — volumes mapped to monthly costs  
5. **Scope ladder** (Section 9\) — where they are, where they could grow

Use the same visual language across every blueprint so customers (and you) can pattern-match across engagements.

---

## Pre-delivery checklist

Before handing the document over, the project CTO confirms:

- [ ] Customer name spelled correctly on every page (it's always the typo that gets noticed)  
- [ ] Headline numbers (Executive Summary) match the actual measured performance in the build  
- [ ] All approval gate owners are real named people who've consented to the responsibility  
- [ ] Cost model has been sanity-checked against the actual LLM spend in the build period  
- [ ] "Where to grow next" section has a specific named workflow, not a generic suggestion  
- [ ] Kill-switch is operational and the customer has tested it  
- [ ] Document is under 15 pages  
- [ ] No clip-art, stock photography, or AI-generated illustration anywhere  
- [ ] Page 1 (Executive Summary) reads cleanly on its own — would still be useful if the rest of the document were lost  
- [ ] Delivery is scheduled as a walked-through session, not an email attachment

---

## One philosophical note for project CTOs

The customer is paying for the build. The document is paying for the renewal.

Consultancies that produce thick, technical, opaque handovers train their customers to need them forever, which feels like a moat but actually creates resentment and churn risk. The Agentic Engineering approach is the opposite: produce a document so clear that the customer feels in control of what they bought. *That's* what makes them come back for the next phase — because they trust they could leave any time and choose to stay.

The Solution Blueprint isn't just a deliverable. It's the artefact that proves we operate under the "you're the board, the agents are the workforce" philosophy.  
