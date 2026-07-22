# HFPSS Studio 使用指南

这份指南说明当前本地应用中哪些操作已经可以可靠使用，以及每项功能
**不会**替你证明什么。界面、API 与项目 JSON 都保留了 source locator、
grading convention 和 review status；请在保存研究结论前填写准确出处。

## 启动与确认当前页面

唯一应运行的应用目录是：

```text
E:\课程\PACE2025_fly\HFPSS Q_8\DoodleSS\HFPSS-Studio
```

在此目录执行：

```powershell
.\run-latest.ps1
```

然后打开 <http://127.0.0.1:5078/>。更新后请重启脚本并在浏览器按
`Ctrl+F5`；`http://127.0.0.1:5078/api/health` 会返回应用版本和当前
project revision，可用于确认不是旧原型或静态测试页。

## 画图的基本工作流

1. 顶部 **Workspace** 下拉菜单选择 grading workspace；顶部 **Page (r)**
   选择页面。默认 E2--E25；最末项可增加新页面。
2. 鼠标滚轮缩放，左键空白处（Select 工具）或中键拖动平移。图只显示
   HFPSS 的上半平面；`0` 可重新适配可行区域。
3. 使用工具栏 Select、Generator、Differential、Relation、Delete、Rename。
   工具键分别为 `V/G/D/R/X/N`，`[`、`]` 翻页，`Ctrl+Z/Ctrl+Y` 为 history。
4. 任何 candidate 或 suggested proposition 都应被审阅并补充准确引用；它
   不是已建立的定理。

### Beta 手动画图与 legacy 15.3 对照

快捷键仅在没有打开编辑对话框、输入框、textarea、下拉框或
`contenteditable` 获得输入焦点时生效；输入中文或其他 IME 组合文字时也会
暂停。`E` 在 HFPSS Studio 中表示 **Find deductions**，不是 legacy 15.3 的
extension mode。

| 用户可见操作 | HFPSS Studio beta | 与 `sseq ver15.3.html` 的关系 |
| --- | --- | --- |
| Generator | `G` 后单击格点；填写 label/expression；实时 KaTeX preview；同格点自动避让 | 覆盖 legacy 手工加点，并用确定性 packing 代替固定八方向 offset |
| Differential | `D` 后选择 source/target；显示跟随指针的 preview；保存 candidate 与 provenance proposition | 覆盖 legacy 两点连箭头，但增加 page、liveness 和 grading 校验 |
| Relation | `R` 后选择两点；candidate relation 会显示在图上并进入 proof tree | 覆盖 legacy 手工关系线，同时保留 review status |
| Delete | `X` 后单击 class；不确认，归档 class 并保留 proof/differential/relation history | 不等同于 legacy 直接擦除记录；目前不能直接点线删除 differential/relation claim |
| Rename | `N` 后单击 class；只改 label | 覆盖 legacy rename，同时保持 grade 和 provenance 不变 |
| Select | `V` 后单击 class 打开 inspector；左拖空白处平移 | 覆盖检查与画布平移；不支持 legacy 的 class 内部视觉 offset 拖动 |
| Pan/Zoom | Select 空白左拖；任意工具中键拖动或 `Alt`+左拖；滚轮以指针为中心缩放；`0` Fit view | 覆盖 legacy pan/zoom，并保留上半平面约束 |
| Page | 顶部按钮/下拉框或 `[`、`]`；可从菜单增加 E26 以后页面 | 覆盖 legacy page selector，并按 fate 控制 page liveness |
| History | `Ctrl+Z`；`Ctrl+Y` 或 `Ctrl+Shift+Z` | class、differential 和 relation 使用同一事务 history |
| Periodicity Tool | 定义多个 `(p,q)` 手动画图规则；复合应用到 box；或只平移 differential | 复刻 legacy 三个周期区块，但所有生成结果明确标为 manual-unverified candidate |
| Project JSON | 顶部 **Export JSON** 下载完整 Studio project；**Import JSON** 必须先 Preview，再由用户明确 Apply | 不直接导入 legacy 画布 JSON，也不会在选中文件时立即覆盖项目 |
| Clear current canvas | 顶部同名按钮经确认后归档当前 workspace 的全部 active dots；数学记录保留，并可一次 Undo | 是可恢复的 workspace 级归档，不是 legacy 的不可逆 Clear All |

