# 客户搜索详细SOP

**版本**：v3.1 | **更新日期**：2026-10-19  
**适用场景**：从0到1寻找候选客户、验证邮箱、找决策人

---

## 📍 一、客户搜索渠道（去哪找）

### 1.1 主流搜索渠道

| 渠道 | 优先级 | 适用场景 | 搜索方式 |
|------|--------|----------|----------|
| **Google搜索** | ⭐⭐⭐⭐⭐ | 通用，覆盖面广 | 关键词组合搜索 |
| **LinkedIn** | ⭐⭐⭐⭐⭐ | 找决策人、验证公司信息 | 高级搜索+公司页面 |
| **行业展会参展商名单** | ⭐⭐⭐⭐ | 高质量B2B客户 | 展会官网下载PDF/Excel |
| **行业目录/B2B平台** | ⭐⭐⭐⭐ | 已验证的公司名录 | ThomasNet/Kompass/Europages/Clutch/协会名录 |
| **竞品客户逆向分析** | ⭐⭐⭐ | 精准但需技巧 | 查竞品官网case study/客户logo |
| **行业协会会员列表** | ⭐⭐⭐ | 高质量但数量少 | 协会官网会员目录 |
| **Instagram/Facebook/X** | ⭐⭐ | 发现小公司，但联系信息少 | 公司名搜索→官网→联系 |
| **公开招标/采购门户** | ⭐⭐⭐⭐ | 项目型、机构客户、服务采购 | 关键词+地区检索公告 |
| **招聘信号** | ⭐⭐⭐⭐ | 软件/服务/设备耗材：在招=有预算 | 岗位关键词+地区 |
| **评测/生态站** | ⭐⭐⭐ | 软件、专业服务 | G2/Capterra/Clutch/合作伙伴目录 |

### 1.2 各渠道详细操作流程

---

## 🔍 二、Google搜索详细SOP

### 2.1 关键词组合公式

```
搜索公式 = {市场} + {品类} + {角色词} + {限定词}
```

**角色词库 · 客户光谱**（来自 `targeting.customer_levels`，行业包可预填；完整说明见 `search_guide.md`）：
```
结构：L{n} {层名} : {该层客户在网上自称/被称呼的词}

实体商品示例  L1 渠道商: importer, wholesale, distributor   L2 品牌方: brand, private label   L3 零售: retailer, store chain
工业品示例    L1 OEM: OEM, machine builder                  L2 分销: industrial distributor  L3 集成: system integrator
SaaS 示例     L1 ICP: <industry> company, scale-up         L2 在用竞品: "<competitor> customer"  L3 伙伴: implementation partner
服务示例      L1 中小企业: SME, family business             L2 扩张期: "expanding to", new office  L3 转介: partner agency
项目型示例    L1 总包: general contractor                   L2 设计方: architect, MEP consultant   L3 业主: developer
```
> 一键生成全组合搜索词：`python3 scripts/search_customers.py queries --out queries.txt`（可用 `--levels` 只跑部分层级）。

**限定词库**（可选，按行业挑，提高精准度）：
```
实体/工业：B2B, trade, bulk, import, OEM, ODM, private label, RFQ
软件/服务：B2B, enterprise, SME, "case study", "request for proposal", hiring
项目型：   tender, "bid invitation", specification, project
```

### 2.2 搜索示例

**你自己的行业（用建档 primary_keywords 替换占位符）**：
```
"UK <your-core-term> <customer-type-1>"
"Germany <related-term> <customer-type-2> B2B"
"USA <your-core-term> <buyer-title>"
"Italy <your-core-term> <customer-type-3>"
```

**欧洲市场（务必用当地语言重新构造搜索词，下为句式示例）**：
```
"France <local-language product term> <local-language customer-type term>"
"Italy <local-language product term> <local-language customer-type term>"   # 意大利语
"Deutschland <local-language product term> Großhandel"                   # 德语
"España <local-language product term> mayorista"                         # 西班牙语
```

**通用B2B**：
```
"{country} {product} {customer_type}"
"{country} {product} {buyer_title}"
"{country} {product} request for proposal"
```

### 2.3 Google搜索执行步骤

```python
# 步骤1：构造搜索词
search_queries = [
    f"{market} {product} {customer_type}",      # customer_type 取 targeting.channel_keywords
    f"{market} {product} {customer_type} B2B",
    f"{market} {product} {buyer_title}",        # buyer_title 取 targeting.buyer_titles
    f"{market} {customer_industry} company",    # 软件/服务：按客户所在行业（targeting.customer_industries）
]

# 步骤2：逐个搜索，提取结果
candidates = []
for query in search_queries:
    results = google_search(query, num_pages=3)  # 前3页
    
    for result in results:
        # 提取：公司名、官网URL、简介
        candidate = {
            "brand": extract_brand_name(result.title),
            "website": result.url,
            "description": result.snippet,
            "source": "google",
            "search_query": query
        }
        candidates.append(candidate)

# 步骤3：去重（按域名去重）
candidates = deduplicate_by_domain(candidates)

# 步骤4：初步筛选（排除明显无效）
valid_candidates = []
for c in candidates:
    IF is_valid_domain(c["website"]):
        valid_candidates.append(c)
```

---

## 👤 三、LinkedIn找决策人详细SOP

