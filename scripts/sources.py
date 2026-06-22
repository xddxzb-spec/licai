"""
理财简报 — 新闻来源配置
每个来源定义名称、RSS/API地址、类型标签
"""

SOURCES = [
    # ===== RSS 来源（稳定可靠） =====
    {
        "name": "证券时报",
        "type": "rss",
        "url": "https://www.stcn.com/rss/rss.xml",
        "category": "理财行业泛新闻",
        "site_url": "https://www.stcn.com/",
        "encoding": "utf-8",
    },
    {
        "name": "新浪财经",
        "type": "rss",
        "url": "https://finance.sina.com.cn/roll/index.shtml",
        "category": "理财行业泛新闻",
        "site_url": "https://finance.sina.com.cn/",
        "encoding": "utf-8",
        "fallback_rss": "http://feed.sina.com.cn/api/roll/get?pageid=121&lid=1356&num=20",
    },
    {
        "name": "中国人民银行",
        "type": "rss",
        "url": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
        "category": "理财行业泛新闻",
        "site_url": "https://www.pbc.gov.cn/",
        "encoding": "utf-8",
    },
    {
        "name": "中国证券投资基金业协会",
        "type": "scrape",
        "url": "https://www.amac.org.cn/xwfb/xwdt/",
        "category": "理财行业泛新闻",
        "site_url": "https://www.amac.org.cn/",
        "encoding": "utf-8",
    },

    # ===== 需要爬虫抓取的网站 =====
    {
        "name": "财联社",
        "type": "api",
        "url": "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6",
        "category": "理财行业泛新闻",
        "site_url": "https://www.cls.cn/",
        "api_type": "telegraph",
    },
    {
        "name": "东方财富网",
        "type": "rss",
        "url": "https://finance.eastmoney.com/a/czqyw.html",
        "category": "理财行业泛新闻",
        "site_url": "https://www.eastmoney.com/",
        "encoding": "gbk",
    },
    {
        "name": "华尔街见闻",
        "type": "scrape",
        "url": "https://wallstreetcn.com/news/global",
        "category": "理财行业泛新闻",
        "site_url": "https://wallstreetcn.com/",
        "encoding": "utf-8",
    },
    {
        "name": "中债估值中心",
        "type": "scrape",
        "url": "https://www.chinabond.com.cn/Channel/19012917",
        "category": "理财估值新闻",
        "site_url": "https://www.chinabond.com.cn/",
        "encoding": "utf-8",
    },
    {
        "name": "中国理财网",
        "type": "scrape",
        "url": "https://www.chinawealth.com.cn/",
        "category": "理财估值新闻",
        "site_url": "https://www.chinawealth.com.cn/",
        "encoding": "utf-8",
    },
]

# 理财关键词（用于筛选相关新闻）
FINANCE_KEYWORDS = [
    "理财", "银行理财", "理财子", "理财产品", "固收", "净值", "估值",
    "债", "利率", "国债", "信用债", "城投债", "利差", "收益率",
    "央行", "逆回购", "MLF", "LPR", "存款", "社融", "货币",
    "基金", "ETF", "指数", "养老理财", "养老金",
    "监管", "金融监管", "银保监", "证监会", "资管", "非标",
    "委外", "穿透", "合规", "风险管理", "资本",
    "资产荒", "配置", "投资策略", "FOF", "MOM",
    "股市", "A股", "沪深300", "债券市场", "汇率",
]

# 估值类关键词（分类用）
VALUATION_KEYWORDS = [
    "估值", "净值", "收益率", "利率", "国债", "利差", "信用债",
    "城投债", "非标", "市值法", "摊余成本", "定价", "指数",
    "债市", "债券", "久期", "评级", "违约", "偿付",
    "基准利率", "DR007", "逆回购", "MLF", "LPR",
    "理财产品净值", "破净", "浮亏", "回撤",
]
