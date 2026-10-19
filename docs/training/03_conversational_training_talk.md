# B2B Customer Development SOP v3.1 · Conversational training talk

> For: in-house training of front-line salespeople or new hires; reads naturally even when delivered word for word. About 45 minutes.
> Difference from the "full training script": the explanatory tone is gone; it is spoken language, uses "you" and "we" a lot, and leans on scenarios.
> Text in parentheses is a note for the speaker, not to be read aloud.

---

## Opening

Hi everyone. In this hour I am not going to teach you how to write e-mails or how to search for customers. You can all do that to some degree.

I am going to talk about one chart. This chart deals with three things that give everyone a headache.

First: has this ever happened to you? You sent an e-mail three months ago, the customer suddenly replies today, and you cannot remember why you wrote to them or what you said.

Second: a colleague leaves and hands over an Excel sheet with a few hundred customers, a line of notes next to each one, and you have no idea what those notes mean.

Third: everyone uses AI to write e-mails now. Have you thought about who catches it when the AI gets it wrong or sends it to the wrong person?

(Pause two seconds, look around the room.)

This chart was drawn for those three things. Let's walk it from top to bottom.

---

## Block one: before we start, close the gate

Look at the top of the chart: three boxes, called the Install Gate.

What does that mean? After you install this tool, it is not usable right away. It asks you for three things first, and until they are complete, none of the search or send scripts will move.

Thing one, the company profile. What we do, what form the product takes, where we are different, what titles we want to reach. Note: at least two differentiators and at least one title. Why so demanding? Because how the search queries are generated and how the e-mails are written all comes from here. If this is empty, everything downstream is empty.

Thing two, the seven files for the AI. Who you are, what you must never do, what the boss likes and dislikes, how to keep working notes. These seven files get a health check. Some people try to save effort by flipping "filled" to true. That does not pass. It checks whether you wrote empty shells that say nothing, and whether sample text was left unreplaced.

Thing three, your own confirmation. After you confirm, the system records a fingerprint.

The fingerprint matters, so a word more. After you confirm, if a single character in the files changes, the scripts stop and say: the files changed, read them again and confirm again.

Why so much trouble? We learned the hard way. The profile was written three months ago, the product changed long ago, and the AI was still sending the old wording. The fingerprint prevents that.

(You can ask: how long since your product information was last updated?)

Remember one line: say clearly who we are, what we sell and whom we look for, before any automation starts working.

---

## Block two: plug in what you already have

Gate passed; don't rush to search yet. Look at the second row, the Data Access Layer, five boxes.

A premise first. This tool ships with no customer data at all, not a single row. The customers are all yours. At install it asks: where does your customer DB come from? An Excel you already have to import, a CRM to sync from, or nothing yet. One of three, and you must answer.

Then the five boxes, left to right.

Box one: the trade software, customs data or CRM you already use. Export the sheet, drop it into a folder, and the system reminds you to import it.

Box two: import your own customer DB. One rule to remember: existing customers, do-not-contact and peers never enter the cold pool. Do-not-contact addresses go to the blacklist automatically. However you search later, even if you find these people again, nothing can be sent to them.

Box three: the sending channel. Three routes. A business mailbox connected directly with a client key — the most common. If you have several mailboxes, host them and the system steps up volume by warm-up tier and stops any mailbox whose bounces climb. The third route is an MCP connector: it only creates drafts, and you decide whether to press send.

Box four: CRM sync. Export in HubSpot, Salesforce, OKKI and similar formats. Pushing into the CRM is a dry run by default — it only shows you what it would push, it does not push. To push for real you switch it on yourself.

Box five: Data Triggers. Runs once a day and checks for you: is the pool big enough, are there new files to import, which customers are due for follow-up, has anyone replied, are bounces abnormal. The result is a to-do list.

One point I want to stress. The triggers do only two things: remind you, or stop a mailbox that is misbehaving. They never send anything for you.

(You can ask: if it sent automatically, what is the worst that could happen? Let people answer.)

Remember one line: data access plugs in what you already have so the later steps have raw material, but it makes no outbound decision for you.

---

## Block three: how the pool never dries up

Look at the green block on the left, the self-replenishing engine.

