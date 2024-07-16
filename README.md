# ⚡Spider_DCD ⚡

汽车大模型项目代码

### Install Python Requirements

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install Playwright

安装了playwright的依赖之后，请记得使用以下代码安装playwright的浏览器依赖：

```bash
python3 -m playwright install
# or 
playwright install
```

## ✅TO DO LIST：

- [ ] 汽车之家的口碑评论数据
- [ ] 懂车帝程序的bug
  - [ ] 多值数据抓取
  - [ ] 部分数据无法定位
  - [ ] 滚动逻辑测试
- [ ] 储存数据，建立知识库
- [ ] 数据喂给大模型，做RAG检索增强生成  

## References:

+ [Playwright API](https://playwright.dev/python/docs/intro)
+ [lxml](https://lxml.de/)



