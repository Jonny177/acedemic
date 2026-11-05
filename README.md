# Lekai Wang — academic

这是独立的 GitHub Pages 学术资料站源码。目标仓库为 `Jonny177/acedemic`，成功部署后的默认地址为：

[https://jonny177.github.io/acedemic/](https://jonny177.github.io/acedemic/)

仓库名采用实际创建的拼写 `acedemic`；本地项目目录仍为 `academic/`。

现有 `Jonny177.github.io` 仓库及其主页保留。不要把本项目推送到原主页仓库，也不要覆盖原主页的 `index.html`。本项目没有配置自定义域名。

源码本身不代表网站已经发布；是否上线，以 GitHub Actions 的成功部署记录和实际网址为准。

## 内容与稿件说明

- 个人信息存放在 `data/profile.json`，稿件目录存放在 `data/drafts.json`。
- 三篇材料来自用户提供的 AI 生成稿件，网站统一列在 **Working drafts**，并明确说明其结论未在本站被呈现为已核验成果。
- 所提供的 LaTeX 源文件没有填写作者署名及稿件日期。详情页会如实显示缺失的信息；站点所有者的姓名不会自动作为论文作者。
- PDF 与 LaTeX 下载保留提供文件的原始内容。网站上的草稿说明不等于修改了 PDF 内文，也不代表完成了数学证明或参考文献审查。
- 页面中的简介是便于查阅的描述性摘要，不是发表记录，也没有添加期刊、DOI 或本稿的 arXiv 编号。

## 项目结构

```text
academic/
├── data/                    # 个人信息和稿件数据
├── static/
│   ├── assets/              # 样式与目录交互脚本
│   └── files/               # 三组原始 PDF / TeX 文件
├── scripts/
│   ├── build.py             # 使用 Python 标准库生成网页
│   └── check.py             # 检查页面、链接、稿件状态与下载文件
├── .github/workflows/pages.yml
└── site/                    # 构建结果；不提交到源码仓库
```

## 本地查看与更新

安装 Python 3.10 或更新版本后，在本项目目录运行：

```sh
python scripts/build.py
python scripts/check.py
```

然后用浏览器打开 `site/index.html`。也可以启动本地预览：

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

打开 [本地预览](http://127.0.0.1:8000/)，结束时在终端按 `Ctrl+C`。

修改 JSON 或静态资源后，重新执行上述构建和检查命令，再刷新浏览器。不要直接修改 `site/` 内的 HTML，因为下次构建会重新生成它们。

页面使用相对链接，可同时用于本地文件预览和 GitHub Pages 的 `/acedemic/` 子路径。新增文件或链接时也应遵守这一点，例如使用 `files/name.pdf`，不要写成 `/files/name.pdf`。

## 推荐发布方式：GitHub Actions

1. 使用 GitHub 上已建立的 [`Jonny177/acedemic`](https://github.com/Jonny177/acedemic) 仓库，并确认其可见性为 **Public**。
2. 将本项目的源码提交到该仓库的 `main` 分支，包含 `data/`、`static/`、`scripts/`、`.github/workflows/pages.yml`、`.gitignore` 和本说明文件。
3. 在仓库 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。
4. 在 **Actions** 中打开 **Deploy academic to GitHub Pages**。首次可使用 **Run workflow**；之后推送到 `main` 会自动重新构建、检查并部署。
5. 等待 `build` 和 `deploy` 都成功后，访问目标网址。部署失败时查看对应步骤的日志。

本流程使用 Python 标准库，无需安装前端框架、Node.js 或 Python 第三方包。

若使用 Git 命令行，且远端 `acedemic` 仓库是新建的空仓库，可在本目录运行：

```sh
git init -b main
git add .
git commit -m "Create academic site"
git remote add origin https://github.com/Jonny177/acedemic.git
git push -u origin main
```

若远端已有内容，应先克隆仓库，再把本项目源码复制进去提交。使用 GitHub Desktop 也可以完成同样的提交和推送。

## 备用发布方式：直接发布构建结果

如果暂时不使用 Actions 构建流程：

1. 先在本地执行构建和检查。
2. 把 **`site/` 里面的内容**复制到 `acedemic` 仓库发布分支的根目录，确保该目录直接包含 `index.html`、`drafts/`、`assets/`、`files/` 以及生成的 `.nojekyll` 文件。
3. 此方式不需要上传构建工作流；若同一分支已有 `.github/workflows/pages.yml`，先停用或移除该工作流，再选用本方式。
4. 在 **Settings → Pages** 选择 **Deploy from a branch**，然后选择相应分支和 **`/(root)`**。

不能只上传整个 ZIP，也不能把 `site/` 文件夹原封不动套在发布根目录外层。GitHub 不会自动把上传的 ZIP 解压成网站。若收到打包文件，请先在本地解压，再上传所需目录中的内容。

两种发布方式选一种即可。成功部署后，这个项目站的地址是 `/acedemic/`；原有个人主页地址仍是域名根路径。
