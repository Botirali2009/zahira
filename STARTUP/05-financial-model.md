# HujjatAI Financial Model

## Starting Position

- **Cash:** $30,000
- **Founder:** 1 (based in Tashkent)
- **Legal status:** IT Park resident LLC
- **Tax regime:** 0% corporate tax, 0% social payments, 7.5% employee income tax
- **Exchange rate assumption:** 12,800 UZS/USD (mid-2026), 7% annual depreciation modeled

---

## Monthly Cost Structure by Phase

### Phase 1: Validation (Month 1)

| Category | Monthly Cost |
|----------|-------------|
| Founder salary (minimal draw) | $0 |
| Customer interview expenses | $200 |
| Legal entity formation | $500 |
| ML engineer trial tasks | $500 |
| IT Park registration | $0 |
| Prototype (Figma free + API tests) | $0 |
| Contingency | $2,000 |
| **Total** | **$3,200** |

### Phase 2: Build MVP (Months 2-3)

| Category | Monthly Cost |
|----------|-------------|
| ML engineer salary | $2,000 |
| Frontend developer salary (starts Month 2.5) | $1,000 |
| Cloud infrastructure (GCP dev) | $200 |
| AI API costs (Vision + OpenAI testing) | $50 |
| 1C partner consulting | $250 |
| Accountant consultant (domain expert) | $100 |
| SaaS tools (GitHub, domains, email) | $75 |
| **Monthly total** | **$3,675** |
| **Phase total (8 weeks)** | **$14,800** |

Note: Frontend dev starts at Week 7, so Month 2 is lower (~$2,675) and Month 3 is higher (~$4,675). The $14,800 includes $6,500 contingency built into Phase 2 budget.

### Phase 3: Launch (Month 4)

| Category | Monthly Cost |
|----------|-------------|
| ML engineer salary | $2,000 |
| Frontend developer salary | $1,200 |
| Cloud infrastructure (production) | $300 |
| AI API costs (real customer usage) | $100 |
| Marketing (Telegram ads, events) | $300 |
| Legal (contracts, DPA) | $300 |
| Payment processing setup | $50 |
| Contingency | $1,850 |
| **Phase total (4 weeks)** | **$6,500** |

### Phase 4: Growth (Months 5-9)

| Category | Monthly Cost |
|----------|-------------|
| ML engineer salary (raised) | $2,500 |
| Frontend developer salary (raised) | $1,500 |
| Customer Success hire (starts Month 6) | $1,200 |
| Cloud infrastructure (scaling) | $700 |
| AI API costs (scaling) | $200 |
| 1C partner commissions | $500 |
| Marketing | $400 |
| Office (IT Park, post free period) | $300 |
| Tools and subscriptions | $150 |
| **Monthly total (from Month 6)** | **$7,450** |

### Phase 5: Scale (Months 10-12)

| Category | Monthly Cost |
|----------|-------------|
| Engineering team (5 people) | $8,300 |
| Sales/CS team (2 people) | $2,500 |
| Operations/admin | $1,000 |
| Infrastructure at scale | $1,500 |
| Marketing | $1,000 |
| Office space | $500 |
| Legal/compliance | $200 |
| **Monthly total** | **$15,000** |

---

## Revenue Model

### Pricing

| Tier | Price (USD) | Price (UZS) | Included Pages | Target |
|------|-------------|-------------|----------------|--------|
| Starter | $50/month | 640,000 UZS | 500 pages | 50-100 employees |
| Professional | $150/month | 1,920,000 UZS | 2,000 pages | 100-300 employees |
| Enterprise | $300/month | 3,840,000 UZS | 5,000 pages | 300-500 employees |

**Founding customer discount:** First 10 customers get 50% off for 12 months ($75/month for Professional tier).

### Payment Collection

- **Primary:** Bank wire transfer (standard for Uzbek B2B). Net-30 payment terms.
- **Secondary:** Uzcard/Humo corporate cards via Payme merchant integration (1.5% fee).
- **Tertiary:** Click/Payme for smaller customers.
- **Collection risk:** Budget 5% of revenue for late/non-payment. Uzbek B2B payment culture averages 15-30 day delays.

### Conversion Funnel (steady state, Month 6+)

| Stage | Volume | Conversion |
|-------|--------|------------|
| Leads (from all channels) | 40/month | -- |
| Demo/trial requests | 20/month | 50% |
| Trials started | 15/month | 75% |
| Converted to paid | 8-10/month | 55-65% |

