# AI SIGNAL

每天从免费公开渠道采集、核验并精选 AI 资讯的静态网站。公开页面只展示有官方原文，或有两个独立可靠来源互相印证的内容。

## 本地预览

```bash
python -m pip install -r requirements.txt
python -m http.server 4173 --directory dist
```

## 更新数据

```bash
python scripts/update_news.py --output dist/data
```

GitHub Actions 每天 UTC 01:20 自动运行。若没有合格内容或采集失败，脚本保留上一份有效数据。知乎、微博和微信公众号受公开访问限制，只在无需登录、验证码或付费的前提下尽力覆盖。
