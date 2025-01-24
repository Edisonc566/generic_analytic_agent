import streamlit as st
import time
from datetime import datetime

# 导入后端函数
from back_end_code import (
    check_symbol_exists,
    get_klines_data,
    calculate_indicators,
    analyze_trend,
    get_market_sentiment,
    generate_trading_plan,
    get_ai_analysis,
    generate_tweet,
    TIMEFRAMES  # 导入常量
)


# 设置页面标题和说明
st.title("加密货币多周期分析系统")
st.markdown("""
### 使用说明
- 输入交易对代码（例如：BTC、ETH、PEPE等）
- 系统将自动分析多个时间周期的市场状态
- 提供专业的趋势分析和预测
- 分析整体市场情绪
- 提供详细的交易计划
- 生成多种风格的分析总结推文
""")


# 主界面
# 创建两列布局
col1, col2 = st.columns([2, 1])

with col1:
    # 用户输入代币代码
    symbol = st.text_input("输入代币代码（例如：BTC、ETH、PEPE）", value="BTC", label_visibility="hidden").upper()

with col2:
    # 分析按钮
    analyze_button = st.button("开始分析", type="primary")

# 添加分割线
st.markdown("---")

if analyze_button:
    # 检查代币是否存在
    if check_symbol_exists(symbol):
        with st.spinner(f'正在分析 {symbol} 的市场状态...'):
            all_timeframe_analysis = {}

            # 获取各个时间周期的数据并分析
            for tf, info in TIMEFRAMES.items():
                df = get_klines_data(symbol, info['interval'])
                if df is not None:
                    df = calculate_indicators(df)
                    analysis = analyze_trend(df)
                    all_timeframe_analysis[info['name']] = analysis

            # 显示当前价格
            current_price = all_timeframe_analysis['日线']['current_price']
            st.metric(
                label=f"{symbol}/USDT 当前价格",
                value=f"${current_price:,.8f}" if current_price < 0.1 else f"${current_price:,.2f}"
            )

            # 生成交易计划
            trading_plan = generate_trading_plan(symbol)

            # 获取并显示 AI 分析
            st.subheader("多周期分析报告")
            analysis = get_ai_analysis(symbol, all_timeframe_analysis, trading_plan)
            st.markdown(analysis)

            # 添加市场情绪
            market_sentiment = get_market_sentiment()
            st.markdown("---")
            st.subheader("整体市场情绪")
            st.write(market_sentiment)

            # 生成推文
            st.markdown("---")
            st.subheader("多风格推文建议")

            analysis_summary = f"{analysis}\n市场情绪：{market_sentiment}"

            # 定义所有风格
            styles = {
                "女生风格": "女生",
                "交易员风格": "交易员",
                "分析师风格": "分析师",
                "失败交易员风格": "失败交易员"
            }

            # 创建两列布局来显示推文
            col1, col2 = st.columns(2)

            # 生成并显示所有风格的推文
            for i, (style_name, style) in enumerate(styles.items()):
                tweet = generate_tweet(symbol, analysis_summary, style)
                # 在左列显示前两个风格
                if i < 2:
                    with col1:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label="",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}"
                        )
                # 在右列显示后两个风格
                else:
                    with col2:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label="",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}"
                        )

            # 添加时间戳
            st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.error(f"错误：{symbol}USDT 交易对在 Binance 上不存在，请检查代币代码是否正确。")

# 自动刷新选项移到侧边栏
with st.sidebar:
    st.subheader("设置")
    auto_refresh = st.checkbox("启用自动刷新")
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔（秒）", 30, 300, 60)
        st.caption(f"每 {refresh_interval} 秒自动刷新一次")
        time.sleep(refresh_interval)
        st.experimental_rerun()

    st.markdown("---")
    st.subheader("注意事项")
    st.write("请确保您的分析仅供参考，不构成投资建议。加密货币市场风险较大，请谨慎决策。")

# 添加页脚
st.markdown("---")
st.caption("免责声明：本分析仅供参考，不构成投资建议。加密货币市场风险较大，请谨慎决策。")