### 3.1 为什么用LinkedIn？

- **直达决策人**：找到具体采购负责人姓名+职位
- **验证公司信息**：确认公司是否活跃、规模、行业
- **获取联系线索**：部分公开邮箱、WA号

### 3.2 LinkedIn搜索步骤

```python
# 步骤1：搜索公司
company_search_queries = [
    f"{product} {market}",
    f"{product} {customer_type} {market}",
    f"{customer_industry} company {market}"     # 软件/服务：按客户所在行业找
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

# 步骤2：进入公司页面，找 buyer_titles 对应的决策人
for company in companies:
    # 搜索该公司内的决策人
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

# 步骤3：提取关键信息
for company in companies:
    for person in company["decision_makers"]:
        # 尝试从LinkedIn页面提取公开邮箱
        IF person.linkedin_url contains "contact_email":
            person["email"] = extract_email(person.linkedin_url)
        
        # 尝试提取WA号
        IF person.linkedin_url contains "whatsapp":
            person["whatsapp"] = extract_whatsapp(person.linkedin_url)
```

### 3.3 LinkedIn职位优先级

**优先找这些职位**（按优先级排序；以下为采购职能示例，卖软件/服务/项目时按 `targeting.buyer_titles` 替换为 CTO / HR director / project director 等）：
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

## 📧 四、邮箱验证多轮验证SOP

### 4.1 邮箱来源优先级

```
优先级1：LinkedIn公开的邮箱（最可靠）
优先级2：官网About/Contact页面的具名邮箱
优先级3：官网职能邮箱（purchasing@ / partners@ / trade@ / projects@ 等）
优先级4：通过决策人姓名+域名猜测的邮箱
优先级5：info@/contact@等通用邮箱（不对应具体决策人，不推荐）
```

### 4.2 三轮邮箱验证流程

```python
def validate_email_multi_round(email, brand, domain, contact_person=None):
    """
    三轮邮箱验证：
    1. 格式验证 + MX记录验证
    2. 域名一致性验证
    3. 黑名单/冷却期验证
    """
    
    validation_result = {
        "email": email,
        "valid": False,
        "reason": "",
        "round_passed": 0
    }
    
    # ========== 第一轮：格式 + MX记录验证 ==========
    
    # 1.1 邮箱格式检查
    IF not is_valid_email_format(email):
        validation_result["reason"] = "邮箱格式无效"
        RETURN validation_result
    
    # 1.2 提取域名
    email_domain = extract_domain(email)
    
    # 1.3 MX记录验证（用dns_validator.py）
    mx_valid = dns_validator.validate(email_domain)
    IF not mx_valid:
        validation_result["reason"] = f"域名 {email_domain} 无MX记录，无法接收邮件"
        RETURN validation_result
    
    validation_result["round_passed"] = 1
    
    # ========== 第二轮：域名一致性验证 ==========
    
    # 2.1 检查邮箱域名是否与公司官网域名一致
    brand_domain = extract_domain(brand.website)
    
    IF email_domain != brand_domain:
        # 特殊情况：可能是子域名或关联域名
        IF not is_related_domain(email_domain, brand_domain):
            validation_result["reason"] = f"邮箱域名 {email_domain} 与公司域名 {brand_domain} 不一致"
            RETURN validation_result
    
    # 2.2 检查是否为通用邮箱黑名单
    IF is_generic_email(email):
        validation_result["reason"] = f"通用邮箱 {email} 不对应具体决策人，建议找决策人具名邮箱"
        validation_result["warning"] = "generic_email"
        # 不直接返回false，但标记警告
    
    validation_result["round_passed"] = 2
    
    # ========== 第三轮：黑名单/冷却期验证 ==========
    
    # 3.1 检查是否在黑名单
    check_result = csv_ops.check(email)
    
    IF check_result == "blacklisted":
        validation_result["reason"] = "邮箱已在黑名单"
        RETURN validation_result
    
    # 3.2 检查是否在冷却期
    IF check_result == "in_cooldown":
        cooldown_info = csv_ops.cooldown(email)
        validation_result["reason"] = f"邮箱在冷却期，{cooldown_info.days_left}天后可发"
        validation_result["cooldown_until"] = cooldown_info.cooldown_until
        RETURN validation_result
    
    # 3.3 检查是否已转WA渠道
    IF check_result == "wa_only":
        validation_result["reason"] = "客户已转WA渠道，不发邮件"
        RETURN validation_result
    
    # 3.4 检查是否重复发送
    IF check_result == "duplicate":
        validation_result["reason"] = "已发送过，不可重复发送"
        RETURN validation_result
    
    # 3.5 跨品牌排重
    IF csv_ops.cross_brand_check(email_domain) == "duplicate":
        validation_result["reason"] = "跨品牌重复，同一老板旗下多品牌"
        RETURN validation_result
    
    validation_result["round_passed"] = 3
    
    # ========== 全部通过 ==========
    validation_result["valid"] = True
    validation_result["reason"] = "三轮验证全部通过"
    
    RETURN validation_result
```

### 4.3 邮箱验证命令速查

```bash
# 第一轮：MX验证
python3 scripts/dns_validator.py input.json output.json

# 第二轮+第三轮：综合验证（查重+黑名单+冷却期）
python3 scripts/csv_ops.py check <email>

# 跨品牌排重
python3 scripts/csv_ops.py cross_brand_check <domain>

# 冷却期查询
python3 scripts/csv_ops.py cooldown <email>
```

