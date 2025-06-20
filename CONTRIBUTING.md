# 贡献指南

感谢您考虑为达梦数据库MCP服务项目做出贡献！

## 🤝 如何贡献

### 1. 报告问题

如果您发现了bug或有功能建议，请：

1. 检查 [Issues](../../issues) 确保问题未被报告
2. 创建新的Issue，详细描述：
   - 问题的具体表现
   - 重现步骤
   - 预期行为
   - 实际行为
   - 环境信息（达梦数据库版本、Python版本、Cursor版本）

### 2. 提交代码

1. **Fork项目**
   ```bash
   git clone https://github.com/Gcluowenqiang/Dm-mcp.git
   cd Dm-mcp
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/新功能名称
   # 或
   git checkout -b fix/修复问题名称
   ```

3. **编写代码**
   - 遵循现有的代码风格
   - 添加必要的注释
   - 确保代码通过测试
   - 遵循DRY、KISS、SOLID、YAGNI原则

4. **提交更改**
   ```bash
   git commit -m "feat: 添加新功能描述"
   # 或
   git commit -m "fix: 修复问题描述"
   ```

5. **推送到远程仓库**
   ```bash
   git push origin feature/新功能名称
   ```

6. **创建Pull Request**
   - 清晰描述更改内容
   - 引用相关的Issue编号
   - 确保CI检查通过

## 📋 代码规范

### Python代码风格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用有意义的变量和函数名
- 添加文档字符串和注释
- 最大行长度：88字符

### 达梦数据库相关规范
- 遵循达梦数据库最佳实践
- 使用标准的达梦SQL语法
- 适当处理达梦特有的数据类型
- 确保与dmPython驱动的兼容性

### 提交信息格式
使用约定式提交格式：
```
type(scope): description

[optional body]

[optional footer]
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 添加测试
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化
- `security`: 安全相关修复

示例：
```
feat(database): 添加对达梦新数据类型的支持

增加对达梦CLOB和BLOB数据类型的解析和文档生成支持

Closes #123
```

## 🧪 测试

运行测试：
```bash
python -m pytest tests/
```

添加新功能时，请同时添加相应的测试用例。

### 测试数据库连接
确保在测试环境中：
- 已安装达梦数据库
- 配置了正确的连接参数
- 创建了测试用的schema和表

## 📝 文档

- 更新相关的文档文件
- 确保README.md保持最新
- 在代码中添加必要的注释
- 更新CHANGELOG.md记录变更

## 🔒 安全注意事项

- 不要在代码中硬编码敏感信息
- 确保新功能遵循现有的安全模式
- 测试时使用测试数据库，不要使用生产数据
- 遵循最小权限原则

## 🐳 Docker开发

如果您的贡献涉及Docker：
- 确保Dockerfile遵循最佳实践
- 测试容器构建和运行
- 更新相关的Docker文档

## 🛡️ 许可证

通过贡献代码，您同意您的贡献将基于MIT许可证进行许可。

## 📚 开发环境设置

1. **克隆仓库**
   ```bash
   git clone https://github.com/Gcluowenqiang/Dm-mcp.git
   cd Dm-mcp
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   ```bash
   cp cursor-config-example.json cursor-config-local.json
   # 编辑cursor-config-local.json填入真实的达梦数据库连接信息
   ```

## 🎯 贡献优先级

我们特别欢迎以下类型的贡献：

### 高优先级
- 性能优化
- 安全漏洞修复
- 达梦数据库兼容性改进
- 文档完善

### 中优先级
- 新功能开发
- 代码重构
- 测试用例添加
- 错误处理改进

### 低优先级
- 代码风格改进
- 注释完善
- 示例代码

## 💬 讨论

如有疑问，可以通过以下方式联系：
- 创建Issue进行讨论
- 提交Pull Request描述中详细说明
- 发送邮件至项目维护者

## 🏆 贡献者

感谢所有为本项目做出贡献的开发者！

---

再次感谢您的贡献！🎉

**项目地址**: [https://github.com/Gcluowenqiang/Dm-mcp](https://github.com/Gcluowenqiang/Dm-mcp) 