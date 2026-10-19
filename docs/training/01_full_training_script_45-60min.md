# B2B Customer Development SOP v3.1 · Full training script

> Purpose: explain the whole logic alongside the "B2B Customer Development closed-loop flowchart v3.1". Suggested length: 45–60 minutes.
> How to teach: first explain "why a closed loop", then walk the chart top to bottom. For every stage cover only three things: what problem this step solves, where its exit is, and who signs off.
> Markers: [Say] is spoken content; [Pause] is a place to ask the audience a question or give an example; [One line] is the takeaway for the stage.

---

## Opening (3 min)

[Say]
Look at the overall shape of this chart first. It is not a straight line from top to bottom; it is a loop. The Install Gate is at the top, the seven steps are in the middle, and the "Win Review" at the bottom writes its conclusions back into the files at the top before the next round starts.

The most common failure in customer development is not "we cannot find customers". It is three things:
First, a pile of lists and a pile of e-mails, and nobody knows which e-mail worked or why.
Second, when a new hire takes over, all the experience lives in the senior salesperson's head and cannot be handed over.
Third, AI tools are used more and more, but there is no brake. One wrong e-mail is one customer lost.

This SOP is designed to fix those three things: every step leaves a data trace, every step can be followed by a new hire, and every outbound action needs a human decision.

[Pause] Ask the audience: in your current process, three months after an e-mail goes out, can you still trace "why we sent it to this person"?

[One line] The core of this chart is not "how to find customers" but "how to make finding customers reviewable, transferable, and safe to hand partly to AI".

---

## Layer one: the Install Gate (5 min)

[Say]
At the very top are three checks, called the Install Gate. It means: once this tool is installed, until these three things are filled in, every search and send script refuses to run.

Check 1, the company profile. Industry, offer type, product facts, differentiation, the buyer titles you look for. Note that it requires at least two differentiators and at least one buyer title, because every search query and e-mail template later grows out of this.

Check 2, the Soul Seven Kit. Seven files written for the AI: who you are, where the red lines are, what the boss prefers, how to keep working notes. This check is a content health check. Flipping "filled" to true is not enough; it looks for empty shells and sample text that was never replaced.

Check 3, user attestation. After you confirm, the system records a content fingerprint. From then on, any edit makes the scripts stop and ask for a new confirmation.

[Pause] Someone will ask: why so strict? Because we have seen too many cases of "the profile was written three months ago, the product changed long ago, and the AI still sends e-mails with the old wording". The fingerprint prevents exactly that.

[One line] The gate's essence: state clearly "who we are, what we sell, whom we look for" before any automation starts.

---

## Layer two: the Data Access Layer (8 min)

[Say]
This layer is new in v3.1 and is configured right after the gate. One premise first: this tool ships with no customer database at all. All customer data is yours, and at install you declare one of three states: already imported, synced from CRM, or none yet.

The layer has five boxes, left to right:

Box one, external exports. The export from the trade SaaS, customs-data platform or CRM you already use, as Excel or CSV, goes into an inbox folder and the system reminds you to import it.
Box two, own customer DB import. This is required at install. The key rule: existing customers, do-not-contact and peers never enter the cold-outreach pool. Do-not-contact addresses go to the blacklist automatically.
Box three, the sending channel. Three routes: a business mailbox connected directly with a client key; several mailboxes hosted with warm-up tiers that step up volume and pause automatically when the bounce rate is exceeded; or an MCP connector that only creates drafts for you to send manually.
Box four, CRM sync. Export in HubSpot, Salesforce, OKKI and similar formats, or push directly. Pushing is a dry run by default; a real push must be switched on explicitly.
Box five, Data Triggers. One scan a day: is the pool big enough, are there new files, which follow-ups are due, are there new replies, are bounces abnormal. The results go into a to-do queue.

[Pause] Stress one design principle here: the triggers only "remind" and "stop", they never "send". The only automatic action is pausing a mailbox when its bounces look abnormal. Every other outbound action needs a human decision. Ask the audience: if the system sent automatically, what is the worst case?

[One line] The Data Access Layer plugs in what you already have (customer DB, mailboxes, CRM) so the later steps have raw material, but it makes no outbound decision for you.

---

## The self-replenishing engine: four-axis rotation (6 min)

[Say]
The green block on the left is the self-replenishing engine. Its problem: the customer pool must neither dry up nor be used up in one go.

