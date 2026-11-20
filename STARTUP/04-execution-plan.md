# HujjatAI Execution Plan

## Timeline Summary (Gantt-Style)

```
Month:        1         2         3         4         5         6         7         8         9        10        11        12
Week:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48
PHASE 1: VALIDATION
  Customer interviews    [========]
  IT Park registration   [==============]
  Legal entity (LLC)        [======]
  Prototype/mockups         [======]
  LOI collection               [======]
  Hire ML engineer               [======]

PHASE 2: BUILD MVP
  Backend foundation               [======]
  OCR pipeline                        [======]
  NLP extraction                         [======]
  1C integration                            [======]
  Web interface                                [======]
  Hire frontend dev                [======]
  Beta testing                                    [========]

PHASE 3: LAUNCH
  Beta onboarding                                       [======]
  Pricing validation                                       [====]
  Support/feedback                                      [========]
  Marketing channels                                       [======]

PHASE 4: GROWTH
  Scale acquisition                                               [========================]
  Feature expansion                                               [========================]
  Team scaling                                                       [====================]
  Partnership dev                                                 [========================]

PHASE 5: SCALE
  Regional prep                                                                              [================]
  Fundraising                                                                                   [============]
  Team to 15                                                                                 [================]
```

## Budget Summary

| Phase | Duration | Spend | Cumulative |
|-------|----------|-------|------------|
| Phase 1: Validation | Weeks 1-4 | $3,200 | $3,200 |
| Phase 2: Build MVP | Weeks 5-12 | $14,800 | $18,000 |
| Phase 3: Launch | Weeks 13-16 | $6,500 | $24,500 |
| Phase 4: Growth | Months 5-9 | $42,000 | $66,500 |
| Phase 5: Scale | Months 10-12+ | $48,000 | $114,500 |

**Phases 1-3 fit within the $30K starting capital.** Phase 4+ requires revenue (projected $5K-15K/month by Month 5) and/or seed funding from IT Park Ventures ($150-200K).

---

## Phase 1: Validation (Weeks 1-4)

**Objective:** Confirm willingness to pay, validate core assumptions, and establish legal/operational foundation.

**Total Phase Cost: $3,200**

### 1.1 Customer Discovery Interviews

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 1-2 (10 business days) |
| Cost | $200 (transportation, coffee meetings, small gifts for interviewees) |
| Target | 15 interviews completed |

**Who to interview:**
- 8 chief accountants at companies with 100-300 employees (sweet spot)
- 3 chief accountants at companies with 300-500 employees (upmarket validation)
- 2 heads of accounting firms that serve multiple SMBs
- 2 1C implementation partners (channel validation)

**Where to find them:**
- Telegram group "Buxgalteriya UZ" (~8K members): post asking for 30-minute paid interviews ($10-15 per interview in Uzbek context is generous)
- Ask 1C partners (Rarus Tashkent, Softline Uzbekistan) for introductions to their clients
- Personal network: every Uzbek entrepreneur knows 2-3 chief accountants
- LinkedIn Uzbekistan: search "bosh hisobchi" or "glavnyy bukhgalter"

**Falsifiable hypotheses to test:**

| # | Hypothesis | Kill Criteria |
|---|-----------|---------------|
| H1 | Chief accountants spend 3+ hours/day on manual document data entry | Fewer than 8/15 confirm this time commitment |
| H2 | They would pay $100-200/month for a tool that cuts this by 70% | Fewer than 6/15 say "yes" or "probably" at $150/month price point |
| H3 | 1C export compatibility is a hard requirement (not nice-to-have) | Fewer than 12/15 name 1C integration as essential |
| H4 | Mixed-script documents (Uzbek Latin + Russian) are a daily problem | Fewer than 10/15 report dealing with mixed-script documents weekly |
| H5 | The chief accountant has budget authority for tools under $200/month | Fewer than 10/15 can approve this spend without director involvement |

**Interview script (core questions):**

1. "Walk me through what happens when a stack of invoices arrives on your desk. What do you do first?"
2. "How many documents does your team process per week? Per month?"
3. "What percentage are in Uzbek Latin vs. Russian vs. mixed?"
4. "What is the most time-consuming part of getting invoice data into 1C?"
5. "Have you tried any tools to automate this? What happened?"
6. "If a tool could extract all invoice fields and generate a ready-to-import 1C file, what would that be worth to you monthly?"
7. "Who would need to approve a $150/month software purchase in your company?"
8. "What would make you NOT trust such a tool?" (surfaces adoption barriers)
9. "If I built this and gave you free access for a month, would you test it with real documents?"
10. "Can you show me 5 recent invoices so I can see the formats you deal with?" (collect sample documents)

**Success criteria:** 10+ of 15 interviewees confirm H1-H4. At least 5 express strong willingness to pay. Collect 50+ sample document images.

**Decision gate:** If fewer than 6/15 express willingness to pay at $100/month, STOP. Pivot or abandon.


### 1.2 IT Park Registration

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 1-4 (runs in parallel with interviews; approval takes 2-4 weeks) |
| Cost | $0 (no registration fee) |

**Process:**

1. **Week 1, Day 1-2:** Prepare application package:
   - Business plan (2-3 pages describing the AI/software product)
   - Founder CV/resume
   - Copy of passport
   - Proposed company name (check availability at my.gov.uz)
   - Description of IT services to be provided (must qualify as "software development" or "IT services")