---

## 🎯 五、找决策人邮箱详细SOP

### 5.1 方法1：LinkedIn直接获取（最可靠）

```python
# 步骤1：在LinkedIn公司页面找决策人
people = linkedin_search(company_name, role=profile.targeting.buyer_titles)

# 步骤2：进入个人页面，查看公开联系信息
for person in people:
    IF person.linkedin_page contains "email":
        email = extract_email(person.linkedin_page)
        person["email"] = email
    
    IF person.linkedin_page contains "whatsapp":
        wa = extract_whatsapp(person.linkedin_page)
        person["whatsapp"] = wa

# 步骤3：验证邮箱（三轮验证）
for person in people:
    IF person.email:
        validation = validate_email_multi_round(person.email, company, domain, person.name)
        IF validation.valid:
            person["email_validated"] = True
```

### 5.2 方法2：官网About/Contact页面

```python
# 步骤1：访问官网Contact页面
contact_page = fetch(brand.website + "/contact")

# 步骤2：提取邮箱
emails = extract_emails(contact_page)

# 步骤3：筛选优先级
priority_emails = []
for email in emails:
    IF local_part(email) in FUNCTION_PREFIXES:   # purchasing/partners/trade/projects...
        priority_emails.append((email, "high"))
    ELIF "buyer" in email OR "purchasing" in email:
        priority_emails.append((email, "high"))
    ELIF "info" in email OR "contact" in email:
        priority_emails.append((email, "low"))  # 通用邮箱，不推荐
    ELSE:
        priority_emails.append((email, "medium"))

# 步骤4：验证高优先级邮箱
for email, priority in priority_emails:
    IF priority == "high":
        validation = validate_email_multi_round(email, brand, domain)
        IF validation.valid:
            RETURN email
```

### 5.3 方法3：邮箱格式猜测（email_guesser.py）

**适用场景**：知道决策人姓名，但不知道邮箱格式

```python
# 步骤1：准备输入数据
input_data = [
    {
        "brand": "Brand Name",
        "contact_person": "Hannah Smith",
        "website": "https://brand.example",
        "domain": "brand.example"
    }
]

# 步骤2：运行邮箱猜测工具
# python3 scripts/email_guesser.py input.json output.json

# 步骤3：工具自动推导9种常见格式
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

# 步骤4：对每个猜测邮箱进行MX验证
for email in guessed_emails:
    domain = extract_domain(email)
    IF dns_validator.validate(domain):
        # MX有效，保留
        valid_guesses.append(email)

# 步骤5：选择最可能的格式
# 通常 firstname.lastname@ 是最常见的企业邮箱格式
best_guess = valid_guesses[0] if valid_guesses else None

# 步骤6：发送测试邮件验证（可选，谨慎使用）
# 如果不确定，可以先发一封简短的确认邮件
```

### 5.4 方法4：Hunter.io / Apollo.io 等工具

**适用场景**：已有公司域名，批量查找该公司邮箱和决策人  
**优劣势**：
- ✅ 批量查询效率高，有可信度评分
- ❌ 免费版额度有限，API需要付费

```python
# Hunter.io API — 按域名搜索邮箱
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
            "confidence": email_data["confidence"]  # 可信度评分
        })
    
    RETURN emails

# Apollo.io API — 按公司+职位搜索决策人
def apollo_search(company_name):
    api_key = os.getenv("APOLLO_API_KEY")
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    data = {
        "api_key": api_key,
        "q_organization_domains": extract_domain(company_name),
        "person_titles": profile["targeting"]["buyer_titles"]   # 如 ["procurement manager"] / ["CTO"] / ["HR director"]
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

**与现有方法的配合**：在LinkedIn找到决策人姓名后，用Hunter.io/Apollo验证并补充邮箱

---

### 5.5 方法5：Chrome扩展工具（Hunter.io / Apollo / Lusha / Kaspr / ContactOut）

**适用场景**：在LinkedIn页面一键提取决策人邮箱，适合小批量精准查找  
**优劣势**：
- ✅ 操作极简：安装扩展→打开LinkedIn profile→点击扩展→自动提取邮箱
- ✅ 免费额度够小批量使用（Hunter.io 25次/月，Lusha 5次/月，Kaspr 2次/周）
- ✅ 多个扩展可叠加使用，互为补充
- ❌ 免费版额度有限，不适合大批量
- ❌ 依赖LinkedIn页面结构，LinkedIn反爬可能影响

**操作步骤**：
```python
# 步骤1：安装Chrome扩展
# 在Chrome Web Store搜索安装以下扩展（至少装2个互备）：
extensions = ["Hunter.io", "Apollo", "Lusha", "Kaspr", "ContactOut"]

# 步骤2：打开目标LinkedIn profile页面
for person in decision_makers:
    open_browser(person.linkedin_url)

# 步骤3：点击扩展图标 → 自动提取邮箱
# Hunter.io：显示该公司所有邮箱 + 可信度评分
# Apollo：显示决策人邮箱 + 电话
# Lusha：显示邮箱 + 手机号
# Kaspr：显示LinkedIn邮箱 + 电话
# ContactOut：显示邮箱 + 电话 + 社交媒体

