"""
StockTools - 股票行情查询工具
提供实时股价查询能力，使用腾讯财经公开接口。
"""

from langchain_core.tools import tool
import requests


@tool
def get_realtime_stock_data(symbol_list: str) -> str:
    """获取A股实时行情数据。支持上海A股(sh)和深圳A股(sz)。
    
    Args:
        symbol_list: 股票代码列表，格式为"市场代码+股票代码"，多个用逗号分隔。
                     例如: "sh600519" (贵州茅台), "sz300315" (掌趣科技)
                     批量查询: "sz300315,sh600519"
                     - 上海A股前缀: sh (如 sh600519)
                     - 深圳A股前缀: sz (如 sz000001)
    
    Returns:
        包含股票名称、最新价、涨跌幅等信息的格式化文本
    """
    url = f"http://qt.gtimg.cn/q={symbol_list}"
    
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'gbk'
        
        stock_lines = response.text.strip().split(';')
        
        results = []
        for line in stock_lines:
            if not line.strip():
                continue
            
            try:
                data_string = line.split('"')[1]
                parts = data_string.split('~')
                
                if len(parts) > 32:
                    stock_name = parts[1]
                    stock_code = parts[2]
                    current_price = float(parts[3])
                    yesterday_close = float(parts[4])
                    today_open = float(parts[5])
                    change_amount = float(parts[31])
                    change_percent = float(parts[32])
                    turnover_rate = float(parts[38]) if len(parts) > 38 else 0.0
                    
                    change_direction = "📈" if change_percent >= 0 else "📉"
                    
                    result = f"""{change_direction} {stock_name} ({stock_code})
  当前价格: ¥{current_price:.2f}
  今日开盘: ¥{today_open:.2f}
  昨日收盘: ¥{yesterday_close:.2f}
  涨跌金额: {change_amount:+.2f} 元
  涨跌幅: {change_percent:+.2f}%
  换手率: {turnover_rate:.2f}%"""
                    
                    results.append(result)
            except (IndexError, ValueError) as e:
                continue
        
        if results:
            return "\n\n".join(results)
        else:
            return f"未找到股票数据，请检查股票代码格式是否正确。\n示例: sh600519 (上海A股), sz000001 (深圳A股)"
    
    except requests.Timeout:
        return "请求超时，请稍后重试。"
    except requests.RequestException as e:
        return f"网络请求失败: {str(e)}"
    except Exception as e:
        return f"获取行情失败: {str(e)}"


@tool
def search_stock_by_name(keyword: str) -> str:
    """根据关键词搜索股票代码。输入股票名称或拼音缩写，返回匹配的股票列表。
    
    Args:
        keyword: 股票名称关键词或拼音缩写，如"茅台"、"贵州茅台"、"mt"
    
    Returns:
        匹配的股票代码和名称列表
    """
    stock_mapping = {
        "贵州茅台": "sh600519", "茅台": "sh600519", "mt": "sh600519",
        "掌趣科技": "sz300315", "掌趣": "sz300315",
        "平安银行": "sz000001", "平安": "sz000001",
        "中国平安": "sh601318",
        "招商银行": "sh600036", "招行": "sh600036",
        "工商银行": "sh601398", "工行": "sh601398",
        "建设银行": "sh601939", "建行": "sh601939",
        "中国石油": "sh601857", "中石油": "sh601857",
        "中国石化": "sh600028", "中石化": "sh600028",
        "比亚迪": "sz002594", "byd": "sz002594",
        "宁德时代": "sz300750", "宁德": "sz300750",
        "腾讯控股": "hk00700", "腾讯": "hk00700",
        "阿里巴巴": "hk09988", "阿里": "hk09988",
        "美团": "hk03690",
        "京东": "hk09618",
        "小米": "hk01810",
        "百度": "hk09888",
        "网易": "hk09999",
        "五粮液": "sz000858",
        "泸州老窖": "sz000568",
        "洋河股份": "sz002304",
        "海天味业": "sh603288",
        "隆基绿能": "sh601012", "隆基": "sh601012",
        "通威股份": "sh600438",
        "阳光电源": "sz300274",
        "中芯国际": "sh688981",
        "韦尔股份": "sh603501",
        "立讯精密": "sz002475",
        "歌尔股份": "sz002241",
        "京东方A": "sz000725",
        "TCL科技": "sz000100",
        "格力电器": "sz000651", "格力": "sz000651",
        "美的集团": "sz000333", "美的": "sz000333",
        "海尔智家": "sh600690", "海尔": "sh600690",
        "中国中免": "sh601888",
        "上海机场": "sh600009",
        "中国国航": "sh601111",
        "南方航空": "sh600029",
        "东方航空": "sh600115",
    }
    
    keyword_lower = keyword.lower()
    matches = []
    
    for name, code in stock_mapping.items():
        if keyword_lower in name.lower() or name in keyword:
            matches.append(f"• {name}: {code}")
    
    if matches:
        result = f"找到 {len(matches)} 个匹配结果:\n" + "\n".join(matches[:10])
        result += "\n\n💡 使用 get_realtime_stock_data 工具查询实时价格，传入股票代码即可。"
        return result
    else:
        return f"未找到匹配 '{keyword}' 的股票。\n请尝试输入完整的股票名称，或直接使用股票代码查询。\n示例: sh600519 (上海A股), sz000001 (深圳A股)"


STOCK_TOOLS = [get_realtime_stock_data, search_stock_by_name]