Anyone who has done outreach knows the two fears. One: you keep searching and run out. Two: you hit every customer in a market in one go, and then there is nothing left.

This engine runs once a day at a fixed time. It checks the pool first: at least 100 new customers ready to send, enough for 30 days. If not, it replenishes.

Replenishing is not random; it rotates four axes.

Depth rotates fastest. Today find companies, tomorrow find the decision makers inside them, the day after deep-dive the stock: peers of existing customers, peers of success cases.

Reach goes region by region from near to far. The most familiar market first.

Height goes tier by tier from high to low. The ideal tier first.

Breadth rotates slowest. Keywords widen slowly from core to broad.

(Ask: why is Depth fastest and Breadth slowest?)

My take: for the same batch of companies, finding the decision makers is worth more than switching batches. And once the keywords loosen, the junk in the results explodes, so that moves last.

A full cycle is 72 runs, roughly two and a half months, and only then is a market covered. Slow on purpose.

Remember one line: the queries differ every day, but not at random.

---

## Block four: Step 0, look at last week first

Why is there a "Step 0"?

Because before every round you look at the conclusions of the last one. How the wins were made, what WhatsApp fed back, which rules last week's review changed. All of that sits in a place called "this week's conclusions".

Searching without looking there means starting from zero every week.

---

## Block five: searching, three iron rules

Step 1, Search Candidates. Public search only: 15 discovery channels, 10 social platforms, 30 procurement-chain titles. Anything that needs a login — adding contacts, sending DMs, joining groups — is marked "manual" and the scripts never touch it. The scripts only generate the queries; they never log into any platform for you.

Before what you found goes into the pool, the red area on the right holds three iron rules.

Rule one: check the DB first. Compare the list with your own customer DB; existing customers, people already contacted and do-not-contact do not come in.

Rule two: watch the funnel. Look at the conversion of every stage. Duplicates in the DB above forty percent mean your queries keep hitting the same people — change direction. A named rate below twenty percent means you mostly found info@-type generic mailboxes — change direction too.

Rule three: wide entry, strict sending. Leads without a named mailbox come in tagged pending. But before sending, a real person's mailbox must be found.