# 步骤4：提取并验证
for extension in extensions:
    IF extension.has_result():
        email = extension.get_email()
        confidence = extension.get_confidence()
        IF confidence >= 80:
            person["email"] = email
            person["email_source"] = extension.name
            BREAK  # 找到高可信度邮箱即可停止
```

**与现有方法的配合**：LinkedIn找决策人（方法1）→ Chrome扩展提取邮箱（方法5）→ 三轮验证（§四）

---

### 5.6 方法6：海关数据（ImportGenius / Panjiva）

**适用场景**（实体商品/物流）：验证客户是否真的在进口同类产品，找到真实进口商+联系人  
**优劣势**：
- ✅ 数据真实可靠（基于海关提单，不是猜测）
- ✅ 能验证客户是否真的在进口你的品类
- ✅ 能找到竞争对手的客户（反向挖角）
- ❌ 付费工具（ImportGenius $99/月起）
- ❌ 部分国家海关数据不公开（如EU部分国家）

**操作步骤**：
```python
# 步骤1：搜索HS编码或产品名称
# ImportGenius / Panjiva 支持按HS编码或关键词搜索
search_queries = [
    f"HS:{hs_code} importer {target_country}",  # HS编码搜索
    f"{product_name} importer {target_country}"    # 产品名称搜索
]

# 步骤2：查看海关提单
for query in search_queries:
    results = importgenius_search(query)
    for shipment in results:
        # 提单中包含：进口商名称、出口商、品名、数量、日期
        importer = {
            "company_name": shipment.importer_name,
            "origin": shipment.exporter_name,
            "product": shipment.product_description,
            "quantity": shipment.quantity,
            "date": shipment.shipment_date
        }
        importers.append(importer)

# 步骤3：提取进口商名称 → 反查官网 → 找决策人
for importer in importers:
    # 去Google搜索公司官网
    website = google_search(f"{importer['company_name']} official website")
    
    # 验证是否真的在进口你的品类
    IF product_category in importer["product"].lower():
        importer["verified_importer"] = True
        importer["website"] = website
        # 进入官网找决策人（用方法1-4）
        importer["decision_makers"] = find_decision_makers(website)
```

**与现有方法的配合**：海关数据验证进口真实性 → Google/LinkedIn找官网和决策人 → 邮件联系

---

### 5.7 方法7：展会数据（演讲者/参展商名录）

**适用场景**：展会参展商是最高质量的B2B客户，演讲者是最高价值决策人  
**优劣势**：
- ✅ 参展商是已验证的活跃买家/卖家
- ✅ 演讲者/论坛嘉宾是行业KOL，公开活跃+有联系方式
- ✅ 展会官网通常提供PDF/Excel名录下载
- ❌ 展会数据有时效性（展后可能更新不及时）
- ❌ 名录可能缺少直接联系方式

**操作步骤**：
```python
# 步骤1：搜索行业展会
exhibition_sources = [
    f"{target_market} {product} trade show 2026",
    f"{target_market} {product} exhibition exhibitor list",
    f"trade fair {product} {target_country}"
]

# 步骤2：进入展会官网 → 下载参展商名录
for source in exhibition_sources:
    results = google_search(source)
    for result in results:
        IF "exhibitor list" IN result.url OR "download" IN result.url:
            # 下载PDF/Excel名录
            exhibitor_data = download_file(result.url)
            # PDF用parse_file解析，Excel用csv读取
            
            # 提取公司名+联系人
            for entry in exhibitor_data:
                exhibitors.append({
                    "company": entry.company_name,
                    "booth": entry.booth_number,  # 如有
                    "contact": entry.contact_name,  # 如有
                    "email": entry.email,  # 如有
                    "website": entry.website,  # 如有
                    "source": "exhibition"
                })

# 步骤3：重点关注演讲者/论坛嘉宾
# 演讲者 = 最高价值决策人（公开活跃+有联系方式）
speakers = extract_speakers(exhibition_website)
for speaker in speakers:
    speaker["priority"] = "highest"  # 演讲者优先级最高
    # 直接搜索邮箱
    speaker["email"] = find_email(speaker.name, speaker.company)

# 步骤4：对参展商用常规方法补充决策人信息
for exhibitor in exhibitors:
    IF not exhibitor.contact:
        exhibitor.decision_makers = linkedin_search(exhibitor.company, role="buyer")
```

**与现有方法的配合**：展会获取候选公司 → LinkedIn/Chrome扩展找决策人邮箱 → 常规验证

---

### 5.8 方法8：Instagram/社媒反查

**适用场景**：小公司/创始人主导的公司，官网联系信息少但社媒活跃（任何行业的 LinkedIn/IG/X 都适用）  
**优劣势**：
- ✅ 能发现搜索引擎上不显眼的小公司
- ✅ 公司帖子中常标注创始人/负责人
- ✅ 小公司决策链短，创始人直接决策
- ❌ 联系信息需要反查（从社媒→官网→邮箱）
- ❌ 大公司不适合（联系信息已有更好的渠道获取）

**操作步骤**：
```python
# 步骤1：在社媒搜索公司名/行业标签
search_queries = [
    f"#{product}",
    f"#{product}{customer_type}",       # customer_type 取 targeting.channel_keywords
    f"{brand_name}"  # 已知公司名时
]

