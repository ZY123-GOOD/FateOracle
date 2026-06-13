"""
八字分析Web界面 - Streamlit应用
"""

import streamlit as st
import datetime
import os
import json
from typing import Optional

# 导入核心模块
from bazi_core import BaziCore
from city_location import get_all_cities, city_to_longitude
from api_client import BaziAnalyzer, APIConfig, BaziAnalysisService
from user_manager import UserManager

# 设置页面配置
st.set_page_config(
    page_title="八字排盘分析",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    .result-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        margin-bottom: 20px;
    }
    .sizhu-display {
        font-size: 24px;
        font-weight: bold;
        letter-spacing: 4px;
    }
    .shishen-tag {
        background: rgba(255,255,255,0.2);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
    }
    .config-section {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
    }
    .history-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
    }
    .history-item:hover {
        background: #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

# 全局状态管理
if 'bazi_result' not in st.session_state:
    st.session_state['bazi_result'] = None
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None
if 'qa_result' not in st.session_state:
    st.session_state['qa_result'] = None
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None
if 'user_manager' not in st.session_state:
    st.session_state['user_manager'] = UserManager()
if 'qa_history' not in st.session_state:
    st.session_state['qa_history'] = []
if 'current_bazi_history_id' not in st.session_state:
    st.session_state['current_bazi_history_id'] = None

MAX_HISTORY_COUNT = 50  # 最大历史记录数


def get_api_config() -> APIConfig:
    """获取当前的API配置（从环境变量）"""
    return APIConfig()


def has_api_key() -> bool:
    """检查是否配置了API Key（从环境变量）"""
    return bool(os.getenv("BAZI_API_KEY", ""))


def is_logged_in() -> bool:
    """检查用户是否已登录"""
    return st.session_state['current_user'] is not None


def get_remaining_credits() -> int:
    """获取用户剩余次数"""
    if not is_logged_in():
        return 0
    return st.session_state['user_manager'].check_credits(
        st.session_state['current_user']['id']
    )


def consume_credit(action_type: str) -> bool:
    """
    消耗一次问答机会
    
    Args:
        action_type: 'basic_analysis' 或 'qa'
    
    Returns:
        是否成功
    """
    if not is_logged_in():
        return False
    success = st.session_state['user_manager'].consume_credit(
        st.session_state['current_user']['id'],
        action_type
    )
    if success:
        # 更新缓存的用户信息
        user = st.session_state['user_manager'].get_user_info(
            st.session_state['current_user']['id']
        )
        if user:
            st.session_state['current_user'] = user
    return success


def main():
    """主函数"""
    # 标题
    st.title("🔮 八字排盘分析系统")
    st.markdown("根据出生时间和地点，进行专业的八字命理分析")
    
    # 侧边栏：用户认证 + 历史记录
    with st.sidebar:
        st.header("🔐 用户中心")
        
        if is_logged_in():
            # 已登录状态
            user = st.session_state['current_user']
            st.success(f"✓ 欢迎, {user['username']}")
            st.info(f"剩余次数: {user['credits']}次")
            
            if st.button("退出登录"):
                st.session_state['current_user'] = None
                st.session_state['qa_history'] = []
                st.session_state['bazi_result'] = None
                st.session_state['analysis_result'] = None
                st.session_state['current_bazi_history_id'] = None
                st.rerun()
        else:
            # 未登录状态 - 显示登录/注册选项卡
            auth_tab1, auth_tab2 = st.tabs(["登录", "注册"])
            
            with auth_tab1:
                login_username = st.text_input("用户名", key="login_username")
                login_password = st.text_input("密码", type="password", key="login_password")
                
                if st.button("登录"):
                    success, msg, user = st.session_state['user_manager'].login(
                        login_username, login_password
                    )
                    if success:
                        st.session_state['current_user'] = user
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            
            with auth_tab2:
                reg_username = st.text_input("用户名", key="reg_username")
                reg_email = st.text_input("邮箱", key="reg_email")
                reg_password = st.text_input("密码", type="password", key="reg_password")
                reg_password2 = st.text_input("确认密码", type="password", key="reg_password2")
                
                if st.button("注册"):
                    if reg_password != reg_password2:
                        st.error("两次输入的密码不一致")
                    else:
                        success, msg = st.session_state['user_manager'].register(
                            reg_username, reg_password, reg_email
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
        
        st.divider()
        
        # 历史排盘记录
        st.header("📜 排盘历史")
        
        if is_logged_in():
            history = st.session_state['user_manager'].get_bazi_history(
                st.session_state['current_user']['id'],
                limit=MAX_HISTORY_COUNT
            )
            
            if history:
                st.caption(f"共 {len(history)} 条记录")
                
                for record in history:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            if st.button(
                                f"{record['birth_time']} | {record['city']}",
                                key=f"history_btn_{record['id']}",
                                help="点击加载此记录",
                                use_container_width=True
                            ):
                                # 加载历史记录
                                bazi_result = json.loads(record['bazi_result'])
                                st.session_state['bazi_result'] = bazi_result
                                st.session_state['analysis_result'] = record['analysis_result']
                                st.session_state['current_bazi_history_id'] = record['id']
                                # 加载关联的问答历史
                                qa_history = st.session_state['user_manager'].get_qa_history_by_bazi(
                                    st.session_state['current_user']['id'],
                                    record['id']
                                )
                                st.session_state['qa_history'] = [
                                    {'question': qa['question'], 'answer': qa['answer']}
                                    for qa in qa_history
                                ]
                                st.rerun()
                        with col2:
                            if st.button(
                                "🗑️",
                                key=f"delete_btn_{record['id']}",
                                help="删除此记录"
                            ):
                                st.session_state['user_manager'].delete_bazi_history(
                                    st.session_state['current_user']['id'],
                                    record['id']
                                )
                                st.success("已删除")
                                st.rerun()
            else:
                st.info("暂无排盘记录")
                
            # 检查历史记录数量
            total_count = st.session_state['user_manager'].get_bazi_history_count(
                st.session_state['current_user']['id']
            )
            if total_count >= MAX_HISTORY_COUNT:
                st.warning(f"⚠️ 历史记录已达{MAX_HISTORY_COUNT}条上限，请删除部分记录")
        else:
            st.info("登录后查看排盘历史")
    
    # 主内容区：出生信息输入 + 排盘结果
    if st.session_state['bazi_result']:
        # 显示排盘结果
        display_bazi_result(st.session_state['bazi_result'])
        
        # 分析选项卡
        tab1, tab2 = st.tabs(["基础分析", "命理问答"])
        
        with tab1:
            display_basic_analysis()
        
        with tab2:
            display_qa()
    else:
        # 显示出生信息输入表单
        display_birth_info_form()


def display_birth_info_form():
    """出生信息输入表单"""
    st.subheader("📅 出生信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 日期选择
        birth_date = st.date_input(
            "出生日期",
            value=datetime.date(1990, 5, 15),
            min_value=datetime.date(1900, 1, 1),
            max_value=datetime.date.today()
        )
        
        # 时间选择
        birth_time = st.time_input("出生时间", value=datetime.time(10, 30))
        
        # 性别选择
        gender = st.radio("性别", ["男", "女"], index=0)
    
    with col2:
        # 城市选择
        city = st.text_input(
            "输入出生城市名称",
            value="北京",
            placeholder="例如: 北京、上海、深圳、朔州...",
            key="city_input"
        ).strip()
        
        # 验证城市是否存在
        if city:
            longitude = city_to_longitude(city)
            if longitude:
                st.success(f"✓ 已识别城市: {city} (经度: {longitude}°)")
            else:
                st.warning(f"⚠ 未找到城市 '{city}'，请检查名称是否正确")
                city = None
        else:
            st.info("请输入出生城市名称")
            city = None
    
    # 排盘按钮
    if st.button("开始排盘", type="primary"):
        if not city:
            st.warning("请先输入出生城市")
        else:
            with st.spinner("正在排盘..."):
                try:
                    bazi = BaziCore(city=city)
                    result = bazi.solar_to_bazi(
                        birth_date.year,
                        birth_date.month,
                        birth_date.day,
                        birth_time.hour,
                        birth_time.minute,
                        gender
                    )
                    st.session_state['bazi_result'] = result
                    st.session_state['analysis_result'] = None
                    st.session_state['qa_history'] = []
                    st.session_state['current_bazi_history_id'] = None
                    
                    # 保存到历史记录（如果已登录）
                    if is_logged_in():
                        bazi_result_json = json.dumps(result, ensure_ascii=False)
                        st.session_state['user_manager'].save_bazi_result(
                            st.session_state['current_user']['id'],
                            result['出生时间'],
                            gender,
                            city,
                            bazi_result_json,
                            None
                        )
                    
                    st.success("排盘成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"排盘失败: {e}")


def display_bazi_result(result: dict):
    """显示排盘结果"""
    st.subheader("📋 八字排盘结果")
    
    # 基本信息卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("出生时间", result['出生时间'])
    with col2:
        st.metric("出生地", result['出生地'])
    with col3:
        st.metric("真太阳时", result['真太阳时'])
    with col4:
        st.metric("性别", result['性别'])
    
    # 四柱展示
    st.markdown("---")
    st.subheader("【四柱八字】")
    
    sizhu = result["四柱"]
    cols = st.columns(4)
    
    for i, (zhu_name, zhu_info) in enumerate(sizhu.items()):
        with cols[i]:
            st.markdown(f"""
            <div class="result-card">
                <div style="font-size: 14px; opacity: 0.8;">{zhu_name}</div>
                <div class="sizhu-display">{zhu_info['干']}{zhu_info['支']}</div>
                <div style="margin-top: 8px;">
                    <span class="shishen-tag">{result['十神'][zhu_name]['天干十神']}</span>
                    <span class="shishen-tag">{result['十神'][zhu_name]['地支十神']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # 日主信息
    st.markdown(f"**日主**: {result['日干']} ({get_wuxing(result['日干'])}命)")
    
    # 十神详情
    st.markdown("---")
    st.subheader("【十神分析】")
    for zhu_name, zhu_info in result["十神"].items():
        cg_str = ", ".join([f"{c['藏干']}({c['十神']})" for c in zhu_info["地支藏干"]])
        st.write(f"**{zhu_name}**: 天干{zhu_info['天干十神']} | 地支{zhu_info['地支十神']} | 藏干[{cg_str}]")
    
    # 大运
    st.markdown("---")
    st.subheader("【大运】")
    dayun = result["大运"]
    st.write(f"起运年龄: **{dayun['起运岁数']}岁** | 方向: **{dayun['顺逆']}行**")
    
    # 展示更多大运（8个）
    dy_cols = st.columns(4)
    for i, dy in enumerate(dayun["大运列表"][:8]):
        with dy_cols[i % 4]:
            st.info(f"""
            **{dy['大运']}**
            {dy['起运年龄']}~{dy['止运年龄']}岁
            (约{dy['起运年份']}年起)
            """)
    
    # 流年分析
    st.markdown("---")
    st.subheader("【大运流年】")
    
    current_year = datetime.datetime.now().year
    from bazi_core import LiunianAnalysis
    liunian = LiunianAnalysis.calc_liunian(result, current_year)
    
    st.write(f"**{current_year}年流年柱:** {liunian['流年柱']}")
    
    if liunian['当前大运']:
        st.write(f"**当前大运:** {liunian['当前大运']['大运']} "
                f"({liunian['当前大运']['起运年龄']}~{liunian['当前大运']['止运年龄']}岁)")
    
    st.markdown("**与四柱关系:**")
    for zhu_name, relation in liunian['与四柱关系'].items():
        st.write(f"- {zhu_name}: 天干{relation['流年天干关系']} | 地支{relation['流年地支关系']}")


def get_wuxing(tian_gan: str) -> str:
    """获取天干的五行属性"""
    wuxing_map = {
        '甲': '木', '乙': '木',
        '丙': '火', '丁': '火',
        '戊': '土', '己': '土',
        '庚': '金', '辛': '金',
        '壬': '水', '癸': '水'
    }
    return wuxing_map.get(tian_gan, '')


def display_basic_analysis():
    """基础分析"""
    st.subheader("🧠 基础命理分析")
    
    if st.session_state['analysis_result']:
        st.write(st.session_state['analysis_result'])
    else:
        if has_api_key():
            # 检查登录状态
            if not is_logged_in():
                st.warning("⚠️ 请先登录以使用AI分析功能")
                st.info("💡 新用户注册即送10次问答机会")
            else:
                credits = get_remaining_credits()
                if credits <= 0:
                    st.warning("⚠️ 您的问答次数已用完")
                else:
                    if st.button("🔮 解答"):
                        # 消耗次数
                        if consume_credit('basic_analysis'):
                            with st.spinner("正在调用AI分析..."):
                                try:
                                    service = BaziAnalysisService(api_config=get_api_config())
                                    result = service.full_analysis(
                                        year=int(st.session_state['bazi_result']['出生时间'][:4]),
                                        month=int(st.session_state['bazi_result']['出生时间'][5:7]),
                                        day=int(st.session_state['bazi_result']['出生时间'][8:10]),
                                        hour=int(st.session_state['bazi_result']['出生时间'][11:13]),
                                        minute=int(st.session_state['bazi_result']['出生时间'][14:16]),
                                        gender=st.session_state['bazi_result']['性别'],
                                        city=st.session_state['bazi_result'].get('出生地')
                                    )
                                    st.session_state['analysis_result'] = result['分析结果']
                                    st.write(result['分析结果'])
                                    
                                    # 保存分析结果到历史记录
                                    if is_logged_in() and st.session_state['current_bazi_history_id']:
                                        st.session_state['user_manager'].save_bazi_result(
                                            st.session_state['current_user']['id'],
                                            st.session_state['bazi_result']['出生时间'],
                                            st.session_state['bazi_result']['性别'],
                                            st.session_state['bazi_result']['出生地'],
                                            json.dumps(st.session_state['bazi_result'], ensure_ascii=False),
                                            result['分析结果']
                                        )
                                    
                                    st.success(f"✓ 分析完成，剩余次数: {get_remaining_credits()}次")
                                except Exception as e:
                                    st.error(f"分析失败: {e}")
                        else:
                            st.error("无法消耗次数，请重试")
        else:
            st.warning("⚠️ 未配置API Key，无法进行AI分析")
            st.info("请设置环境变量 `BAZI_API_KEY` 或在代码中配置API")


MAX_CONVERSATION_ROUNDS = 10  # 最大对话轮数

def display_qa():
    """问答功能 - 支持多轮对话（最多10轮）"""
    st.subheader("❓ 命理问答")

    # 检查登录状态
    if not is_logged_in():
        st.warning("⚠️ 请先登录以使用问答功能")
        st.info("💡 新用户注册即送10次问答机会")
        return

    # 检查是否达到对话上限
    if len(st.session_state['qa_history']) >= MAX_CONVERSATION_ROUNDS:
        st.warning(f"⚠️ 已达到{MAX_CONVERSATION_ROUNDS}轮对话上限，请刷新页面重新开始")
        # 显示历史但不允许继续
        for i, qa_pair in enumerate(st.session_state['qa_history']):
            with st.container():
                st.markdown(f"**问：** {qa_pair['question']}")
                st.markdown(f"**答：** {qa_pair['answer']}")
                st.divider()
        st.info("💡 点击页面右上角菜单 → 刷新页面，或按 F5")
        return

    # 检查剩余次数
    credits = get_remaining_credits()
    st.caption(f"💬 账户剩余次数: {credits}次 | 本轮对话: {len(st.session_state['qa_history']) + 1}/{MAX_CONVERSATION_ROUNDS}")

    if credits <= 0:
        st.warning("⚠️ 您的问答次数已用完")
        # 仍可查看历史
        for i, qa_pair in enumerate(st.session_state['qa_history']):
            with st.container():
                st.markdown(f"**问：** {qa_pair['question']}")
                st.markdown(f"**答：** {qa_pair['answer']}")
                st.divider()
        return

    # 显示问答历史（只读）
    for i, qa_pair in enumerate(st.session_state['qa_history'][:-1]):
        with st.container():
            st.markdown(f"**问：** {qa_pair['question']}")
            st.markdown(f"**答：** {qa_pair['answer']}")
            st.divider()
    
    # 最后一个问答对（可编辑）
    if st.session_state['qa_history']:
        last_qa = st.session_state['qa_history'][-1]
        # 显示已回答的问题（只读）
        st.markdown(f"**问：** {last_qa['question']}")
        st.markdown(f"**答：** {last_qa['answer']}")
        st.divider()
        # 添加新问题输入框
        new_question = st.text_area(
            "请输入您的问题", 
            placeholder="例如：我的事业运势如何？适合从事什么行业？",
            key=f"new_question_{len(st.session_state['qa_history'])}"
        )
        
        if has_api_key():
            if st.button("🔮 解答", key=f"ask_btn_{len(st.session_state['qa_history'])}"):
                if new_question.strip():
                    # 消耗次数
                    if consume_credit('qa'):
                        with st.spinner("正在解答..."):
                            try:
                                service = BaziAnalysisService(api_config=get_api_config())
                                result = service.ask_question(
                                    year=int(st.session_state['bazi_result']['出生时间'][:4]),
                                    month=int(st.session_state['bazi_result']['出生时间'][5:7]),
                                    day=int(st.session_state['bazi_result']['出生时间'][8:10]),
                                    hour=int(st.session_state['bazi_result']['出生时间'][11:13]),
                                    minute=int(st.session_state['bazi_result']['出生时间'][14:16]),
                                    gender=st.session_state['bazi_result']['性别'],
                                    question=new_question,
                                    city=st.session_state['bazi_result'].get('出生地'),
                                    conversation_history=st.session_state['qa_history']
                                )
                                # 添加新问答到历史
                                st.session_state['qa_history'].append({
                                    'question': new_question,
                                    'answer': result['回答']
                                })
                                
                                # 保存问答记录到数据库
                                if is_logged_in() and st.session_state['current_bazi_history_id']:
                                    st.session_state['user_manager'].save_qa_history(
                                        st.session_state['current_user']['id'],
                                        st.session_state['current_bazi_history_id'],
                                        new_question,
                                        result['回答']
                                    )
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"分析失败: {e}")
                    else:
                        st.error("无法消耗次数，请重试")
                else:
                    st.warning("请输入问题")
        else:
            st.warning("⚠️ 未配置API Key，无法进行AI问答")
    else:
        # 第一个问题
        first_question = st.text_area(
            "请输入您的问题", 
            placeholder="例如：我的事业运势如何？适合从事什么行业？",
            key="first_question"
        )
        
        if has_api_key():
            if st.button("🔮 解答", key="first_ask_btn"):
                if first_question.strip():
                    # 消耗次数
                    if consume_credit('qa'):
                        with st.spinner("正在解答..."):
                            try:
                                service = BaziAnalysisService(api_config=get_api_config())
                                result = service.ask_question(
                                    year=int(st.session_state['bazi_result']['出生时间'][:4]),
                                    month=int(st.session_state['bazi_result']['出生时间'][5:7]),
                                    day=int(st.session_state['bazi_result']['出生时间'][8:10]),
                                    hour=int(st.session_state['bazi_result']['出生时间'][11:13]),
                                    minute=int(st.session_state['bazi_result']['出生时间'][14:16]),
                                    gender=st.session_state['bazi_result']['性别'],
                                    question=first_question,
                                    city=st.session_state['bazi_result'].get('出生地'),
                                    conversation_history=None
                                )
                                # 添加到历史
                                st.session_state['qa_history'].append({
                                    'question': first_question,
                                    'answer': result['回答']
                                })
                                
                                # 保存问答记录到数据库
                                if is_logged_in() and st.session_state['current_bazi_history_id']:
                                    st.session_state['user_manager'].save_qa_history(
                                        st.session_state['current_user']['id'],
                                        st.session_state['current_bazi_history_id'],
                                        first_question,
                                        result['回答']
                                    )
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"分析失败: {e}")
                    else:
                        st.error("无法消耗次数，请重试")
                else:
                    st.warning("请输入问题")
        else:
            st.warning("⚠️ 未配置API Key，无法进行AI问答")


if __name__ == "__main__":
    main()