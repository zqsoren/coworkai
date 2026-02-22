"""
Data Visualization Skill（Layer 2 标准技能）
读取数据 -> 生成 Matplotlib 代码 -> 执行 -> 保存图片 -> 返回路径
"""

SKILL_NAME = "data_viz"
SKILL_DESCRIPTION = "数据可视化：读取 CSV/JSON 数据，生成图表并保存"


def run(data_path: str, chart_type: str = "bar",
        output_dir: str = "output", **kwargs) -> str:
    """
    生成数据可视化
    
    Args:
        data_path: 数据文件路径（CSV 或 JSON）
        chart_type: 图表类型（bar, line, pie, scatter, heatmap）
        output_dir: 输出目录
    """
    import os
    import json
    from datetime import datetime

    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")  # 非交互式后端
        import matplotlib.pyplot as plt
        
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError as e:
        return f"依赖缺失: {e}。请安装 pandas 和 matplotlib。"

    # 读取数据
    ext = os.path.splitext(data_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(data_path)
        elif ext == ".json":
            df = pd.read_json(data_path)
        else:
            return f"不支持的数据格式: {ext}。请使用 .csv 或 .json。"
    except Exception as e:
        return f"数据读取失败: {e}"

    # 生成图表
    fig, ax = plt.subplots(figsize=(10, 6))
    try:
        if chart_type == "bar":
            df.plot(kind="bar", ax=ax)
        elif chart_type == "line":
            df.plot(kind="line", ax=ax)
        elif chart_type == "pie":
            if len(df.columns) >= 2:
                df.set_index(df.columns[0])[df.columns[1]].plot(kind="pie", ax=ax, autopct="%1.1f%%")
            else:
                df.iloc[:, 0].value_counts().plot(kind="pie", ax=ax, autopct="%1.1f%%")
        elif chart_type == "scatter":
            if len(df.columns) >= 2:
                ax.scatter(df.iloc[:, 0], df.iloc[:, 1])
                ax.set_xlabel(df.columns[0])
                ax.set_ylabel(df.columns[1])
        elif chart_type == "heatmap":
            import seaborn as sns
            sns.heatmap(df.corr(), annot=True, ax=ax, cmap="YlOrRd")
        else:
            return f"不支持的图表类型: {chart_type}。支持: bar, line, pie, scatter, heatmap"
    except Exception as e:
        plt.close(fig)
        return f"图表生成失败: {e}"

    ax.set_title(f"数据可视化 - {chart_type.upper()}")
    plt.tight_layout()

    # 保存
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chart_{chart_type}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return f"图表已保存: {filepath}"