下列 legacy 15.3 功能尚未直接移植：legacy 任意画布 JSON 格式的直接载入、拖动
class 修改纯视觉 offset、直接点击删除 connection，以及启发式 extension
批量生成。Studio 不会把手动画图周期自动解释为带来源的数学
结论；周期、跨 grading 产品和 deduction 应使用各自的 certificate/candidate
工作流。

### Select、检查器与画布

- 在 Select 模式中，左键拖动没有点的空白区域可以平移画布；中键拖动在
  各工具模式中都可平移，滚轮用于缩放。
- 鼠标悬停会高亮点。单击点后，它会保持选中高亮，右侧检查器会显示所有
  当前可用信息：label、grade、representation、state/fate、source/provenance、
  HFPSS/Tate fate events 和相关 differential claims。
- 手动画图周期实体化得到带独立 ID 的 class，可在 Select 模式单独检查并用
  Delete 归档。Advanced/Certified D8 的仅渲染周期实例仍打开基础代数元；
  目前不能直接修改这种 render-only translated instance。

点的颜色表示当前记录的命运，不表示 torsion、order 或 coefficient：

- 绿色：有 accepted proposition 支持的 permanent cycle；
- 灰色：命运 unresolved；
- 玫红色：支撑 accepted differential；
- 紫色：接收 accepted differential；
- 深色实线箭头：accepted differential；
- 琥珀色虚线箭头：candidate 或 under-review differential。

accepted `d_r` 只在 `E_r` 页显示；有效的 source 和 target 不再出现在
`E_{r+1}`。candidate arrow 本身不会改变代数元的 fate。

### 创建与编辑记录

1. **Generator (`G`)**：单击允许的格点，填写 label 和 semantic
   expression。非 Tate workspace 不允许负 filtration。
2. **Differential (`D`)**：在正确的 `E_r` 页依次单击 source 和 target。
   服务会检查 workspace、page liveness 和 convention 中的 differential
   shift；新记录仍是 candidate，不会自动成为 accepted theorem。
3. **Relation (`R`)**：依次选择两个代数元，保存 candidate relation
   proposition。它不会自动变成可执行的代数重写规则。
4. **Delete (`X`)**：不弹出确认框，归档图上的代数元，但保留 provenance、
   differential、relation 和 proof history。
5. **Rename (`N`)**：只改显示 label，不改 grading 或 proof history。

`Ctrl+Z` 撤销，`Ctrl+Y` 或 `Ctrl+Shift+Z` 重做。历史记录使用完整项目
snapshot，所以相关 differential 和 relation 会随事务一起恢复；一次新编辑会
清空 Redo 栈。该栈只存在于当前服务器进程并有长度上限，重启后不可依赖。

### 完整 Project JSON 与安全清空

- 顶部 **Export JSON** 下载完整的 Studio project JSON。
- 顶部 **Import JSON** 选择文件后只做只读 Preview。对话框会显示 revision、
  记录数量、迁移信息、warning 和数学 status policy；此时不会替换当前项目。
  核对后必须再次单击 **Apply reviewed import** 才会应用。若 preview digest 或
  expected revision 已不匹配，服务会拒绝应用，需重新 Preview。
- 顶部 **Clear current canvas** 会先显示确认说明。确认后，它归档当前
  workspace 中所有页面的 active dots，但不物理删除 class records、
  differentials、relations、propositions、provenance 或 fate history；整个清空
  只产生一个 history checkpoint，可用一次 **Undo** 恢复。
- `Delete (X)` 适合归档单个 class，不弹确认；**Clear current canvas** 是影响
  整个当前 workspace 的批量操作，所以必须确认。两者都不是不可逆删除。

### Grading atlas、跨 grading 产品与 TeX

- 顶部普通 **Workspace** 下拉框只列出已有实际 class 数据的 Q8 HFPSS chart
  workspaces，避免把 reference/support 和尚未计算的空 sector 混进日常画图流程。
  这只是导航筛选，不删除任何存储数据。
- 左侧保存完整 4×4 的 16 个 RO(Q8) sectors。空 sector 表示“尚未计算”，
  不是零；这些 sector 始终可从 atlas 打开。