### Per-Page Economics

| Cost Component | Cost per Page |
|----------------|---------------|
| Google Cloud Vision OCR | $0.0015 |
| GPT-4o-mini extraction | $0.000075 |
| Compute/storage | $0.0003 |
| **Total COGS per page** | **$0.0019** |

At Professional tier ($150/month for 2,000 pages): COGS = $3.80/month. Gross margin = 97.5%.

Even at maximum usage, per-page costs are negligible. The real costs are people and infrastructure (fixed), not marginal AI costs.

---

## Unit Economics

| Metric | Value | Calculation |
|--------|-------|-------------|
| **Average Revenue Per Customer (ARPC)** | $125/month | Blended across tiers: ~45% Starter ($50), ~40% Professional ($150), ~15% Enterprise ($300). Founding discounts lower effective average in Months 4-6. |
| **Gross Margin** | 78% | After AI APIs, cloud infra allocated per customer, and payment processing |
| **Customer Acquisition Cost (CAC)** | $65 | Blended: $50 referral fee (60%) + $100 marketing cost (25%) + $0 organic (15%) + overhead allocation |
| **Lifetime Value (LTV)** | $2,625 | ARPC x Gross Margin x Avg Lifetime = $125 x 0.78 x 27 months |
| **LTV/CAC Ratio** | 40:1 | $2,625 / $65 |
| **Payback Period** | 0.7 months | CAC / (ARPC x Gross Margin) = $65 / ($125 x 0.78) |
| **Monthly Churn** | 3.5% | Assumed; implies ~27-month average lifetime |
| **Net Revenue Retention** | 105% | Customers upgrade tiers as document volume grows |

### CAC Breakdown by Channel

| Channel | CAC | % of Customers | Notes |
|---------|-----|----------------|-------|
| 1C partner referrals | $50 | 60% | $50 referral fee per converted customer |
| Telegram/community | $100 | 25% | Content creation + ad spend / conversions |
| Word-of-mouth | $0 | 15% | Organic from satisfied customers |
| **Blended CAC** | **$65** | 100% | |

### Why LTV/CAC is High

This is a low-CAC business because:
1. The 1C partner channel has built-in trust (partner recommends to existing client)
2. No paid ads or expensive sales team in early phases
3. Chief accountants do not churn on tools that work (switching cost is retraining + reconfiguration)

LTV/CAC will compress as the company scales into paid channels (Google ads, outbound sales). Target: maintain above 5:1 through Month 12.

---

## 12-Month P&L Projection (Base Case)

| | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Revenue** | $0 | $0 | $0 | $375 | $1,000 | $1,980 | $3,360 | $4,750 | $6,500 | $8,775 | $11,200 | $14,500 |
| **COGS** | $0 | $0 | $0 | $50 | $150 | $350 | $600 | $850 | $1,200 | $1,600 | $2,100 | $2,800 |
| **Gross Profit** | $0 | $0 | $0 | $325 | $850 | $1,630 | $2,760 | $3,900 | $5,300 | $7,175 | $9,100 | $11,700 |
| | | | | | | | | | | | | |
| **Salaries** | $0 | $2,000 | $3,200 | $3,200 | $3,500 | $4,700 | $5,200 | $5,200 | $5,200 | $8,300 | $10,500 | $13,700 |
| **Cloud/Infra** | $0 | $200 | $200 | $300 | $400 | $500 | $600 | $700 | $900 | $1,200 | $1,400 | $1,500 |
| **Marketing** | $0 | $0 | $0 | $300 | $300 | $400 | $400 | $400 | $400 | $800 | $1,000 | $1,000 |
| **Legal/Admin** | $500 | $0 | $0 | $300 | $100 | $100 | $100 | $100 | $100 | $200 | $200 | $200 |
| **Office** | $0 | $0 | $0 | $0 | $0 | $300 | $300 | $300 | $300 | $500 | $500 | $500 |
| **Tools/SaaS** | $0 | $75 | $75 | $75 | $100 | $150 | $150 | $150 | $150 | $200 | $200 | $200 |
| **1C Commissions** | $0 | $0 | $0 | $0 | $250 | $400 | $500 | $500 | $500 | $500 | $500 | $500 |
| **Contingency/Other** | $2,700 | $0 | $6,500 | $1,850 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| **Total OpEx** | $3,200 | $2,275 | $9,975 | $6,025 | $4,650 | $6,550 | $7,250 | $7,350 | $7,550 | $11,700 | $14,300 | $17,600 |
| | | | | | | | | | | | | |
| **Net Income** | -$3,200 | -$2,275 | -$9,975 | -$5,700 | -$3,800 | -$4,920 | -$4,490 | -$3,450 | -$2,250 | -$4,525 | -$5,200 | -$5,900 |
| **Cumulative Cash** | $26,800 | $24,525 | $14,550 | $8,850 | $5,050 | $130 | -$4,360 | -$7,810 | -$10,060 | -$14,585 | -$19,785 | -$25,685 |

