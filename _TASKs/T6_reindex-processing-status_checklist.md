# Task 6 实施检查清单

## 📋 方案A：保守修复（推荐先实施）

### 前置准备
- [ ] 阅读完整的 `task6.md` 文档
- [ ] 备份当前代码：`git commit -am "Backup before Task 6 implementation"`
- [ ] 创建新分支：`git checkout -b fix/reindex-processing-status`

### 代码修改
- [ ] 打开文件：`backend/routers/documents.py`
- [ ] 定位到第821-828行
- [ ] 将以下代码：
  ```python
  if status_record.status in [StatusEnum.PENDING, StatusEnum.PROCESSING]:
      files_skipped += 1
      logger.debug(...)
      continue
  ```
  修改为：
  ```python
  if status_record.status == StatusEnum.PENDING:
      files_skipped += 1
      logger.debug(...)
      continue

  if status_record.status == StatusEnum.PROCESSING:
      if not req.force:
          files_skipped += 1
          logger.debug(...)
          continue
  ```
- [ ] 保存文件
- [ ] 检查语法错误：`python -m py_compile backend/routers/documents.py`

### 测试验证
- [ ] 重启后端服务
- [ ] 准备测试数据：确保有3个PROCESSING状态的文档
- [ ] 点击"Re-index Failed Files"按钮（force=false）
- [ ] 验证：PROCESSING文档被标记为PENDING
- [ ] 验证：后台开始处理这些文档
- [ ] 检查日志：确认没有错误

### 部署
- [ ] 提交代码：`git commit -am "Fix: Allow PROCESSING documents to be re-indexed in force mode"`
- [ ] 推送到远程：`git push origin fix/reindex-processing-status`
- [ ] 创建Pull Request
- [ ] 代码审查通过后合并
- [ ] 部署到生产环境

---

## 📋 方案B：完整修复（可选，建议在方案A稳定后实施）

### 前置准备
- [ ] 确认方案A已成功实施并稳定运行
- [ ] 在测试环境中进行以下操作
- [ ] 备份LightRAG知识图谱数据

### 代码修改 - Step 1: 添加删除方法
- [ ] 打开文件：`backend/services/rag_service.py`
- [ ] 在 `query()` 方法之后添加 `delete_document_from_kg()` 方法
- [ ] 参考 `task6.md` 第313-357行的完整代码
- [ ] 保存文件

### 代码修改 - Step 2: 修改重新索引逻辑
- [ ] 打开文件：`backend/routers/documents.py`
- [ ] 定位到第847行（`if should_reindex:` 块）
- [ ] 在状态更新之前添加文档删除逻辑
- [ ] 参考 `task6.md` 第373-437行的完整代码
- [ ] 添加必要的import：`from lightrag.utils import compute_mdhash_id`
- [ ] 保存文件

### 测试验证（测试环境）
- [ ] 重启后端服务
- [ ] 准备测试数据：1个INDEXED文档 + 3个PROCESSING文档
- [ ] 点击"Force Re-index All Files"按钮（force=true）
- [ ] 验证：所有4个文档被标记为PENDING
- [ ] 验证：INDEXED文档先被删除，日志显示"Deleting document from knowledge graph"
- [ ] 验证：后台处理所有4个文档
- [ ] 验证：不再出现"Ignoring document ID (already exists)"警告
- [ ] 检查知识图谱：确认文档数据被更新

### 性能测试
- [ ] 测试少量文档（<10个）的重新索引性能
- [ ] 测试大量文档（>50个）的重新索引性能
- [ ] 监控系统资源使用情况
- [ ] 确认没有内存泄漏或性能问题

### 部署
- [ ] 在测试环境中运行至少24小时
- [ ] 确认没有异常错误
- [ ] 提交代码：`git commit -am "Feature: Add force re-index with document deletion"`
- [ ] 推送到远程
- [ ] 创建Pull Request
- [ ] 代码审查通过后合并
- [ ] 部署到生产环境
- [ ] 持续监控日志和性能指标

