import streamlit as st
import os
import json
import re
import time  # 导入计时模块
import secrets
from openai import OpenAI

# --- 1. 初始化配置 ---
st.set_page_config(page_title="南大往事：真伪鉴别挑战", layout="centered", page_icon="🏛️")

client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

# --- 2. 样式美化 ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #1E3A8A; font-family: 'serif'; }
    div.stButton > button { width: auto; max-width: 400px; border-radius: 10px; height: 3em; background-color: #5C9EFF; color: white; transition: 0.3s; }
    div.stButton > button:hover { background-color: #4A86E8; transform: scale(1.02); }
    .stExpander { border: 1px solid #E0E0E0; border-radius: 10px; margin-bottom: 10px !important; }
    </style>
    """, unsafe_allow_html=True)


# --- 3. 核心逻辑函数 (提速优化版) ---
def generate_challenge():
    start_time = time.time()

    prompt = """
    你是南京大学校史与吴健雄研究专家。请生成5条关于“南京大学校史”或“吴健雄”的短事迹，每条30到50字左右，并严格满足以下要求：
    1. 其中**正好3条完全真实、2条完全虚构**，虚构的必须乍看合理但经不起严格考证。
    2. 真事迹应选取鲜为人知但确切的细节（如具体年份、地点、实验名称、学脉关联等），假事迹要巧妙扭曲真实细节（如改关键人物、机构、事件因果等）。
    3. 虚构条目必须能被了解过南大历史和吴健雄事迹的人一眼识破，但外行不易分辨。
    4. 严禁生成任何解释、开场白或结束语，**只输出一个严格符合JSON格式的对象**，格式如下：
    {"data": [{"content": "事迹文本", "is_real": true/false, "explanation": "对假事迹指出错误并纠正，对真事迹简要注明出处依据或补充背景信息"}]}
    5. 确保数组长度为5，且is_real字段恰好有3个true、2个false。不得多也不能少。
    """

    # 尝试次数
    max_retries = 2
    for i in range(max_retries):
        try:
            # 💡 关键修改：加入 timeout 参数，设置 15 秒超时
            response = client.chat.completions.create(
                model="deepseek-v4-flash",  
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                timeout=15.0  # 超过 15 秒没反应直接跳到 except
            )

            api_duration = time.time() - start_time
            raw_content = response.choices[0].message.content

            json_str = re.search(r'\{.*\}', raw_content, re.DOTALL).group(0)
            data = json.loads(json_str)["data"]

            print(f"⚡ 性能监控 | 第 {i + 1} 次尝试成功 | API 耗时: {api_duration:.2f} 秒")

            return data

        except Exception as e:
            print(f"⚠️ 第 {i + 1} 次尝试失败或超时: {str(e)}")
            if i < max_retries - 1:
                print("🔄 正在尝试重新连接...")
                time.sleep(1)  # 等 1 秒再试
            else:
                st.error("🚨 API 响应太慢或网络拥堵，请稍后再试。")
                return None


# --- 4. 主界面 ---
st.markdown("<h1 class='main-title'>🏛️ 南大往事：真伪鉴别挑战</h1>", unsafe_allow_html=True)
st.write("在下面 5 条表述中，藏着 **2 条 AI 编造的谎言**，你能识破吗？")

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

# 生成/重置按钮
if st.button("✨ 生成新挑战 / 刷新题目"):
    loading_texts = ["正在查阅档案馆资料...", "正在编造足以乱真的谎言..."]
    import random

    with st.spinner(f"🚀 {random.choice(loading_texts)}"):
        st.session_state.quiz_data = generate_challenge()
        st.session_state.submitted = False
        st.session_state.selected_indices = []
        if st.session_state.quiz_data:
            st.rerun()

# --- 5. 答题与解析 ---
if st.session_state.quiz_data:
    st.divider()

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            st.subheader("🕵️ 请勾选你认为【编造】的 2 条：")
            current_selections = []
            for i, item in enumerate(st.session_state.quiz_data):
                if st.checkbox(f"事迹 {i + 1}: {item['content']}", key=f"check_{i}"):
                    current_selections.append(i)
            
            st.markdown("""
            <style>
            /* 定位表单提交按钮 */
            div[data-testid="stFormSubmitButton"] > button {
                background-color: #FF3333 !important;  /* 默认红色 */
                color: white !important;               /* 文字白色 */
                border-radius: 10px !important;        /* 圆角 */
                height: 3em !important;                /* 高度 */
                transition: 0.3s !important;           /* 过渡效果 */
            }
            /* 提交按钮悬浮效果（加深红色） */
            div[data-testid="stFormSubmitButton"] > button:hover {
                background-color: #D92D2D !important;  /* 悬浮加深红色 */
                transform: scale(1.02) !important;     /* 轻微放大 */
            }
            </style>
            """, unsafe_allow_html=True)
            
            if st.form_submit_button("🔥 提交答案"):
                if len(current_selections) != 2:
                    st.warning("⚠️ yo~必须且只能选择 2 个你认为是谎言的选项哦！")
                else:
                    st.session_state.selected_indices = current_selections
                    st.session_state.submitted = True
                    st.rerun()
    else:
        # 显示结果逻辑
        correct_indices = [i for i, item in enumerate(st.session_state.quiz_data) if not item['is_real']]
        user_choice = st.session_state.selected_indices

        res_col, btn_col = st.columns([3, 1])

        with res_col:
            if set(user_choice) == set(correct_indices):
                st.success("🎉 哟！这么有实力~！")
                st.balloons()
            else:
                st.error("❌ 一定是题目太难了, 对不对[doge]")

        with btn_col:
            if st.button("🔄 再来一局"):
                st.session_state.quiz_data = None
                st.session_state.submitted = False
                st.session_state.selected_indices = []
                st.rerun()

        if set(user_choice) == set(correct_indices):
            import os  # 确保导入os用于生成凭证

            st.markdown(f"### 🏆 领奖凭证: `{secrets.token_hex(4).upper()}`")

        st.divider()
        st.subheader("📜 真相揭晓与深度解析")
        for i, item in enumerate(st.session_state.quiz_data):
            if item['is_real']:
                with st.expander(f"✅ 事迹 {i + 1}（属实）：{item['content'][:25]}..."):
                    st.write(f"**完整内容：** {item['content']}")
                    st.info(f"📚 **背景：** {item.get('explanation', '确有其事。')}")
            else:
                st.markdown(f"❌ :red[**事迹 {i + 1}（虚构）：{item['content']}**]")
                st.warning(f"🔎 **破绽所在：** {item.get('explanation', '这是虚构内容。')}")

else:
    st.info("👆 请点击上方按钮开启你的挑战之旅！")

# --- 6. 侧边栏 ---
with st.sidebar:
    st.markdown(
        f"""<div style="text-align: center; margin-bottom: 30px;">
            <img src="https://www.nju.edu.cn/images/logo.png" width="225" style="filter: brightness(0) saturate(100%) invert(23%) sepia(68%) saturate(1200%) hue-rotate(255deg) brightness(85%) contrast(95%);">
            </div>""", unsafe_allow_html=True)
    st.header("🎮 游戏规则")
    st.write("1. 题目由 Deepseek-V4-Flash 生成")
    st.write("2. 5 条事迹中只有 2 条是假的")
    st.write("3. 全部找对即可获得领奖凭证")
    st.divider()
    st.markdown(
        f"""<div style="text-align: center;">
        <img src="https://i.stardots.io/168423434010/StarDots_2026-02-11T16_07_21.6300Z_1499.png" width="100">
        <p style="margin-top: 10px; font-weight: bold; color: #5C9EFF;">本站由 柳穿鱼 创建</p>
        <p style="font-size: 0.8em; color: gray;">© 2026 NJU 星光集市</p>
        </div>""", unsafe_allow_html=True)

# --- 7. 底部提示（新增） ---
st.divider()
st.caption("⚠️ 内容由AI生成，请仔细甄别~")
