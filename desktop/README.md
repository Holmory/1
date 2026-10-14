# LSA Data Viewer — Windows 11 x64

原生桌面程序：选择 Excel 后直接在程序窗口显示交互图谱和信号下降统计，不需要打开浏览器或导出。程序界面为中文，完全本地运行。

## 使用

1. 解压构建附件，打开 `LSA-Data-Viewer.exe`，点击“打开 Excel”。
2. 选择样品、ROI 和绘图 cycle（Ctrl / Shift 多选）。窗口自动绘制曲线。
3. 图谱支持滚轮缩放、拖动平移、右键菜单、点击图例隐藏/显示 ROI；鼠标移动时下方显示最近采集点的时间、响应、cycle 和进样名称。“恢复全图范围”重置缩放。
4. 默认只显示 `time <= 12450 s` 的数据，排除示例中最后 cycle 末尾的再生信号。截止时间可修改，也可取消勾选。原始 Excel 不修改。CSV / HTML 导出使用同一截止过滤；PNG 保存当前图谱视图。
5. 在“统计的分析物名称”中选择 OSMR 或其他分析物。表格自动更新。

## 统计定义（重要）

每个工作表、样品和 ROI 独立计算，不平均 ROI：

- Blank 为名称以 Buffer 或 Blank 开头的 cycle，按时间选第一个。
- 分析物由下拉框选择，按时间选 blank 起始之后的第一和最后一个对应 cycle。
- 每个起始响应取该 cycle 的**第一个采集点**，不是 cycle 内实际注射开始位置的自动识别，也不是多个点平均值。
- 第一段下降 = 第一 blank 起始响应 − 第一分析物起始响应。
- 第二段下降 = 第一 blank 起始响应 − 最后一分析物起始响应。
- 单位 RU；保留符号，正值下降、负值上升。
- 表中显示三个取值点的 cycle、时间和原始响应，以及两项下降高度，保留六位小数。
- 统计使用当前样品、选中 ROI、截止时间内的全部 cycle，**不随绘图 cycle 隐藏而重新定义“第一/最后”**。缺少 blank 或分析物时显示 N/A。
- 已被截止时间完全排除的 cycle 不参与统计。时间按秒处理，不自动换算。

## Excel 格式及验证

标签格式：`[sample (ROI) - reagent (cycle)] Time values` 与 `Ru values`（也支持 Response values）。数值从 B 列横向排列。以工作表、样品、ROI、进样名称、cycle 配对，再按原列配对 time/response，非依赖相邻行。

保留原始负响应和连续时间，不平滑、不扣基线、不拟合。不同 cycle 间使用断开的线段，不在人为重复边界时间处连线。每轮时间必须严格递增，跨周期重置/重叠的时间会报错；不推测时间偏移。未知标签提示跳过，缺失配对或非法数值报错。公式必须有 Excel 保存的数值缓存。

## 下载与构建

GitHub 仓库 Actions → **Build LSA Windows EXE** → 最新成功构建 → 下载附件 **LSA-Data-Viewer-Windows-x64**（需要登录 GitHub），解压运行。附件保留 30 天，可重新运行构建生成。

本地构建：安装 Python 3.12 x64 后双击 `build_windows.bat`，生成 `desktop/dist/LSA-Data-Viewer.exe`。构建需要网络安装依赖，最终程序离线运行。EXE 未签名，Windows 可能提示未知发布者。

## 开发测试

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r desktop/requirements.txt
python -m unittest discover -s desktop/tests -v
python desktop/lsa_app.py
```

技术：PySide6 + pyqtgraph 原生交互图表，openpyxl 读取数据；Plotly 仅用于可选的独立 HTML 导出。测试涵盖导入配对、截止边界、数据不被修改、带符号的统计、缺失事件、ROI 筛选、内嵌绘图和图片导出。Windows 工作流也执行打包 EXE 的 `--self-test`，用合成 Excel 验证界面、统计、截断和导出。

所有实验数据留在本地，不提交至 GitHub，也无需云服务。导出的 HTML/CSV/PNG 含实验数据，请按自己的数据管理要求保存。