### Key Observations

1. **$30K runs out in Month 6** without external funding. Cumulative cash hits $130 at end of Month 6.
2. **The company is never self-sustaining on $30K alone** in the base case. Revenue grows fast but team scaling outpaces it.
3. **Breakeven month (revenue > costs): Month 9 is close** -- $6,500 revenue vs $7,550 costs. But by then the team has grown.
4. **Funding inflection:** Seed round must close by Month 6-7 to avoid running out of cash. Alternatively, delay Phase 4 hiring.

### Cash Runway Without Revenue

If zero revenue materializes:
- Months 1-3 burn: $15,450 (Phases 1-2)
- Month 4 burn: $6,025 (Phase 3 with contingency)
- Month 5 burn: $4,650
- **Cash hits zero mid-Month 5** at current burn rate without revenue.

With just the initial $30K and no revenue, the company survives ~5 months. This is why LOI validation in Phase 1 is critical. If demand is not validated by Week 4, stop spending.

---

## Scenario Analysis

### Conservative Scenario (Slow Adoption)

**Assumptions:** Half the customers of base case. Average revenue $100/month (more Starter tier). 5% monthly churn.

| | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|
| Customers | 3 | 5 | 9 | 14 | 19 | 25 | 32 | 40 | 50 |
| MRR | $300 | $500 | $900 | $1,400 | $1,900 | $2,500 | $3,200 | $4,000 | $5,000 |
| Monthly Costs | $5,500 | $4,650 | $5,500 | $5,800 | $6,000 | $6,200 | $7,500 | $8,500 | $10,000 |
| Net Burn | -$5,200 | -$4,150 | -$4,600 | -$4,400 | -$4,100 | -$3,700 | -$4,300 | -$4,500 | -$5,000 |
| Cumulative Cash | $9,350 | $5,200 | $600 | -$3,800 | -$7,900 | -$11,600 | -$15,900 | -$20,400 | -$25,400 |

**Result:** Cash runs out early Month 6. Must raise by Month 5 or die. Total funding needed to reach Month 12: ~$25,000 beyond the initial $30K. Breakeven never reached in 12 months.

**Decision:** If conservative scenario plays out, raise a small bridge ($30-50K from IT Park Ventures or angels) by Month 5, or cut costs aggressively (delay frontend hire, founder does sales/CS).

### Base Scenario (Moderate Growth)

See full P&L table above. Cash runs out Month 6. Requires $50-100K bridge by Month 6 or $150-200K seed round closing Month 7-8.

**Revenue at Month 12:** $14,500 MRR ($174K ARR). 100 customers.

### Aggressive Scenario (Fast Traction)

**Assumptions:** 50% more customers than base. Average revenue $140/month (more Professional/Enterprise). 2.5% monthly churn. Word-of-mouth kicks in Month 5.

| | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|
| Customers | 7 | 15 | 27 | 42 | 57 | 75 | 97 | 120 | 150 |
| MRR | $735 | $1,575 | $3,240 | $5,460 | $7,695 | $10,500 | $13,580 | $16,800 | $21,000 |
| Monthly Costs | $5,500 | $5,200 | $7,000 | $8,000 | $8,500 | $9,500 | $13,000 | $15,000 | $18,000 |
| Net Burn | -$4,765 | -$3,625 | -$3,760 | -$2,540 | -$805 | $1,000 | $580 | $1,800 | $3,000 |
| Cumulative Cash | $9,785 | $6,160 | $2,400 | -$140 | -$945 | $55 | $635 | $2,435 | $5,435 |

**Result:** Breakeven in Month 9. Cash gap is small (under $1,000 negative at worst, Months 7-8). Could potentially survive without external funding if founder defers salary and negotiates payment terms. Realistically, still raises seed ($150-300K) in Month 8-10 to accelerate growth while metrics are strong.

**Revenue at Month 12:** $21,000 MRR ($252K ARR). 150 customers.

