# 從記憶保存到認知重建：長期 AI 記憶的生成基底、再生性遺忘與認知等價

**From Memory Preservation to Cognitive Reconstruction: Generative Substrates, Regenerative Forgetting, and Cognitive Equivalence for Long-Lived AI Systems**

**版本：v0.1**  
**日期：2026-08-27**  
**性質：理論命題論文 / Conceptual Architecture Paper**  
**狀態：尚未形成實證性完備理論；本文提出可形式化、可驗證、可工程化的研究框架。**

---

## 摘要

現有長期 AI 記憶系統通常把「記得更多」視為主要目標：將過去對話、文件、工作狀態、摘要、向量索引或結構化紀錄持續保存，並在未來任務中檢索。然而，若一個長期運作的 AI 持續將每一次已形成的認知狀態、解釋、推理結果與工作脈絡都視為應永久保存的記憶，則記憶容量、檢索複雜度、上下文重建成本與語義漂移風險將隨時間不斷累積。

本文提出一個不同的命題：

> **記憶未必需要保存完整認知；對某些認知而言，只需保存足以在未來重新生成有效認知的條件。**

因此，本文區分「認知狀態」與「持久化記憶」，並提出 **認知因式分解（cognitive factorization）**、**認知重建（cognitive reconstruction）**、**認知等價（cognitive equivalence）** 與 **再生性遺忘（regenerative forgetting）** 四個核心概念。本文將可持久化資訊劃分為不可重建證據、結構記憶、生成記憶、可重新計算資訊與暫態工作認知五類，並提出一個記憶處置算子，使 AI 在任務結束時不再只回答「要不要存」，而是決定應採取 PRESERVE、STRUCTURALIZE、GENERATIZE、RECOMPUTE 或 DISCARD 中的哪一種持久化語義。

本文進一步定義重建算子、驗證算子與觀察等價條件，主張重建後的認知不必在文字、推理軌跡或內部表示上與原始認知相同，而應在指定的錨點、不變量、決策、依賴與證據義務下保持功能等價。基於此觀點，遺忘不再必然代表資訊損失，而可能是將暫時物化的認知解除物化，只保留其生成基底。

既有 MNEME 已建立 `MEMORY.md != MEMORY` 與 `MEMORY != CONTEXT` 的工程分離；本文進一步提出：

```text
MEMORY != COGNITION
```

若此命題成立，長期 AI 記憶的核心研究問題將不再只是「如何保存更多」，而是：

> **對一個未來仍需有效工作的 AI 而言，要重新知道某件事，最低限度必須保留什麼？**

---

## 關鍵詞

AI 長期記憶、認知重建、認知因式分解、再生性遺忘、結構記憶、生成記憶、認知等價、上下文重建、MNEME、SOACR、AI Residence

---

# 1. 問題背景：記憶容量不是唯一問題

長期 AI 記憶常被描述成儲存與檢索問題：

```text
experience
→ store
→ index
→ retrieve
→ context
```

在這個模型下，只要某段歷史資訊未被保存，就可能被視為「失憶」；只要保存得越多，系統似乎就越完整。

然而，這種假設隱含了一個未被充分區分的等式：

```text
what the AI once understood
≈
what the memory system must preserve
```

此等式對某些資料成立，例如原始觀測、明確決策、不可逆事件與外部證據；但對大量「已形成的認知」並不一定成立。

例如，一個 AI 在某次工程工作中形成了完整的架構理解。該理解可能以數萬字討論、數十輪推理、反例比較與局部假設構成。若未來的任務只是再次理解該架構，真正需要永久保存的未必是所有表面敘述，而可能只是：核心目標、不可違反的不變量、模組與依賴結構、已接受與已否決的決策、關鍵證據、可重新展開認知的生成規則，以及對重建結果的驗證條件。

因此，長期 AI 記憶的問題可以重新表述為：哪些資訊必須被保存，哪些認知可以由結構重新生成，哪些資訊應重新查詢，哪些暫態工作狀態應主動消失？

這不是單純的摘要問題，而是持久化語義的重新分類。

# 2. 三個基本不等式

本文以三個不等式作為出發點：

```text
MEMORY.md != MEMORY
MEMORY != CONTEXT
MEMORY != COGNITION
```

前兩個不等式已出現在 MNEME 的既有設計中：人類可讀文件與工作上下文都只是由 canonical memory 所形成的投影或 materialization。本文新增第三個不等式：一個 AI 在某時刻形成的完整工作認知狀態，不必被逐項永久保存。

