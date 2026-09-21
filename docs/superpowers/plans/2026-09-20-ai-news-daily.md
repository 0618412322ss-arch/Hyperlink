# AI 资讯日报 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个每天从免费公开渠道采集并核验 AI 资讯、精选 5–8 条、以高级黑白网页公开展示的 GitHub Pages 网站。

**Architecture:** Python 采集流水线读取官方 RSS 与公开页面，将候选内容标准化、去重、核验、评分后写入按日期组织的静态 JSON。无框架 HTML/CSS/JavaScript 前端读取该数据并提供来源筛选、详情展开与历史浏览；GitHub Actions 每日运行流水线，只有校验成功才更新数据，并通过 GitHub Pages 发布 `dist/`。

**Tech Stack:** Python 3.12、requests、feedparser、BeautifulSoup4、pytest、HTML5、CSS、原生 JavaScript、GitHub Actions、GitHub Pages

**Spec:** `docs/superpowers/specs/2026-09-20-ai-news-daily-design.md`

## Global Constraints

- 只使用免费、公开可访问的数据源，不绕过登录、验证码、付费墙或平台访问控制。
- 每天运行一次，读取最近 48 小时的候选内容。
- 公开首页只显示核验通过的内容；目标为 5–8 条，合格内容不足时如实少于 5 条。
- 官方来源可单源核验；非官方消息必须至少有两个相互独立且关键事实一致的可靠来源。
- 自动任务失败或没有合格内容时保留最后一次成功发布的版本。
- 前端为高级黑白编辑部风格，兼容桌面和移动设备，具备键盘焦点态和减少动态效果支持。
- 每条公开资讯必须包含时间、背景、核心内容、影响、来源渠道、核验说明和原文链接。

## Review Focus

- 某一来源超时或页面结构改变时，其他来源仍可继续处理，且损坏条目不会进入公开数据。
- 两条不同标题但指向同一事件的资讯必须合并，不能重复占据精选名额。
- 日期、主体或 URL 缺失的候选必须拒绝，不得在摘要阶段凭空补齐。
- 合格内容少于 5 条时应发布真实数量并显示说明，而不是用低可信内容补足。
- GitHub Actions 更新失败时不得覆盖现有 `dist/data/latest.json` 或触发错误版本部署。

---

### Task 1: 项目骨架与数据契约

**Files:**
- Create: `requirements.txt`
- Create: `src/models.py`
- Create: `tests/test_models.py`
- Create: `data/sources.json`
- Create: `.gitignore`

**Interfaces:**
- Consumes: 无。
- Produces: `Candidate.from_mapping(dict) -> Candidate`、`Article.to_public_dict() -> dict`、统一来源配置结构。

- [ ] **Step 1: 写数据契约失败测试**

```python
def test_candidate_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="title"):
        Candidate.from_mapping({"url": "https://openai.com/news/"})

def test_public_article_contains_required_sections():
    article = make_article()
    assert set(article.to_public_dict()) >= {
        "id", "title", "published_at", "background", "summary",
        "impact", "channel", "verification", "sources", "tags"
    }
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_models.py -v`

Expected: FAIL，因为 `src.models` 尚不存在。

- [ ] **Step 3: 实现不可变数据模型和来源配置**

```python
@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    published_at: datetime
    publisher: str
    channel: str
    excerpt: str
    official: bool

    @classmethod
    def from_mapping(cls, raw: dict) -> "Candidate":
        for key in ("title", "url", "published_at", "publisher", "channel"):
            if not raw.get(key):
                raise ValueError(f"missing {key}")
        if urlparse(raw["url"]).scheme not in {"http", "https"}:
            raise ValueError("invalid url")
        return cls(
            title=raw["title"].strip(),
            url=raw["url"],
            published_at=datetime.fromisoformat(raw["published_at"].replace("Z", "+00:00")),
            publisher=raw["publisher"].strip(),
            channel=raw["channel"].strip(),
            excerpt=raw.get("excerpt", "").strip(),
            official=bool(raw.get("official", False)),
        )
```

`data/sources.json` 明确定义 OpenAI、Google、Microsoft、Anthropic、百度、腾讯的官方来源，以及知乎、微博、微信公众号的公开发现入口；每项包含 `name`、`channel`、`url`、`kind`、`official` 和解析器名称。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m pytest tests/test_models.py -v`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add requirements.txt src/models.py tests/test_models.py data/sources.json .gitignore
git commit -m "feat: define news data contract and sources"
```

### Task 2: 免费公开来源采集器

**Files:**
- Create: `src/collectors.py`
- Create: `tests/fixtures/openai-feed.xml`
- Create: `tests/fixtures/anthropic-news.html`
- Create: `tests/test_collectors.py`

**Interfaces:**
- Consumes: `Candidate.from_mapping(dict)` 和 `data/sources.json`。
- Produces: `collect_source(source: dict, session: requests.Session) -> list[Candidate]`、`collect_all(sources: list[dict]) -> tuple[list[Candidate], list[dict]]`。

