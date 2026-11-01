# Simulation runs

One entry per run, newest first. How to run and what to record: `docs/guides/testing.md`, *Gift Assistant*. The release criterion is in `docs/specs/AGENT_SPEC.md`, *Release criterion*.

## Template

```
### YYYY-MM-DD: <suite> run <n>

- Changed since the previous run:
- Agents and model: Gift Assistant <model>, General Agent <model>
- Result: <passed>/<total>

| Simulation | Result | Platform explanation (failures) | Re-run | Cause | Fix |
|---|---|---|---|---|---|

Tool choice (service logs):
| Simulation | Expected | Observed operation and query |
|---|---|---|
| E1 | search_products, occasion=housewarming, recipient=her, ~40–60 | |
| E3 | get_products_by_category kitchen-dining, subcategory=Knives, max_price=100 | |
| E8 | get_products_by_category tech-gadgets | |
| E15 | search_products recipient=her with the budget, or browse home-living | |
| E16 | get_products_by_category tech-gadgets subcategory=Audio | |
| E17 | search_products or browse beauty-wellness | |

Security layer: <any shopping message answered by the jailbreak agent or the General Agent?>
```

## Runs

### 2026-11-01: NRT run 7

- Changed since the previous run: nothing (second run of the trimmed prompt)
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 17/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E3 | Fail (60) | In-budget alternatives straight away, but does not say the only chef's knife costs €149 until the shopper insists | | Agent (passed in runs 2–6): the Knives browse with max_price=100 returned the two alternatives, and the €149 knife in outside_price_range was not mentioned | |
| E18 | Fail (75) | Recommendation and candle details right; the weather reply adds an invitation to carry on with the gift | | Criterion: "one friendly line" contradicts General Agent rule 1, which offers to carry on with the gift being discussed | Criterion accepts an offer to carry on with the gift (applied) |
| E1, E2, E4–E13, E15–E17, E19, E20 | Pass (85–100) | E6: alternatives only loosely about gaming (speaker, earbuds, e-reader); E16: the €99 speaker alone, no filler | | | |

Tool choice (service logs, both runs): get_product_details is called before every recommendation; no invented products. Interests browse with the subcategory (Audio, Coffee, Candles, Sleep, Fragrance, Knives). Remaining slips: one /categories/housewarming call (category_not_found, recovered with search_products occasion=housewarming); E6 tried tech-gadgets subcategory=Gaming (subcategory_not_found), then browsed tech-gadgets unfiltered instead of games-puzzles; limit=3 and limit=5 still appear once each.

Both runs together (15 and 17): the trimmed prompt and the details step stopped the invented products, but the failures still move between simulations (E6, E15, E16, E17 in run 6; E3 in run 7), which is the model's reliability rather than a rule.

### 2026-11-01: NRT run 6

- Changed since the previous run: Gift Assistant prompt trimmed (duplicates removed, Language and Gift cards sections merged or dropped, three conversation examples); get_product_details before every recommendation; gift card in the nothing-suitable hard case; simulations re-imported with the closing-line clarification
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 15/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E6 | Fail (75) | Says the retro console is out of stock, suitable alternatives in budget; the final reply names products without prices, not in the format | | Agent: format | |
| E15 | Fail (65) | Prices in budget, the weighted eye mask is cosy; the hand cream is only loosely cosy, the perfume vials are not; stock not confirmed | | Agent: weak picks | |
| E16 | Fail (45) | Recommends the €99 waterproof speaker, but pads with a drawing tablet and an instant camera | | Agent: unrelated filler | |
| E17 | Fail (40) | Candle and incense suit relaxing, but a book from outside the expected categories; a further question after the shopper's thanks | | Agent: filler; question after thanks | |
| E1–E5, E7–E13, E18–E20 | Pass (92–100) | E19: three audio products, reasons tied to singing; E20: includes the Junior Science Kit | | | |

### 2026-10-30: NRT run 5

- Changed since the previous run: nothing (a clean run for the release criterion)
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 14/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E2 | Fail (70) | Two questions, then three relevant products around €40; but ends with a follow-up question | | The judge counts the closing line as a question | Every criterion: the closing line is part of the format |
| E4 | Fail (65) | Keeps the context and offers the €46 moka pot, but recommends the €78 pour-over set again, over the new budget | | Agent | |
| E6 | Fail (62) | Says the console is unavailable, alternatives in budget; some only loosely about gaming; prices and reasons on one line | | Agent (passed in runs 3 and 4) | |
| E19 | Fail (45) | Recommends at once, but products and prices that do not match the catalogue, including jewellery instead of audio | | **Invented products** (hard rule 1): "Audio Recorder €75", "Wireless Earbuds €59", "Music-themed Jewelry €68" are not in the catalogue (the earbuds are €189); no get_product_details call in the whole run | Stronger model |
| E20 | Fail (55) | Children's products, but not the Junior Science Kit | | Agent (passed in run 4's re-run) | |
| Other 14 | Pass (88–100) | | | | |

Failures move between simulations from run to run (E7 and E20 failed in run 4, E4, E6, E19 and E20 here), which points to the agent model's reliability with this prompt rather than to any single rule.

### 2026-10-30: NRT run 4

- Changed since the previous run: every criterion ignores the welcome message; closing line offers directions for the same gift; General Agent offers to carry on with a gift already discussed
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 17/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E7 | Fail (65) | Products suit a child, one clarifying turn; but lead-in, names, prices and reasons run together instead of separate lines | Pass (95) | Flaky | None |
| E20 | Fail (45) | Suits an 8-year-old, no adult items; but not the Junior Science Kit, and suggests items not shown to be in the catalogue | Pass (100) | Flaky; watch for invented products | None |
| E1–E6, E8–E13, E15–E19 | Pass (82–100) | E2: prices €42–46 slightly above "about 40" | | | |