# 3. 形式化：認知狀態與持久記憶

令 AI 在時間 t 的某個可工作的認知狀態為：

\[
C_t
\]

令其持久化記憶狀態為：

\[
M_t
\]

傳統直覺常近似於：

\[
M_t \approx C_t
\]

即把當時已形成的重要認知盡可能保存。

本文改採：

\[
M_t = F(C_t,E_t)
\]

其中 F 為**認知因式分解算子**，E_t 為當時可用的證據、環境與外部狀態。

未來時間 t' 需要重新取得工作認知時：

\[
\hat C_{t'} = R(M_t,X_{t'},W_{t'})
\]

其中 R 為**認知重建算子**；X_{t'} 為當下任務、身份、權限、工具與局部上下文；W_{t'} 為需要重新查詢或重新計算的外部世界狀態；\hat C_{t'} 為重建出的認知。

關鍵在於：

\[
\hat C_{t'} \neq C_t
\]

並不必然代表失敗。未來任務、外部世界與可用模型可能已不同；真正需要的不是逐字還原，而是在關鍵約束下保有有效等價。

# 4. 認知因式分解：保存生成基底，而非所有表面認知

本文將一個可重建認知的持久生成基底暫定為：

\[
K=(A,S,G,O,P)
\]

其中：

## 4.1 Anchors — 錨點 A

不可任意重算或改寫的事實性基底，例如使用者明確要求、已做決策、commit hash、實驗結果、日期與事件、外部觀測、身份證據與原始來源。

錨點具有不可替代性。重新生成一個「內容相似」的錨點不能取代原始證據。

## 4.2 Structure — 結構 S

認知中的關係骨架，例如 dependency graph、causal graph、hierarchy、module topology、theory relation、decision tree、constraint graph 與 state transition。

很多長篇認知其實是某種結構的語言展開。若結構本身可被持久保存，未來可以重新生成不同表述的工作認知。

## 4.3 Generators — 生成規則 G

生成規則不是已展開的完整認知，而是「如何重新得出認知」的規則，例如：

```text
identity must be resolved before private retrieval
Capability != Authority
rollback != compensation
if dependency B changes, dependent A must be revalidated
```

它們可以是推導規則、重建 recipe、展開策略、認知模板或狀態恢復程序。

## 4.4 Obligations / Invariants — 義務與不變量 O

重建後的認知不能只是「看起來合理」。必須存在一組不可違反的重建義務，例如某些事實不可變、某些決策不可偷偷反轉、identity boundary 不可跨越、dependency 必須保持、provenance 必須可追溯，以及 freshness requirement 必須重新查詢。

O 因此構成 reconstruction contract。

## 4.5 Provenance — 來源 P

若系統只保留結構與規則，而無法回答「這些結構與規則為什麼成立」，重建就很容易逐步變成自洽但錯誤的敘事。因此需要保存 source、event、document、experiment、commit、decision record、derivation 與 timestamp。

# 5. 五種持久化語義

本文提出五類持久化語義。

## 5.1 Type E — Evidential / Irreducible Memory

這類資訊不能由重建代替，例如原始觀測、使用者原話、實驗數值、commit hash、明確事件、簽章、identity evidence。

其核心特性是：

\[
R(E) \neq E
\]

即使 R(E) 能生成語義完全相同的句子，那也不再是原始證據。

因此：

```text
Evidential memory → PRESERVE
```

## 5.2 Type S — Structural Memory

這類資訊的價值在於關係結構，而不是所有語言展開結果，例如模組依賴、專案結構、理論分類、constraint topology、workflow state graph。

因此可以採：

```text
expanded explanation
→ structure
→ STRUCTURALIZE
```

## 5.3 Type G — Generative / Reconstructible Memory

這類認知的表面表述可以消失，只需保留生成所需的基底與義務，例如某架構為什麼被採用、某理論如何由前提展開、某專案的整體理解、某套方法論的操作性認知。

可保存 anchors + structure + rules + obligations + provenance，而不必永久保存每次完整展開。

## 5.4 Type R — Recomputable Knowledge

某些資訊甚至不適合被當成長期記憶，例如最新 package version、當前 GitHub HEAD、最新市場價格、今天的天氣、即時 API 文件狀態。

真正需要保存的可能是 where/how to query、freshness requirement、previous observation 與 observation time。

未來應採：

\[
W_{t'}=Q(Source,t')
\]

而不是沿用：

\[
W_{t'}=W_t
\]

因此：

```text
dynamic world knowledge → RECOMPUTE
```

## 5.5 Type W — Working / Ephemeral Cognition

這類是任務期間暫時存在的工作認知，例如暫時假設、scratch reasoning、局部分解、一次性候選排序與 debugging 中間狀態。

任務結束後可能只留下 final finding、failure evidence、decision 與 replay recipe，其餘：

```text
working cognition → DISCARD
```

# 6. Memory Disposition：從「要不要存」改成「如何持久化」

本文提出 Memory Disposition Operator：

\[
D(c)\in\{PRESERVE,STRUCTURALIZE,GENERATIZE,RECOMPUTE,DISCARD\}
\]

其中 c 是一個 cognition candidate。

例如：

| cognition candidate | disposition |
|---|---|
| 「採用方案 B」這個正式決策 | PRESERVE |
| 方案 B 的 dependency graph | STRUCTURALIZE |
| 為什麼方案 B 整體可行的長篇解釋 | GENERATIZE |
| 某套件目前最新版 | RECOMPUTE |
| 當時列出的十二個暫時猜測 | DISCARD |

這比「importance score > threshold 就寫進 memory」多了一層持久化語義。重要度不能回答「這個資訊應該以哪一種形式在未來存在」，而 disposition 可以。

# 7. 認知重建不是普通摘要

普通摘要通常是：

```text
large text
→ shorter text
```

它不一定知道哪些內容不可丟、哪些關係必須保存、哪些決策不可改、哪些資訊應重新查詢、哪些表述可以重新生成。

本文的重建流程則是：

```text
Cognition
→ Factorization
→ Anchors
→ Structure
→ Generators
→ Obligations
→ Provenance
→ Reconstruction
→ Candidate Cognition
→ Verification
```

因此它比較接近**可驗證的認知編譯與重建**，而非文字壓縮。

# 8. 重建算子與驗證算子

令：

\[
K=(A,S,G,O,P)
\]

重建：

\[
\hat C=R(K,X,W)
\]

但 R 的輸出不能直接視為有效 cognition。需要：

\[
V(\hat C,K,X,W)\in\{PASS,PARTIAL,FAIL\}
\]

最低限度可以檢查：Anchor preservation、Invariant satisfaction、Dependency consistency、Decision consistency、Provenance coverage、Freshness obligations、Authority boundaries。

因此：

```text
reconstruction != generation
```

更準確地說：

```text
reconstruction
=
generation under canonical obligations
+ verification
```

# 9. 認知等價：不要求相同文字，也不要求相同推理軌跡

若未來 AI 重新理解一個系統，它幾乎不可能產生與過去完全相同的 token sequence。要求 \hat C=C 並不合理。

本文提出用指定觀察面 Q 定義認知等價：

\[
C\sim_Q\hat C
\]

其中 Q 可以是一組 obligation queries，例如核心不變量、write authority、被否決決策、dependency、fresh query requirement 與 identity boundary。

如果原 cognition 與 reconstruction 在這些關鍵觀察面保持一致，即可視為功能上等價，即使文字、敘述順序、推理過程、使用模型與局部抽象層級不同。

```text
COGNITIVE EQUIVALENCE
!= TOKEN EQUALITY
!= TRACE EQUALITY
```

# 10. 再生性遺忘：遺忘可以是解除物化，而非資訊損失

傳統 forgetting 常被理解為：

```text
information was present
→ information is gone
```

本文提出另一種形式：

```text
surface cognition was materialized
→ surface cognition is de-materialized
→ generative substrate remains
```

稱為 **Regenerative Forgetting — 再生性遺忘**。

其核心不是把所有東西刪掉，而是刪除「可安全重新生成的表面物化」。例如，一個 AI 不再保存某次 20,000 token 的架構說明，但保存 12 個 anchors、18 條 dependency edges、7 個 invariants、4 個 rejected decisions、2 個 reconstruction recipes 與 provenance pointers。

因此：

\[
Forget(C)\neq Lose(K)
\]

只要 K 足以在 obligations 下重新生成有效 cognition，forgetting 就可以是一種受控 de-materialization。

# 11. 長期記憶成長率

若每一輪 cognition 都直接追加：

\[
M_{t+1}=M_t+\Delta C_t
\]

則持久記憶容量會近似隨 cognition production 持續成長。

若導入 factorization：

\[
M_{t+1}=M_t+\Delta A+\Delta S+\Delta G+\Delta O+\Delta P-\Delta D
\]

其中 \Delta D 包括 derivable content elimination、semantic duplication removal、expired working cognition、superseded projection、recomputable-state retirement 與 redundant explanation de-materialization。

理想狀態下可能出現：

\[
\frac{d|M|}{dt}\ll\frac{d|C|}{dt}
\]

這不是本文宣稱已被證明的結果，而是一個可實驗命題：若大量 cognition 屬於 constrained reconstructible，而不是 irreducible evidence，則長期持久記憶的成長率可能顯著低於 AI 實際生成與使用的認知總量。

# 12. Cognitive Seed：認知種子

本文可將 K=(A,S,G,O,P) 視為一種 Cognitive Seed：

```text
Project Cognitive Seed
├── Anchors
│   ├── goals
│   ├── accepted decisions
│   └── external evidence
├── Structure
│   ├── modules
│   ├── dependencies
│   └── state relations
├── Generators
│   ├── reconstruction recipes
│   └── derivation rules
├── Obligations
│   ├── invariants
│   ├── authority boundaries
│   └── freshness rules
└── Provenance
    ├── commits
    ├── experiments
    └── source documents
```

同一 seed 可以針對不同任務展開不同 cognition，而不要求這些工作 cognition 彼此相同。

# 13. 從 Retrieval 到 Reconstruction

典型 RAG 模式：

```text
query
→ retrieve old text
→ insert old text
→ answer
```

本文提出的模式：

```text
MemoryNeed
→ determine required cognitive domain
→ retrieve anchors
→ retrieve structure
→ retrieve generators
→ retrieve obligations
→ refresh recomputable state
→ reconstruct
→ verify
→ materialize context
```

因此 retrieval 只是一個子程序。核心能力變成 Cognitive Reconstruction。

長期 AI 記憶系統未來可能不再以「找回最相似內容」為主要指標，而要回答：能否用最少且可驗證的持久基底，重建足以完成當下任務的 cognition？

# 14. 與 MNEME 的關係

既有 MNEME 已經區分：

```text
MEMORY.md != MEMORY
MEMORY != CONTEXT
CANONICAL STATE != PROJECTION
PROPOSAL != COMMIT
```

本文新增：

```text
MEMORY != COGNITION
```

因此，MNEME 未來可以從 canonical memory layer 進一步被理解為 **Canonical Cognitive Substrate**。

這不是說 MNEME 現在已經完成這種能力，而是本文指出一種演化方向：

```text
Canonical Evidence
      +
Structural Memory
      +
Generative Memory
      +
Recomputation Metadata
      ↓
Cognitive Reconstruction
      ↓
Validated Cognition
      ↓
Working Context
```

這個方向仍必須保持既有 transaction safety、provenance、authority separation、scope isolation 與 fail-closed write semantics。

# 15. 與 SOACR 的關係

在既有架構中，SOACR 的位置偏向：

```text
MemoryNeed
→ retrieval / routing
→ reconstruction
→ continuation
```

若採本文命題，SOACR 可以進一步承擔：

```text
MemoryNeed
→ Cognitive Need
→ Seed Selection
→ Reconstruction Plan
→ External Recompute
→ Candidate Cognition
→ Verification
→ Context Materialization
```

因此，SOACR 不只是決定「取哪幾條 memory」，而可能需要決定「當下需要重建哪一種 cognition」。

# 16. Cognitive Virtual Memory 類比

此架構與虛擬記憶體有一個有限但有用的類比。作業系統不要求將所有可能工作狀態永久保留在 RAM，而會利用 persistent backing、executable structure、page-in、recomputation、cache 與 eviction。

對長期 AI 而言：

```text
persistent cognitive substrate
→ page fault: need architecture cognition
→ reconstruct
→ verify
→ materialize into model context
```

因此可以得到一個概念：**Cognitive Virtual Memory**。

其中 MNEME 類似 persistent cognitive backing；SOACR 類似 cognitive page manager / reconstruction orchestrator；model context 類似有限 working memory；reconstructed cognition 類似按需 materialized working state。

此類比不是說 cognition 與 RAM 等價，而是說明：不必把所有曾物化的 cognition 永久保存在可立即消費的形式中。

# 17. 最大安全風險：把不可重建證據誤判成可重建

本文最大的安全風險不是 reconstruction 失敗本身，而是：

```text
irreducible evidence
→ mistakenly classified as reconstructible
→ original evidence discarded
```

此錯誤可能不可逆。例如使用者正式決策只留下摘要、實驗原始數值只留下結論、identity evidence 只留下生成描述、特定時間的法律狀態被當成可重新推導。

因此本文主張：**reconstructibility classification 應採保守策略。**

不確定時應傾向 PRESERVE，而不是 GENERATIZE。

# 18. 其他主要失敗模式

1. **Hidden Dependency Loss**：表面內容可重建，但關鍵依賴未保存。
2. **Semantic Drift**：模型或生成規則變化，重建 cognition 漂離原 obligations。
3. **False Equivalence**：表面回答類似，但關鍵 decision/authority boundary 已不同。
4. **Stale Recompute**：應 fresh query 的資訊仍使用舊快取。
5. **Provenance Collapse**：系統能重建答案，卻說不出原始證據。
6. **Over-Factorization**：為節省記憶而把本應直接保存的資訊拆得過度複雜。

# 19. 一個最小判定原則

對 cognition candidate c，可以依次詢問：

1. 若原始內容消失，未來是否仍需要「它曾經真的發生過」的證據？若是：PRESERVE。
2. 它是否主要是一個關係／依賴／狀態結構？若是：STRUCTURALIZE。
3. 它是否能由 anchors + structure + rules + obligations 重新生成，而且不要求字面相同？若是：GENERATIZE。
4. 它是否應由未來世界重新查詢，而不是沿用舊值？若是：RECOMPUTE。
5. 它是否只服務於當前工作，且沒有後續證據、決策或 replay 價值？若是：DISCARD。

若任何判定不確定：

```text
PRESERVE / REVIEW
```

而不是自動刪除。

# 20. 對「記憶完整性」的新定義

傳統完整性容易被理解為「保存越多歷史內容越完整」。本文提出：

> **記憶完整性不應等於表面歷史內容完整性，而應等於未來所需證據與有效 cognition 的可恢復性完整性。**

若對所有必要的未來 cognition need n∈N，系統皆能找到必要 evidence、取得可重建結構、補 fresh world state、生成 cognition 並通過 obligations，則可稱其具有：

**Reconstructive Memory Completeness**。

即使大量過去表面 cognition 已被 de-materialize。

# 21. 與「全部保存」的關係

本文並不主張應盡量刪除資料。在儲存成本很低、證據價值高或 reconstructibility 未被證明時，完整保留原始資料可能仍然是最佳策略。

因此本文不是：

```text
store less at all costs
```

而是：

```text
do not confuse
"can be stored"
with
"must remain materialized as canonical cognition"
```

原始 archive 甚至可以繼續存在，但未必需要被視為 active canonical working memory。

# 22. 可驗證研究命題

本文提出以下可實驗命題：

## H1 — Memory Growth Hypothesis

在長期任務中，若大量 cognition 可被 factorize，則 cognitive substrate 的增長速度可以顯著低於完整 cognition archive。

## H2 — Reconstruction Sufficiency Hypothesis

對某類 constrained-reconstructible cognition，保存 A,S,G,O,P 可在指定觀察集合 Q 下重建功能等價 cognition。

## H3 — Regenerative Forgetting Hypothesis

在保留 seed 與 verifier 的前提下，刪除表面 cognition 不必降低未來任務成功率。

## H4 — Task-Conditioned Reconstruction Hypothesis

同一 cognitive seed 針對不同任務生成不同 cognition，比重播單一歷史摘要更有效率。

## H5 — Evidence Separation Hypothesis

將 evidential memory 與 reconstructible cognition 分離，可降低「生成內容取代原始證據」的錯誤風險。

# 23. 建議的實驗路線

## Phase 1 — Observation Only

對既有 memory 進行只讀分析：

```text
possible_exact
possible_structural
possible_generative
possible_recomputable
possible_ephemeral
unknown
```

只做 candidate classification，不自動刪除或轉換。

## Phase 2 — Parallel Reconstruction

保留完整原始記憶，同時建立 cognitive seed，比較 full-memory reconstruction 與 seed-based reconstruction。

## Phase 3 — Obligation Benchmarks

建立固定的 observation queries 與 verifier，測試：

\[
C\sim_Q\hat C
\]

是否成立。

## Phase 4 — Controlled De-materialization

只有在重建與驗證反覆通過後，才允許某些 surface cognition 不再進 active memory；原始 archive 仍可保留。

## Phase 5 — Long-Horizon Evaluation

測量 memory growth、reconstruction latency、token cost、task success、semantic drift、evidence retention、false equivalence rate 與 recomputation freshness。

# 24. 對 Private Residence Dry-Run Migrator 的影響

原本 Dry-Run Migrator 的問題是：哪些 Markdown 可以安全映射成 MNEME record？

本文提出後，應增加第二個只讀觀察層：

```text
Compatibility Mapping
        ↓
Persistence Candidate Analysis
        ├── Evidential
        ├── Structural
        ├── Generative
        ├── Recomputable
        ├── Ephemeral
        └── Unknown
```

但這個分類器在第一版不應有刪除權或 canonical commit authority。

尤其：

```text
possible_generative
!=
safe_to_delete_original
```

因此 Dry-Run Migrator 更適合先成為 **Memory Factorization Analyzer** 的一部分，而不是直接成為 migration engine。

# 25. 核心不變量擴充

若未來進入實作，可考慮加入以下概念性 invariants：

```text
MEMORY != COGNITION
RECONSTRUCTION != RECALL
RECONSTRUCTIBLE != DISPENSABLE
GENERATED EQUIVALENCE != EVIDENCE EQUALITY
ARCHIVE != ACTIVE MEMORY
FORGETTING != NECESSARILY LOSS
RECOMPUTABLE != STALE-CACHE-REUSABLE
SEED != AUTHORITY
```

其中最重要的一條是：

```text
RECONSTRUCTIBLE != DISPENSABLE
```

能重建不等於現在就有權刪除原始資料。

# 26. 最終命題

本文可將整個方向壓縮成以下敘述：

> 長期 AI 記憶的最小持久化單位，不必總是「AI 曾經知道過什麼」；對可重建認知而言，更重要的可能是「要在未來重新形成有效認知，最低限度必須保留哪些證據、結構、生成規則、約束與來源」。

因此：

\[
Memory \neq Stored\ Cognition
\]

而可能更接近：

\[
Memory = Conditions\ for\ Valid\ Future\ Cognition
\]

這使得 AI 的遺忘可以被重新理解：

> **遺忘不一定是資訊消失；它也可以是暫時認知的解除物化，只要足以重新生成有效認知的 canonical substrate 仍然存在。**

若此命題成立，長期 AI 記憶的研究中心將從：

```text
How do we store more?
```

轉向：

```text
What must remain invariant
so that valid cognition can exist again?
```

# 27. 結論

本文提出一種從「記憶保存」走向「認知重建」的長期 AI 記憶觀。主要貢獻包括：

1. 區分 Memory 與 Cognition；
2. 提出 cognitive factorization；
3. 以 A,S,G,O,P 表示 cognitive seed；
4. 區分 Evidential、Structural、Generative、Recomputable、Ephemeral 五種持久化語義；
5. 提出 Memory Disposition Operator；
6. 定義 reconstruction + verification 流程；
7. 以 observational equivalence 取代 token equality；
8. 提出 Regenerative Forgetting；
9. 提出 Reconstructive Memory Completeness；
10. 建立與 MNEME、SOACR、Cognitive Virtual Memory 的可能架構連結。

這些概念目前仍屬理論命題，尤其「哪些 cognition 真正可安全 factorize」仍需要大量實驗與負向驗證。

因此，本文不主張立即讓 AI 自主刪除其完整歷史。相反地，第一個工程原則應是：

> **先證明能重建，再討論能否解除物化；先保證證據不可失，再追求記憶效率。**

在這個前提下，長期 AI 記憶才可能從不斷膨脹的歷史倉庫，轉變成一個可驗證、可重建、可按需物化的 **Canonical Cognitive Substrate**。

---

## 與既有工程基線的關係

本文建立於現有 MNEME 的兩個已完成設計基線之上，但不等同於它們已實作的能力：

- `docs/superpowers/specs/2026-08-27-mneme-v0.1-design.md`
- `docs/superpowers/specs/2026-08-27-memory-markdown-compatibility-profile-design.md`

既有工程已建立 canonical memory、transaction、route、budgeted projection 與 Markdown compatibility；本文新增的 cognitive factorization、reconstructive memory、regenerative forgetting 與 cognitive equivalence 仍屬後續研究命題。