- [ ] **Step 1: 写 RSS、HTML 和单源失败测试**

```python
def test_parse_rss_returns_normalized_candidates(fixture_text):
    items = parse_rss(fixture_text, SOURCE)
    assert items[0].publisher == "OpenAI"
    assert items[0].official is True

def test_collect_all_isolates_source_failure(monkeypatch):
    candidates, errors = collect_all([GOOD_SOURCE, BROKEN_SOURCE])
    assert len(candidates) == 1
    assert errors[0]["source"] == "broken"
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_collectors.py -v`

Expected: FAIL，因为解析函数尚不存在。

- [ ] **Step 3: 实现有限超时、重试和解析器**

```python
def collect_all(sources):
    candidates, errors = [], []
    session = requests.Session()
    for source in sources:
        try:
            candidates.extend(collect_source(source, session))
        except (requests.RequestException, ValueError) as exc:
            errors.append({"source": source["name"], "error": str(exc)})
    return candidates, errors
```

RSS 解析器读取 feed 元数据；HTML 解析器只提取配置中明确的公开标题、日期、链接和摘要。请求超时为 15 秒，每个来源最多重试 2 次。知乎、微博和微信公众号入口若要求登录或返回验证码，记录失败并跳过。

- [ ] **Step 4: 运行采集器测试**

Run: `python -m pytest tests/test_collectors.py -v`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/collectors.py tests/fixtures tests/test_collectors.py
git commit -m "feat: collect public AI news sources"
```

### Task 3: 去重、核验、评分与摘要流水线

**Files:**
- Create: `src/pipeline.py`
- Create: `scripts/update_news.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `list[Candidate]`。
- Produces: `deduplicate(candidates) -> list[list[Candidate]]`、`verify_cluster(cluster) -> VerificationResult`、`select_daily(candidates, limit=8) -> list[Article]`、`scripts/update_news.py --output dist/data`。

- [ ] **Step 1: 写去重、核验和不足五条测试**

```python
def test_duplicate_event_uses_one_slot():
    clusters = deduplicate([same_event_a, same_event_b])
    assert len(clusters) == 1

def test_unofficial_single_source_is_not_published():
    assert verify_cluster([unofficial]).status == "pending"

def test_select_daily_does_not_pad_low_quality_items():
    assert len(select_daily([verified_a, verified_b])) == 2
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_pipeline.py -v`

Expected: FAIL，因为流水线函数尚不存在。

- [ ] **Step 3: 实现确定性核验和选择规则**

```python
def verify_cluster(cluster):
    official = [item for item in cluster if item.official]
    independent_hosts = {urlparse(item.url).hostname for item in cluster}
    if official:
        return VerificationResult("verified", "官方原始来源可访问")
    if len(independent_hosts) >= 2:
        return VerificationResult("verified", "两个独立公开来源关键事实一致")
    return VerificationResult("pending", "仅有单一非官方来源")
```

标准化标题用于相似度比较，规范化 URL 用于精确去重；评分由时效性、官方等级、关键词影响度和来源多样性组成。背景、摘要和影响仅从来源标题与公开摘要中压缩生成，不添加来源中不存在的数字或判断。

- [ ] **Step 4: 实现原子写入与失败保护**

先将 `latest.json`、日期归档和 `index.json` 写入临时目录，全部通过 JSON Schema、URL、日期、数量和重复项校验后再用 `os.replace` 更新正式文件；零条合格内容时返回非零退出码，不替换旧文件。

- [ ] **Step 5: 运行流水线测试**

Run: `python -m pytest tests/test_pipeline.py -v`

Expected: PASS，包括来源失败隔离、重复事件、字段缺失、少于五条和零条保护场景。

- [ ] **Step 6: 提交**

```bash
git add src/pipeline.py scripts/update_news.py tests/test_pipeline.py
git commit -m "feat: verify and curate daily AI news"
```

### Task 4: 高级黑白资讯前端

**Files:**
- Create: `dist/index.html`
- Create: `dist/styles.css`
- Create: `dist/app.js`
- Create: `dist/data/latest.json`
- Create: `dist/data/index.json`
- Create: `tests/test_static_site.py`

**Interfaces:**
- Consumes: `dist/data/latest.json` 与 `dist/data/index.json`。
- Produces: 公开首页、分类与来源筛选、可访问详情展开、历史日期浏览。

- [ ] **Step 1: 写静态入口和数据契约测试**

```python
def test_site_has_required_landmarks():
    html = Path("dist/index.html").read_text(encoding="utf-8")
    for marker in ("<header", "<main", "<footer", "id=\"news-grid\""):
        assert marker in html

def test_latest_has_five_to_eight_verified_articles():
    payload = json.loads(Path("dist/data/latest.json").read_text(encoding="utf-8"))
    assert 5 <= len(payload["articles"]) <= 8
    assert all(a["verification"]["status"] == "verified" for a in payload["articles"])
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_static_site.py -v`

Expected: FAIL，因为网页尚不存在。

- [ ] **Step 3: 构建第一屏和视觉系统**

