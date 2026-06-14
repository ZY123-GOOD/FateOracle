# 🔮 八字分析系统

基于 Streamlit 构建的八字命理分析 Web 应用。

## ✨ 功能特性

- **八字排盘**: 根据出生日期、时间和地点准确计算八字命盘
- **真太阳时**: 根据经度自动调整真太阳时
- **综合分析**:
  - 基础命理分析
  - 日主与十神分析
  - 大运流年分析
- **AI智能问答**: 关于命运的问题获取AI生成的洞察
- **八字相合**: 分析两人之间的关系合盘
- **用户管理**: 注册、登录和积分系统
- **历史记录**: 保存和管理您的八字分析历史

## 🛠️ 技术栈

- **框架**: Streamlit
- **语言**: Python 3.8+
- **数据库**: SQLite
- **API**: 兼容OpenAI的API

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/BaZi.git
cd BaZi

# 安装依赖
pip install -r requirements.txt
```

## ⚙️ 配置

在项目根目录创建 `.env` 文件，包含以下环境变量：

```env
# API配置
BAZI_API_KEY=your-api-key-here
BAZI_API_BASE_URL=https://api.example.com/v1
BAZI_MODEL=your-model-name
```

## 🚀 运行应用

```bash
# 开发模式
streamlit run app.py

# 生产模式
streamlit run app.py --server.headless=true
```

## 📖 使用方法

1. **注册/登录**: 创建账户或使用已有账户登录
2. **输入出生信息**: 输入出生日期、时间、性别和出生城市
3. **生成八字**: 点击"开始排盘"生成八字命盘
4. **查看分析**: 浏览基础分析和问答部分
5. **合盘分析**: 使用"八字相合"选项卡分析人际关系

## 📁 项目结构

```
BaZi/
├── app.py                 # 主Streamlit应用
├── bazi_core.py           # 核心八字计算逻辑
├── city_location.py       # 城市经度数据库
├── api_client.py          # AI分析的API客户端
├── user_manager.py        # 用户管理模块
├── prompt_builder.py      # AI提示词模板
├── requirements.txt       # 依赖列表
└── .streamlit/
    └── config.toml        # Streamlit配置
```

## 📄 许可证

本项目仅供个人使用。

## ⚠️ 免责声明

本应用仅供娱乐目的。所提供的命理分析不应被视为重要人生决策的专业建议。