2. **Week 1, Day 3:** Submit application online at itpark.uz/register. Upload all documents in PDF format.

3. **Week 2:** IT Park commission reviews application. They check:
   - Is this genuinely an IT/software company? (Yes: document AI SaaS)
   - Does it create jobs in Uzbekistan? (Yes: plan to hire 3-5 engineers)
   - Is the product exportable or import-substituting? (Both: replaces foreign tools, applicable to regional markets)

4. **Weeks 3-4:** Receive approval notification. Typical timeline is 10-15 business days.

5. **Upon approval:** Receive IT Park resident certificate. This certificate is required for LLC registration with tax benefits.

**Benefits received:**
- 0% corporate income tax (until 2040)
- 0% social fund payments for employees
- 7.5% personal income tax (vs. standard 12%)
- Access to IT Park co-working space in Tashkent ($0 for first 6 months)
- Eligibility for IT Park Ventures funding ($50K-500K seed rounds)
- Simplified visa process for foreign hires

**Risk:** Application rejected (rare for genuine IT companies). Mitigation: the description must emphasize AI/ML and software, not "consulting" or "services."

### 1.3 Legal Entity Formation (LLC)

| Attribute | Detail |
|-----------|--------|
| Owner | Founder + lawyer |
| Timeline | Weeks 2-3 (start after IT Park application submitted) |
| Cost | $500 (lawyer fee $300, notary $100, misc fees $100) |

**Steps:**

1. Reserve company name at my.gov.uz ($0, instant)
2. Draft charter (ustav) -- lawyer handles this. Standard IT company template exists.
3. Open temporary bank account for charter capital deposit. Minimum charter capital: 400,000 UZS (~$32). Deposit the minimum.
4. Notarize charter and founder's decision ($100)
5. Register at tax authority through my.gov.uz single-window system (1-3 business days)
6. Receive company TIN (INN) and registration certificate
7. Open permanent bank account (recommend Kapitalbank or Hamkorbank -- both have good online banking)
8. Register for VAT (mandatory if annual revenue exceeds 1 billion UZS / ~$80K)
9. Link IT Park resident status to the LLC (submit certificate to tax authority)

**Lawyer recommendation:** Use an IT-specialized lawyer. IT Park maintains a list of recommended legal advisors. Budget $300 for full LLC formation package.