It runs once a day at a fixed time and first checks the pool: are there at least 100 sendable cold candidates, and at least 30 days of reserve. If not, it replenishes.

Replenishment rotates four axes, the core change in v3.1:

- Depth rotates fastest. Day one finds companies, day two finds the decision makers in those companies, day three deep-dives the stock: peers of existing customers, peers of success cases.
- Reach moves regions from near to far. Hit the most familiar market first, then expand.
- Height moves customer tiers from high to low. Hit the ideal tier first, then go down.
- Breadth rotates slowest. Keywords widen slowly from core terms to broad terms.

[Pause] Why does Depth rotate fastest and Breadth slowest? Let the audience think. The answer: for the same batch of companies, finding the decision makers is worth more than switching to another batch; and once keywords widen, noise rises sharply, so it moves last.

[One line] Four-axis rotation guarantees that today's queries differ from yesterday's, but not randomly; a market counts as covered only when a full cycle is done.

---

## Step 0: Omni-channel Review (3 min)

[Say]
Why is there a "Step 0"? Because before every round, you look at the conclusions of the last one. How were the wins made, what did WhatsApp feed back, which changes did last week's review write back. Those conclusions live in a place called "this week's conclusions" and are the starting point of this round.

[One line] Searching without reviewing means starting from zero every week.

---

## Step 1: Search Candidates (5 min)

[Say]
Public search only. 15 discovery channels, public search queries for 10 social platforms, 30 procurement-chain titles. Every action that needs a login — connection requests, DMs, joining groups — is marked "manual" and never executed by a script.

The red area on the right is the Three Iron Rules of Search, sitting between search and research:

First, check the DB first. Compare the list you found with your own customer DB; anything that is not a truly new customer does not come in.
Second, funnel diagnosis. Watch the conversion of every stage. Duplicates in the DB above 40% mean the queries hit old ground; a named-mailbox rate below 20% means you mostly found generic mailboxes. Both mean: change the search direction.
Third, pending into the pool. Wide entry, strict sending. Without a named mailbox the lead is tagged pending; before sending, a real person's mailbox must be found.

[Pause] Ask: why wide entry and strict sending? Because entering the pool costs nothing, while sending costs sender reputation.

[One line] The quality metric of search is not "how many found" but "how many are truly new, and how many have a named mailbox".

---

## Step 2: Background Research (5 min)

[Say]
This is the core of the whole flow and the step that can never be skipped. Five sources, three research principles, and the most important one: the brand name does not decide the need; research does.

Evidence has three tiers: S1 is what the company says publicly itself, S2 is a credible third party, S3 is a guess. The rule: at least one S1, or two independent S2, before a customer gets a tag. S3 only means "need review": a human decides, the AI draws no conclusion.

E-mails may quote S1 and S2 facts only.

[Pause] Counter-example: seeing "Organic" in a company name and pushing the organic-certification line — that is S3. The right move is to look for a certification page on its website; only when found is it S1.

[One line] Research decides the need; the evidence tier decides whether it may go into the e-mail.

---

## Step 3: Need Positioning (3 min)

[Say]
Dual tags: the need tag decides which product line to push, the solution tag decides which hook to use. Both come from research evidence.

There is a conflict check: if the positioning rules say "never push this solution to this kind of customer", the system blocks it and hands it to a human.

[One line] Tags are the output of research, not an input made up on the spot.

---

## Step 4: Write Content (4 min)

[Say]
A few hard rules: write the whole e-mail in the recipient's native language; 120 words or fewer; plain text, no images; quote S1 and S2 facts only; follow-ups must change the angle and bring new information, never "just a reminder".

After writing come the three pre-send checks: is the mailbox named, has it been de-duplicated, are the notes complete. Any failure goes back for correction.

[Pause] Why 120 words? Let the audience describe the cold e-mails they receive and at what length they close them.

[One line] One e-mail, one verified fact, one question.

---

## Step 5: Send (5 min)

[Say]
Before sending, do a dry run: read every subject, body and local time window, and only send for real after confirming.

Rules: send only to named decision makers; send in the recipient's local weekday morning and afternoon windows; no more than 200 a day; 30 seconds apart. Outside the window the e-mail is deferred this round, not dropped.

The sending channel is one of the three routes configured in the Data Access Layer. With hosted mailboxes, each mailbox has a cap per warm-up tier and the next one takes over when the cap is reached. Every e-mail carries an unsubscribe header and an opt-out line automatically.