(Ask: why wide entry and strict sending? Answer: entering the pool costs nothing; sending costs your mailbox's reputation.)

Remember one line: search quality is not how many you found, but how many are truly new and how many have a real person's mailbox.

---

## Block six: research, never skip it

Step 2, Background Research. The most important step in the whole flow, and the one most easily skipped.

One principle: the brand name does not decide the need; research does.

An example. You find a company with "Organic" in its name. Do you immediately want to pitch the organic-certification line? Wait. The name is only your guess. Go to their website and look for a certification page. If you find it, that is evidence.

Evidence has three tiers. S1: what the company says publicly itself — website, annual report, job ads. S2: credible third parties — trade media, customs records. S3: your guess.

The rule: at least one S1, or two independent S2, before a customer gets a tag. S3 only means "need review": a person decides, the AI draws no conclusion.

E-mails may quote S1 and S2 facts only. What you guessed cannot go in.

Step 3, Need Positioning, produces two tags. One: which product line to push. Two: which hook to use. Both come from research evidence. If the rules say "never push this solution to this kind of customer", the system blocks it.

Remember one line: research decides the need; the evidence tier decides whether it can go into the e-mail.

---

## Block seven: writing and sending

Step 4, writing the e-mail. A few hard rules.

Write the whole e-mail in the recipient's native language, not just the greeting. 120 words or fewer. Plain text, no images, no attachments. Only the S1 and S2 facts we just talked about. Follow-ups must change the angle and bring new information; never "just a quick reminder".

(Ask: when you receive a cold e-mail, how long before you close it?)

After writing, three checks: is the mailbox named, has it been de-duplicated, are the notes complete. Any failure goes back for fixing.

Step 5, sending. Dry run first. In the dry run the system lists every e-mail's subject, body and the recipient's current local time for you; only after you confirm does it send for real.

Sending rules: named decision makers only. Send in the recipient's local weekday morning and afternoon windows; outside the window it is deferred, not dropped. At most 200 a day, 30 seconds apart. With several hosted mailboxes, each has a cap per warm-up tier and the next one takes over at the cap. Every e-mail carries an opt-out automatically.

Remember one line: sending is the only truly outbound action on the whole line, so dry run, window, cap and opt-out — none of the four can be missing.

---

## Block eight: managing after sending

Step 6, follow-up.

Scan bounces and replies every 24 to 48 hours. The mailbox is opened read-only; nothing in it changes.

Cadence: e-mail cooldowns of 3 days, 3 days, 10 days, four e-mails at most. Social DMs at 1, 3, 7, 21 days. One customer, one channel per day; never e-mail and WhatsApp together.

Four exits.

Bounce: blacklist, permanent stop, and a new lead enters the pool to replace it.

Reply: to a human. Quotes, lead times, enquiries all need a person's confirmation. If the customer clearly says no, every channel stops.

No reply: continue by cooldown. If the fourth e-mail still gets no reply, stop generic mailboxes and use LinkedIn or a personal mailbox only.

(Ask: why stop at the fourth? Answer: sending more only hurts mailbox reputation; switching channels works better than adding attempts.)

Order placed: into the Win Review.

Remember one line: follow-up is not sending more times; it is changing angle and channel on a cadence, and stopping on time.

---

## Block nine: WhatsApp, stricter rules

Step 7, WhatsApp.

To be clear, WhatsApp is not a first-contact channel. One of three signals starts it: three or more e-mails without reply; a high-value customer goes straight to WhatsApp; the customer gave their number.

Bulk sending has anti-ban iron rules.

Validate the list first. Wrong number format, duplicates, empty messages, unreplaced placeholders — any failure and nothing goes out.

Send to your own test number first.

The real run goes one by one, 8 to 15 seconds apart, hard stop at 200. Then check the screenshots.

Why so strict? One wrong e-mail loses one customer. A WhatsApp ban loses the whole number and every chat on it.

WhatsApp also has its own review: funnel, region, need, hook.

---

## Block ten: review, closing the loop

Step 8, once a week.

Won customers go into the success-case library. But note: the pain point must be the version you confirmed; the AI only lists candidates.

The omni-channel review breaks results down by region, need tag, hook type and channel to see which path wins most. Win attribution tells you whether e-mail or WhatsApp works better and which region deserves more.

Then the write-back. What was answered wrong, missed or overstepped this week goes back into the matching file. Change the rule, not just one sentence.

Re-run the health check, write the conclusions into "this week's conclusions", and the next round starts there.

(Back to the opening.) Remember the first question? Can we trace it three months later? The answer is in this step. Because every round's conclusions are written back into the files, not kept in someone's head.

Remember one line: the output of a review is not a report; it is a change to the files.

---

## Closing

At the bottom of the chart is the data layer — customer DB, send history, blacklist and so on — running through everything. Send records pass through a single script: de-dup before, record after, blacklist on bounce.

Three iron rules.

Scripts read; they never edit customer data on their own.

Pain points, tags, sending, CRM pushes, quotes: all decided by people.

Keys live in environment variables only, never in any file.

Back to the three opening questions.

Can we trace it? Every e-mail maps to one customer, one tag, one piece of evidence, one send record.

Can we hand it over? A new hire installs the tool, the gate tells them what to fill in, the flowchart tells them what to run at each step.

Does the AI have brakes? Gate, fingerprint, dry run, window, cap, human sign-off. Six.

Last sentence. This SOP does not guarantee your win rate. It guarantees that every time you fail, you know where it went wrong and where to fix it.

Questions are welcome now.

---

## Q&A reference

**Someone asks: why not just buy a big database and send to the list?**
You can; the Data Access Layer is for that. But the list still goes through research and named-mailbox verification. It saves search time, not judgement.

**Someone asks: two and a half months per rotation cycle — isn't that too slow?**
Slow on purpose. Burning a market in one go and hitting the same people twice is what is really slow.

**Someone asks: where do the warm-up numbers come from?**
They are defaults we set; there is no industry standard. Tune them to your own mailbox's bounce rate.

**Someone asks: can the AI reply to customers automatically?**
No. The AI may draft; a person must press send.

**Someone asks: does the opt-out line lower reply rates?**
The sender rules of the major mailbox providers require one-click unsubscribe for bulk mail. Without it, the e-mail may never reach the inbox.