### 1.4 Prototype and Mockup Testing

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 2-3 |
| Cost | $0 (use Figma free tier + real API calls on founder's accounts) |

**Deliverables:**

1. **Clickable Figma prototype** of the core flow: upload document > see extracted fields > correct errors > export to 1C. Show to interview subjects in Week 3-4 follow-ups.

2. **Technical proof-of-concept:** Take 10 real sample invoices (collected during interviews). Run through Google Cloud Vision API + GPT-4o-mini extraction prompt. Measure:
   - What percentage of fields extract correctly?
   - Where does Uzbek Latin script fail?
   - What is the end-to-end latency?

   This costs <$1 in API calls and validates the core technical assumption before spending on development.

3. **1C export test:** Generate one XML import file manually from extracted data. Import into a test 1C installation (ask a 1C partner for access to a demo environment). Confirm the format works.

**Success criteria:** Prototype resonates in follow-up conversations. POC achieves 80%+ accuracy on sample invoices. 1C import works on at least one configuration.

### 1.5 Letter of Intent (LOI) Collection

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 3-4 |
| Cost | $0 |

**Target:** 3-5 signed LOIs from companies committing to:
- Pay $75/month (founding customer 50% discount from $150 standard price) for 12 months
- Provide real documents for testing during beta
- Give 30 minutes/week of feedback time

**LOI format:** Simple one-page document (not legally binding but demonstrates serious intent). Include: company name, signatory (chief accountant), agreed price, start date conditional on product readiness.

**Why this matters:** De-risks Phase 2 spending. If you cannot get 3 companies to sign a non-binding LOI at $75/month, the demand hypothesis is wrong. Stop before spending $15K on development.

**Decision gate:** Fewer than 3 LOIs after 15 interviews = revisit pricing, positioning, or target segment before proceeding to Phase 2.

### 1.6 Hire ML Engineer (Start Search)

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 3-4 (search); hire starts Week 5 |
| Cost | $500 (two weeks of part-time trial tasks before full commitment) |

**Role:** ML/Backend Engineer (first hire)

**Requirements:**
- Strong Python (FastAPI, async programming)
- Experience with at least one: computer vision, NLP, or document processing
- Comfortable with cloud APIs (GCP, AWS)
- Uzbek or Russian speaker (for understanding document content)
- Based in Tashkent (or willing to relocate)

**Where to find:**
- IT Park University career board (graduates earn $800-1,200/month starting)
- INHA University in Tashkent CS department (Korean-Uzbek university, strong technical program)
- Telegram group "AI Uzbekistan" (~3K members): post job description
- HeadHunter.uz (primary job board in Uzbekistan)
- LinkedIn: search "machine learning" + "Tashkent"
- Referrals from IT Park community

**Compensation:** $1,500-2,000/month for junior-mid level (2-4 years experience). $2,000-2,500/month for senior (5+ years). With IT Park benefits, total employer cost is only 7.5% above salary (no social fund).

**Hiring process:**
1. Post job description (Week 3, Day 1)
2. Screen resumes (3-5 days, expect 20-40 applications)
3. Technical assessment: give candidates a real task -- "take this invoice image, use Google Cloud Vision API to extract text, then use GPT-4o-mini to extract vendor name and total amount. Return structured JSON." Pay $50 for completed assessment.
4. Top 2 candidates get 1-week paid trial ($250 each) working on the actual POC pipeline
5. Hire the better performer. Start full-time Week 5.


---

## Phase 2: Build MVP (Weeks 5-12)

**Objective:** Build a functional product that 5 customers can use for real invoice processing. Ship quality over scope.

**Total Phase Cost: $14,800**
- ML engineer salary: $3,000-4,000 (8 weeks at $1,500-2,000/month prorated)
- Frontend developer salary: $1,600-2,400 (8 weeks at $800-1,200/month prorated, starts Week 7)
- Infrastructure (AWS): $1,200 (8 weeks at $150/month dev environment, scaling up in Week 9)
- API costs (Google Vision + OpenAI for testing): $200
- 1C partner consulting: $500 (integration testing and format validation)
- Accountant consultant (part-time domain expert): $800 (8 weeks at $100/month)
- Contingency: $2,000

### 2.1 Backend Foundation (Weeks 5-6)

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Weeks 5-6 |
| Cost | Included in salary |

**Deliverables:**
- FastAPI application scaffold with project structure, config management, logging
- PostgreSQL database schema: users, companies, documents, extractions, corrections
- File upload endpoint with S3 (or MinIO) storage integration
- Celery + Redis task queue for async document processing
- Basic authentication (JWT tokens, email/password)
- Docker Compose setup for local development
- CI pipeline on GitHub Actions (lint, test, build)

**Tech decisions locked:**
- Python 3.11+, FastAPI 0.100+
- PostgreSQL 15 with SQLAlchemy ORM
- Alembic for migrations
- pytest for testing
- Pydantic v2 for data validation

### 2.2 OCR Pipeline (Weeks 6-7)

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Weeks 6-7 (overlaps with backend foundation) |
| Cost | Google Cloud Vision API testing: ~$50 |

**Deliverables:**
- Document preprocessing: deskew, denoise, binarization (OpenCV)
- Script detection per text block (Cyrillic vs. Latin classifier, simple rule-based using Unicode ranges)
- Google Cloud Vision API integration for OCR
- Text block segmentation and ordering (top-to-bottom, left-to-right)
- OCR result caching (same document hash = skip re-processing)
- Accuracy logging: store raw OCR output alongside final extraction for quality tracking

**Accuracy target:** 95%+ character-level accuracy on printed invoices scanned at 200+ DPI. 85%+ on phone camera captures.

### 2.3 NLP/Field Extraction (Weeks 7-8)

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Weeks 7-8 |
| Cost | OpenAI API testing: ~$50 |

**Deliverables:**
- GPT-4o-mini prompt engineering for structured field extraction from OCR text
- Extraction schema: vendor_name, vendor_tin, invoice_number, invoice_date, line_items[], total_amount, vat_amount, currency
- Confidence scoring per field (based on prompt output + heuristic validation)
- Template matching: after 10+ documents from same vendor, learn field positions and switch to rule-based extraction
- Validation rules: TIN format check (9 digits), amount consistency (line items sum to total), date format normalization
- Fallback logic: if GPT-4o-mini confidence is low, flag for human review rather than guessing

**Prompt strategy:** Few-shot prompting with 5-10 example invoice extractions. System prompt specifies Uzbek/Russian document context and expected output JSON schema. Temperature = 0 for deterministic extraction.

### 2.4 1C Integration (Weeks 8-9)

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer + 1C consultant |
| Timeline | Weeks 8-9 |
| Cost | $500 (1C partner consulting) |

**Deliverables:**
- XML export generator for 1C:Enterprise 8.3 Buxgalteriya configuration
- Mapping layer: extracted fields to 1C chart of accounts (configurable per customer)
- Support for "Postupleniye tovarov i uslug" (goods/services receipt) document type in 1C
- Export validation: generated XML passes 1C import without errors
- Testing on 3 different 1C installations (partner provides access to client test environments)

**1C partner:** Engage one Tashkent-based 1C:Franchisee (there are ~200 in Uzbekistan). Offer them referral commission ($50/customer they bring) in exchange for:
- Access to test 1C environments
- Validation of XML import format
- Introduction to their client base (Phase 3)

**Target partner firms:** Rarus Tashkent, Softline Uzbekistan, or smaller local partners (more responsive, more motivated by referral fees).

### 2.5 Hire Frontend Developer (Week 5-6 search, starts Week 7)

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Search in Weeks 5-6, start Week 7 |
| Cost | $800-1,200/month |

**Role:** Frontend Developer

**Requirements:**
- Next.js + TypeScript (2+ years)
- React component libraries (Tailwind CSS, shadcn/ui preferred)
- Responsive web design
- Basic understanding of REST APIs
- Uzbek or Russian speaker

**Where to find:**
- Same channels as ML engineer (IT Park, INHA, HeadHunter.uz)
- Telegram group "Frontend Uzbekistan"
- Freelance platforms (Upwork) for initial trial if local search is slow

**Compensation:** $800-1,200/month for mid-level. $1,200-1,500/month for senior. Junior ($500-700) acceptable if strong portfolio.

### 2.6 Web Interface (Weeks 9-11)

| Attribute | Detail |
|-----------|--------|
| Owner | Frontend Developer |
| Timeline | Weeks 9-11 |
| Cost | Included in salary |

**Deliverables:**
- Document upload page: drag-drop, batch upload (up to 20 files), progress indicator
- Processing queue view: status per document (processing, ready, error)
- Extraction review page: original document image on left, extracted fields on right, inline editing
- Confidence indicators: green (high), yellow (medium), red (low) per field
- 1C export button: download XML file or copy to clipboard
- Correction submission: user edits feed back to extraction improvement pipeline
- Dashboard: documents processed this month, accuracy rate, time saved estimate
- Auth flows: login, register, password reset, invite team member
- Company settings: logo, name, 1C configuration mapping

**UX principles:**
- Chief accountants are not technical. Zero jargon in the UI.
- Three-click workflow: upload > review > export. Nothing else required.
- Uzbek language interface (with Russian toggle). No English.
- Works on 1366x768 screens (standard office monitor resolution in Uzbekistan)

### 2.7 Beta Testing (Weeks 11-12)

| Attribute | Detail |
|-----------|--------|
| Owner | Founder + ML Engineer |
| Timeline | Weeks 11-12 |
| Cost | $200 (customer site visits, minor infrastructure scaling) |

**Process:**
1. Onboard 3-5 LOI customers (from Phase 1) onto the live system
2. Each customer uploads 20-50 real invoices in first week
3. Founder sits with chief accountant during first session (in person or screen-share)
4. Track: accuracy per customer, correction frequency, time-to-export, user confusion points
5. Daily bug fixes and accuracy improvements based on real document failures
6. End of Week 12: each customer has processed 50+ documents successfully

**Success criteria:**
- 3+ customers actively using the product by end of Week 12
- 85%+ extraction accuracy on their actual invoices (90% target, 85% minimum acceptable)
- Average processing time under 30 seconds
- 1C export works on each customer's specific installation
- No critical bugs (data loss, incorrect extraction posted to 1C)

**Decision gate:** If accuracy is below 80% after two weeks of tuning, extend Phase 2 by 2 weeks (budget allows). If below 70%, fundamental technical approach needs revision.


---

## Phase 3: Launch (Weeks 13-16)

**Objective:** Convert beta users to paying customers. Onboard 10 total paying customers. Validate pricing. Establish support workflow.

**Total Phase Cost: $6,500**
- ML engineer salary: $3,000-4,000 (4 weeks)
- Frontend developer salary: $1,600-2,400 (4 weeks)
- Infrastructure (production): $600 (scaling to handle 10 customers)
- Marketing/acquisition: $500 (Telegram ads, 1C partner events)
- Legal (data processing agreement template): $300

### 3.1 Beta-to-Paid Conversion

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Week 13 |
| Cost | $0 |

**Process:**
1. Meet each beta customer in person. Show them their usage data (documents processed, time saved, accuracy achieved).
2. Present pricing: "You have been using this free. Starting next month, it is $75/month (founding customer price, normally $150). You keep this price for 12 months."
3. Get signed service agreement and first payment (bank transfer or Uzcard/Humo payment).
4. Target: convert 3-5 of beta customers to paid.

**If conversion is low (fewer than 3):** The problem is either accuracy (product issue) or perceived value (positioning issue). Conduct exit interviews with non-converters. Extend free period by 2 weeks while fixing top complaints.

### 3.2 Pricing Validation

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 13-14 |
| Cost | $0 |

**Pricing tiers (test these):**

| Tier | Monthly Price | Included | Target Customer |
|------|--------------|----------|-----------------|
| Starter | $50/month | 500 documents/month | 50-100 employee companies |
| Professional | $150/month | 2,000 documents/month | 100-300 employee companies |
| Enterprise | $300/month | 5,000 documents/month + priority support | 300-500 employee companies |

**Founding customer pricing:** 50% off for first 12 months for first 10 customers. They get locked at $75/month (Professional tier equivalent).

**Validation method:** Present all three tiers to new prospects (not beta customers). Track which tier they gravitate toward. If 80%+ choose Starter, the Professional tier is overpriced. If 50%+ choose Enterprise, raise all prices.

**Payment methods:** Bank transfer (primary for B2B in Uzbekistan), Uzcard/Humo (local payment cards), Payme/Click (mobile payment apps). Set up merchant account with Payme ($50 setup, 1.5% transaction fee).

### 3.3 New Customer Acquisition (to reach 10 total)

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Weeks 13-16 |
| Cost | $500 |

**Channels:**

1. **1C partner referrals (primary):** The 1C partner from Phase 2 introduces HujjatAI to their existing clients during regular support visits. Offer $50 referral bonus per converted customer. Target: 3-5 customers from this channel.

2. **Telegram group outreach:** Post case study from beta customers (anonymized) in "Buxgalteriya UZ" and "1C Uzbekistan" groups. Include short video demo (screen recording, 2 minutes). Target: 2-3 inbound inquiries.

3. **Direct outreach:** Call/visit 10 companies identified during Phase 1 interviews who expressed interest but did not sign LOIs. Offer free 2-week trial. Target: 2-3 conversions.

4. **IT Park community:** Present at IT Park demo day or networking event. Get introductions to other IT Park residents who might have accounting departments as customers. Target: 1-2 customers.

**Not doing yet:** Paid ads, SEO, content marketing, cold email. These are premature at 10 customers. Direct relationships and referrals only.

### 3.4 Onboarding Process

| Attribute | Detail |
|-----------|--------|
| Owner | Founder (first 10 customers personally) |
| Timeline | Ongoing from Week 13 |
| Cost | $0 (founder time) |

**Standard onboarding (45 minutes per customer):**

1. **Pre-session (5 min):** Create customer account, configure company name and 1C version
2. **Demo call or visit (30 min):** Share screen. Upload 3 of their actual invoices. Show extraction results. Let them correct any errors. Export to 1C. Import into their 1C (they share screen for this part).
3. **Post-session (10 min):** Send login credentials. Share Telegram support chat invite. Schedule 1-week check-in.
4. **Week 1 check-in (15 min):** "How many documents did you process? Any issues? What accuracy are you seeing?"

**Why founder does this personally:** Every onboarding reveals product gaps, UX confusion, and new document formats. This information is gold for the engineering team. Stop personal onboarding only after 20+ customers when patterns are clear enough to document.

### 3.5 Support Setup

| Attribute | Detail |
|-----------|--------|
| Owner | Founder + ML Engineer (rotate) |
| Timeline | Week 13 onward |
| Cost | $0 (founder/engineer time) |

**Support channels:**
- Primary: Telegram group chat per customer (chief accountant + HujjatAI team). This is how Uzbek businesses communicate.
- Secondary: Email for formal issues (invoicing, contracts, account problems)
- Not yet: Phone support, ticketing system. Premature at 10 customers.

**SLA (communicated to customers):**
- Response time: 2 hours during business hours (9am-6pm Tashkent time, Monday-Friday)
- Critical bugs (data loss, incorrect 1C export): fix within 24 hours
- Accuracy complaints: investigate within 48 hours, retrain/fix within 1 week

**Feedback collection:** At end of each week, ask in Telegram: "What was the most annoying thing about HujjatAI this week?" Track responses in a spreadsheet. Prioritize fixes by frequency.

### 3.6 Legal and Compliance

| Attribute | Detail |
|-----------|--------|
| Owner | Founder + lawyer |
| Timeline | Week 13 |
| Cost | $300 |

**Deliverables:**
- Service agreement template (between HujjatAI LLC and customer)
- Data processing agreement (DPA) per Uzbek Personal Data Law
- Privacy policy for web application
- Terms of Service
- Register as data processor with State Inspectorate for Personal Data Protection (filing only, no fee)


---

## Phase 4: Growth (Months 5-9)

**Objective:** Scale from 10 to 50+ paying customers. Expand features. Build the data moat. Reach $10K+ MRR.

**Total Phase Cost: $42,000** (offset by revenue starting Month 5)
- ML engineer salary: $10,000-12,500 (5 months at $2,000-2,500, raise after Phase 3 performance)
- Frontend developer salary: $5,000-7,500 (5 months at $1,000-1,500, raise)
- New hire: Customer Success / Sales (starts Month 6): $4,000-6,000 (4 months at $1,000-1,500)
- Infrastructure (scaling): $3,500 (average $700/month for 50 customers)
- API costs at scale: $500 (50K pages/month)
- Marketing budget: $2,000 ($400/month)
- 1C partner commissions: $2,500 (50 customers x $50)
- Office/co-working: $1,500 (IT Park space becomes paid after Month 6, ~$300/month)
- Contingency: $3,000

**Revenue projection for this phase:**

| Month | Paying Customers | Avg Revenue/Customer | MRR |
|-------|-----------------|---------------------|-----|
| 5 | 10 | $100 | $1,000 |
| 6 | 18 | $110 | $1,980 |
| 7 | 28 | $120 | $3,360 |
| 8 | 38 | $125 | $4,750 |
| 9 | 50 | $130 | $6,500 |

**Cumulative revenue Months 5-9: ~$17,600.** Net burn for Phase 4: ~$24,400 ($42K spend - $17.6K revenue). Covered by remaining capital ($5,500 from initial $30K) plus early revenue. Gap of ~$19K requires either: (a) faster revenue ramp, (b) IT Park Ventures seed round, or (c) founder investment.

### 4.1 Scale Customer Acquisition

| Attribute | Detail |
|-----------|--------|
| Owner | Founder (Months 5-6), then Customer Success hire (Month 7+) |
| Timeline | Months 5-9 continuous |
| Cost | $2,500 (commissions) + $2,000 (marketing) |

**Channel expansion:**

| Channel | Investment | Expected Customers | CAC |
|---------|-----------|-------------------|-----|
| 1C partner network (expand to 3-5 partners) | $50/referral | 25-30 | $50 |
| Telegram group marketing (case studies, demos) | $200/month content creation | 5-10 | $100 |
| Accountant conference presence (2 events) | $500/event | 5-8 | $75 |
| Word-of-mouth from existing customers | $0 | 5-10 | $0 |
| Direct outreach (warm leads from Phase 1-3) | Founder time | 3-5 | $0 |

**Acquisition target:** 8-10 new customers per month by Month 7.

**Key activities:**
- Sign 3-5 additional 1C partners as referral channels (Months 5-6)
- Publish 2 case studies per month in Telegram groups (real numbers: "Company X reduced invoice processing time by 75%")
- Attend ICTWEEK Uzbekistan conference (annual, usually September) with demo booth ($500)
- Attend 1C partner annual gathering in Tashkent with short presentation slot

### 4.2 Feature Expansion

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer + Frontend Developer |
| Timeline | Months 5-9 (one major feature per month) |
| Cost | Included in salaries |

**Feature roadmap (prioritized by customer demand from Phase 3 feedback):**

| Month | Feature | Rationale |
|-------|---------|-----------|
| 5 | Waybill (TTN) extraction | Second most common document type after invoices; 60% of customers requested it |
| 6 | Batch processing improvements (upload 50+ files, background processing with email notification) | Customers want to dump a day's worth of scans and come back later |
| 7 | Vendor management (auto-categorize by vendor, show processing history per vendor) | Reduces repeat corrections; surfaces template learning benefit |
| 8 | Analytics dashboard (processing volume trends, accuracy over time, cost savings report) | Helps chief accountants justify continued spend to directors |
| 9 | API access (REST API for 1C partners to integrate directly) | Enables 1C partners to embed HujjatAI in their solutions; new revenue channel |

**What stays OUT until Phase 5:** Mobile app, contract extraction, tax form auto-filing, multi-company support, on-premise deployment.

### 4.3 Accuracy Improvement

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Ongoing, Months 5-9 |
| Cost | Included in salary + $200/month additional GPU compute for training |

**Targets:**
- Month 5: 92% accuracy on seen templates, 80% on unseen
- Month 7: 95% on seen templates, 87% on unseen
- Month 9: 97% on seen templates, 90% on unseen

**How:**
- Customer corrections provide labeled training data (5,000+ examples by Month 6)
- Fine-tune PaddleOCR on Uzbek Latin script (requires collected dataset of 10K+ labeled characters)
- Implement template learning: after 10 documents from same vendor, switch to rule-based extraction (faster, cheaper, more accurate)
- Begin training custom extraction model (Qwen2.5-7B fine-tune) to reduce OpenAI API dependency
- A/B test extraction approaches: GPT-4o-mini vs. fine-tuned model on same documents

### 4.4 Hire Customer Success / Sales

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Month 6 (search Month 5, start Month 6) |
| Cost | $1,000-1,500/month |

**Role:** Customer Success + Sales (combined role at this stage)

**Responsibilities:**
- Onboard new customers (take over from founder)
- Weekly check-ins with existing customers
- Handle support escalations (Telegram groups)
- Visit prospects, demo the product, close deals
- Collect feedback systematically

**Profile:**
- 2-3 years experience in B2B software sales or customer success in Uzbekistan
- Fluent Uzbek and Russian
- Understands accounting basics (does not need to be an accountant)
- Comfortable with technology (can demo software, troubleshoot basic issues)
- Has own transportation (customer visits across Tashkent)

**Where to find:**
- HeadHunter.uz: search "менеджер по работе с клиентами" or "sales manager IT"
- IT Park community: people who joined IT startups but want more customer-facing roles
- 1C partner companies: someone who already knows the accounting software market

**Compensation:** $1,000-1,500/month base + 10% commission on new customer revenue for first 3 months of that customer's subscription.

### 4.5 Partnership Development

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Months 5-9 |
| Cost | $500 (partnership events, meals) |

**Target partnerships:**

| Partner Type | Specific Targets | Value to HujjatAI | Offer to Partner |
|---|---|---|---|
| 1C implementation firms | Rarus, Softline, 3-5 local firms | Customer access, credibility | $50/referral + co-branded marketing |
| Accounting associations | "Auditorlar palatasi" (Chamber of Auditors) | Event access, member directory | Free tool for association members (trial) |
| IT Park ecosystem | Other IT Park residents building enterprise tools | Cross-referrals, shared learnings | Reciprocal referrals |
| Hardware vendors | Scanner/MFP distributors (Xerox, Canon dealers in Tashkent) | Bundle scanning hardware + HujjatAI | Revenue share or referral fee |

**Priority:** 1C partners are the single most important channel. Every 1C partner serves 20-100 companies. One good partnership can deliver 10+ customers.

### 4.6 Infrastructure Scaling

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Month 5 (setup), ongoing maintenance |
| Cost | $700/month average |

**Scaling plan:**

| Customers | Monthly Docs | Infrastructure Needs | Monthly Cost |
|-----------|-------------|---------------------|--------------|
| 10-20 | 5K-15K | t3.medium API + spot GPU + RDS small | $400 |
| 20-35 | 15K-40K | t3.large API + reserved GPU + RDS medium | $600 |
| 35-50 | 40K-75K | t3.xlarge API + dedicated GPU + RDS medium | $900 |

**Key scaling decisions:**
- Month 6: Move from spot to reserved GPU instance (if processing volume requires consistent availability)
- Month 7: Implement document processing queue prioritization (paid tiers process first)
- Month 8: Add read replica for PostgreSQL (dashboard queries should not slow down processing)
- Month 9: Evaluate self-hosted ML models vs. continued API usage (cost crossover analysis)


---

## Phase 5: Scale (Months 10-12+)

**Objective:** Reach 100+ customers and $15K+ MRR. Prepare for regional expansion. Raise seed round. Build team to 10-15 people.

**Total Phase Cost: $48,000** (3 months; fully covered by revenue + fundraising)
- Engineering team (5 people): $25,000 (3 months at ~$8,300/month total)
- Sales/CS team (2 people): $7,500 (3 months)
- Operations/admin (1 person): $3,000 (3 months)
- Infrastructure at scale: $4,500 ($1,500/month for 100+ customers)
- Marketing budget: $3,000 ($1,000/month)
- Legal/compliance (regional expansion prep): $2,000
- Office space: $1,500 (3 months)
- Contingency: $1,500

**Revenue projection:**

| Month | Paying Customers | Avg Revenue/Customer | MRR |
|-------|-----------------|---------------------|-----|
| 10 | 65 | $135 | $8,775 |
| 11 | 80 | $140 | $11,200 |
| 12 | 100 | $145 | $14,500 |

**Cumulative revenue Months 10-12: ~$34,500.** Phase 5 is cash-flow neutral or positive.

### 5.1 Team Scaling

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Months 10-12 |
| Cost | Included in Phase 5 personnel budget |

**Target team structure by Month 12:**

| Role | Count | Monthly Salary | Status |
|------|-------|---------------|--------|
| Founder/CEO | 1 | $2,000 (start taking salary) | Existing |
| ML Engineer (senior) | 1 | $2,500 | Existing (raised from Phase 2) |
| Backend Developer | 1 | $1,500 | New hire Month 10 |
| Frontend Developer | 1 | $1,500 | Existing (raised) |
| Mobile Developer (React Native) | 1 | $1,500 | New hire Month 11 |
| Customer Success Manager | 1 | $1,500 | Existing (raised) |
| Sales Manager | 1 | $1,200 + commission | New hire Month 10 |
| QA/Document Analyst | 1 | $800 | New hire Month 11 (reviews extraction quality) |
| Operations/Admin | 1 | $700 | New hire Month 12 |
| **Total** | **9** | **$13,700/month** | |

**Hiring priorities by month:**
- Month 10: Backend Developer (handle feature velocity), Sales Manager (dedicated outbound)
- Month 11: Mobile Developer (camera capture feature), QA/Document Analyst (quality at scale)
- Month 12: Operations/Admin (invoicing, HR, office management)

### 5.2 Regional Expansion Preparation

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Months 10-12 |
| Cost | $2,000 (legal research, market assessment, travel) |

**Target markets (in priority order):**

| Market | Why | TAM | Entry Complexity |
|--------|-----|-----|-----------------|
| Kazakhstan | Largest Central Asian economy. Also transitioning Kazakh from Cyrillic to Latin. 1C dominant. | $50M+ | Medium (different regulations, but similar document formats) |
| Kyrgyzstan | Small market but nearly identical to Uzbekistan (1C, Russian/Kyrgyz mix, similar company sizes) | $5M | Low (minimal localization needed) |
| Tajikistan | Smaller market, Tajik-Russian mix, 1C used | $3M | Low-medium |

**Preparation tasks:**
- Month 10: Research Kazakhstan document formats, tax regulations, and 1C configurations specific to KZ
- Month 11: Identify 1C partners in Almaty and Astana. Initial conversations about partnership.
- Month 12: Collect 50 sample Kazakh invoices. Test existing OCR pipeline on Kazakh Latin + Cyrillic.
- Month 12: Legal assessment of data protection requirements in Kazakhstan (more strict than Uzbekistan)

**Do not:** Open an office, hire locally, or spend meaningful money on expansion until Uzbekistan is profitable and growing steadily. Regional expansion is a Month 13-18 activity. Phase 5 is preparation only.

### 5.3 Fundraising

| Attribute | Detail |
|-----------|--------|
| Owner | Founder |
| Timeline | Months 10-12 |
| Cost | $500 (pitch materials, travel to investor meetings) |

**Fundraising target:** $150,000-300,000 seed round

**Use of funds:**
- 50% engineering team expansion (accelerate product development)
- 25% sales and marketing (paid acquisition, events, content)
- 15% regional expansion (Kazakhstan market entry)
- 10% buffer

**Target investors:**

| Investor | Type | Check Size | Why Relevant |
|----------|------|-----------|--------------|
| IT Park Ventures | Government-backed VC | $50K-500K | Mandate to fund IT Park residents. Easiest first check. |
| Sturgeon Capital | Central Asia-focused VC (London) | $200K-2M | Invested in Uzbek startups before. Understands the market. |
| Uzum Ventures | Corporate VC (Uzum ecosystem) | $100K-500K | Strategic interest in B2B fintech/accounting tools |
| 500 Global | Global accelerator | $150K (standard terms) | Has invested in Central Asian startups |

**Fundraising preparation (Months 10-11):**
- Build pitch deck (10-12 slides): problem, solution, traction, market, team, financials, ask
- Prepare data room: financials, customer list, growth metrics, product demo video
- Get warm introductions through IT Park network
- Target: 3-5 investor meetings by Month 12

**Metrics investors want to see:**
- 100+ paying customers
- $15K+ MRR with 20%+ month-over-month growth
- Net revenue retention >100% (customers upgrade or buy more)
- CAC payback period <3 months
- Gross margin >70%

### 5.4 Product-Market Fit Metrics

| Attribute | Detail |
|-----------|--------|
| Owner | Founder + Customer Success |
| Timeline | Measured continuously from Month 10 |
| Cost | $0 |

**PMF indicators to track:**

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Monthly churn | <3% | Customers who cancel / total customers |
| NPS score | >40 | Quarterly survey (simple Telegram poll) |
| Organic referrals | 20%+ of new customers | Ask "how did you hear about us?" at signup |
| Usage frequency | 4+ days/week | Track login and upload activity |
| Expansion revenue | 10%+ of MRR from upgrades | Customers moving from Starter to Professional |
| Sean Ellis test | 40%+ "very disappointed" | Survey: "How would you feel if HujjatAI disappeared?" |

**If PMF metrics are not met by Month 12:** Do not raise funding. Instead, dig into why customers churn, what they are missing, and whether the product needs fundamental changes. Raising on bad metrics leads to bad outcomes.

### 5.5 Self-Hosted ML Transition

| Attribute | Detail |
|-----------|--------|
| Owner | ML Engineer |
| Timeline | Months 10-12 |
| Cost | Included in infrastructure budget (GPU costs shift from API to compute) |

**Transition plan:**

| Component | Current (API) | Target (Self-hosted) | Savings at 100K pages/month |
|-----------|--------------|---------------------|----------------------------|
| OCR | Google Cloud Vision ($150/month at scale) | PaddleOCR on GPU ($0 per-page) | $150/month |
| NLP extraction | GPT-4o-mini ($20/month at scale) | Fine-tuned Qwen2.5-7B | $20/month |
| Total | $170/month | $0 marginal (GPU fixed cost $350-500) | Net: break-even at 60K pages, savings above |

**Milestones:**
- Month 10: PaddleOCR fine-tuned on Uzbek Latin (requires 10K labeled character images collected from customers)
- Month 11: Qwen2.5-7B fine-tuned on 30K extraction examples. A/B test vs. GPT-4o-mini.
- Month 12: Full transition to self-hosted models for 80%+ of documents. Keep GPT-4o-mini as fallback for low-confidence cases.

**Benefit beyond cost:** Latency drops from 3-5 seconds (API round-trip) to <500ms (local inference). Customers notice immediately.

---

## Key Decisions and Gates

| Gate | Timing | Decision | Criteria to Proceed | If Failed |
|------|--------|----------|--------------------|-----------| 
| G1 | End of Week 2 | Continue building or pivot | 10+ of 15 interviews validate core hypotheses | Pivot target customer or problem |
| G2 | End of Week 4 | Commit $15K to development | 3+ signed LOIs at $75/month | Revisit pricing/positioning or abandon |
| G3 | End of Week 12 | Launch commercially | 85%+ accuracy on beta customer documents, 3+ active beta users | Extend beta 2 weeks, fix accuracy |
| G4 | End of Month 4 | Scale acquisition spend | 10+ paying customers, <5% monthly churn | Fix product/retention before spending on growth |
| G5 | End of Month 9 | Raise external funding | 50+ customers, $6K+ MRR, clear growth trajectory | Bootstrap to profitability, grow slower |
| G6 | End of Month 12 | Enter Kazakhstan market | 100+ UZ customers, PMF metrics met, $15K+ MRR | Focus on Uzbekistan depth over breadth |

---

## Cost Tracking Summary

### Phase 1 Breakdown ($3,200)

| Item | Cost |
|------|------|
| Customer interview expenses (transportation, coffee, gifts) | $200 |
| Legal entity formation (lawyer, notary, fees) | $500 |
| ML engineer trial tasks (2 candidates x $250) | $500 |
| IT Park registration | $0 |
| Prototype/mockups | $0 |
| LOI collection | $0 |
| Miscellaneous/contingency | $2,000 |
| **Total** | **$3,200** |

### Phase 2 Breakdown ($14,800)

| Item | Cost |
|------|------|
| ML engineer salary (8 weeks) | $3,500 |
| Frontend developer salary (6 weeks, starts Week 7) | $1,800 |
| AWS infrastructure (dev/staging) | $1,200 |
| API costs (Google Vision + OpenAI testing) | $200 |
| 1C partner consulting | $500 |
| Part-time accountant consultant | $800 |
| Domain, SSL, email, misc SaaS tools | $300 |
| Contingency | $6,500 |
| **Total** | **$14,800** |

### Phase 3 Breakdown ($6,500)

| Item | Cost |
|------|------|
| ML engineer salary (4 weeks) | $2,000 |
| Frontend developer salary (4 weeks) | $1,200 |
| Infrastructure (production) | $600 |
| Marketing/acquisition (Telegram, events) | $500 |
| Legal (agreements, DPA, privacy policy) | $300 |
| Payment processing setup (Payme merchant) | $50 |
| Contingency | $1,850 |
| **Total** | **$6,500** |

### Total Spend Through First Revenue (Phases 1-3): $24,500

Remaining from $30K starting capital at end of Phase 3: **$5,500 buffer.**

First revenue arrives Month 4 (Week 13). At 5 paying customers x $75/month = $375/month initial MRR. Cash-flow positive target: Month 8-9 (when MRR exceeds monthly burn).

