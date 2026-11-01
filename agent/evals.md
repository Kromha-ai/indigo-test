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

### 2026-11-01: NRT run 19

- Changed since the previous run: nothing (second run with the General Agent on gpt-5.6-luna)
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-5.6-luna (EU)
- Result: 16/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E18 | Fail (75) | Short weather reply without a forecast, but asks who the gift is for instead of offering to carry on; back on the Ember Ceramic Candle with details | | General Agent: its weather example ends with "Who are you shopping for?", which contradicts its rule 1 (also run 17, on gpt-4.1-mini) | |
| E2 | Fail (60) | Asks who it is for, what they like and the budget: three questions where the criterion allows two; then three cooking gifts | | Prompt: "whatever is missing among who it is for, what they are into and the budget" allows three, the spec two | |
| E4 | Fail (25) | Keeps part of the context; offers a €50 gift card and the €78 pour-over set again, over the new €60 limit | | Gift Assistant: shows again a product above the new limit (also runs 5, 12, 18) | |
| Other 16 | Pass | | | | |

### 2026-11-01: NRT run 18

- Changed since the previous run: General Agent model gpt-4.1-mini (EU) to gpt-5.6-luna (EU)
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-5.6-luna (EU)
- Result: 17/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E20 | Fail (55) | One suitable product, no repeated question; but not the Junior Science Kit, and a single product instead of a few | | Gift Assistant | |
| E4 | Fail (70) | The €46 moka pot in budget; then the €78 pour-over set again, over budget | | Gift Assistant: shows again a product above the new limit | |
| Other 17 | Pass | | | | |

### 2026-11-01: NRT run 17 (final)

- Changed since the previous run: nothing
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-4.1-mini (EU)
- Result: 18/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E18 | Fail (78) | Short weather reply with no forecast; back on the Ember Ceramic Candle with details and no repeated questions; but the weather reply also asks "Who is the gift for?" | | General Agent: asks who the gift is for although a gift is already being discussed (its rule 1); first time since run 7 | Watch |
| Other 18 | Pass | | | | |

### 2026-11-01: NRT run 16

- Changed since the previous run: nothing (README and walkthrough only)
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-4.1-mini (EU)
- Result: 19/19

### 2026-11-01: NRT run 15

- Changed since the previous run: nothing (second run for the release criterion)
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-4.1-mini (EU)
- Result: 18/19 (release criterion met: two consecutive runs at 18/19 or more, no invented products)

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E6 | Fail (68) | Console out of stock; the mechanical keyboard is a fitting alternative in budget; the drawing tablet does not suit a gamer, and the first suggestions are only loosely about gaming | | Agent: filler | Watch |
| Other 18 | Pass | | | | |

### 2026-11-01: NRT run 14

- Changed since the previous run: outside_price_range.above_max names its cheapest product (service redeployed, tool collection re-imported); reply to thanks without a new question
- Agents and model: Gift Assistant gpt-5.6-luna (EU), General Agent gpt-4.1-mini (EU)
- Result: 18/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E9 | Fail (70) | Takes the deadline into account and offers the digital gift cards; but the closing line offers to look for a physical gift that arrives in time, though physical products take at least 2 days | | Agent: the closing line offers a direction the tools already ruled out | Watch |
| Other 18 | Pass | E3 and E19 pass with the fixes | | | |

### 2026-11-01: NRT run 13

- Changed since the previous run: nothing (second run on gpt-5.6 luna)
- Agents and model: Gift Assistant gpt-5.6 luna, General Agent gpt-4.1-mini (EU)
- Result: 18/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E19 | Fail (78) | Three relevant audio products straight after "she loves to sing"; but after the shopper's thanks, asks again about preferences or budget | | Agent: a question after thanks | |
| Other 18 | Pass | | | | |

### 2026-11-01: NRT run 12

- Changed since the previous run: Gift Assistant model gpt-4.1-mini (EU) to gpt-5.6 luna (Creativity 0.1, prompt unchanged)
- Agents and model: Gift Assistant gpt-5.6 luna, General Agent gpt-4.1-mini (EU)
- Result: 17/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E3 | Fail (78) | Two alternatives under €100, the paring knife not passed off as a chef's knife; the €149 chef's knife only named after the follow-up | | Service: outside_price_range.above_max gives a count and a lowest price, not which product it is, so the model cannot tell the €149 product is the chef's knife (also run 7) | |
| E4 | Fail (20) | After the €60 limit, recommends the €78 pour-over set again, then generic kitchen gifts, losing the coffee context | | Agent (also run 5) | |
| Other 17 | Pass | | | | |

### 2026-11-01: NRT run 11