### Scenario Comparison Summary

| Metric | Conservative | Base | Aggressive |
|--------|-------------|------|------------|
| Month 12 MRR | $5,000 | $14,500 | $21,000 |
| Month 12 Customers | 50 | 100 | 150 |
| Month cash runs out | Month 6 | Month 6 | Month 7 |
| Breakeven month | Never (in 12 months) | ~Month 14 | Month 9 |
| External funding needed | $25K+ bridge | $100-200K seed | Optional ($150-300K for growth) |
| Month 12 ARR | $60K | $174K | $252K |

---

## Funding Strategy

### Phase 1: Bootstrap ($30K founder capital, Months 1-6)

The $30K covers product development through launch and early traction. No external funding needed until product-market fit signals appear.

### Phase 2: Bridge or Seed (Month 5-8)

**Trigger:** Cash below $5K with growing customer base and positive unit economics.

**Option A: Small bridge ($30-50K)**
- Source: IT Park Ventures quick-decision program or angel investors
- Terms: SAFE note, $500K-1M valuation cap
- Timeline: 2-4 weeks from first meeting to wire
- Use: Extend runway 3-4 months to hit seed-round metrics

**Option B: Seed round ($150-300K)**
- Source: Institutional seed investors (see below)
- Terms: Priced equity round, 15-20% dilution, $1-2M pre-money valuation
- Timeline: 6-10 weeks from first pitch to close
- Use: Scale team to 10, enter Kazakhstan, reach $15K+ MRR

### Target Investors

| Investor | Type | Typical Check | Stage | Contact Path |
|----------|------|---------------|-------|-------------|
| **IT Park Ventures** | Government-backed VC ($10M fund) | $50K-500K | Pre-seed to Seed | Direct through IT Park resident network. Mandate to fund Uzbek tech. Fastest path to first institutional check. |
| **Sturgeon Capital** | Central Asia VC (London-based) | $200K-2M | Seed to Series A | Warm intro through IT Park or ICTWEEK. Have invested in Uzbek fintech (Humans.uz, others). Understand the market. |
| **Uzum Ventures** | Corporate VC (Uzum/Tashkent) | $100K-500K | Seed | Strategic fit: Uzum is building financial infrastructure. HujjatAI is adjacent. Intro through IT Park network. |
| **500 Global** | Global accelerator | $150K (standard SAFE) | Pre-seed/Seed | Apply to batch program. Central Asia is an emerging market they track. |
| **EBRD Star Venture** | DFI-backed program | $50K-100K (grant + equity) | Early stage | Apply through EBRD Uzbekistan office. Non-dilutive component attractive. |
| **Local angels** | Individual investors in Tashkent tech scene | $10K-50K | Pre-seed | IT Park demo days, Startup Grind Tashkent, personal network |

### Milestones Before Raising

| Milestone | Why It Matters |
|-----------|---------------|
| 30+ paying customers | Proves repeatable demand beyond founder network |
| $4K+ MRR | Shows willingness to pay at scale |
| 90%+ extraction accuracy | Proves technical moat |
| <5% monthly churn | Proves retention/stickiness |
| 20%+ MoM revenue growth | Proves growth trajectory |
| 3+ 1C partner referral channels | Proves scalable distribution |

### Dilution Expectations

| Round | Amount Raised | Pre-Money Valuation | Dilution | Founder Ownership After |
|-------|--------------|--------------------|-----------|-----------------------|
| Seed | $200K | $1M-1.5M | 13-17% | 83-87% |
| Series A (Month 18-24) | $1-2M | $5-8M | 15-25% | 62-74% |

Single founder retaining 80%+ post-seed is strong. No co-founder dilution. Employee option pool (10%) should be created at seed round.

---

## Key Financial Risks

### 1. Currency Risk (UZS/USD)

- Revenues collected in UZS; cloud costs paid in USD.
- UZS has depreciated ~7%/year against USD over past 3 years. Central Bank targets gradual depreciation.
- **Mitigation:** Price contracts in USD-equivalent (customers pay UZS at daily exchange rate). Keep 50%+ of cash in USD account. Convert to UZS only for local salaries/expenses.
- **Worst case:** 15% sudden devaluation (happened in 2017). Impact: salaries become 15% cheaper in USD terms (good for costs), but customer price sensitivity increases if USD-denominated prices feel more expensive.

### 2. Payment Collection

