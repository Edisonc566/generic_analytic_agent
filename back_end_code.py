import pandas as pd
import numpy as np
import requests
from datetime import datetime
import streamlit as st
import time
import anthropic

# graph TD
#     A[check_symbol_exists] --> B[get_klines_data]
#     B --> C[calculate_indicators]
#     C --> D[analyze_trend]
#     D --> E[get_ai_analysis]
#     F[get_market_sentiment] --> E
#     G[generate_trading_plan] --> E

# 设置 Claude API 配置
CLAUDE_API_KEY: str = st.secrets["CLAUDE_API_KEY"]

client = anthropic.Client(api_key=CLAUDE_API_KEY)
claude_model = "claude-3-opus-20240229"  # claude_model="claude-3-5-sonnet-20241022"
# Binance API 端点
BINANCE_API_URL = "https://api.binance.com/api/v3"

# 定义时间周期
TIMEFRAMES = {
    "5m": {"interval": "5m", "name": "5分钟"},
    "15m": {"interval": "15m", "name": "15分钟"},
    "1h": {"interval": "1h", "name": "1小时"},
    "4h": {"interval": "4h", "name": "4小时"},
    "1d": {"interval": "1d", "name": "日线"}
}

def check_symbol_exists(symbol):
    """检查交易对是否存在"""
    try:
        info_url = f"{BINANCE_API_URL}/exchangeInfo"
        response = requests.get(info_url, timeout=10)
        response.raise_for_status()
        symbols = [s['symbol'] for s in response.json()['symbols']]
        return f"{symbol}USDT" in symbols
    except Exception as e:
        st.error(f"检查交易对时发生错误: {str(e)}")
        return False