- Tate、C4、`(*-H)` 等参考数据从左侧 **Reference / Support** 区域打开。
- Cross-graded product 中先选左右 sector、class 和同一个 `E_r` 页。Preview
  只检查 representation sum、page liveness 和 normalisation path；Store
  candidate 只保存候选产品记录，不会自动创建结果类、微分或证明。
- `C3` 的 `omega` orbit/transport 不能自行把 `sigma_i + 2 sigma_j` 与
  `2 sigma_i + sigma_j` 合并；缺少 certificate 和 coefficient-action
  proposition 时必须保持独立。
- 顶部导出按钮下载当前 workspace、当前页的 chart TeX 或 article TeX。
  导出是带 provenance 注释的当前状态快照，不支持从 TeX 反向导入。

## 显式有限 E2 presentation（推荐的代数输入方式）

在左侧选择 **Advanced E2 presentation**。该对话框会为当前 workspace
生成一个 JSON 模板；其中 source locator 字段故意为空，Preview 和
Materialize 都会拒绝没有准确出处的输入。

1. 修改 `name`、`source_ref`、`scope`、generator grades 和每条 relation 的
   `source_ref`。不要把模板中的 placeholder 当作出处。
2. 目前必须保留：

   ```json
   "coefficient_context_id": "formal-integer-presentation",
   "coefficient_domain": "integers"
   ```

3. 使用 **Preview**。它检查 monic orientation、grade homogeneity、
   termination 和 pairwise critical pairs；若给出 `polynomial`，它返回精确
   normal form。Preview 不会写入 project。
4. 确认输入及出处后，使用 **Materialize explicit data**。它只保存明确列出
   的 generator dots 和 relation propositions；不会展开所有 monomial，
   不会产生 product dots、permanent cycles 或 differentials。

该 evaluator 当前**拒绝** F4、W(F4)、residue 和 2-adic coefficient
contexts。它绝不会把整数 `2` 静默解释为 `0`。这不是 bug：相应 scalar
algebra 尚未实现，必须由未来的专门计算模块处理。

完整 JSON contract 见 [E2_PRESENTATION_INPUT.md](E2_PRESENTATION_INPUT.md)。

### PowerShell API 示例

将对话框中的 JSON 保存为 `presentation.json` 后，可在 PowerShell 中进行
无界面操作（请将 `ws_integer` 替换为实际 workspace ID）：

```powershell
$body = Get-Content .\presentation.json -Raw
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:5078/api/v2/e2-presentations/preview `
  -ContentType 'application/json' -Body $body

# Run only after reviewing Preview; this persists explicit generators and relations.
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:5078/api/v2/e2-presentations `
  -ContentType 'application/json' -Body $body
```

已保存的 presentation 可查阅：

```powershell
Invoke-RestMethod http://127.0.0.1:5078/api/v2/e2-presentations
```

## 手动画图周期（ver15.3-compatible）

左侧 **Periodicity Tool** 是绘图编辑器，不是 theorem prover。它包含与
`sseq ver15.3.html` 对应的三个区块：

1. **Define New Rule**：输入 multiplier 的 LaTeX 名称及 `(p,q)`，加入规则
   列表；列表中的规则可以删除。增加和删除规则均进入 Undo/Redo，并随完整
   Project JSON 导入导出。
2. **Apply All Rules to Box**：输入 `p_min/p_max/q_min/q_max`，先 Preview。
   当前规则列表会复合应用于当前页的 cycles、differential arrows 和 relation
   connections。蓝色空心点与蓝色虚线是预览，不会修改项目；核对摘要后才点
   **Apply All Rules to Box**。整次 Apply 是一个 history checkpoint。
3. **Apply Periodicity to Differentials Only**：输入一个 `(p,q)`。对每条当前页
   differential 及平移量检查端点：两端存在则只连箭头；恰好一端缺失则补齐
   缺失的点再连；两端都缺失则跳过。仍须 Preview 后才可 Apply。

实体化的点、箭头和 relation 都是独立存储记录，并以青蓝描边/虚线与普通
记录区分；它们可选择、检查、归档，且进入 Project JSON 与 Undo/Redo。
其 status 始终从 `manual-unverified` / `candidate` 开始。工具不会因为用户输入
了向量就声称该向量是 spectral-sequence period，也不会把复制的 differential
自动标为 accepted。

