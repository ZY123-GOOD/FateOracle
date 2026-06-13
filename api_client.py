"""
八字分析API调用封装模块
支持OpenAI兼容格式的API（适用于Qwen等模型的中转API）
"""

import os
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass

# 尝试加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件
    print("[INFO] .env文件加载成功")
except ImportError:
    print("[警告] python-dotenv未安装，无法自动加载.env文件")
    print("建议安装: pip install python-dotenv")

# 尝试导入openai库
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[警告] openai库未安装，请执行: pip install openai")


@dataclass
class APIConfig:
    """API配置"""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"  # 默认OpenAI，可改为中转API地址
    model: str = "qwen-plus"  # 模型名称
    temperature: float = 0.7  # 温度参数
    max_tokens: int = 2000  # 最大输出长度
    timeout: int = 120  # 超时时间（秒）- 增加超时时间
    
    def __post_init__(self):
        """从环境变量加载默认值"""
        # 优先从环境变量读取
        env_key = os.getenv("BAZI_API_KEY", "")
        env_url = os.getenv("BAZI_API_BASE_URL", "")
        env_model = os.getenv("BAZI_API_MODEL", "")
        
        if env_key:
            self.api_key = env_key
        elif not self.api_key:
            self.api_key = ""
            
        if env_url:
            self.base_url = env_url
        elif not self.base_url or self.base_url == "https://api.openai.com/v1":
            # 如果没有设置环境变量且使用默认值，检查是否有其他配置
            pass
        
        # 确保base_url以/v1结尾
        if self.base_url and not self.base_url.endswith("/v1"):
            self.base_url = self.base_url.rstrip("/") + "/v1"
            
        if env_model:
            self.model = env_model


class BaziAnalyzer:
    """八字分析器 - 封装API调用"""

    def __init__(self, config: APIConfig = None):
        """
        初始化分析器
        
        Args:
            config: API配置，不提供时使用默认配置
        """
        if not HAS_OPENAI:
            raise ImportError("请先安装openai库: pip install openai")
        
        self.config = config or APIConfig()
        
        # 初始化OpenAI客户端
        self.client = openai.OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        
        # 导入prompt构建器
        from prompt_builder import BaziPromptBuilder
        self.prompt_builder = BaziPromptBuilder()

    def analyze_basic(self, bazi_result: Dict) -> str:
        """
        基础八字分析
        
        Args:
            bazi_result: 八字排盘结果
        
        Returns:
            分析结果文本
        """
        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_basic_analysis_prompt(bazi_result)
        
        return self._call_api(system_prompt, user_prompt)

    def analyze_fortune(self, bazi_result: Dict, period: str = "未来一年",
                        current_year: int = None) -> str:
        """
        运势预测分析
        
        Args:
            bazi_result: 八字排盘结果
            period: 预测时间段
            current_year: 当前年份
        
        Returns:
            分析结果文本
        """
        from datetime import datetime
        if current_year is None:
            current_year = datetime.now().year
        
        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_fortune_prompt(
            bazi_result, period, current_year
        )
        
        return self._call_api(system_prompt, user_prompt)

    def answer_question(self, bazi_result: Dict, question: str,
                        current_year: int = None,
                        conversation_history: List[Dict] = None) -> str:
        """
        回答用户问题（支持上下文记忆）

        Args:
            bazi_result: 八字排盘结果
            question: 用户问题
            current_year: 当前年份
            conversation_history: 对话历史 [{"question": ..., "answer": ...}, ...]

        Returns:
            回答文本
        """
        from datetime import datetime
        if current_year is None:
            current_year = datetime.now().year

        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_qa_prompt(
            bazi_result, question, current_year, conversation_history
        )

        return self._call_api(system_prompt, user_prompt)

    def _call_api(self, system_prompt: str, user_prompt: str,
                  retry_count: int = 2) -> str:
        """
        调用API
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            retry_count: 重试次数（建议不超过2次）
        
        Returns:
            API返回的分析结果
        """
        for attempt in range(retry_count):
            try:
                # 设置单次请求超时
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout
                )
                
                return response.choices[0].message.content
                
            except openai.APIConnectionError as e:
                error_msg = f"[错误] API连接失败: {e}"
                print(error_msg)
                if attempt < retry_count - 1:
                    print(f"  正在重试... ({attempt + 1}/{retry_count})")
                    time.sleep(1)
                else:
                    return f"[错误] API连接失败，请检查网络或API地址"
                    
            except openai.AuthenticationError as e:
                print(f"[错误] API认证失败: {e}")
                return f"[错误] API Key无效或已过期，请检查配置"
                
            except openai.RateLimitError as e:
                print(f"[错误] API请求频率超限: {e}")
                if attempt < retry_count - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"  等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    return f"[错误] API请求频率超限，请稍后再试"
                    
            except openai.APIError as e:
                print(f"[错误] API服务错误: {e}")
                if attempt < retry_count - 1:
                    print(f"  正在重试... ({attempt + 1}/{retry_count})")
                    time.sleep(1)
                else:
                    return f"[错误] API服务异常"
                    
            except Exception as e:
                print(f"[错误] 未知错误: {e}")
                return f"[错误] 发生未知错误: {str(e)[:100]}"
        
        return "[错误] API调用失败"

    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            True表示连接成功，False表示失败
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )
            print(f"[成功] API连接正常，模型: {self.config.model}")
            return True
        except Exception as e:
            print(f"[失败] API连接测试失败: {e}")
            return False


