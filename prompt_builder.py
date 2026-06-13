"""
八字分析Prompt模板构建模块
将排盘结果格式化为结构化prompt，供大模型分析
"""

from typing import Dict, Optional, List


class BaziPromptBuilder:
    """八字分析Prompt构建器"""

    # 系统提示词模板
    SYSTEM_PROMPT = """你是一位专业的八字命理分析师，精通四柱命理学、五行生克、十神关系、大运流年等知识。

你的分析应该：
1. 基于传统命理学理论，客观、专业地解读
2. 结合五行强弱、十神配置、格局特点进行分析
3. 提供有建设性的建议，而非宿命论式的断言
4. 语言通俗易懂，避免过于玄奥的术语堆砌
5. 尊重用户隐私，不涉及敏感话题

注意：命理分析仅供参考，人生发展取决于个人努力和选择。"""

    # 基础分析prompt模板
    BASIC_ANALYSIS_TEMPLATE = """请对以下八字进行基础命理分析：

【基本信息】
出生时间：{birth_time}
出生地点：{birth_place}
性别：{gender}
真太阳时：{true_solar_time}

【四柱八字】
年柱：{year_zhu}（{year_shishen}）
月柱：{month_zhu}（{month_shishen}）
日柱：{day_zhu}（日主：{day_gan}）
时柱：{hour_zhu}（{hour_shishen}）

【五行分析】
日主：{day_gan}（{day_wuxing}）
五行分布：{wuxing_distribution}

【十神配置】
{shishen_detail}

【大运】
起运年龄：{qiyun_age}岁
大运方向：{dayun_direction}
前几步大运：{dayun_list}

请从以下几个方面进行分析：
1. **日主强弱**：分析日主五行在八字中的强弱程度
2. **格局特点**：判断可能的格局类型（如正官格、偏财格等）
3. **性格特质**：基于十神配置分析性格倾向
4. **事业方向**：适合的行业和发展方向
5. **财运分析**：财运特点和理财建议
6. **感情婚姻**：感情运势和婚姻特点
7. **健康注意**：需要关注的健康方面"""

    # 运势预测prompt模板
    FORTUNE_TEMPLATE = """请对以下八字进行{period}运势预测分析：

【基本信息】
出生时间：{birth_time}
性别：{gender}
日主：{day_gan}（{day_wuxing}）

【四柱八字】
年柱：{year_zhu}
月柱：{month_zhu}
日柱：{day_zhu}
时柱：{hour_zhu}

【大运流年】
当前大运：{current_dayun}（{dayun_age_range}）
{period}流年：{liunnian_list}

请分析{period}的：
1. **整体运势**：运势总体走向和特点
2. **事业运势**：工作、事业方面的机遇和挑战
3. **财运走势**：财务收入、投资方面的运势
4. **感情运势**：人际关系、感情婚姻方面
5. **健康运势**：身体状况和需要注意的方面
6. **关键节点**：重要时间节点和转折点
7. **建议提醒**：趋吉避凶的建议"""

    # 问答prompt模板（支持对话历史）
    QA_TEMPLATE = """用户问题：{question}

【八字信息】
出生时间：{birth_time}
性别：{gender}
四柱：{year_zhu} {month_zhu} {day_zhu} {hour_zhu}
日主：{day_gan}（{day_wuxing}）
当前大运：{current_dayun}
当前年份：{current_year}年

{conversation_history}
请基于以上八字信息和对话历史，回答用户的问题。回答要：
1. 结合命理理论，给出专业分析
2. 注意与前面的对话上下文关联，保持回答的连贯性
3. 提供具体、有针对性的建议
4. 语言通俗易懂，避免玄奥术语
5. 保持客观中立，不做绝对断言"""

    def __init__(self):
        pass

    def build_basic_analysis_prompt(self, bazi_result: Dict) -> str:
        """
        构建基础分析prompt
        
        Args:
            bazi_result: 八字排盘结果字典
        
        Returns:
            格式化后的prompt字符串
        """
        # 提取关键信息
        sizhu = bazi_result["四柱"]
        shishen = bazi_result["十神"]
        dayun = bazi_result["大运"]
        
        # 计算五行分布
        wuxing_dist = self._calc_wuxing_distribution(bazi_result)
        
        # 格式化十神详情
        shishen_detail = self._format_shishen_detail(shishen)
        
        # 格式化大运列表
        dayun_list = self._format_dayun_list(dayun["大运列表"][:5])
        
        # 构建prompt
        prompt = self.BASIC_ANALYSIS_TEMPLATE.format(
            birth_time=bazi_result["出生时间"],
            birth_place=bazi_result.get("出生地", "未知"),
            gender=bazi_result["性别"],
            true_solar_time=bazi_result.get("真太阳时", bazi_result["出生时间"]),
            year_zhu=bazi_result["年柱"],
            year_shishen=shishen["年柱"]["天干十神"],
            month_zhu=bazi_result["月柱"],
            month_shishen=shishen["月柱"]["天干十神"],
            day_zhu=bazi_result["日柱"],
            day_gan=bazi_result["日干"],
            hour_zhu=bazi_result["时柱"],
            hour_shishen=shishen["时柱"]["天干十神"],
            day_wuxing=self._get_wuxing(bazi_result["日干"]),
            wuxing_distribution=wuxing_dist,
            shishen_detail=shishen_detail,
            qiyun_age=dayun["起运岁数"],
            dayun_direction=dayun["顺逆"],
            dayun_list=dayun_list
        )
        
        return prompt

    def build_fortune_prompt(self, bazi_result: Dict, period: str = "未来一年",
                             current_year: int = None) -> str:
        """
        构建运势预测prompt
        
        Args:
            bazi_result: 八字排盘结果
            period: 预测时间段（如"未来一年"、"2024年"等）
            current_year: 当前年份（用于计算流年）
        
        Returns:
            格式化后的prompt
        """
        from datetime import datetime
        
        if current_year is None:
            current_year = datetime.now().year
        
        sizhu = bazi_result["四柱"]
        dayun = bazi_result["大运"]
        
        # 计算当前大运
        current_dayun = self._get_current_dayun(dayun, bazi_result, current_year)
        
        # 计算流年
        liunnian_list = self._calc_liunnian(current_year, 5)
        
        prompt = self.FORTUNE_TEMPLATE.format(
            period=period,
            birth_time=bazi_result["出生时间"],
            gender=bazi_result["性别"],
            day_gan=bazi_result["日干"],
            day_wuxing=self._get_wuxing(bazi_result["日干"]),
            year_zhu=bazi_result["年柱"],
            month_zhu=bazi_result["月柱"],
            day_zhu=bazi_result["日柱"],
            hour_zhu=bazi_result["时柱"],
            current_dayun=current_dayun["大运"] if current_dayun else "未起运",
            dayun_age_range=f"{current_dayun['起运年龄']}~{current_dayun['止运年龄']}岁" if current_dayun else "",
            liunnian_list=liunnian_list
        )
        
        return prompt

    def build_qa_prompt(self, bazi_result: Dict, question: str,
                        current_year: int = None,
                        conversation_history: List[Dict] = None) -> str:
        """
        构建问答prompt

        Args:
            bazi_result: 八字排盘结果
            question: 用户问题
            current_year: 当前年份
            conversation_history: 对话历史 [{"question": ..., "answer": ...}, ...]

        Returns:
            格式化后的prompt
        """
        from datetime import datetime

        if current_year is None:
            current_year = datetime.now().year

        dayun = bazi_result["大运"]
        current_dayun = self._get_current_dayun(dayun, bazi_result, current_year)

        # 格式化对话历史
        history_str = self._format_conversation_history(conversation_history)

        prompt = self.QA_TEMPLATE.format(
            question=question,
            birth_time=bazi_result["出生时间"],
            gender=bazi_result["性别"],
            year_zhu=bazi_result["年柱"],
            month_zhu=bazi_result["月柱"],
            day_zhu=bazi_result["日柱"],
            hour_zhu=bazi_result["时柱"],
            day_gan=bazi_result["日干"],
            day_wuxing=self._get_wuxing(bazi_result["日干"]),
            current_dayun=current_dayun["大运"] if current_dayun else "未起运",
            current_year=current_year,
            conversation_history=history_str
        )

        return prompt

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.SYSTEM_PROMPT

    # ========== 辅助方法 ==========

    def _get_wuxing(self, gan: str) -> str:
        """获取天干五行"""
        WUXING_GAN = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
            "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
        }
        return WUXING_GAN.get(gan, "未知")

    def _calc_wuxing_distribution(self, bazi_result: Dict) -> str:
        """计算五行分布"""
        WUXING_GAN = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
            "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
        }
        WUXING_ZHI = {
            "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
            "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"
        }
        
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        
        sizhu = bazi_result["四柱"]
        for zhu in ["年柱", "月柱", "日柱", "时柱"]:
            gan = sizhu[zhu]["干"]
            zhi = sizhu[zhu]["支"]
            wuxing_count[WUXING_GAN.get(gan, "土")] += 1
            wuxing_count[WUXING_ZHI.get(zhi, "土")] += 1
        
        # 格式化输出
        result = []
        for wx, count in wuxing_count.items():
            if count > 0:
                result.append(f"{wx}{count}个")
        
        return "、".join(result)

    def _format_shishen_detail(self, shishen: Dict) -> str:
        """格式化十神详情"""
        lines = []
        for zhu_name, zhu_info in shishen.items():
            cg_str = "、".join([f"{c['藏干']}({c['十神']})" for c in zhu_info["地支藏干"]])
            lines.append(f"{zhu_name}: 天干{zhu_info['天干十神']}，地支{zhu_info['地支十神']}, 藏干[{cg_str}]")
        return "\n".join(lines)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史对话）"

        lines = []
        for i, qa in enumerate(history, 1):
            lines.append(f"【第{i}轮问答】")
            lines.append(f"问：{qa.get('question', '')}")
            lines.append(f"答：{qa.get('answer', '')}")
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def _format_dayun_list(self, dayun_list: List) -> str:
        """格式化大运列表"""
        return "、".join([f"{d['大运']}({d['起运年龄']}岁)" for d in dayun_list])

    def _get_current_dayun(self, dayun: Dict, bazi_result: Dict, current_year: int) -> Optional[Dict]:
        """获取当前大运"""
        # 从出生年份推算当前年龄
        birth_year = int(bazi_result["出生时间"].split("-")[0])
        current_age = current_year - birth_year
        
        for dy in dayun["大运列表"]:
            if current_age >= dy["起运年龄"] and current_age < dy["止运年龄"]:
                return dy
        
        return None

    def _calc_liunnian(self, start_year: int, count: int) -> str:
        """计算流年干支"""
        TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        
        result = []
        for i in range(count):
            year = start_year + i
            gan_idx = (year - 4) % 10
            zhi_idx = (year - 4) % 12
            result.append(f"{year}年{TIANGAN[gan_idx]}{DIZHI[zhi_idx]}")
        
        return "、".join(result)


# ========== 测试 ==========
def test_prompt_builder():
    """测试Prompt构建"""
    from bazi_core import BaziCore
    
    # 创建排盘结果
    bazi = BaziCore(city="北京")
    result = bazi.solar_to_bazi(1990, 5, 15, 10, 30, "男")
    
    # 构建prompt
    builder = BaziPromptBuilder()
    
    print("=" * 60)
    print("【系统提示词】")
    print(builder.get_system_prompt())
    print("=" * 60)
    
    print("\n【基础分析Prompt】")
    print(builder.build_basic_analysis_prompt(result))
    print("=" * 60)
    
    print("\n【运势预测Prompt】")
    print(builder.build_fortune_prompt(result, "2024年", 2024))
    print("=" * 60)
    
    print("\n【问答Prompt】")
    print(builder.build_qa_prompt(result, "我的事业运势如何？适合从事什么行业？", 2024))


if __name__ == "__main__":
    test_prompt_builder()