# 步骤2：浏览公司帖子 → 找创始人/负责人信息
for post in instagram_posts:
    # 公司帖子的caption/bio中常提到：
    # "Founded by @username" / "Head of X: @username"
    IF "founded by" IN post.caption OR "owner" IN post.bio:
        founder = extract_mention(post.caption)
        person = {
            "name": founder,
            "role": "founder",
            "instagram": f"@{founder}",
            "brand": post.account_name,
            "brand_website": post.account.bio.link  # bio链接通常是官网
        }
        found_contacts.append(person)

# 步骤3：反查官网 → 找邮箱
for person in found_contacts:
    IF person.brand_website:
        # 访问官网Contact/About页面找邮箱
        emails = extract_emails_from_website(person.brand_website)
        person["email"] = emails[0] if emails else None
        
        IF not person.email:
            # 用邮箱猜测工具
            guessed = email_guesser.guess(person.name, extract_domain(person.brand_website))
            person["email"] = guessed

# 步骤4：验证邮箱（三轮验证）
```

**与现有方法的配合**：社媒发现公司→反查官网→方法2/3获取邮箱→验证

---

### 5.9 方法9：竞品客户逆向分析

**适用场景**：从竞品官网找到已在使用同类产品的客户，精准挖角  
**优劣势**：
- ✅ 客户已验证有该品类需求（正在使用竞品说明一切）
- ✅ 转化率高（已知需求+已知供应痛点）
- ✅ 竞品官网About/Press/Case Study/客户logo公开可得
- ❌ 需要了解竞品是谁
- ❌ 可能涉及商业敏感问题

**操作步骤**：
```python
# 步骤1：确定竞品列表
competitors = search_competitors(product_category)

# 步骤2：从竞品官网提取客户信息
for competitor in competitors:
    # 2.1 Case Study / Success Stories
    case_studies = fetch(competitor.website + "/case-studies")
    for case in case_studies:
        clients.append({
            "brand": case.client_name,
            "website": case.client_website,
            "source": f"competitor:{competitor.name}",
            "context": case.description  # 了解客户的具体需求
        })
    
    # 2.2 客户logo墙
    client_logos = extract_logos(competitor.website + "/clients")
    for logo in client_logos:
        clients.append({
            "brand": logo.name,
            "website": logo.link,
            "source": f"competitor:{competitor.name}"
        })
    
    # 2.3 Press / News中的合作公告
    press_releases = fetch(competitor.website + "/press")
    for release in press_releases:
        IF "partner" IN release.title OR "supply" IN release.title:
            partner = extract_partner(release)
            clients.append({
                "brand": partner.name,
                "website": partner.website,
                "source": f"competitor:{competitor.name}:press"
            })

# 步骤3：去重 → 搜索官网 → 找决策人
clients = deduplicate_by_domain(clients)
for client in clients:
    client.decision_makers = linkedin_search(client.brand, role=profile.targeting.buyer_titles)
    client.emails = find_emails(client)
```

**与现有方法的配合**：竞品官网提取客户→LinkedIn找决策人→Chrome扩展提邮箱→验证

---

### 5.10 方法10：Xing（德语区专用）

**适用场景**：DACH市场（德国/奥地利/瑞士）的专业商务社交平台  
**优劣势**：
- ✅ DACH市场2200万用户，德国市场必备
- ✅ 德语区商务人士更活跃于Xing而非LinkedIn
- ✅ 搜索公司→找决策人，操作类似LinkedIn
- ❌ 仅适用于德语区市场
- ❌ €12.99/月（Premium版），免费版功能有限

**操作步骤**：
```python
# 步骤1：注册Xing账号（Premium版推荐）
# https://www.xing.com

# 步骤2：搜索DACH市场目标公司
search_queries = [
    f"{product} {market}",         # 如 "<your-product-term> Deutschland"
    f"{product} Großhandel",       # 德语搜索
    f"{product} Einkauf"           # "Einkauf" = 采购
]

# 步骤3：找决策人
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

# 步骤4：提取邮箱 → 验证
for contact in contacts:
    IF not contact.email:
        # 用邮箱猜测工具
        guessed = email_guesser.guess(contact.name, contact.domain)
        contact.email = guessed
    # 三轮验证
    contact.validated = validate_email_multi_round(contact.email)
```

**与现有方法的配合**：Xing是LinkedIn在DACH市场的补充。IF 目标市场=DACH → 优先用Xing+LinkedIn并行

---

### 5.11 方法11：行业协会目录

**适用场景**：行业协会会员名录通常是Owner/Buyer级别，高质量决策人  
**优劣势**：
- ✅ 会员名录中联系人通常是Owner/Buyer级别（最高决策层）
- ✅ 协会会员=已验证的行业参与者
- ✅ 通常包含直接联系方式
- ❌ 数量少（一个协会可能只有几十到几百会员）
- ❌ 部分协会目录需要付费查看

**操作步骤**：
```python
# 步骤1：搜索行业协会
association_sources = [
    f"{target_market} {product} trade association",
    f"{target_market} {product} industry association members",
    f"{target_country} {product} guild directory"
]

