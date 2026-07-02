# Boss 直聘 · 区块链 / Web3 / 钱包 开发岗

## 筛选

- **搜索词**：区块链、web3、钱包、以太坊、区块链开发、web3开发
- **匹配**：`title` 含 区块链 / 以太坊 / web3 / 钱包，且为开发岗（排除产品/运营/测试/实习等）
- **活跃**：近一月（本月活跃及更近）

## 采集

```bash
cd bossJD
pip install -r requirements.txt
playwright install chromium

# 1. 登录（打开 Chrome → 手动登录 → **完成后**回终端按 Enter）
python scrape.py --login

# 若之前误保存了无效登录，先清除再登
python scrape.py --clear-session

# 全量采集（默认 api + 近一月活跃 + 翻页 20）
python scrape.py --mode api --fetch-detail --max-pages 20
```

**重要**：必须先在浏览器里**完整登录成功**，再回到终端按 Enter；脚本会验证 `wt2`/`bst` Cookie 和职位 API，**验证失败不会保存 auth 文件**。

若出现 **about:blank**：在地址栏手动输入 `https://www.zhipin.com` 回车，再点「登录」。