class BaziAnalysisService:
    """
    八字分析服务 - 整合排盘和分析
    提供一站式服务接口
    """

    def __init__(self, api_config: APIConfig = None):
        """
        初始化服务
        
        Args:
            api_config: API配置
        """
        # 导入排盘核心
        from bazi_core import BaziCore
        
        self.api_config = api_config or APIConfig()
        self.analyzer = None  # 延迟初始化，避免未安装openai时报错
        
    def _init_analyzer(self):
        """延迟初始化分析器"""
        if self.analyzer is None:
            self.analyzer = BaziAnalyzer(self.api_config)
        return self.analyzer

    def full_analysis(self, year: int, month: int, day: int,
                      hour: int, minute: int, gender: str,
                      city: str = None, longitude: float = 116.4) -> Dict:
        """
        完整分析流程
        
        Args:
            year, month, day, hour, minute: 出生时间
            gender: 性别
            city: 出生城市
            longitude: 出生地经度
        
        Returns:
            包含排盘结果和分析结果的字典
        """
        from bazi_core import BaziCore
        
        # 1. 排盘
        bazi = BaziCore(city=city, longitude=longitude)
        bazi_result = bazi.solar_to_bazi(year, month, day, hour, minute, gender)
        
        # 2. 分析
        analyzer = self._init_analyzer()
        analysis_result = analyzer.analyze_basic(bazi_result)
        
        return {
            "排盘结果": bazi_result,
            "分析结果": analysis_result
        }

    def fortune_analysis(self, year: int, month: int, day: int,
                         hour: int, minute: int, gender: str,
                         period: str = "未来一年",
                         city: str = None, longitude: float = 116.4) -> Dict:
        """
        运势预测分析
        
        Args:
            period: 预测时间段
        
        Returns:
            包含排盘和运势分析的字典
        """
        from bazi_core import BaziCore
        
        # 排盘
        bazi = BaziCore(city=city, longitude=longitude)
        bazi_result = bazi.solar_to_bazi(year, month, day, hour, minute, gender)
        
        # 运势分析
        analyzer = self._init_analyzer()
        analysis_result = analyzer.analyze_fortune(bazi_result, period)
        
        return {
            "排盘结果": bazi_result,
            "运势分析": analysis_result
        }

    def ask_question(self, year: int, month: int, day: int,
                     hour: int, minute: int, gender: str,
                     question: str,
                     city: str = None, longitude: float = 116.4,
                     conversation_history: List[Dict] = None) -> Dict:
        """
        问答分析（支持上下文记忆）

        Args:
            question: 用户问题
            conversation_history: 对话历史 [{"question": ..., "answer": ...}, ...]

        Returns:
            包含排盘和回答的字典
        """
        from bazi_core import BaziCore

        # 排盘
        bazi = BaziCore(city=city, longitude=longitude)
        bazi_result = bazi.solar_to_bazi(year, month, day, hour, minute, gender)

        # 回答问题（传入对话历史）
        analyzer = self._init_analyzer()
        answer = analyzer.answer_question(
            bazi_result, question,
            conversation_history=conversation_history
        )

        return {
            "排盘结果": bazi_result,
            "回答": answer
        }


# ========== 配置文件示例 ==========
CONFIG_EXAMPLE = """
# 八字分析API配置示例
# 将以下内容保存为 .env 文件或设置环境变量

# API Key（必填）
BAZI_API_KEY=your_api_key_here

# API地址（可选，用于中转API）
BAZI_API_BASE_URL=https://your-api-proxy.com/v1

# 或者在代码中直接配置：
config = APIConfig(
    api_key="your_api_key",
    base_url="https://your-api-proxy.com/v1",
    model="qwen-plus",
    temperature=0.7,
    max_tokens=2000
)
"""


def print_config_help():
    """打印配置帮助"""
    print("=" * 60)
    print("八字分析API配置说明")
    print("=" * 60)
    print(CONFIG_EXAMPLE)
    print("=" * 60)
    print("\n常用中转API示例：")
    print("  - OpenAI官方: https://api.openai.com/v1")
    print("  - 阿里云百炼: https://dashscope.aliyuncs.com/compatible-mode/v1")
    print("  - 其他中转: 根据服务商文档配置")
    print("=" * 60)


# ========== 测试 ==========
def test_api():
    """测试API调用"""
    from bazi_core import BaziCore
    
    print("=" * 60)
    print("八字分析API测试")
    print("=" * 60)
    
    # 检查配置
    api_key = os.getenv("BAZI_API_KEY", "")
    if not api_key:
        print("[警告] 未设置API Key")
        print("请设置环境变量 BAZI_API_KEY 或在代码中配置")
        print_config_help()
        return
    
    # 创建配置
    config = APIConfig()
    print(f"\nAPI地址: {config.base_url}")
    print(f"模型: {config.model}")
    
    # 创建分析器
    analyzer = BaziAnalyzer(config)
    
    # 测试连接
    print("\n正在测试API连接...")
    if not analyzer.test_connection():
        print("连接失败，请检查配置")
        return
    
    # 排盘
    print("\n正在排盘...")
    bazi = BaziCore(city="北京")
    bazi_result = bazi.solar_to_bazi(1990, 5, 15, 10, 30, "男")
    print(bazi.format_output(bazi_result))
    
    # 分析
    print("\n正在进行基础分析...")
    analysis = analyzer.analyze_basic(bazi_result)
    print("\n【分析结果】")
    print(analysis)
    
    print("=" * 60)


if __name__ == "__main__":
    test_api()