# 步骤2：访问协会官网 → 查看会员目录
for source in association_sources:
    results = google_search(source)
    for result in results:
        IF "member" IN result.url OR "directory" IN result.url:
            member_page = fetch(result.url)
            
            # 提取会员信息
            for member in extract_members(member_page):
                members.append({
                    "company": member.name,
                    "contact": member.contact_name,  # 通常是Owner/Director
                    "title": member.title,
                    "email": member.email,
                    "phone": member.phone,
                    "website": member.website,
                    "source": "industry_association",
                    "association": result.title
                })

# 步骤3：对会员用常规方法验证+补充
for member in members:
    IF not member.email:
        member.email = find_email_via_website(member.website)
    member.validated = validate_email_multi_round(member.email)
```

**与现有方法的配合**：协会获取联系人→验证邮箱→直接发信（协会会员通常就是决策人，无需再找人）

---

### 5.12 方法12：Clay多源瀑布

**适用场景**：大批量高精度需求，同时拉50+数据源，覆盖率最高  
**优劣势**：
- ✅ 同时聚合50+数据源（LinkedIn/Hunter/Apollo/Lusha/官网等）
- ✅ 瀑布逻辑：源1没有自动试源2源3，最大化覆盖率
- ✅ 自动化程度最高，适合大规模开发
- ❌ 付费工具（$149/月起）
- ❌ 学习曲线较陡

**操作步骤**：
```python
# 步骤1：在Clay中创建Table，导入目标公司列表
# Clay支持CSV导入或直接搜索

# 步骤2：配置Waterfall Enrichment（瀑布式数据拉取）
# 选择"Find work email" → 配置多个数据源优先级：
waterfall_config = {
    "source_1": "LinkedIn (via PhantomBuster)",  # 最高优先
    "source_2": "Hunter.io",
    "source_3": "Apollo",
    "source_4": "Lusha",
    "source_5": "Kaspr",
    "source_6": "ContactOut",
    "source_7": "RocketReach",
    "source_8": "官网猜测（根据已知邮箱格式推导）",
    "fallback": "标记为email_not_found"
}
# Clay自动按优先级依次尝试，源1没有自动试源2源3

# 步骤3：运行Waterfall → 获取结果
results = clay.run_waterfall_enrichment(waterfall_config)

# 步骤4：分析覆盖率
total = len(results)
found = sum(1 for r in results if r.email_found)
coverage = found / total * 100
print(f"邮箱覆盖率: {coverage}% ({found}/{total})")

# 步骤5：对覆盖率不足的，手动用其他方法补充
unfound = [r for r in results if not r.email_found]
for company in unfound:
    # 尝试Instagram反查/海关数据/协会等
    try_alternative_sources(company)
