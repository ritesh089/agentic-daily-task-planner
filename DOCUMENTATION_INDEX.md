# Framework Documentation Index

**Quick reference for all framework documentation**

---

## 📖 Documentation Structure

### For Framework Users

| Document | Purpose | Lines | What's Inside |
|----------|---------|-------|---------------|
| **[README.md](README.md)** | Entry point | ~500 | • Quick start<br>• Feature overview<br>• Installation<br>• Examples |
| **[User Guide](docs/USER_GUIDE.md)** | Complete tutorial | ~900 | • Quick start<br>• Core concepts<br>• Configuration<br>• Building workflows<br>• Memory management<br>• Observability<br>• Durability<br>• Error handling<br>• MCP integration<br>• Best practices |
| **[API Reference](docs/API_REFERENCE.md)** | API documentation | ~600 | • Configuration API<br>• Errors API<br>• Resilience API<br>• Lifecycle API<br>• Health API<br>• All framework components<br>• Code examples |
| **[Troubleshooting](docs/TROUBLESHOOTING.md)** | Problem solving | ~600 | • Common issues<br>• Solutions<br>• Diagnostics<br>• Error resolution<br>• Health checks |

### For Framework Developers

| Document | Purpose | Lines | What's Inside |
|----------|---------|-------|---------------|
| **[Developer Guide](docs/DEVELOPER_GUIDE.md)** | Architecture & contributing | ~900 | • Architecture overview<br>• Component design<br>• Design principles<br>• Development setup<br>• Testing guide<br>• Contributing guidelines<br>• Implementation details |

---

## 🚀 Getting Started Path

### New Users
1. Read **README.md** (5 minutes)
2. Follow **Quick Start** in [User Guide](docs/USER_GUIDE.md) (15 minutes)
3. Try an example from `examples/` directory (10 minutes)
4. Build your first workflow following [User Guide](docs/USER_GUIDE.md) (30 minutes)

### Experienced Users
- **Need API info?** → [API Reference](docs/API_REFERENCE.md)
- **Having issues?** → [Troubleshooting](docs/TROUBLESHOOTING.md)
- **Best practices?** → [User Guide - Best Practices](docs/USER_GUIDE.md#best-practices)

### Contributors
1. Read [User Guide](docs/USER_GUIDE.md) to understand user perspective
2. Study [Developer Guide](docs/DEVELOPER_GUIDE.md) for architecture
3. Review `tests/` for testing patterns
4. Follow contribution guidelines in [Developer Guide](docs/DEVELOPER_GUIDE.md#contributing)

---

## 📚 Documentation by Topic

### Configuration
- **Quick Start**: [User Guide - Configuration](docs/USER_GUIDE.md#configuration)
- **API Reference**: [API Reference - Configuration](docs/API_REFERENCE.md#configuration)
- **Troubleshooting**: [Troubleshooting - Configuration Issues](docs/TROUBLESHOOTING.md#configuration-issues)
- **CLI**: `bin/framework config --help`

### Workflows
- **Tutorial**: [User Guide - Building Workflows](docs/USER_GUIDE.md#building-workflows)
- **Examples**: `examples/` directory
- **CLI**: `bin/framework init --help`

### Memory Management
- **Guide**: [User Guide - Memory Management](docs/USER_GUIDE.md#memory-management)
- **API**: [API Reference - Memory](docs/API_REFERENCE.md#memory)
- **Examples**: `examples/conversational-assistant/`

### Observability
- **Guide**: [User Guide - Observability](docs/USER_GUIDE.md#observability)
- **API**: [API Reference - Observability](docs/API_REFERENCE.md#observability)
- **Setup**: [User Guide - Quick Start](docs/USER_GUIDE.md#quick-start)

### Durability
- **Guide**: [User Guide - Durability](docs/USER_GUIDE.md#durability--checkpointing)
- **API**: [API Reference - Durability](docs/API_REFERENCE.md#durability)
- **Troubleshooting**: [Troubleshooting - Database Issues](docs/TROUBLESHOOTING.md#databasecheckpoint-issues)

### Error Handling
- **Guide**: [User Guide - Error Handling](docs/USER_GUIDE.md#error-handling)
- **API**: [API Reference - Errors](docs/API_REFERENCE.md#errors)
- **Resilience**: [API Reference - Resilience](docs/API_REFERENCE.md#resilience)

### MCP Integration
- **Guide**: [User Guide - MCP Integration](docs/USER_GUIDE.md#mcp-integration)
- **API**: [API Reference - MCP](docs/API_REFERENCE.md#mcp)
- **Examples**: `examples/conversational-assistant/`

---

## 🔧 Tools & Commands

### CLI Commands
```bash
# Health check
bin/framework health

# Configuration
bin/framework config                  # Show config
bin/framework config --validate       # Validate config
bin/framework config --create FILE    # Create example

# Workflow management
bin/framework init NAME --template TYPE    # Create workflow
bin/framework validate PATH                # Validate workflow

# Version
bin/framework version
```

**Full Reference**: [User Guide - CLI Tools](docs/USER_GUIDE.md#cli-tools)

---

## 🆘 Getting Help

### Common Questions

**Q: How do I get started?**  
A: Follow [User Guide - Quick Start](docs/USER_GUIDE.md#quick-start)

**Q: Where are the code examples?**  
A: Check `examples/` directory and [User Guide](docs/USER_GUIDE.md)

**Q: Something's not working, help!**  
A: Run `bin/framework health` and check [Troubleshooting](docs/TROUBLESHOOTING.md)

**Q: What APIs are available?**  
A: See [API Reference](docs/API_REFERENCE.md)

**Q: I want to contribute**  
A: Read [Developer Guide - Contributing](docs/DEVELOPER_GUIDE.md#contributing)

**Q: How does X work internally?**  
A: See [Developer Guide](docs/DEVELOPER_GUIDE.md)

---

## 📊 Documentation Coverage

| Topic | User Guide | API Reference | Troubleshooting | Developer Guide |
|-------|:----------:|:-------------:|:---------------:|:---------------:|
| Configuration | ✅ | ✅ | ✅ | ✅ |
| Workflows | ✅ | ✅ | ✅ | ✅ |
| Memory | ✅ | ✅ | ✅ | ✅ |
| Observability | ✅ | ✅ | ✅ | ✅ |
| Durability | ✅ | ✅ | ✅ | ✅ |
| Error Handling | ✅ | ✅ | ✅ | ✅ |
| MCP | ✅ | ✅ | ✅ | ✅ |
| CLI Tools | ✅ | ✅ | ✅ | ✅ |
| Testing | ✅ | - | - | ✅ |
| Contributing | - | - | - | ✅ |

---

## 🎯 Documentation Goals

✅ **User-Friendly**: Clear, concise, practical  
✅ **Comprehensive**: Covers all features  
✅ **Organized**: Easy to navigate  
✅ **Searchable**: Good headings and TOC  
✅ **Examples**: Real code examples  
✅ **Up-to-Date**: Maintained with framework

---

## 📝 Maintenance

This documentation is maintained alongside the framework code.

**When making changes:**
1. Update relevant sections
2. Check cross-references
3. Test code examples
4. Update version numbers

**Last Updated**: November 25, 2025  
**Framework Version**: 1.0.0-beta