def get_klines_data(symbol, interval, limit=200):
    """获取K线数据"""
    try:
        klines_url = f"{BINANCE_API_URL}/klines"
        params = {
            "symbol": f"{symbol}USDT",
            "interval": interval,
            "limit": limit
        }
        response = requests.get(klines_url, params=params)
        response.raise_for_status()

        # 处理K线数据
        df = pd.DataFrame(response.json(), columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # 转换数据类型
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df
    except Exception as e:
        st.error(f"获取K线数据时发生错误: {str(e)}")
        return None

def calculate_indicators(df):
    """计算技术指标"""
    # 计算MA20
    df['ma20'] = df['close'].rolling(window=20).mean()

    # 计算BOLL指标
    df['boll_mid'] = df['close'].rolling(window=20).mean()
    df['boll_std'] = df['close'].rolling(window=20).std()
    df['boll_up'] = df['boll_mid'] + 2 * df['boll_std']
    df['boll_down'] = df['boll_mid'] - 2 * df['boll_std']

    # 计算MA20趋势
    df['ma20_trend'] = df['ma20'].diff().rolling(window=5).mean()

    # MACD指标
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # RSI指标
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df

def analyze_trend(df):
    """分析趋势"""
    current_price = df['close'].iloc[-1]
    ma20_trend = "上升" if df['ma20_trend'].iloc[-1] > 0 else "下降"

    # BOLL带支撑阻力
    boll_up = df['boll_up'].iloc[-1]
    boll_mid = df['boll_mid'].iloc[-1]
    boll_down = df['boll_down'].iloc[-1]

    # [新增] MACD分析
    macd = df['macd'].iloc[-1]
    signal = df['signal'].iloc[-1]
    macd_hist = df['macd_hist'].iloc[-1]
    macd_trend = "多头" if macd > signal else "空头"
    macd_strength = abs(macd_hist)
    
    # [新增] RSI分析
    rsi = df['rsi'].iloc[-1]
    rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"
    
    # 检查RSI背离
    price_trend = "上升" if df['close'].iloc[-1] > df['close'].iloc[-5] else "下降"
    rsi_trend = "上升" if df['rsi'].iloc[-1] > df['rsi'].iloc[-5] else "下降"
    rsi_divergence = "背离" if price_trend != rsi_trend else "一致"

    return {
        "current_price": current_price,
        "ma20_trend": ma20_trend,
        "support_resistance": {
            "strong_resistance": boll_up,
            "middle_line": boll_mid,
            "strong_support": boll_down
        },
        "macd_analysis": {
                "trend": macd_trend,
                "strength": macd_strength,
                "current_macd": macd,
                "current_signal": signal,
                "histogram": macd_hist
            },
        "rsi_analysis": {
                "current_value": rsi,
                "status": rsi_status,
                "divergence": rsi_divergence}
    }

def get_market_sentiment():
    """获取市场情绪，基于上涨和下跌的币种比例"""
    try:
        info_url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(info_url)
        response.raise_for_status()
        data = response.json()
        usdt_pairs = [item for item in data if item['symbol'].endswith('USDT')]
        total_pairs = len(usdt_pairs)
        if total_pairs == 0:
            return "无法获取USDT交易对数据"

        up_pairs = [item for item in usdt_pairs if float(item['priceChangePercent']) > 0]
        up_percentage = (len(up_pairs) / total_pairs) * 100

        # 分类情绪
        if up_percentage >= 80:
            sentiment = "极端乐观"
        elif up_percentage >= 60:
            sentiment = "乐观"
        elif up_percentage >= 40:
            sentiment = "中性"
        elif up_percentage >= 20:
            sentiment = "悲观"
        else:
            sentiment = "极端悲观"

        return f"市场情绪：{sentiment}（上涨交易对占比 {up_percentage:.2f}%）"
    except Exception as e:
        return f"获取市场情绪时发生错误: {str(e)}"

def generate_trading_plan(symbol):
    """生成交易计划"""
    try:
        prompt = f"""
        你是一名专业的加密货币交易员，请为交易对 {symbol}/USDT 提供一个详细的顺应趋势的交易计划。包括但不限于入场点、止损点、目标价位和资金管理策略。
        """
        response = client.messages.create(
            model=claude_model,  
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"交易计划生成失败: {str(e)}"

def generate_tweet(symbol, analysis_summary, style):
    """生成推文内容"""
    try:
        style_prompts = {
            "女生": "少女风",
            "交易员": "专业简洁",
            "分析师": "严谨专业",
            "失败交易员": "讽刺幽默"
        }
        
        prompt = f"{style_prompts.get(style, '')}风格，{symbol}/USDT分析推文(价格/趋势/建议，限280字):\n{analysis_summary}"
        
        response = client.messages.create(
            model=claude_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        tweet = response.content[0].text.strip()
        return tweet[:277] + "..." if len(tweet) > 280 else tweet
    except Exception as e:
        return f"推文生成失败: {str(e)}"

def get_ai_analysis(symbol, analysis_data, trading_plan):
    """获取 AI 分析结果"""
    try:
        # 准备多周期分析数据
        prompt = f"""
        作为一位专业的加密货币分析师，请基于以下{symbol}的多周期分析数据提供详细的市场报告：

        各周期趋势分析：
        {analysis_data}

        详细交易计划：
        {trading_plan}

        请提供以下分析（使用markdown格式）：

        ## 市场综述
        [在多周期分析框架下的整体判断]

        ## 趋势分析
        - 短期趋势、多空力量、超买超卖情况（5分钟-15分钟）：
        - 中期趋势、多空力量、超买超卖情况（1小时-4小时）：
        - 长期趋势、多空力量、超买超卖情况（日线）：
        - 趋势协同性分析：

        ## 关键价位
        - 主要阻力位：
        - 主要支撑位：
        - 当前价格位置分析：

        ## 未来目标预测
        1. 24小时目标：
        2. 3天目标：
        3. 7天目标：

        ## 操作建议
        - 短线操作：
        - 中线布局：
        - 风险提示：

        请确保分析专业、客观，并注意不同时间框架的趋势、多空力量、超买超卖情况关系。
        """
        response = client.messages.create(
            model=claude_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"AI 分析生成失败: {str(e)}"