```

**与现有方法的配合**：Clay是方法1-5的批量自动化版本。大批量需求用Clay→小批量精准需求用手动方法→Clay找不到的用冷门渠道补充

---

### 5.12b 方法13–15：招标门户 / 招聘信号 / 评测与生态站（软件、服务、项目型首选）

| 方法 | 去哪找 | 为什么有效 | 脚本渠道 |
|---|---|---|---|
| 招标门户 | 各国公共采购网（TED、SAM.gov、本地政府采购网）、行业招标平台 | 有预算、有需求、有截止日 | `channels --ch tender` |
| 招聘信号 | LinkedIn Jobs、公司 careers 页、招聘网站 | 在招 = 在投入这件事；岗位描述写着痛点和在用工具 | `channels --ch hiring` |
| 评测/生态站 | G2、Capterra、Clutch、应用市场、合作伙伴目录 | 能看到谁在用竞品、谁在比方案、谁在找伙伴 | `channels --ch review partners` |
| 会议名录 | 行业峰会 sponsors / speakers 页 | 决策人公开且活跃 | `channels --ch events` |

操作同其他方法：拿到公司 → 官网 → `buyer_titles` 对应决策人 → 三轮邮箱验证 → 入池。

### 5.13 方法优先级总表（实操版）

| 方法 | 适用场景 | 成本 | 邮箱质量 | 效率 | 实操状态 |
|------|---------|------|---------|------|----------|
| 1. LinkedIn直接获取 | 通用 | 免费 | ⭐⭐⭐⭐⭐ | 中 | ✅ **可用** |
| 2. 官网About/Contact | 通用 | 免费 | ⭐⭐⭐⭐ | 高 | ✅ **可用** |
| 3. 邮箱格式猜测 | 已知决策人姓名 | 免费 | ⭐⭐⭐ | 高 | ✅ **可用** |
| 4. Hunter.io/Apollo API | 批量域名查询 | 付费 | ⭐⭐⭐⭐ | 高 | ⚠️ 需注册 |
| 5. Chrome扩展 | LinkedIn页面一键提取 | 免费额度 | ⭐⭐⭐⭐ | 极高 | ⚠️ **需安装**（推荐注册Hunter.io免费账号） |
| 6. 海关数据 | 验证真实进口商（实体商品/物流） | 付费 | ⭐⭐⭐ | 中 | ❌ **暂不操作**（用竞品逆向替代） |
| 7. 展会数据 | 高质量B2B客户 | 免费部分 | ⭐⭐⭐⭐ | 中 | ✅ **可用**（展会官网免费名录） |
| 8. 社媒反查 | 小公司/创始人主导 | 免费 | ⭐⭐ | 低 | ✅ **可用** |
| 9. 竞品客户逆向 | 精准挖角 | 免费 | ⭐⭐⭐⭐ | 中 | ✅ **可用**（重点推荐） |
| 10. Xing | DACH市场 | 付费（以官网为准） | ⭐⭐⭐⭐ | 中 | ❌ **暂不操作**（用LinkedIn替代） |
| 11. 行业协会目录 | 高质量Owner/Buyer | 免费 | ⭐⭐⭐⭐⭐ | 低 | ✅ **可用** |
| 12. Clay多源瀑布 | 大批量高精度 | 付费（以官网为准） | ⭐⭐⭐⭐ | 极高 | ❌ **暂不操作**（成本高，其他渠道够用） |
| 13. 招标门户 | 项目型/机构客户/服务 | 多数免费 | ⭐⭐⭐⭐ | 中 | ✅ **可用** |
| 14. 招聘信号 | 软件/服务/设备耗材 | 免费 | ⭐⭐⭐⭐ | 高 | ✅ **可用** |
| 15. 评测/生态站 | 软件/专业服务 | 免费 | ⭐⭐⭐ | 中 | ✅ **可用** |

---

### 5.14 实操优先级排序

**✅ 立即可用（免费，无需注册）**：
1. LinkedIn直接搜
2. 官网About页
3. 竞品逆向分析
4. 展会名录（官网免费下载）
5. Instagram反查
6. 行业协会目录

**⚠️ 一次性注册即可用**：
- Apollo免费账号（50条/月）
- Hunter.io Chrome扩展（25次/月免费额度）

**❌ 暂不操作**：
- 海关数据（ImportGenius/Panjiva）→ 用竞品逆向替代
- Xing（€12.99/月）→ 用LinkedIn搜德国客户替代
- Clay（$149/月）→ 太贵，其他渠道够用

---

## 🔄 六、完整客户搜索工作流（15 种方法版）

```python
def complete_customer_search_workflow(target_market, target_product):
    """
    完整客户搜索工作流（v3.0 — 15 种方法；方法13–15 见 5.12b）：
    0. 渠道优先级决策 → 选择最佳搜索渠道组合
    1. 多渠道搜索 → 候选公司列表
    2. 决策人查找 → 15 种方法组合
    3. 邮箱收集 → 多来源汇总
    4. 三轮验证 → 筛选有效邮箱
    5. 邮箱猜测 → 补充决策人邮箱
    6. 输出 → 最终候选清单
    """
    
    # ========== 阶段0：渠道优先级决策 ==========
    print("🎯 阶段0：决定搜索渠道组合...")
    
    channels = []
    
    # IF 目标市场=DACH → 优先用Xing
    IF target_market == "DACH" OR target_market IN ["DE", "AT", "CH"]:
        channels.append("xing")           # 方法10
        channels.append("linkedin")       # 方法1
        channels.append("google")         # 默认
        PRINT "🇩🇪 DACH市场：Xing + LinkedIn + Google")
    
    # IF 需要验证真实进口 → 用海关数据
    ELIF verification_mode == "verify_importer":
        channels.append("customs_data")   # 方法6
        channels.append("linkedin")       # 方法1
        channels.append("google")         # 默认
        PRINT "📦 验证进口商：海关数据 + LinkedIn + Google")
    
    # IF 有行业展会近期举办 → 优先展会数据
    ELIF has_recent_exhibition(target_market, target_product):
        channels.append("exhibition")     # 方法7
        channels.append("linkedin")       # 方法1
        channels.append("google")         # 默认
        PRINT "🎪 有近期展会：展会数据 + LinkedIn + Google")
    
    # IF 小公司/创始人主导 → Instagram反查
    ELIF target_customer_type == "small_brand" OR target_customer_type == "DTC":
        channels.append("instagram")      # 方法8
        channels.append("google")         # 默认
        channels.append("linkedin")       # 方法1
        PRINT "📱 小公司/创始人主导：Instagram + Google + LinkedIn")
    
    # IF 大批量高精度需求 → Clay多源瀑布
    ELIF batch_mode == "large_scale":
        channels.append("clay")           # 方法12
        PRINT "⚡ 大批量：Clay多源瀑布")
    
    # 默认 → LinkedIn + Chrome扩展 + 官网
    ELSE:
        channels.append("linkedin")       # 方法1
        channels.append("chrome_ext")     # 方法5
        channels.append("website")        # 方法2
        PRINT "🔍 默认：LinkedIn + Chrome扩展 + 官网")
    
    # 补充渠道（所有模式都可选）
    IF has_competitors(target_product):
        channels.append("competitor_analysis")  # 方法9
    IF has_industry_association(target_market, target_product):
        channels.append("association")          # 方法11
    
    # ========== 阶段1：多渠道搜索 ==========
    print(f"🔍 阶段1：多渠道搜索（{len(channels)}个渠道）...")
    
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
    
    # 去重（按域名去重）
    candidates = deduplicate_by_domain(candidates)
    print(f"✅ 找到 {len(candidates)} 个候选公司")
    
    # ========== 阶段2：决策人查找（15 种方法组合） ==========
    print("👤 阶段2：多渠道查找决策人...")
    
    for candidate in candidates:
        decision_makers = []
        
        # 优先LinkedIn（方法1）
        people = linkedin_search_decision_maker(candidate["brand"])
        decision_makers.extend(people)
        
        # Xing（DACH市场补充，方法10）
        IF target_market IN ["DE", "AT", "CH"]:
            xing_people = xing_search_decision_maker(candidate["brand"])
            decision_makers.extend(xing_people)
        
        # Chrome扩展提取（方法5，LinkedIn页面一键提取）
        for person in decision_makers:
            IF not person.email:
                ext_email = chrome_extension_extract(person.linkedin_url)
                IF ext_email:
                    person.email = ext_email
        
        # 展会演讲者（如来源是展会，方法7）
        IF candidate.source == "exhibition":
            speakers = extract_exhibition_speakers(candidate)
            decision_makers.extend(speakers)
        
        # 协会会员（如来源是协会，方法11）
        IF candidate.source == "association":
            # 协会会员通常就是决策人
            pass
        
        # Instagram反查（小公司/创始人主导，方法8）
        IF candidate.source == "instagram":
            founder = instagram_find_founder(candidate)
            IF founder:
                decision_makers.append(founder)
        
        candidate["decision_makers"] = deduplicate_people(decision_makers)
        print(f"  - {candidate['brand']}: 找到 {len(decision_makers)} 个决策人")
    
    # ========== 阶段3：邮箱收集（多来源汇总） ==========
    print("📧 阶段3：多渠道收集邮箱...")
    
    for candidate in candidates:
        emails = []
        
        # 3.1 从LinkedIn/Chrome扩展提取（方法1+5）
        for person in candidate["decision_makers"]:
            IF person.email:
                emails.append({
                    "email": person.email,
                    "source": person.get("email_source", "linkedin"),
                    "person": person.name,
                    "title": person.title
                })
        
        # 3.2 从官网提取（方法2）
        contact_emails = extract_emails_from_website(candidate["website"])
        for email in contact_emails:
            emails.append({
                "email": email,
                "source": "website",
                "person": None,
                "title": None
            })
        
        # 3.3 Hunter.io/Apollo API（方法4）
        hunter_emails = hunter_io_search(extract_domain(candidate["website"]))
        for h_email in hunter_emails:
            IF h_email.confidence >= 80:
                emails.append({
                    "email": h_email.email,
                    "source": "hunter_io",
                    "person": f"{h_email.first_name} {h_email.last_name}",
                    "title": h_email.position
                })
        
        # 3.4 海关数据联系人（方法6）
        IF candidate.source == "customs_data":
            customs_contacts = extract_customs_contacts(candidate)
            for contact in customs_contacts:
                emails.append({
                    "email": contact.email,
                    "source": "customs_data",
                    "person": contact.name,
                    "title": contact.title
                })
        
        # 3.5 Clay结果（方法12）
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
        print(f"  - {candidate['brand']}: 收集到 {len(emails)} 个邮箱")
    
    # ========== 阶段4：三轮邮箱验证 ==========
    print("✅ 阶段4：三轮邮箱验证...")
    
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
        print(f"  - {candidate['brand']}: {len(valid_emails)}/{len(candidate['emails'])} 个邮箱有效")
    
    # ========== 阶段5：邮箱猜测（补充） ==========
    print("🎯 阶段5：邮箱猜测补充...")
    
    for candidate in candidates:
        # 如果有决策人但没有邮箱，尝试猜测（方法3）
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
    
    # ========== 阶段6：输出最终清单 ==========
    print("📋 阶段6：生成最终候选清单...")
    
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
    
    # 按邮箱质量排序：具名邮箱 > 猜测邮箱 > 通用邮箱
    final_candidates.sort(key=lambda c: email_quality_score(c["valid_emails"]), reverse=True)
    
    # 保存到文件
    save_to_csv(final_candidates, "candidates_validated.csv")
    print(f"✅ 最终输出 {len(final_candidates)} 个有效候选客户")
    
    RETURN final_candidates