- Uzbek B2B payments average 15-30 day delays. Some stretch to 60 days.
- Government-linked companies can delay 90+ days.
- **Mitigation:** Require prepayment for Starter tier. Net-30 for Professional/Enterprise with late fees. Cut service access after 45 days unpaid. Avoid government contracts until cash-flow positive.
- **Budget impact:** Model assumes 5% revenue loss to non-payment. At $14.5K MRR, that is $725/month.

### 3. Customer Churn

- Base case assumes 3.5% monthly churn (27-month average lifetime).
- If churn hits 7% (14-month lifetime), LTV drops to $1,365 and LTV/CAC drops to 21:1 -- still healthy but growth slows.
- **Key churn drivers:** Accuracy below expectations, 1C integration breaks on updates, competitor enters market, company switches away from 1C.
- **Mitigation:** Monthly check-ins for first 6 months. Immediate response to accuracy complaints. Lock customers into annual contracts with 10% discount ($135/month for Professional).

### 4. AI API Cost Increases

- OpenAI and Google Cloud have both raised prices historically.
- Current GPT-4o-mini pricing: $0.15/1M input tokens, $0.60/1M output tokens. A 3x increase would raise per-page cost from $0.000075 to $0.000225 -- still negligible.
- Google Cloud Vision: $1.50/1000 pages. A 2x increase to $3.00/1000 pages raises monthly cost from $150 to $300 at 100K pages/month. Manageable.
- **Mitigation:** Self-hosted model transition planned for Months 10-12 eliminates API dependency entirely. PaddleOCR (open source) + fine-tuned Qwen2.5-7B replaces both APIs.

### 5. Competitive Entry

- Potential competitors: foreign doc-AI tools (Rossum, Nanonets) localizing to Uzbekistan, or local devs building a similar product.
- **Moat:** Uzbek Latin OCR accuracy (trained on real Uzbek invoices), 1C integration depth, and chief accountant relationships are not replicable quickly.
- **If a well-funded competitor enters:** Shift to annual contracts, deepen 1C partnerships (exclusive referral deals), and accelerate self-hosted ML to reduce costs below what API-dependent competitors can match.

### 6. Founder Risk (Single Point of Failure)

- One founder doing sales, product, fundraising, and management through Month 6.
- If founder is incapacitated, company stops.
- **Mitigation:** Hire Customer Success by Month 6 who can handle existing customers. ML engineer should be able to run product development independently by Month 4. Document all processes.

---

## Cash Flow Sensitivity

### What Moves the Needle Most

| Variable | +/- Change | Impact on Month 12 Cash |
|----------|-----------|------------------------|
| Customer growth rate | +/-20% | +/- $15,000 |
| Average revenue per customer | +/- $25/month | +/- $8,000 |
| ML engineer salary | +/- $500/month | +/- $6,000 |
| Churn rate | +/- 1.5% monthly | +/- $4,000 |
| Time to first customer | +/- 1 month | +/- $5,000 |
| Cloud costs | +/- $300/month | +/- $3,600 |

**The single biggest lever is customer growth rate.** Everything else is secondary. The financial model lives or dies on whether 1C partner referrals deliver 5-8 customers/month from Month 5 onward.

---

## Monthly Cash Position (Base Case, Visual)

```
Month:  1      2      3      4      5      6      7      8      9      10     11     12
Cash:  $26.8K $24.5K $14.6K $8.9K  $5.1K  $0.1K  ---FUNDING REQUIRED---
                                                    |
                                          Seed round closes (~$200K)
                                                    |
Post-funding:                                      $200K  $196K  $191K  $185K
```

The business requires external capital by Month 6. This is by design -- the $30K funds validation and MVP, then traction metrics unlock institutional funding. Attempting to reach profitability on $30K alone requires cutting team investment (slower growth) or aggressive scenario traction (unlikely on first attempt).

---

## Summary Financial Metrics

| Metric | Month 6 | Month 9 | Month 12 |
|--------|---------|---------|----------|
| MRR | $1,980 | $6,500 | $14,500 |
| ARR | $23,760 | $78,000 | $174,000 |
| Customers | 18 | 50 | 100 |
| Monthly burn (net of revenue) | $4,920 | $2,250 | $5,900 |
| Gross margin | 78% | 78% | 81% |
| CAC (blended) | $65 | $65 | $75 |
| LTV/CAC | 40:1 | 40:1 | 35:1 |
| Team size | 4 | 4 | 9 |
| Runway remaining (no funding) | 0 months | -- | -- |