[One line] Sending is the only truly outbound action in the whole flow, so dry run, window, cap and opt-out are all mandatory.

---

## Step 6: Follow-up Management (5 min)

[Say]
Scan bounces and replies every 24 to 48 hours. The mailbox is opened read-only; nothing inside it is changed.

Cadence: e-mail follows cooldowns of 3 days, 3 days, 10 days, four e-mails at most. Social DMs follow 1, 3, 7, 21 days. One customer, one channel per day.

Four exits:
- Bounce: blacklist, stop for good, back to the pool for replenishment.
- Reply: to a human. Quotes, lead times and enquiry replies must be confirmed by a person. An explicit refusal stops every channel.
- No reply: continue by cooldown; at the fourth e-mail stop generic mailboxes and use LinkedIn or a personal mailbox only.
- Order: into the Win Review.

[Pause] Ask: why stop generic mailboxes at the fourth e-mail? Because sending more only damages sender reputation; switching channels beats adding attempts.

[One line] Follow-up is not "send more times"; it is changing angle and channel on a cadence, and stopping on time.

---

## Step 7: WhatsApp Trigger (5 min)

[Say]
WhatsApp is not a first-contact channel; it is triggered. Any one of three signals starts it: three or more e-mails without reply; a high-value customer goes straight to WhatsApp; the customer gave their number.

Bulk sending has anti-ban iron rules: validate the list first — number format, duplicates, empty messages, unreplaced placeholders — any failure blocks sending. Send to your own test number first. The real run sends one by one, 8 to 15 seconds apart, and stops hard at 200. Afterwards, check the screenshots.

WhatsApp has its own review: funnel, broken down by region, need and hook.

[One line] WhatsApp rules are stricter than e-mail because the cost of a ban is the whole number, not one e-mail.

---

## Step 8: Win Review and kit write-back (5 min)

[Say]
This closes the loop, once a week.

Won customers go into the success-case library, but the pain point must be the version confirmed by the user; the AI only lists candidates.
The omni-channel review breaks results down by region, need tag, hook type and channel to see which path wins most. Win attribution tells you whether e-mail or WhatsApp performs better and which region deserves more weight.
Kit write-back: what was answered wrong, missed or overstepped this week goes back into the matching file — change the rule, not just one sentence.
Finally re-run the health check, write the conclusions into "this week's conclusions", and the next round starts there.

[Pause] Return to the opening question: three months later, can you trace "why we sent it to this person"? The answer is here — because every round's conclusions are written back into the files.

[One line] The output of a review is not a report; it is a change to the files.

---

## Bottom: the data layer and the iron rules (3 min)

[Say]
At the very bottom is the data layer that runs through everything: customer DB, send history, blacklist, WhatsApp contacts, success cases, pipeline, mailbox usage, CRM sync log. Send records pass through a single script: de-dup before sending, record after sending, blacklist on bounce.

Three iron rules to close:
Scripts read customer data and never edit it on their own.
Pain points, tags, sending, CRM pushes and quotes are all human decisions.
Keys live in environment variables only, never in any file.

---

## Closing and Q&A (5 min)

[Say]
Back to the three opening questions:

Can we trace it? Every e-mail maps to one customer, one tag, one piece of evidence, one send record.
Can we hand it over? A new hire installs the tool, the gate tells them what to fill in, the flowchart tells them which command to run at each step.
Does the AI have brakes? Gate, fingerprint, dry run, window, cap, human sign-off — six of them.

Last sentence: this SOP does not guarantee a win rate. It guarantees that every failure tells you where it went wrong and where to fix it.

---

## Frequently asked questions

| Audience may ask | Suggested answer |
|---|---|
| Why not pull lists straight from a big database? | You can; the Data Access Layer exists for that. But those lists still go through research and named-mailbox verification. It saves search time, not judgement. |
| Is four-axis rotation too slow? | A full cycle is 72 runs, roughly two and a half months to cover one market. Slow by design: never use up a market in one go, never hit the same ground twice. |
| Where do the warm-up tier numbers come from? | They are adjustable defaults with no industry-standard source. Tune them to your own mailbox's bounce history. |
| Can the AI reply to customers automatically? | No. Every reply goes to a human. The AI may draft; a person must press send. |
| Does the opt-out line hurt reply rates? | The sender guidelines of the major mailbox providers require one-click unsubscribe for bulk mail; leaving it out hurts inbox placement instead. |