## Advanced / Certified D^8（已验证的单一自动分支）

此操作只适用于 integer-graded Q8 HFPSS 的 **E3 及以后**页面。选择图上的
class 后，展开左侧 **Advanced / Certified · Source-backed D8** 区域操作。
该区域即使当前
workspace 或页面不适用，也会保留显示并说明禁用原因，而不是藏在 class
检查器中：

1. 保持非零整数 translation，必要时从下拉框选择当前页、以该 class 为 source
   的 accepted outgoing `d_r`；不选 arrow 则只生成 class copy。
2. 先点 **Preview D8 copy**，确认目标的 grade、是否新建/复用，以及没有冲突。
   Preview 不会修改 chart 或 project。
3. 再点 **Materialize distinct copy**。系统保存独立 class records；若选择了
   accepted arrow，也保存独立 derived differential 和带 provenance 的 propositions。
   同一个 rule、anchor、translation 重复执行会复用既有记录；占用同一目标 cell
   或 endpoint 的不同记录会被拒绝，绝不覆盖。

出处为 DKLLW24 Proposition 4.1（本地 PDF 第 25 页：`D^8` 是可逆 `(64,0)`
周期类）和 section 6.1.2（本地 PDF 第 51 页：non-E2 HFPSS pages 按 `D^8`
64-周期）。这是实际存储的 source-backed operation，不是画布的 visual repeat。

`E2`、`g=kD^3`、其他 workspace、under-review differential 和组合周期规则均
不适用这张 certificate。可以使用上方手动画图周期工具生成
`manual-unverified` candidates，但必须另行附加 source locator、hypotheses 与
审阅，不能由画图操作自动升级。

## Differential candidate enumeration

In the browser, select a class and use **Find compatible d_r candidates** in
the right-hand Class Fate inspector. It queries the current page and displays
only `review-only · not saved` results—there is no save or accept action. If
the selected Comparison targets this workspace, qualifying comparison-transport
candidates appear separately with their hypotheses.

这个 API 给出 **review candidates**，不是自动 differential discovery。
它仅检查 `(stem, filtration)` 的 `d_r=(-1,+r)`、representation coordinate
不变，以及 source/target 在该页 live。它不写入 JSON，不创建 arrow，也不
改变 fate/proposition tree。

```powershell
$candidateBody = @{ source_id = 'class_replace_me'; page = 3 } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:5078/api/v2/workspaces/ws_integer/differential-candidates `
  -ContentType 'application/json' -Body $candidateBody
