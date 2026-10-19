# Detailed customer search SOP

**Version**: v3.1 | **Updated**: 2026-10-19  
**Scenario**: finding candidate customers from zero, verifying mailboxes, finding decision makers

---

## 📍 1. Search channels (where to look)

### 1.1 Main channels

| Channel | Priority | Best for | How |
|------|--------|----------|----------|
| **Google search** | ⭐⭐⭐⭐⭐ | generic, widest coverage | keyword combinations |
| **LinkedIn** | ⭐⭐⭐⭐⭐ | finding decision makers, verifying companies | advanced search + company pages |
| **Trade-show exhibitor lists** | ⭐⭐⭐⭐ | high-quality B2B customers | PDF/Excel download from the show website |
| **Industry directories / B2B platforms** | ⭐⭐⭐⭐ | verified company lists | ThomasNet / Kompass / Europages / Clutch / association directories |
| **Competitor customer reverse-lookup** | ⭐⭐⭐ | precise but needs skill | competitor case studies / customer logos |
| **Industry association member lists** | ⭐⭐⭐ | high quality, small volume | association member directories |
| **Instagram / Facebook / X** | ⭐⭐ | finds small companies, little contact data | company name → website → contact |
| **Public tender / procurement portals** | ⭐⭐⭐⭐ | project-based, institutional, service procurement | keyword + region search of notices |
| **Hiring signals** | ⭐⭐⭐⭐ | software / services / equipment & consumables: hiring = budget | job keyword + region |
| **Review / ecosystem sites** | ⭐⭐⭐ | software, professional services | G2 / Capterra / Clutch / partner directories |

### 1.2 Detailed procedures per channel follow below.

---

## 🔍 2. Google search SOP

### 2.1 Keyword formula

```
query = {market} + {category} + {role term} + {qualifier}
```

**Role-term bank · customer spectrum** (from `targeting.customer_levels`, pre-fillable by industry packs; full explanation in `search_guide.md`):
```
structure: L{n} {tier name} : {terms this tier uses for itself / is called online}

physical goods   L1 channel partners: importer, wholesale, distributor   L2 brands: brand, private label   L3 retail: retailer, store chain
industrial       L1 OEM: OEM, machine builder                           L2 distribution: industrial distributor  L3 integration: system integrator
SaaS             L1 ICP: <industry> company, scale-up                   L2 competitor users: "<competitor> customer"  L3 partners: implementation partner
services         L1 SMEs: SME, family business                          L2 expanding: "expanding to", new office  L3 referrals: partner agency
project-based    L1 main contractors: general contractor                L2 designers: architect, MEP consultant   L3 owners: developer
```
> Generate every combination at once: `python3 scripts/search_customers.py queries --out queries.txt` (`--levels` runs only some tiers).

**Qualifier bank** (optional, pick per industry for precision):
```
physical / industrial: B2B, trade, bulk, import, OEM, ODM, private label, RFQ
software / services:   B2B, enterprise, SME, "case study", "request for proposal", hiring
project-based:         tender, "bid invitation", specification, project
```

### 2.2 Query examples