在 HTML 中加入内嵌 SVG favicon、跳转到正文链接、站名、最后更新时间、精选数量、主报道、筛选栏、卡片网格和透明说明。CSS 使用象牙白、近黑、灰阶和低饱和墨绿色；以高对比衬线标题、现代无衬线正文、非对称网格、细线和大留白形成编辑部风格。

- [ ] **Step 4: 实现筛选、详情和历史交互**

```javascript
const state = { category: "全部", source: "全部", articles: [] };
function applyFilters() {
  return state.articles.filter(article =>
    (state.category === "全部" || article.category === state.category) &&
    (state.source === "全部" || article.publisher === state.source)
  );
}
```

详情使用原生 `<details>`；所有外链设置 `rel="noopener noreferrer"`；加载失败时显示明确错误信息和最近更新时间。移动端单栏，无横向溢出，焦点态清晰，并尊重 `prefers-reduced-motion`。

- [ ] **Step 5: 写入 6 条已核验首版真实资讯**

基于上线当天可访问的官方原文填入 OpenAI、Google、Microsoft、Anthropic、百度和腾讯各一条；每条记录保留原文 URL、发布时间、核验时间和简短核验说明。

- [ ] **Step 6: 运行静态与 JavaScript 语法检查**

Run: `python -m pytest tests/test_static_site.py -v`

Run: `node --check dist/app.js`

Expected: 全部 PASS。

- [ ] **Step 7: 提交**

```bash
git add dist tests/test_static_site.py
git commit -m "feat: build editorial AI news dashboard"
```

### Task 5: 每日自动更新与 GitHub Pages 发布

**Files:**
- Create: `.github/workflows/daily-news.yml`
- Create: `README.md`
- Modify: `scripts/update_news.py`
- Test: `tests/test_workflow.py`

**Interfaces:**
- Consumes: 仓库源码、公开网络来源和现有 `dist/data`。
- Produces: 每日数据提交、GitHub Pages 构建产物和公开站点部署。

- [ ] **Step 1: 写工作流安全测试**

```python
def test_workflow_has_daily_schedule_and_pages_permissions():
    workflow = Path(".github/workflows/daily-news.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "scripts/update_news.py" in workflow
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_workflow.py -v`

Expected: FAIL，因为工作流尚不存在。

- [ ] **Step 3: 创建每日更新与 Pages 工作流**

```yaml
on:
  schedule:
    - cron: "20 1 * * *"
  workflow_dispatch:
permissions:
  contents: write
  pages: write
  id-token: write
```

工作流安装锁定版本依赖、运行测试、运行采集器、仅在数据实际变化时提交，然后上传 `dist/` Pages artifact 并部署。采集或测试失败时作业立即结束，不提交也不部署。

- [ ] **Step 4: 编写使用与核验说明**

README 说明网站目标、覆盖范围、免费来源限制、核验规则、本地运行、手动更新、每日计划和 GitHub Pages 设置步骤，不包含任何令牌或私密信息。

- [ ] **Step 5: 运行完整测试**

Run: `python -m pytest -v`

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add .github/workflows/daily-news.yml README.md scripts/update_news.py tests/test_workflow.py
git commit -m "ci: update and deploy AI news daily"
```

### Task 6: 真实数据刷新、视觉验收与公开上线

**Files:**
- Modify: `dist/data/latest.json`
- Modify: `dist/data/index.json`
- Modify: GitHub 仓库默认分支配置（远程操作）

**Interfaces:**
- Consumes: 已完成的采集器、前端和 GitHub 仓库 `https://github.com/0618412322ss-arch/Hyperlink`。
- Produces: 可公开访问的 GitHub Pages URL。

- [ ] **Step 1: 联网执行首轮采集并审查 5–8 条结果**

Run: `python scripts/update_news.py --output dist/data`

Expected: 成功输出 5–8 条已核验内容；逐条确认日期、发布主体、官方原文 URL 和摘要均与来源一致。

- [ ] **Step 2: 启动本地预览并检查响应**

Run: `python -m http.server 4173 --directory dist`

Expected: `http://localhost:4173/` 返回 200，控制台无阻塞错误。

- [ ] **Step 3: 检查桌面和移动端**

验证 1440×900 与 390×844：首屏主报道可读、筛选可操作、详情可展开、无横向滚动、外链正确、键盘焦点可见。

- [ ] **Step 4: 推送准确源码到指定仓库**

```bash
git remote add origin https://github.com/0618412322ss-arch/Hyperlink.git
git branch -M main
git push -u origin main
```

Expected: 远程 `main` 与本地 `HEAD` 一致。

- [ ] **Step 5: 启用并验证 GitHub Pages**

将 Pages 构建来源设为 GitHub Actions，手动运行 `Daily AI News`，等待 `deploy-pages` 成功。访问仓库返回的 Pages URL，确认首页与本地版本一致且资源无 404。

- [ ] **Step 6: 最终提交与状态确认**

Run: `git status --short`

Expected: 无未提交文件；公开 URL 可访问，页面显示真实最后更新时间和 5–8 条已核验资讯。