---

## 🔍 验证检查点

### 功能验证
- [ ] "Re-index Failed Files"按钮正常工作
- [ ] "Force Re-index All Files"按钮正常工作
- [ ] PROCESSING状态文档可以被重新处理
- [ ] FAILED状态文档可以被重试
- [ ] INDEXED状态文档在force模式下可以被重新索引（方案B）

### 日志验证
- [ ] 日志中没有错误信息
- [ ] 日志中显示正确的文档处理流程
- [ ] 方案B：日志显示文档删除操作
- [ ] 方案B：不再出现"Ignoring document ID (already exists)"警告

### 性能验证
- [ ] 重新索引操作在合理时间内完成
- [ ] 系统资源使用正常
- [ ] 没有内存泄漏
- [ ] 并发处理正常

---

## ⚠️ 回滚准备

### 回滚触发条件
- [ ] 出现严重错误或系统崩溃
- [ ] 性能严重下降
- [ ] 数据丢失或损坏
- [ ] 用户反馈功能异常

### 回滚步骤
- [ ] 停止后端服务
- [ ] 恢复代码：`git revert <commit-hash>` 或 `git checkout <previous-commit>`
- [ ] 重启后端服务
- [ ] 验证系统恢复正常
- [ ] 通知相关人员

### 回滚后处理
- [ ] 分析失败原因
- [ ] 修复问题
- [ ] 在测试环境中重新验证
- [ ] 准备下一次部署

---

## 📊 成功标准

### 方案A成功标准
- [x] PROCESSING状态文档不再被错误跳过
- [x] "Re-index Failed Files"按钮正常工作
- [x] 所有测试场景通过
- [x] 没有新的错误或警告
- [x] 用户反馈功能正常

### 方案B成功标准
- [x] 方案A的所有成功标准
- [x] "Force Re-index All Files"可以真正重新索引所有文档
- [x] 文档删除操作正常工作
- [x] 不再出现"Ignoring document ID (already exists)"警告
- [x] 知识图谱数据正确更新
- [x] 性能在可接受范围内

---

## 📝 注意事项

### 重要提醒
1. **先实施方案A**：解决紧急问题，风险低
2. **测试环境验证**：方案B必须在测试环境中充分验证
3. **备份数据**：实施方案B前备份LightRAG知识图谱数据
4. **监控日志**：部署后持续监控日志和性能指标
5. **用户沟通**：如果需要长时间重新索引，提前通知用户

### 常见问题
1. **Q**: 如果文档删除失败怎么办？
   **A**: 代码已包含容错处理，会继续重新索引

2. **Q**: 如何确认文档ID是否正确？
   **A**: 检查日志中的doc_id，格式应为"doc-{32位md5hash}"

3. **Q**: 重新索引需要多长时间？
   **A**: 取决于文档数量和大小，通常每个文档1-5分钟

4. **Q**: 可以同时重新索引多个文档吗？
   **A**: 可以，系统会按批次处理（默认批次大小在配置中设置）

---

## ✅ 完成确认

### 方案A完成确认
- [ ] 所有代码修改已完成
- [ ] 所有测试已通过
- [ ] 代码已提交并合并
- [ ] 已部署到生产环境
- [ ] 运行稳定，没有问题

### 方案B完成确认
- [ ] 所有代码修改已完成
- [ ] 所有测试已通过
- [ ] 性能测试已通过
- [ ] 代码已提交并合并
- [ ] 已部署到生产环境
- [ ] 运行稳定，没有问题

### 文档更新
- [ ] 更新用户文档（如果需要）
- [ ] 更新技术文档
- [ ] 记录已知问题和解决方案
- [ ] 归档任务文档

---

**任务负责人**: _______________
**开始日期**: _______________
**完成日期**: _______________
**审核人**: _______________
**审核日期**: _______________