**Your own industry (replace placeholders with your profile's primary_keywords)**:
```
"UK <your-core-term> <customer-type-1>"
"Germany <related-term> <customer-type-2> B2B"
"USA <your-core-term> <buyer-title>"
"Italy <your-core-term> <customer-type-3>"
```

**European markets (always rebuild the query in the local language; patterns below)**:
```
"France <local-language product term> <local-language customer-type term>"
"Italy <local-language product term> <local-language customer-type term>"   # Italian
"Deutschland <local-language product term> Großhandel"                   # German
"España <local-language product term> mayorista"                         # Spanish
```

**Generic B2B**:
```
"{country} {product} {customer_type}"
"{country} {product} {buyer_title}"
"{country} {product} request for proposal"
```

### 2.3 Google search steps

```python
# step 1: build the queries
search_queries = [
    f"{market} {product} {customer_type}",      # customer_type from targeting.channel_keywords
    f"{market} {product} {customer_type} B2B",
    f"{market} {product} {buyer_title}",        # buyer_title from targeting.buyer_titles
    f"{market} {customer_industry} company",    # software / services: by the customer's industry (targeting.customer_industries)
]

# step 2: search one by one, extract results
candidates = []
for query in search_queries:
    results = google_search(query, num_pages=3)  # first 3 pages
    
    for result in results:
        # extract: company name, website URL, description
        candidate = {
            "brand": extract_brand_name(result.title),
            "website": result.url,
            "description": result.snippet,
            "source": "google",
            "search_query": query
        }
        candidates.append(candidate)

# step 3: de-dup (by domain)
candidates = deduplicate_by_domain(candidates)

# step 4: first filter (drop the obviously invalid)
valid_candidates = []
for c in candidates:
    IF is_valid_domain(c["website"]):
        valid_candidates.append(c)
```

---

## 👤 3. Finding decision makers on LinkedIn

### 3.1 Why LinkedIn?

- **Direct to the decision maker**: the actual buyer's name + title
- **Company verification**: is the company active, how big, which industry
- **Contact leads**: some public e-mails, WA numbers

### 3.2 LinkedIn search steps

```python
# step 1: search companies
company_search_queries = [
    f"{product} {market}",
    f"{product} {customer_type} {market}",
    f"{customer_industry} company {market}"     # software / services: by the customer's industry
]

companies = []
for query in company_search_queries:
    results = linkedin_company_search(query)
    for company in results:
        companies.append({
            "name": company.name,
            "website": company.website,
            "size": company.size,
            "industry": company.industry,
            "linkedin_url": company.url
        })

# step 2: open the company page, find the decision makers matching buyer_titles
for company in companies:
    # search people inside the company
    people_search_queries = [
        f"company:{company.name} buyer",
        f"company:{company.name} {buyer_title}",
        f"company:{company.name} procurement",
        f"company:{company.name} purchasing manager"
    ]
    
    decision_makers = []
    for query in people_search_queries:
        people = linkedin_people_search(query)
        for person in people:
            decision_makers.append({
                "name": person.name,
                "title": person.title,
                "company": company.name,
                "linkedin_url": person.url,
                "location": person.location
            })
    
    company["decision_makers"] = decision_makers

# step 3: extract key information
for company in companies:
    for person in company["decision_makers"]:
        # try to extract a public e-mail from the LinkedIn page
        IF person.linkedin_url contains "contact_email":
            person["email"] = extract_email(person.linkedin_url)
        
        # try to extract a WA number
        IF person.linkedin_url contains "whatsapp":
            person["whatsapp"] = extract_whatsapp(person.linkedin_url)
```

### 3.3 LinkedIn title priority

**Look for these titles first** (by priority; procurement examples below — when selling software / services / projects replace them with `targeting.buyer_titles` such as CTO / HR director / project director):
```
1. Head of Buying / Buying Director
2. Buyer / Senior Buyer
3. Procurement Manager / Procurement Director
4. Sourcing Manager / Sourcing Director
5. Purchasing Manager
6. Product Manager (if no buying role)
7. Supply Chain Manager
8. Owner / Founder (for small companies)
```

---

## 📧 4. Multi-round e-mail verification SOP

### 4.1 E-mail source priority

```
priority 1: e-mail published on LinkedIn (most reliable)
priority 2: named e-mail on the website About / Contact page
priority 3: functional mailbox on the website (purchasing@ / partners@ / trade@ / projects@ …)
priority 4: guessed from decision-maker name + domain
priority 5: info@/contact@ generic mailboxes (no decision maker behind them, not recommended)
```

### 4.2 Three-round verification

```python
def validate_email_multi_round(email, brand, domain, contact_person=None):
    """
    three-round e-mail verification:
    1. format + MX record
    2. domain consistency
    3. blacklist / cooldown
    """
    
    validation_result = {
        "email": email,
        "valid": False,
        "reason": "",
        "round_passed": 0
    }
    
    # ========== round 1: format + MX ==========
    
    # 1.1 format
    IF not is_valid_email_format(email):
        validation_result["reason"] = "invalid e-mail format"
        RETURN validation_result
    
    # 1.2 domain
    email_domain = extract_domain(email)
    
    # 1.3 MX record (dns_validator.py)
    mx_valid = dns_validator.validate(email_domain)
    IF not mx_valid:
        validation_result["reason"] = f"domain {email_domain} has no MX record, cannot receive mail"
        RETURN validation_result
    
    validation_result["round_passed"] = 1
    
    # ========== round 2: domain consistency ==========
    
    # 2.1 does the e-mail domain match the company website domain?
    brand_domain = extract_domain(brand.website)
    
    IF email_domain != brand_domain:
        # special case: sub-domain or related domain
        IF not is_related_domain(email_domain, brand_domain):
            validation_result["reason"] = f"e-mail domain {email_domain} does not match company domain {brand_domain}"
            RETURN validation_result
    
    # 2.2 generic mailbox?
    IF is_generic_email(email):
        validation_result["reason"] = f"generic mailbox {email} has no decision maker behind it; find a named mailbox"
        validation_result["warning"] = "generic_email"
        # not returned as false, but flagged
    
    validation_result["round_passed"] = 2
    
    # ========== round 3: blacklist / cooldown ==========
    
    # 3.1 blacklisted?
    check_result = csv_ops.check(email)
    
    IF check_result == "blacklisted":
        validation_result["reason"] = "e-mail is blacklisted"
        RETURN validation_result
    
    # 3.2 in cooldown?
    IF check_result == "in_cooldown":
        cooldown_info = csv_ops.cooldown(email)
        validation_result["reason"] = f"e-mail in cooldown, sendable in {cooldown_info.days_left} days"
        validation_result["cooldown_until"] = cooldown_info.cooldown_until
        RETURN validation_result
    
    # 3.3 moved to WA?
    IF check_result == "wa_only":
        validation_result["reason"] = "customer moved to the WA channel, no e-mail"
        RETURN validation_result
    
    # 3.4 duplicate?
    IF check_result == "duplicate":
        validation_result["reason"] = "already sent, no duplicate sending"
        RETURN validation_result
    
    # 3.5 cross-brand de-dup
    IF csv_ops.cross_brand_check(email_domain) == "duplicate":
        validation_result["reason"] = "cross-brand duplicate, several brands of the same owner"
        RETURN validation_result
    
    validation_result["round_passed"] = 3
    
    # ========== all passed ==========
    validation_result["valid"] = True
    validation_result["reason"] = "all three rounds passed"
    
    RETURN validation_result
```

### 4.3 Verification commands

```bash
# round 1: MX
python3 scripts/dns_validator.py input.json output.json

# rounds 2+3: combined (de-dup + blacklist + cooldown)
python3 scripts/csv_ops.py check <email>

# cross-brand de-dup
python3 scripts/csv_ops.py cross_brand_check <domain>

# cooldown query
python3 scripts/csv_ops.py cooldown <email>
```

---

## 🎯 5. Finding decision-maker e-mails

### 5.1 Method 1: directly from LinkedIn (most reliable)

```python
# step 1: find decision makers on the company page
people = linkedin_search(company_name, role=profile.targeting.buyer_titles)

# step 2: open the profile, read public contact info
for person in people:
    IF person.linkedin_page contains "email":
        email = extract_email(person.linkedin_page)
        person["email"] = email
    
    IF person.linkedin_page contains "whatsapp":
        wa = extract_whatsapp(person.linkedin_page)
        person["whatsapp"] = wa

# step 3: verify (three rounds)
for person in people:
    IF person.email:
        validation = validate_email_multi_round(person.email, company, domain, person.name)
        IF validation.valid:
            person["email_validated"] = True
```

### 5.2 Method 2: website About / Contact page

```python
# step 1: open the Contact page
contact_page = fetch(brand.website + "/contact")

# step 2: extract e-mails
emails = extract_emails(contact_page)

# step 3: prioritise
priority_emails = []
for email in emails:
    IF local_part(email) in FUNCTION_PREFIXES:   # purchasing/partners/trade/projects...
        priority_emails.append((email, "high"))
    ELIF "buyer" in email OR "purchasing" in email:
        priority_emails.append((email, "high"))
    ELIF "info" in email OR "contact" in email:
        priority_emails.append((email, "low"))  # generic, not recommended
    ELSE:
        priority_emails.append((email, "medium"))

# step 4: verify the high-priority ones
for email, priority in priority_emails:
    IF priority == "high":
        validation = validate_email_multi_round(email, brand, domain)
        IF validation.valid:
            RETURN email
```

### 5.3 Method 3: e-mail pattern guessing (email_guesser.py)

**When**: the decision maker's name is known but not the e-mail pattern

```python
# step 1: input
input_data = [
    {
        "brand": "Brand Name",
        "contact_person": "Hannah Smith",
        "website": "https://brand.example",
        "domain": "brand.example"
    }
]

# step 2: run the guesser
# python3 scripts/email_guesser.py input.json output.json

# step 3: the tool derives 9 common patterns
guessed_emails = [
    "hannah.smith@brand.example",      # firstname.lastname
    "hsmith@brand.example",            # flast
    "hannah_s@brand.example",          # first_last
    "hannah@brand.example",            # firstname
    "smith.hannah@brand.example",      # lastname.firstname
    "hs@brand.example",                # fi
    "hannahsmith@brand.example",       # firstlast
    "smithh@brand.example",            # lastfi
    "s.hannah@brand.example"           # last.first
]

# step 4: MX check every guess
for email in guessed_emails:
    domain = extract_domain(email)
    IF dns_validator.validate(domain):
        # MX valid, keep
        valid_guesses.append(email)

# step 5: pick the most likely pattern
# firstname.lastname@ is usually the most common corporate pattern
best_guess = valid_guesses[0] if valid_guesses else None

# step 6: test e-mail (optional, use with care)
# when unsure, a short confirmation e-mail can go first
```

### 5.4 Method 4: Hunter.io / Apollo.io and similar tools

**When**: the company domain is known; batch lookup of e-mails and decision makers  
**Pros / cons**:
- ✅ efficient in batch, with confidence scores
- ❌ limited free quota, paid API

```python
# Hunter.io API — search e-mails by domain
def hunter_io_search(domain):
    api_key = os.getenv("HUNTER_IO_API_KEY")
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    emails = []
    for email_data in data["data"]["emails"]:
        emails.append({
            "email": email_data["value"],
            "first_name": email_data["first_name"],
            "last_name": email_data["last_name"],
            "position": email_data["position"],
            "confidence": email_data["confidence"]  # confidence score
        })
    
    RETURN emails

# Apollo.io API — search decision makers by company + title
def apollo_search(company_name):
    api_key = os.getenv("APOLLO_API_KEY")
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    data = {
        "api_key": api_key,
        "q_organization_domains": extract_domain(company_name),
        "person_titles": profile["targeting"]["buyer_titles"]   # e.g. ["procurement manager"] / ["CTO"] / ["HR director"]
    }
    response = requests.post(url, headers=headers, json=data)
    results = response.json()
    
    people = []
    for person in results["people"]:
        people.append({
            "name": f"{person['first_name']} {person['last_name']}",
            "email": person["email"],
            "title": person["title"],
            "linkedin_url": person["linkedin_url"]
        })
    
    RETURN people
```

**Combining with other methods**: after finding the decision maker's name on LinkedIn, verify and complete the e-mail with Hunter.io / Apollo

---

### 5.5 Method 5: Chrome extensions (Hunter.io / Apollo / Lusha / Kaspr / ContactOut)

**When**: one-click extraction of decision-maker e-mails on LinkedIn pages; good for small, precise batches  
**Pros / cons**:
- ✅ very simple: install → open the LinkedIn profile → click the extension → e-mail extracted
- ✅ free quotas cover small batches (quotas change; check each vendor's current pricing page)
- ✅ several extensions can be stacked
- ❌ free quotas are limited, not for large batches
- ❌ depends on LinkedIn's page structure and anti-automation measures

**Steps**:
```python
# step 1: install the Chrome extensions
# search the Chrome Web Store for these (install at least 2 as backups):
extensions = ["Hunter.io", "Apollo", "Lusha", "Kaspr", "ContactOut"]

# step 2: open the target LinkedIn profile
for person in decision_makers:
    open_browser(person.linkedin_url)

# step 3: click the extension icon → e-mail extracted
# Hunter.io: all e-mails of the company + confidence score
# Apollo: decision-maker e-mail + phone
# Lusha: e-mail + mobile
# Kaspr: LinkedIn e-mail + phone
# ContactOut: e-mail + phone + social media

# step 4: extract and verify
for extension in extensions:
    IF extension.has_result():
        email = extension.get_email()
        confidence = extension.get_confidence()
        IF confidence >= 80:
            person["email"] = email
            person["email_source"] = extension.name
            BREAK  # stop at the first high-confidence e-mail
```

**Combining**: LinkedIn decision maker (method 1) → Chrome extension e-mail (method 5) → three-round verification (§4)

---

### 5.6 Method 6: customs data (ImportGenius / Panjiva)

**When** (physical goods / logistics): verify whether a customer really imports similar products; find real importers + contacts  
**Pros / cons**:
- ✅ real data (based on bills of lading, not guesses)
- ✅ verifies that the customer actually imports your category
- ✅ finds competitors' customers (reverse poaching)
- ❌ paid tools (check the vendors' pricing pages)
- ❌ some countries publish no customs data (parts of the EU)

**Steps**:
```python
# step 1: search by HS code or product name
# ImportGenius / Panjiva support HS code or keyword search
search_queries = [
    f"HS:{hs_code} importer {target_country}",  # HS code
    f"{product_name} importer {target_country}"    # product name
]

# step 2: read the bills of lading
for query in search_queries:
    results = importgenius_search(query)
    for shipment in results:
        # a bill of lading includes: importer, exporter, product, quantity, date
        importer = {
            "company_name": shipment.importer_name,
            "origin": shipment.exporter_name,
            "product": shipment.product_description,
            "quantity": shipment.quantity,
            "date": shipment.shipment_date
        }
        importers.append(importer)

# step 3: importer name → website → decision makers
for importer in importers:
    # find the website via Google
    website = google_search(f"{importer['company_name']} official website")
    
    # verify they really import your category
    IF product_category in importer["product"].lower():
        importer["verified_importer"] = True
        importer["website"] = website
        # find decision makers on the website (methods 1–4)
        importer["decision_makers"] = find_decision_makers(website)
```

**Combining**: customs data verifies real imports → Google / LinkedIn for website and decision makers → e-mail contact

---

### 5.7 Method 7: trade-show data (speakers / exhibitor lists)

**When**: exhibitors are the highest-quality B2B customers; speakers are the highest-value decision makers  
**Pros / cons**:
- ✅ exhibitors are verified active buyers / sellers
- ✅ speakers / panel guests are industry KOLs, publicly active with contact details
- ✅ show websites usually offer PDF / Excel list downloads
- ❌ time-sensitive (lists may be stale after the show)
- ❌ lists may lack direct contacts

**Steps**:
```python
# step 1: search industry shows
exhibition_sources = [
    f"{target_market} {product} trade show 2026",
    f"{target_market} {product} exhibition exhibitor list",
    f"trade fair {product} {target_country}"
]

# step 2: open the show website → download the exhibitor list
for source in exhibition_sources:
    results = google_search(source)
    for result in results:
        IF "exhibitor list" IN result.url OR "download" IN result.url:
            # download the PDF / Excel list
            exhibitor_data = download_file(result.url)
            # parse PDF with parse_file, Excel with csv
            
            # extract company + contact
            for entry in exhibitor_data:
                exhibitors.append({
                    "company": entry.company_name,
                    "booth": entry.booth_number,  # if any
                    "contact": entry.contact_name,  # if any
                    "email": entry.email,  # if any
                    "website": entry.website,  # if any
                    "source": "exhibition"
                })

# step 3: focus on speakers / panel guests
# speakers = highest-value decision makers (publicly active + reachable)
speakers = extract_speakers(exhibition_website)
for speaker in speakers:
    speaker["priority"] = "highest"  # speakers first
    # search the e-mail directly
    speaker["email"] = find_email(speaker.name, speaker.company)

# step 4: complete exhibitor decision makers with the usual methods
for exhibitor in exhibitors:
    IF not exhibitor.contact:
        exhibitor.decision_makers = linkedin_search(exhibitor.company, role="buyer")
```

**Combining**: shows provide candidate companies → LinkedIn / Chrome extensions for decision-maker e-mails → usual verification

---

### 5.8 Method 8: Instagram / social-media reverse lookup

**When**: small or founder-led companies with little website contact data but active social media (LinkedIn / IG / X in any industry)  
**Pros / cons**:
- ✅ finds small companies invisible in search engines
- ✅ company posts often tag the founder / person in charge
- ✅ short decision chains, the founder decides
- ❌ contact data needs a reverse lookup (social → website → e-mail)
- ❌ not for large companies (better channels exist)

**Steps**:
```python
# step 1: search company names / industry hashtags
search_queries = [
    f"#{product}",
    f"#{product}{customer_type}",       # customer_type from targeting.channel_keywords
    f"{brand_name}"  # when the company name is known
]

# step 2: browse company posts → find founder / person in charge
for post in instagram_posts:
    # captions / bios often say:
    # "Founded by @username" / "Head of X: @username"
    IF "founded by" IN post.caption OR "owner" IN post.bio:
        founder = extract_mention(post.caption)
        person = {
            "name": founder,
            "role": "founder",
            "instagram": f"@{founder}",
            "brand": post.account_name,
            "brand_website": post.account.bio.link  # the bio link is usually the website
        }
        found_contacts.append(person)

# step 3: website → e-mail
for person in found_contacts:
    IF person.brand_website:
        # Contact / About page
        emails = extract_emails_from_website(person.brand_website)
        person["email"] = emails[0] if emails else None
        
        IF not person.email:
            # e-mail guesser
            guessed = email_guesser.guess(person.name, extract_domain(person.brand_website))
            person["email"] = guessed

# step 4: verify (three rounds)
```

**Combining**: social media finds the company → website → methods 2/3 for the e-mail → verification

---

### 5.9 Method 9: competitor customer reverse-lookup

**When**: find customers already using a similar product from competitor websites; precise poaching  
**Pros / cons**:
- ✅ the need is verified (using a competitor says it all)
- ✅ high conversion (known need + known supply pain)
- ✅ competitor About / Press / Case Study / logo pages are public
- ❌ you need to know who the competitors are
- ❌ may touch commercially sensitive ground

**Steps**:
```python
# step 1: competitor list
competitors = search_competitors(product_category)

# step 2: extract customers from competitor websites
for competitor in competitors:
    # 2.1 case studies / success stories
    case_studies = fetch(competitor.website + "/case-studies")
    for case in case_studies:
        clients.append({
            "brand": case.client_name,
            "website": case.client_website,
            "source": f"competitor:{competitor.name}",
            "context": case.description  # the customer's specific need
        })
    
    # 2.2 customer logo wall
    client_logos = extract_logos(competitor.website + "/clients")
    for logo in client_logos:
        clients.append({
            "brand": logo.name,
            "website": logo.link,
            "source": f"competitor:{competitor.name}"
        })
    
    # 2.3 partnership announcements in Press / News
    press_releases = fetch(competitor.website + "/press")
    for release in press_releases:
        IF "partner" IN release.title OR "supply" IN release.title:
            partner = extract_partner(release)
            clients.append({
                "brand": partner.name,
                "website": partner.website,
                "source": f"competitor:{competitor.name}:press"
            })

# step 3: de-dup → website → decision makers
clients = deduplicate_by_domain(clients)
for client in clients:
    client.decision_makers = linkedin_search(client.brand, role=profile.targeting.buyer_titles)
    client.emails = find_emails(client)
```

**Combining**: competitor website customers → LinkedIn decision makers → Chrome extension e-mails → verification

---

### 5.10 Method 10: Xing (German-speaking region)

**When**: the professional network of the DACH market (Germany / Austria / Switzerland)  
**Pros / cons**:
- ✅ widely used by DACH business people, often more active there than on LinkedIn
- ✅ company search → decision makers, similar to LinkedIn
- ❌ only for the German-speaking market
- ❌ paid premium tier (check the official price), limited free features

**Steps**:
```python
# step 1: register a Xing account (premium recommended)
# https://www.xing.com

# step 2: search DACH target companies
search_queries = [
    f"{product} {market}",         # e.g. "<your-product-term> Deutschland"
    f"{product} Großhandel",       # German
    f"{product} Einkauf"           # "Einkauf" = procurement
]

# step 3: decision makers
for company in xing_search_results:
    people = xing_people_search(company.name, role="Einkäufer/Buyer")
    for person in people:
        contacts.append({
            "name": person.name,
            "title": person.title,
            "company": company.name,
            "xing_url": person.profile_url,
            "email": person.email if person.email_visible else None,
            "region": "DACH",
            "source": "xing"
        })

# step 4: e-mail → verification
for contact in contacts:
    IF not contact.email:
        # e-mail guesser
        guessed = email_guesser.guess(contact.name, contact.domain)
        contact.email = guessed
    # three rounds
    contact.validated = validate_email_multi_round(contact.email)
```

**Combining**: Xing complements LinkedIn in DACH. IF target market = DACH → run Xing + LinkedIn in parallel

---

### 5.11 Method 11: industry association directories

**When**: association member lists are usually owner / buyer level, high-quality decision makers  
**Pros / cons**:
- ✅ contacts are usually owners / buyers (top decision level)
- ✅ members = verified industry participants
- ✅ usually include direct contacts
- ❌ small volume (dozens to a few hundred members per association)
- ❌ some directories are paywalled

**Steps**:
```python
# step 1: search associations
association_sources = [
    f"{target_market} {product} trade association",
    f"{target_market} {product} industry association members",
    f"{target_country} {product} guild directory"
]

# step 2: association website → member directory
for source in association_sources:
    results = google_search(source)
    for result in results:
        IF "member" IN result.url OR "directory" IN result.url:
            member_page = fetch(result.url)
            
            # extract members
            for member in extract_members(member_page):
                members.append({
                    "company": member.name,
                    "contact": member.contact_name,  # usually owner / director
                    "title": member.title,
                    "email": member.email,
                    "phone": member.phone,
                    "website": member.website,
                    "source": "industry_association",
                    "association": result.title
                })

# step 3: verify + complete with the usual methods
for member in members:
    IF not member.email:
        member.email = find_email_via_website(member.website)
    member.validated = validate_email_multi_round(member.email)
```

**Combining**: association contacts → verify e-mail → send directly (members usually are the decision makers)

---

### 5.12 Method 12: Clay multi-source waterfall

**When**: large, high-precision batches; pulls 50+ data sources at once for the highest coverage  
**Pros / cons**:
- ✅ aggregates 50+ sources (LinkedIn / Hunter / Apollo / Lusha / websites …)
- ✅ waterfall logic: if source 1 has nothing, sources 2, 3 … are tried automatically
- ✅ highest automation, suited to large-scale development
- ❌ paid tool (check the official price)
- ❌ steeper learning curve

**Steps**:
```python
# step 1: create a Clay table, import the target company list
# Clay supports CSV import or direct search

# step 2: configure Waterfall Enrichment
# choose "Find work email" → set source priority:
waterfall_config = {
    "source_1": "LinkedIn (via PhantomBuster)",  # highest
    "source_2": "Hunter.io",
    "source_3": "Apollo",
    "source_4": "Lusha",
    "source_5": "Kaspr",
    "source_6": "ContactOut",
    "source_7": "RocketReach",
    "source_8": "website guess (derived from the known e-mail pattern)",
    "fallback": "flag as email_not_found"
}
# Clay tries each source in order automatically

# step 3: run the waterfall → results
results = clay.run_waterfall_enrichment(waterfall_config)

# step 4: coverage
total = len(results)
found = sum(1 for r in results if r.email_found)
coverage = found / total * 100
print(f"e-mail coverage: {coverage}% ({found}/{total})")

# step 5: complete the rest manually with other methods
unfound = [r for r in results if not r.email_found]
for company in unfound:
    # try Instagram reverse lookup / customs data / associations
    try_alternative_sources(company)
```

**Combining**: Clay is the batch-automated version of methods 1–5. Large batches → Clay; small precise needs → manual methods; what Clay cannot find → niche channels

---

### 5.12b Methods 13–15: tender portals / hiring signals / review and ecosystem sites (first choice for software, services, project-based)

| Method | Where | Why it works | Script channel |
|---|---|---|---|
| Tender portals | national public procurement sites (TED, SAM.gov, local government portals), industry tender platforms | budget, need and deadline are all there | `channels --ch tender` |
| Hiring signals | LinkedIn Jobs, company careers pages, job boards | hiring = investing in this; job descriptions state pains and tools in use | `channels --ch hiring` |
| Review / ecosystem sites | G2, Capterra, Clutch, app marketplaces, partner directories | shows who uses competitors, who compares solutions, who looks for partners | `channels --ch review partners` |
| Conference lists | sponsors / speakers pages of industry summits | decision makers public and active | `channels --ch events` |

Same procedure as the other methods: company → website → decision maker matching `buyer_titles` → three-round verification → pool.

### 5.13 Method priority table (practical)

| Method | Scenario | Cost | E-mail quality | Efficiency | Status |
|------|---------|------|---------|------|----------|
| 1. LinkedIn direct | generic | free | ⭐⭐⭐⭐⭐ | medium | ✅ **usable** |
| 2. Website About / Contact | generic | free | ⭐⭐⭐⭐ | high | ✅ **usable** |
| 3. E-mail pattern guessing | decision-maker name known | free | ⭐⭐⭐ | high | ✅ **usable** |
| 4. Hunter.io / Apollo API | batch domain lookup | paid | ⭐⭐⭐⭐ | high | ⚠️ registration needed |
| 5. Chrome extensions | one-click on LinkedIn | free quota | ⭐⭐⭐⭐ | very high | ⚠️ **install needed** (a free Hunter.io account is recommended) |
| 6. Customs data | verify real importers (physical goods / logistics) | paid | ⭐⭐⭐ | medium | ❌ **not now** (use competitor reverse-lookup instead) |
| 7. Trade-show data | high-quality B2B customers | partly free | ⭐⭐⭐⭐ | medium | ✅ **usable** (free lists on show websites) |
| 8. Social reverse lookup | small / founder-led companies | free | ⭐⭐ | low | ✅ **usable** |
| 9. Competitor reverse-lookup | precise poaching | free | ⭐⭐⭐⭐ | medium | ✅ **usable** (highly recommended) |
| 10. Xing | DACH market | paid (official price) | ⭐⭐⭐⭐ | medium | ❌ **not now** (use LinkedIn instead) |
| 11. Association directories | high-quality owners / buyers | free | ⭐⭐⭐⭐⭐ | low | ✅ **usable** |
| 12. Clay waterfall | large high-precision batches | paid (official price) | ⭐⭐⭐⭐ | very high | ❌ **not now** (costly; other channels suffice) |
| 13. Tender portals | project-based / institutional / services | mostly free | ⭐⭐⭐⭐ | medium | ✅ **usable** |
| 14. Hiring signals | software / services / equipment & consumables | free | ⭐⭐⭐⭐ | high | ✅ **usable** |
| 15. Review / ecosystem sites | software / professional services | free | ⭐⭐⭐ | medium | ✅ **usable** |

---

### 5.14 Practical priority order

**✅ Usable now (free, no registration)**:
1. LinkedIn direct search
2. Website About page
3. Competitor reverse-lookup
4. Trade-show lists (free download from show websites)
5. Instagram reverse lookup
6. Association directories

**⚠️ One-time registration**:
- Apollo free account (quota per the official site)
- Hunter.io Chrome extension (free quota per the official site)

**❌ Not now**:
- Customs data (ImportGenius / Panjiva) → competitor reverse-lookup instead
- Xing → LinkedIn for German customers instead
- Clay → too costly; other channels suffice

---

## 🔄 6. Complete customer search workflow (15 methods)

```python
def complete_customer_search_workflow(target_market, target_product):
    """
    complete search workflow (v3.0 — 15 methods; methods 13–15 in 5.12b):
    0. channel priority decision → best channel mix
    1. multi-channel search → candidate companies
    2. decision-maker lookup → combination of the 15 methods
    3. e-mail collection → multi-source merge
    4. three-round verification → valid e-mails
    5. e-mail guessing → complete decision-maker e-mails
    6. output → final candidate list
    """
    
    # ========== stage 0: channel priority ==========
    print("🎯 stage 0: choosing the channel mix...")
    
    channels = []
    
    # IF target market = DACH → Xing first
    IF target_market == "DACH" OR target_market IN ["DE", "AT", "CH"]:
        channels.append("xing")           # method 10
        channels.append("linkedin")       # method 1
        channels.append("google")         # default
        PRINT "🇩🇪 DACH: Xing + LinkedIn + Google")
    
    # IF real imports must be verified → customs data
    ELIF verification_mode == "verify_importer":
        channels.append("customs_data")   # method 6
        channels.append("linkedin")       # method 1
        channels.append("google")         # default
        PRINT "📦 verify importers: customs data + LinkedIn + Google")
    
    # IF a recent industry show → show data first
    ELIF has_recent_exhibition(target_market, target_product):
        channels.append("exhibition")     # method 7
        channels.append("linkedin")       # method 1
        channels.append("google")         # default
        PRINT "🎪 recent show: show data + LinkedIn + Google")
    
    # IF small / founder-led → Instagram reverse lookup
    ELIF target_customer_type == "small_brand" OR target_customer_type == "DTC":
        channels.append("instagram")      # method 8
        channels.append("google")         # default
        channels.append("linkedin")       # method 1
        PRINT "📱 small / founder-led: Instagram + Google + LinkedIn")
    
    # IF large high-precision batch → Clay waterfall
    ELIF batch_mode == "large_scale":
        channels.append("clay")           # method 12
        PRINT "⚡ large batch: Clay waterfall")
    
    # default → LinkedIn + Chrome extensions + website
    ELSE:
        channels.append("linkedin")       # method 1
        channels.append("chrome_ext")     # method 5
        channels.append("website")        # method 2
        PRINT "🔍 default: LinkedIn + Chrome extensions + website")
    
    # extra channels (optional in every mode)
    IF has_competitors(target_product):
        channels.append("competitor_analysis")  # method 9
    IF has_industry_association(target_market, target_product):
        channels.append("association")          # method 11
    
    # ========== stage 1: multi-channel search ==========
    print(f"🔍 stage 1: multi-channel search ({len(channels)} channels)...")
    
    candidates = []
    
    for channel in channels:
        IF channel == "google":
            results = google_search_candidates(target_market, target_product)
            candidates.extend(results)
        
        ELIF channel == "linkedin":
            results = linkedin_company_search(target_product, target_market)
            candidates.extend(results)
        
        ELIF channel == "xing":
            results = xing_company_search(target_product, target_market)
            candidates.extend(results)
        
        ELIF channel == "customs_data":
            results = customs_data_search(target_product, target_market)
            candidates.extend(results)
        
        ELIF channel == "exhibition":
            results = exhibition_exhibitor_search(target_market, target_product)
            candidates.extend(results)
        
        ELIF channel == "instagram":
            results = instagram_brand_search(target_product, target_market)
            candidates.extend(results)
        
        ELIF channel == "competitor_analysis":
            results = competitor_client_extraction(target_product)
            candidates.extend(results)
        
        ELIF channel == "association":
            results = association_member_search(target_market, target_product)
            candidates.extend(results)
        
        ELIF channel == "clay":
            results = clay_waterfall_enrich(target_market, target_product)
            candidates.extend(results)
    
    # de-dup (by domain)
    candidates = deduplicate_by_domain(candidates)
    print(f"✅ {len(candidates)} candidate companies found")
    
    # ========== stage 2: decision makers (15-method combination) ==========
    print("👤 stage 2: multi-channel decision-maker lookup...")
    
    for candidate in candidates:
        decision_makers = []
        
        # LinkedIn first (method 1)
        people = linkedin_search_decision_maker(candidate["brand"])
        decision_makers.extend(people)
        
        # Xing (DACH complement, method 10)
        IF target_market IN ["DE", "AT", "CH"]:
            xing_people = xing_search_decision_maker(candidate["brand"])
            decision_makers.extend(xing_people)
        
        # Chrome extensions (method 5, one click on LinkedIn)
        for person in decision_makers:
            IF not person.email:
                ext_email = chrome_extension_extract(person.linkedin_url)
                IF ext_email:
                    person.email = ext_email
        
        # show speakers (if the source is a show, method 7)
        IF candidate.source == "exhibition":
            speakers = extract_exhibition_speakers(candidate)
            decision_makers.extend(speakers)
        
        # association members (if the source is an association, method 11)
        IF candidate.source == "association":
            # members usually are the decision makers
            pass
        
        # Instagram reverse lookup (small / founder-led, method 8)
        IF candidate.source == "instagram":
            founder = instagram_find_founder(candidate)
            IF founder:
                decision_makers.append(founder)
        
        candidate["decision_makers"] = deduplicate_people(decision_makers)
        print(f"  - {candidate['brand']}: {len(decision_makers)} decision makers found")
    
    # ========== stage 3: e-mail collection (multi-source) ==========
    print("📧 stage 3: multi-channel e-mail collection...")
    
    for candidate in candidates:
        emails = []
        
        # 3.1 from LinkedIn / Chrome extensions (methods 1+5)
        for person in candidate["decision_makers"]:
            IF person.email:
                emails.append({
                    "email": person.email,
                    "source": person.get("email_source", "linkedin"),
                    "person": person.name,
                    "title": person.title
                })
        
        # 3.2 from the website (method 2)
        contact_emails = extract_emails_from_website(candidate["website"])
        for email in contact_emails:
            emails.append({
                "email": email,
                "source": "website",
                "person": None,
                "title": None
            })
        
        # 3.3 Hunter.io / Apollo API (method 4)
        hunter_emails = hunter_io_search(extract_domain(candidate["website"]))
        for h_email in hunter_emails:
            IF h_email.confidence >= 80:
                emails.append({
                    "email": h_email.email,
                    "source": "hunter_io",
                    "person": f"{h_email.first_name} {h_email.last_name}",
                    "title": h_email.position
                })
        
        # 3.4 customs data contacts (method 6)
        IF candidate.source == "customs_data":
            customs_contacts = extract_customs_contacts(candidate)
            for contact in customs_contacts:
                emails.append({
                    "email": contact.email,
                    "source": "customs_data",
                    "person": contact.name,
                    "title": contact.title
                })
        
        # 3.5 Clay results (method 12)
        IF candidate.source == "clay":
            clay_emails = extract_clay_results(candidate)
            for c_email in clay_emails:
                emails.append({
                    "email": c_email.email,
                    "source": f"clay:{c_email.source}",
                    "person": c_email.name,
                    "title": c_email.title
                })
        
        candidate["emails"] = emails
        print(f"  - {candidate['brand']}: {len(emails)} e-mails collected")
    
    # ========== stage 4: three-round verification ==========
    print("✅ stage 4: three-round e-mail verification...")
    
    for candidate in candidates:
        valid_emails = []
        
        for email_info in candidate["emails"]:
            validation = validate_email_multi_round(
                email_info["email"], 
                candidate["brand"], 
                candidate["website"]
            )
            
            IF validation.valid:
                email_info["validated"] = True
                valid_emails.append(email_info)
            ELSE:
                email_info["validated"] = False
                email_info["invalid_reason"] = validation.reason
        
        candidate["valid_emails"] = valid_emails
        print(f"  - {candidate['brand']}: {len(valid_emails)}/{len(candidate['emails'])} e-mails valid")
    
    # ========== stage 5: e-mail guessing (completion) ==========
    print("🎯 stage 5: e-mail guessing...")
    
    for candidate in candidates:
        # decision maker known but no e-mail → guess (method 3)
        for person in candidate["decision_makers"]:
            IF not person.email:
                guessed = email_guesser.guess(person.name, extract_domain(candidate["website"]))
                IF guessed:
                    validation = validate_email_multi_round(guessed, candidate["brand"], candidate["website"])
                    IF validation.valid:
                        person["email"] = guessed
                        person["email_validated"] = True
                        candidate["valid_emails"].append({
                            "email": guessed,
                            "source": "guessed",
                            "person": person.name,
                            "title": person.title,
                            "validated": True
                        })
    
    # ========== stage 6: final list ==========
    print("📋 stage 6: generating the final candidate list...")
    
    final_candidates = []
    for candidate in candidates:
        IF len(candidate["valid_emails"]) > 0:
            final_candidates.append({
                "brand": candidate["brand"],
                "website": candidate["website"],
                "region": candidate["region"],
                "valid_emails": candidate["valid_emails"],
                "decision_makers": candidate["decision_makers"],
                "source": candidate.get("source", "google")
            })
    
    # sort by e-mail quality: named > guessed > generic
    final_candidates.sort(key=lambda c: email_quality_score(c["valid_emails"]), reverse=True)
    
    # save
    save_to_csv(final_candidates, "candidates_validated.csv")
    print(f"✅ {len(final_candidates)} valid candidates output")
    
    RETURN final_candidates
```

---

## 📊 7. Output formats

### 7.1 CSV (recommended, for csv_ops.py)

```csv
brand,website,region,email,contact_person,title,email_source,validated
Brand A,https://branda.example,UK,john@branda.example,John Smith,Buyer,linkedin,true
Brand B,https://brandb.example,DE,info@brandb.example,,,, false
Brand C,https://brandc.example,FR,marie@brandc.example,Marie Dubois,Sourcing Manager,guessed,true
```

### 7.2 JSON (script input)

```json
[
  {
    "brand": "Brand A",
    "website": "https://branda.example",
    "region": "UK",
    "email": "john@branda.example",
    "contact_person": "John Smith",
    "title": "Buyer",
    "email_source": "linkedin",
    "validated": true
  }
]
```

---

## 🛠️ 8. Tool commands

| Task | Tool | Command |
|------|------|------|
| Google search | built-in search tool | `search_web(["keywords"])` |
| LinkedIn search | browser automation | `computer_use` or `mobile_use` |
| e-mail extraction | Python script | your own or a third-party library |
| MX verification | dns_validator.py | `python3 scripts/dns_validator.py input.json` |
| e-mail guessing | email_guesser.py | `python3 scripts/email_guesser.py input.json` |
| three-round verification | csv_ops.py | `python3 scripts/csv_ops.py check <email>` |
| cross-brand de-dup | csv_ops.py | `python3 scripts/csv_ops.py cross_brand_check <domain>` |

---

**SOP version**: v3.1  
**Last updated**: 2026-10-19  
**Maintainer**: <your-brand> customer development (replace with your company / team name after first install)
