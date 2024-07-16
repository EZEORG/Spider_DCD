# ⚡Spider_DCD ⚡

汽车大模型项目代码


## Requirements.txt


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

初步的计划是，先搁置这一块点击的逻辑。现在留下的几个程序，autohome.py是我计划的最终程序，现在卡在如何遍历每一辆车的每一条评价。也就是刚才说的“查看完整口碑”。autohome-in.py这个程序以完整口碑点击后的页面作为起始页，经过测试，已经能非常完善的爬到需要的数据了。下一步操作，要把遍历的逻辑搞好，然后把-in这个程序拉进去，数据就算是到手了。

傍晚：程序似乎已经调好了，只是没有测试。autohome.py就是最终程序，之前可参考的半成品我都放到了test里面。

