# SPR Kinetics Simulation Web App

零依赖的 HTML / CSS / JavaScript 应用，用标准 1:1 Langmuir 模型模拟 SPR 结合与解离。界面支持实时参数更新、浓度梯度、两种进样模式、KD 与半衰期计算、进样计划和 CSV 导出。无需 npm install、构建或外部 CDN。

## 运行

直接用浏览器打开 `index.html` 即可，支持现代 Chrome、Edge、Firefox 和 Safari。也可在仓库目录启动静态服务：

```sh
python3 -m http.server 8000
```

然后在浏览器访问 `http://localhost:8000`。计算完全在浏览器内进行，不上传数据。

## 使用

- 输入 ka（M⁻¹ s⁻¹）、kd（s⁻¹）、Rmax（RU）和 analyte concentration（nM）。
- 设置结合时间和解离时间（s），最高浓度（nM）、稀释倍数及浓度数量（1–12）。
- 开启浓度梯度时，浓度为 `最高浓度 / 稀释倍数^(N-1)` 至最高浓度，按低到高排列。analyte concentration 显示为从零开始的灰色独立参考曲线。
- 关闭梯度时，只模拟 analyte concentration。最高浓度不会参与该曲线计算。
- Multi-cycle kinetics：每个浓度假设完全再生，起始响应为零；曲线在同一时间轴叠加。
- Carterra LSA kinetics：采用无再生连续进样近似，每个浓度包含一段结合和一段解离，将解离末端的残余响应带入下一周期；使用连续时间轴。此模式不是 Carterra 仪器的协议、流体系统或数据处理的精确复现。
- 修改参数会立即更新。非法参数会清除旧结果并显示提示；恢复默认可重置表单。CSV 包含模拟周期的浓度、时间、响应和阶段，不包含灰色参考曲线。

## 科学模型

设 C 为 mol/L 浓度、R 为响应：

```text
dR/dt = ka × C × (Rmax − R) − kd × R
kobs = ka × C + kd
Req = Rmax × ka × C / kobs
结合：R(t) = Req + (R0 − Req) × exp(−kobs × t)
解离：R(t) = R0 × exp(−kd × t)
KD = kd / ka（M，界面转换为 nM）
t½ = ln(2) / kd（s）
```

当 ka × C + kd = 0 时，结合响应保持 R0；kd = 0 时，解离响应保持不变，半衰期无限。模型允许零浓度作为空白对照。曲线使用解析解，每个阶段采样 240 个区间，并非实时仪器数据或数值拟合。

假设均一、独立的 1:1 结合位点。不考虑传质限制、多价效应、非特异性结合、体相折射率变化、噪声或基线漂移。结果用于教学与实验设计探索，不用于替代实验拟合。

## 测试

安装 Node.js 18 或更高版本后，在仓库目录运行（仅测试需要 Node，应用运行不需要）：

```sh
node --test tests/kinetics.test.js
```

测试覆盖解析解与单位转换、浓度梯度、multi-cycle 归零、LSA 响应及时间连续性、零浓度、零解离速率和非法输入。

## 文件

- `index.html`：页面及参数输入。
- `styles.css`：响应式科研软件界面。
- `kinetics.js`：独立动力学模型，浏览器与 Node 共用。
- `app.js`：交互、SVG 曲线、统计和 CSV 导出。
- `tests/kinetics.test.js`：模型测试。

本次验证：6 项模型测试通过；真实 Chromium 浏览器检查通过，覆盖首次渲染、KD 实时更新、LSA 残余响应、单浓度与零浓度、非法输入、恢复默认、CSV 内容（默认 2405 个数据点）、390px 手机布局和 JavaScript 运行错误检查。

## LSA Excel 交互绘图桌面程序

新增 Windows 11 x64 桌面程序，读取 LSA 横向 Time/Ru 行格式，自动识别样品、ROI、cycle 和进样名称。支持样品/ROI/cycle 筛选、程序内嵌交互曲线及信号下降统计、CSV 和独立 HTML 导出。程序不上传实验数据，现有 SPR 模拟应用保留。

运行、EXE 构建和下载说明见 [desktop/README.md](desktop/README.md)。GitHub Actions 的 `Build LSA Windows EXE` 工作流在 Windows 上打包可执行文件。