- Changed since the previous run: nothing (second run at Creativity 0.1)
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 14/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E3 | Fail (72) | Says the chef's knife costs €149 and offers in-budget alternatives; over about 90 words, and the lead-in "found one" suggests a chef's knife under €100 | | Agent: length, wording | Stronger model |
| E6 | Fail (48) | Console out of stock; four products in the first reply; the second reply not in the format | | Agent: format, product count | Stronger model |
| E9 | Fail (15) | Promises to look for something that "ships by tomorrow"; no digital gift card | | Agent | Stronger model |
| E16 | Fail (65) | The €99 speaker, padded with a poetry anthology | | Agent: filler | Stronger model |
| E17 | Fail (60) | Candle and incense suit; a book outside the expected categories | | Agent: filler | Stronger model |
| Other 14 | Pass | | | | |

### 2026-11-01: NRT run 10

- Changed since the previous run: Gift Assistant Creativity 0.3 to 0.1; reply-in-the-shopper's-language line at the end of the message format
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 16/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E4 | Fail (78) | The €46 moka pot, in budget, coffee and dad kept; the birthday not mentioned | | Agent (borderline) | Stronger model |
| E7 | Fail (78) | Suitable products, format right; about 106 words, over the 90 limit, with shipping and gift wrap details | | Agent: length | Stronger model |
| E20 | Fail (55) | Children's products, no repeat question; no Junior Science Kit, and alternatives not clearly from the catalogue | | Agent | Stronger model |
| Other 16 | Pass | E13 passes with the language line | | | |

Runs 6–11 on gpt-4.1-mini (15, 17, 12, ≤13, 16, 14): neither trimming, targeted fixes nor lower creativity reached 18/19 twice. The recurring failures (E6 gaming alternatives, E9 deadline, E16 and E17 filler) break rules the prompt states explicitly. Next: the Gift Assistant on gpt-4.1 (decision A2).

### 2026-11-01: NRT run 9

- Changed since the previous run: nothing (second run with the games mapping)
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: at most 13/19 (the pasted results were cut off after E2)

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E9 | Fail (20) | Promises gifts that arrive by tomorrow without checking shipping times; no digital gift card | | Agent (passed in runs 2–7) | Stronger model |
| E1 | Fail (65) | No questions, three products; the €32 coaster set is outside €40–60; weak reasons; an unneeded question afterwards | | Agent | Stronger model |
| E4 | Fail (75) | An in-budget coffee option, no repeat; but the dad and the birthday are not kept explicitly | | Agent | Stronger model |
| E6 | Fail (55) | Console out of stock; one gaming accessory (the mechanical keyboard), the rest about running and listening | | Agent | Stronger model |
| E15 | Fail (76) | Candle and diffuser are cosy; the coaster set is not | | Agent | Stronger model |
| E17 | Fail (65) | Candle and incense suit; a book outside the expected categories | | Agent | Stronger model |
| E2, E13 | Pass (100) | | | | |

### 2026-11-01: NRT run 8

- Changed since the previous run: games mapping in the interest line; E18 criterion accepts an offer to carry on with the gift
- Agents and model: Gift Assistant gpt-4.1-mini (EU), General Agent gpt-4.1-mini (EU)
- Result: 12/19

| Simulation | Result | Platform explanation (summarised) | Re-run | Cause | Fix |
|---|---|---|---|---|---|
| E1 | Fail (65) | Three products straight away, but only one in €40–60 (others €32 and €36); reasons not tied to the move | | Agent | Stronger model |
| E6 | Fail (35) | Console out of stock; alternatives a candle, a kitchen knife and an e-reader; the first suggestions generic audio | | Agent: the games mapping did not help | Stronger model |
| E9 | Fail (15) | Ignores the deadline, keeps asking after the budget, no gift card | | Agent (passed in runs 2–7) | Stronger model |
| E13 | Fail (45) | Three products in €40–60, but the reply and reasons are in English | | Agent: Language section removed in the trim | Reply-in-the-shopper's-language line back in the prompt |
| E15 | Fail (68) | Weighted eye mask cosy, cream trio plausible; perfume vials not cosy | | Agent | Stronger model |
| E16 | Fail (65) | The €99 speaker, padded with a poetry anthology and a fountain pen | | Agent | Stronger model |
| E17 | Fail (65) | Candle and incense suit; a book (atlas) outside the expected categories | | Agent | Stronger model |
| E2–E5, E7, E8, E10–E12, E18–E20 | Pass (88–100) | E18 passes with the new criterion; E5: says gift cards are usually available, then that it finds none | | | |

Runs 6–9 (15, 17, 12, at most 13) with the same prompt: the score swings by five between identical runs, and E1, E9 and E16, stable before, now fail. No change to the prompt moves the result in a measurable way; the agent model is the limit.

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