```

若同时给出 `comparison_id`，服务只会从已有 Comparison record 和已接受的
source differential 生成 map-transport candidate；返回值会把 comparison
applicability、source claim、liveness 和 grading translation 列为待审阅
hypotheses。它仍不是 restriction、transfer、norm 或 Tate comparison 已成立
的证明。

```powershell
$candidateBody = @{
  source_id = 'class_in_target_workspace'
  page = 3
  comparison_id = 'comparison_replace_me'
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:5078/api/v2/workspaces/target_workspace_id/differential-candidates `
  -ContentType 'application/json' -Body $candidateBody
```

## 其他候选建议

右侧 **Find deductions**（快捷键 `E`）调用后台已经登记的保守规则，例如
Leibniz 和 vanishing-line 检查；comparison 区域可以请求已有 comparison 的
transport suggestion。推荐流程是：

1. 生成建议；
2. 核对理由、依赖、适用范围和 source references；
3. 需要保留时加入 proof tree；
4. 由研究者对照原始来源后，再通过明确的审阅流程改变 status。

加入 proof tree 仍只保存 candidate。建议接口不会自动接受 proposition、自动
宣布 permanent cycle，也不会穷举所有 Leibniz 后果。

## 来源导入

来源导入是命令行维护流程，不是普通画布操作。详细审计范围、来源定位和
幂等性说明见 [E2_IMPORT_AUDIT.md](E2_IMPORT_AUDIT.md)。

只读检查 legacy JSON：

```powershell
python backend/audit_e2_import.py --workspace sigma_i --legacy-json ..\frontEnd_lty\spectral_sequence_project_newd9d11.json
```

将脚本中已经核对、带引用的有限 catalogue 写入本地项目：

```powershell
python backend/audit_e2_import.py --workspace integer --apply-verified --project backend\data\project.json
```

`--apply-verified` 会修改 `backend/data/project.json`，运行前应自行备份。它不
会把 legacy 图中的所有点、连线、文件名或周期复制自动解释为数学结论。

## 能力与边界

| 功能 | 当前可做 | 当前不做 |
| --- | --- | --- |
| Chart UI | 绘制/编辑 classes、differentials、relations；page、zoom、history、KaTeX | 自动判定图中每个点的数学含义 |
| E2 presentation | 验证显式有限 integral rewrite system；精确 normal form；保留 generators 的 grade/convention/provenance | 计算一般 group cohomology；F4/Witt/2-adic scalar algebra；从论文自动抽取 relations |
| Manual drawing periodicity | 多规则列表；复合复制当前页 cycles/connections 到 box；differential-only 端点补缺；Preview/Apply；一次 Undo；JSON round-trip | 证明输入向量是周期；自动接受复制的 arrow/relation |
| D8 periodicity | integer Q8 HFPSS 的 E3+ 页面中，preview 后生成独立 `(64,0)` class copy；可随 accepted outgoing arrow 生成 derived copy | E2、g=kD^3、v1-local 例外、其他 workspace、under-review arrow 或 visual repeat 的自动传播 |
| Differential candidates | 枚举 bidegree + liveness + representation compatible endpoints，返回 read-only candidates | 证明 nonzero differential；自动持久化或接受 candidate |
| Comparison candidates | 从已有 Comparison 和已接受 source arrow 形成带 hypotheses 的 transport candidates | 自动证明 map hypotheses、restriction、transfer、norm 或 Tate transport |
| Proof tree | 显示 propositions、sources、dependencies 和 review status | 替代人工 proof review |
| Project persistence | 完整 Studio JSON 导出；强制 Preview/明确 Apply 的导入；revision/digest 检查；可撤销的 workspace canvas 归档 | 直接信任或自动套用 legacy 任意画布 JSON |
| Collaboration | 本地 JSON、revision 和 undo/redo | 账号、权限、实时多人同步、冲突处理 |

此外，当前不会自动完成以下工作：

- 从输入环或表示计算完整 HFPSS、全部 differentials 和 extensions；
- 在缺少 page bound、degree argument、来源 proposition 或 comparison theorem
  时判定 permanent cycle；
- 将 TateSS 的负 filtration source 自动当作 HFPSS incoming differential；
- 将普通 relation proposition 当成通用 algebra rewrite system；
- 从任意 TeX、图片或 legacy JSON 恢复可靠语义和 provenance；
- 对 periodic copy 直接执行 translated mutation；
- 在没有 certificate 时仅凭 `C3` 自动合并 orbit 或同步全部数据；
- 从 cross-graded product preview 自动创建结果类、微分或 proof。

遇到空 sector、缺失 fate 或 unresolved status 时，应理解为“当前数据不足”，
而不是零或不存在。

## 研究数据的解释

当前 Q8 seed 是对本地 REU/Overleaf 材料的结构化索引，不是所有图和每个
differential 的 machine-checked transcription。不同 workspace 的 grading
convention 与 source scope 不应被自动混同。对任何新结论，请记录 precise
section/page/theorem locator，并在 proof tree 中保留 premise/hypotheses。

## 测试

以下命令是可执行的软件校验，不是数学证明。服务运行时可先做只读检查：

```powershell
Invoke-RestMethod http://127.0.0.1:5078/api/health
Invoke-RestMethod http://127.0.0.1:5078/api/project
Invoke-RestMethod http://127.0.0.1:5078/api/v2/grading-sectors
Invoke-RestMethod http://127.0.0.1:5078/api/v2/logic-graph
python backend/audit_e2_import.py --help
```

在项目根目录执行：

```powershell
python -m unittest discover -s tests -v
```

测试覆盖 explicit presentation 的 coefficient rejection、exact rewrite、
provenance-preserving materialization，以及 candidate endpoint 的 read-only
boundary；它们不是数学证明本身。