```

---

## 📊 七、搜索结果输出格式

### 7.1 CSV格式（推荐，用于csv_ops.py）

```csv
brand,website,region,email,contact_person,title,email_source,validated
Brand A,https://branda.example,UK,john@branda.example,John Smith,Buyer,linkedin,true
Brand B,https://brandb.example,DE,info@brandb.example,,,, false
Brand C,https://brandc.example,FR,marie@brandc.example,Marie Dubois,Sourcing Manager,guessed,true
```

### 7.2 JSON格式（用于脚本输入）

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

## 🛠️ 八、工具命令速查

| 任务 | 工具 | 命令 |
|------|------|------|
| Google搜索 | 内置搜索工具 | `search_web(["关键词"])` |
| LinkedIn搜索 | 浏览器自动化 | `computer_use` 或 `mobile_use` |
| 邮箱提取 | Python脚本 | 自行编写或使用第三方库 |
| MX验证 | dns_validator.py | `python3 scripts/dns_validator.py input.json` |
| 邮箱猜测 | email_guesser.py | `python3 scripts/email_guesser.py input.json` |
| 三轮验证 | csv_ops.py | `python3 scripts/csv_ops.py check <email>` |
| 跨品牌排重 | csv_ops.py | `python3 scripts/csv_ops.py cross_brand_check <domain>` |

---

**SOP版本**：v3.1  
**最后更新**：2026-10-19  
**维护者**：<your-brand> 客户开发（首次建档后替换为你的公司/团队名）