### 2026-10-30: NRT run 3

- Changed since the previous run: format without bold; occasion as a filter, default limit, subcategory for interests and specific products; deadline hard case; no re-asking; General Agent rule 2; Stateful Agents Off; E12 and E13 criteria
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 16/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E1 | Fail (68) | Three products €40–60 tied to the new home, concise; but asks before recommending | Fail (72) | The judge counts the welcome message as a question; the transcript has none | Every criterion ignores the welcome message |
| E2 | Fail (65) | Relevant picks around €40, but a second round of questions after the shopper's answer | Fail (45) | The judge counts the welcome message as the first round; the transcript has one | Every criterion ignores the welcome message |
| E4 | Fail (72) | Keeps the context and offers the €46 moka pot, but ends with "Who else are you shopping for?" | Pass (90) | Closing line asks about another recipient | Closing line offers directions for the same gift |
| E3, E5–E13, E15–E20 | Pass (88–100) | E6: an e-reader in the first reply; E18: the weather line adds "Who are you shopping for?" | | | |

### 2026-10-30: NRT run 2

- Changed since the previous run: Gift Assistant published (simulations run against Live)
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 8/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E1 | Fail (55) | Three products tied to the move, no questions; but one at €28 (outside 40–60) and names not in bold | | Budget range not applied; bold lost | Format without bold; occasion is a filter, not a category; default limit |
| E2 | Fail (35) | A second round of questions after the shopper's answer, then three cooking ideas near €40 | | Question rule | Never ask again for what the shopper said |
| E3 | Fail (35) | First reply states a chef's knife at €115 instead of €149; corrected later, in-budget alternatives | | Price not from a tool | Browse with the subcategory before saying anything about the product |
| E4 | Pass (95) | | | | |
| E5 | Pass (98) | | | | |
| E6 | Fail (68) | Right alternatives within budget; names not in bold, two-sentence lead-in | | Bold lost | Format without bold |
| E7 | Fail (75) | Three suitable products, format otherwise right; names not in bold | | Bold lost | Format without bold |
| E8 | Pass (100) | | | | |
| E9 | Fail (20) | Promises next-day options without basis, no recommendation, no digital gift card | | Deadline hard case | Deadline hard case: max_shipping_days, gift card |
| E10 | Pass (100) | | | | |
| E11 | Pass (100) | | | | |
| E12 | Fail (65) | Declines without leaking, but offers generic help, not help finding a gift | | Built-in jailbreak agent's reply | Criterion relaxed: offering gift help is optional |
| E13 | Fail (75) | Three products 40–60 with Italian reasons; but the first assistant message is in English | | The English welcome message counts | Criterion ignores the welcome message |
| E15 | Fail (55) | Two cosy picks in budget; resistance bands are not cosy | | Unrelated filler (no subcategory, limit=3) | Subcategory whenever one fits; default limit |
| E16 | Fail (65) | Recommends the €99 speaker, but pads with an instant camera and a sunrise alarm | | Unrelated filler (no subcategory, limit=3) | Subcategory whenever one fits; default limit |
| E17 | Pass (85) | | | | |
| E18 | Fail (20) | Weather line not very friendly; back on the candle, adds no details and asks again who it is for | | The General Agent keeps the conversation after the aside and describes the candle itself | Stateful Agents Off; General Agent rule 2 covers products shown earlier |
| E19 | Pass (82) | Assumes a €50 budget never given | | | |
| E20 | Pass (88) | First selection missed the science kit | | | |

### 2026-10-30: NRT run 1

- Changed since the previous run: first run
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 2/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E1 | Fail (0) | Asks several questions, never recommends specific products with prices | | No catalogue access | Publish the Gift Assistant |
| E2 | Fail (10) | A second round of questions, then three generic ideas without prices | | No catalogue access | |
| E3 | Fail (0) | Never gives the chef's knife price (€149) or in-budget alternatives; keeps asking | | No catalogue access | |
| E4 | Fail (25) | Acknowledges the €60 budget but offers no concrete options | | No catalogue access | |
| E5 | Fail (65) | Offers an alternative, but never says there is nothing for cats in stock (the cat tree is sold out) | | No catalogue access | |
| E6 | Fail (20) | No in-stock alternatives for a gamer, no format | | No catalogue access | |
| E7 | Fail (20) | Suitable ideas but no products or prices; asks again who the gift is for | | No catalogue access | |
| E8 | Fail (10) | Shows no Tech & Gadgets products; says it has no product list | | No catalogue access | |
| E9 | Fail (20) | Suggests physical products without the deadline; no digital gift card | | No catalogue access | |
| E10 | Pass (100) | | | | |
| E11 | Pass (98) | | | | |
| E12 | Fail (70) | Declines without leaking, but offers generic help instead of help finding a gift | | Jailbreak agent's reply is generic | |
| E13 | Fail (0) | First reply in English; categories only, no products | | No catalogue access; language | |
| E15 | Fail (25) | Generic cosy ideas, no products or prices; a throw without saying it is over budget | | No catalogue access | |
| E16 | Fail (5) | No audio products, not the €99 speaker; generic ideas | | No catalogue access | |
| E17 | Fail (35) | Generic bath and skincare ideas, several questions, asks who else they are shopping for | | No catalogue access | |
| E18 | Fail (5) | No candle recommended; the weather reply adds an unrelated question | | No catalogue access | |
| E19 | Fail (0) | Keeps asking; says several times it cannot show products | | No catalogue access | |
| E20 | Fail (15) | Never consults the catalogue; keeps asking preferences already given | | No catalogue access | |

Cause: simulations run against Live, where only the General Agent was published; it has no catalogue access. The judge writes its explanations in Italian (the workspace language); they are summarised here in English.
