# ⚡Spider_DCD ⚡

汽车大模型项目代码

### ⏬Install Python Requirements

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 🚀Install Playwright

安装了playwright的依赖之后，请记得使用以下代码安装playwright的浏览器依赖：

```bash
python3 -m playwright install
# or 
playwright install
```

## ✅TO DO LIST：

- [x] 汽车之家的口碑评论数据
  - [ ] 遍历当前页面汽车卡片后的滚动翻页测试
- [x] 懂车帝程序的bug
  - [x] 多值数据抓取
  - [x] 部分数据无法定位
  - [x] 滚动逻辑测试
- [x] 添加了clear.py程序，清除本地数据文件夹的所有文件，方便测试使用
- [x] pytest测试
  - [ ] pytest测试脚本
- [x] 伪装header
- [ ] 储存数据，建立知识库
- [ ] 数据喂给大模型，做RAG检索增强生成  

## 📖References:

* [Playwright API](https://playwright.dev/python/docs/intro)
* [lxml](https://lxml.de/)
* [pytest](https://docs.pytest.org/)
* [懂车帝](https://www.dongchedi.com/)
* [汽车之家](https://www.autohome.com.cn/)

## 🐳Use Docker

```
docker-compose up --build
```

